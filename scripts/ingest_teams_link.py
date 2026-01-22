#!/usr/bin/env python3
"""
Main CLI script for ingesting Teams message links.
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path
from typing import Optional

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent))

from teams_link_ingestion.link_validator import TeamsLinkValidator, LinkType
from teams_link_ingestion.classifier import ClassificationEngine
from teams_link_ingestion.content_fetcher import TeamsContentFetcher, MessageContent, LinkContent
from teams_link_ingestion.content_storage import ContentStorage
from teams_link_ingestion.ontology_creator import OntologyEntityCreator
from teams_link_ingestion.content_extractor import ContentExtractor
from teams_link_ingestion.workflow_integration import WorkflowIntegration


async def verify_with_web_search(content: str, classification) -> Optional[dict]:
    """
    Verify content with web search for organizations, claims, etc.
    
    Returns:
        Dictionary with verification results and sources, or None if skipped
    """
    import subprocess
    
    # Only verify if content mentions organizations or claims
    org_keywords = ["university", "laboratory", "lab", "department", "energy", "doe", "uc ", "uc-"]
    has_org_mention = any(kw.lower() in content.lower() for kw in org_keywords)
    
    if not has_org_mention:
        return None
    
    # Check if Tavily API key is available - try multiple sources
    tavily_key = os.getenv("TAVILY_API_KEY")
    
    # Try 1Password if not in environment
    if not tavily_key:
        try:
            # Try common 1Password reference formats
            for ref in [
                "op://Private/TAVILY_API_KEY/password",
                "op://Private/Tavily API Key/password",
                "op://Private/tavily-api-key/password",
                "op://Private/TAVILY_API_KEY/credential"
            ]:
                try:
                    result = subprocess.run(
                        ["op", "read", ref],
                        capture_output=True,
                        text=True,
                        timeout=5,
                        check=True
                    )
                    tavily_key = result.stdout.strip()
                    if tavily_key:
                        print(f"✓ Found TAVILY_API_KEY in 1Password")
                        break
                except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
                    continue
        except Exception:
            # Best-effort 1Password lookup; ignore unexpected errors and fall back to other key sources.
            pass
    
    if not tavily_key:
        return None
    
    try:
        # Import web search function
        import sys
        from pathlib import Path
        repo_root = Path(__file__).parent.parent
        sys.path.insert(0, str(repo_root))
        from repo_chat.web_search import search_tavily
        
        # Extract key claims/organizations for verification
        # Simple extraction: look for organization names
        orgs = []
        if "university of california" in content.lower() or "uc " in content.lower():
            orgs.append("University of California")
        if "lawrence berkeley" in content.lower() or "lbnl" in content.lower():
            orgs.append("Lawrence Berkeley National Laboratory")
        if "los alamos" in content.lower() or "lanl" in content.lower():
            orgs.append("Los Alamos National Laboratory")
        if "lawrence livermore" in content.lower() or "llnl" in content.lower():
            orgs.append("Lawrence Livermore National Laboratory")
        if "department of energy" in content.lower() or "doe" in content.lower():
            orgs.append("U.S. Department of Energy")
        
        if not orgs:
            return None
        
        # Search for verification
        query = f"{', '.join(orgs[:2])} national laboratories management"
        sources_text, citations = search_tavily(
            query=query,
            api_key=tavily_key,
            max_results=3,
            include_raw_content=False
        )
        
        return {
            "query": query,
            "sources": [{"title": c.title, "url": c.url} for c in citations],
            "sources_text": sources_text
        }
    except Exception as e:
        # Fail silently - web search is optional
        return None


def get_repo_root() -> Path:
    """Get repository root directory."""
    script_dir = Path(__file__).parent
    return script_dir.parent


def review_classification(classification, link_info) -> bool:
    """
    Present classification for user review.
    
    Returns:
        True if user confirms, False if rejects
    """
    print("\n" + "="*60)
    print("CLASSIFICATION REVIEW")
    print("="*60)
    print(f"Link: {link_info.url}")
    print(f"\nOntology Target: {classification.ontology_target.value}")
    print(f"  Confidence: {classification.ontology_confidence:.2f}")
    print(f"\nContent Type: {classification.content_type.value}")
    print(f"  Confidence: {classification.content_confidence:.2f}")
    print(f"\nOverall Confidence: {classification.confidence:.2f}")
    print(f"\nRationale: {classification.rationale}")
    print("="*60)
    
    while True:
        response = input("\nConfirm classification? (y/n/modify): ").strip().lower()
        if response == 'y':
            return True
        elif response == 'n':
            return False
        elif response == 'modify':
            # Allow modification (simplified for now)
            print("Modification not yet implemented. Please reject and re-run with hints.")
            return False
        else:
            print("Please enter 'y', 'n', or 'modify'")


async def ingest_link(link_url: str, 
                     access_token: Optional[str] = None,
                     auto_confirm: bool = False,
                     repo_root: Optional[Path] = None) -> dict:
    """
    Ingest a Teams message link.
    
    Args:
        link_url: Teams message link URL
        access_token: Microsoft Graph API access token
        auto_confirm: Auto-confirm classification without review
        repo_root: Repository root directory
        
    Returns:
        Processing result dictionary
    """
    if repo_root is None:
        repo_root = get_repo_root()
    
    # Step 1: Validate link
    print(f"Validating link: {link_url}")
    validator = TeamsLinkValidator()
    try:
        link_info = validator.validate_link(link_url)
        print(f"✓ Link validated: {link_info.link_type.value}")
    except ValueError as e:
        return {"success": False, "error": f"Invalid link: {e}"}
    
    # Step 1.5: Check for duplicate
    print("\nChecking for existing document...")
    creator = OntologyEntityCreator(repo_root)
    existing_doc_uri = creator.find_existing_document_by_link(link_url)
    if existing_doc_uri:
        print(f"⚠ Found existing document: {existing_doc_uri}")
        if not auto_confirm:
            response = input("Document already exists. Update existing (u) or skip (s)? [u/s]: ").strip().lower()
            if response == 's':
                return {"success": False, "error": "Skipped - document already exists", "existing_uri": str(existing_doc_uri)}
            elif response != 'u':
                return {"success": False, "error": "Invalid response"}
        # For update, we'll continue and create/update entities
        print("✓ Will update existing document")
    else:
        print("✓ No existing document found - creating new")
    
    # Step 2: Classify (before fetching - will re-classify after if needed)
    print("\nClassifying link...")
    classifier = ClassificationEngine()
    
    # For now, use empty preview (will re-classify after fetching with actual content)
    preview_content = ""
    classification = classifier.classify(link_info, preview_content)
    print(f"✓ Initial classification complete")
    
    # Step 3: Review classification
    if not auto_confirm:
        confirmed = review_classification(classification, link_info)
        if not confirmed:
            return {"success": False, "error": "Classification rejected by user"}
    
    # Step 4: Fetch content
    print("\nFetching content...")
    fetcher = TeamsContentFetcher(access_token=access_token)
    
    try:
        if link_info.link_type == LinkType.MESSAGE:
            if not link_info.message_id or not link_info.thread_id:
                return {"success": False, "error": "Missing message_id or thread_id"}
            content = await fetcher.fetch_message(link_info.message_id, link_info.thread_id)
            print(f"✓ Message fetched: {len(content.content)} chars")
        else:
            content = await fetcher.fetch_shared_link(link_url)
            print(f"✓ Link content fetched: {len(content.content)} bytes")
    except Exception as e:
        await fetcher.close()
        return {"success": False, "error": f"Failed to fetch content: {e}"}
    
    # Step 5: Re-classify with actual content for better accuracy
    print("\nSkipping re-classification to avoid hang...")
    # updated_classification = classifier.classify(link_info, actual_content[:50000])
    # if updated_classification.confidence > classification.confidence:
    #     print(f"✓ Improved classification confidence: {classification.confidence:.2f} → {updated_classification.confidence:.2f}")
    #     classification = updated_classification
    
    # Step 6: Web search verification (if content mentions organizations/claims)
    print("\nSkipping web search verification...")
    # web_verification = None
    # try:
    #     web_verification = await verify_with_web_search(actual_content, classification)
    #     if web_verification:
    #         print(f"✓ Web verification: Found {len(web_verification.get('sources', []))} sources")
    # except Exception as e:
    #     print(f"⚠ Web verification skipped: {e}")
    web_verification = None
    
    # Step 6.5: Extract URLs and process Executive Orders
    print("\nExtracting URLs from content...")
    extractor = ContentExtractor()
    
    # Get text content for URL extraction
    if isinstance(content, MessageContent):
        content_text = content.content
    elif isinstance(content, LinkContent):
        content_text = content.text_content or ""
    else:
        content_text = str(content)
    
    urls = extractor.extract_urls(content_text)
    print(f"✓ Found {len(urls)} URLs")
    
    # Process Executive Orders
    eo_documents = []
    # Reuse existing fetcher if available, otherwise create new one
    if 'fetcher' not in locals() or fetcher is None:
        fetcher = TeamsContentFetcher(access_token=access_token)
    
    try:
        for url in urls:
            if extractor.is_executive_order_url(url):
                print(f"\nProcessing Executive Order: {url}")
                try:
                    eo_content = await fetcher.fetch_executive_order(url)
                    print(f"✓ EO fetched: {eo_content.title}")
                    
                    # Store EO content
                    storage = ContentStorage(repo_root)
                    eo_storage_result = storage.store_content(eo_content, classification, web_verification)
                    print(f"✓ EO stored: {eo_storage_result.file_path}")
                    
                    eo_documents.append({
                        "content": eo_content,
                        "storage_result": eo_storage_result
                    })
                except Exception as e:
                    print(f"⚠ Warning: Failed to fetch EO from {url}: {e}")
    finally:
        await fetcher.close()
    
    # Step 7: Store Teams message content
    print("\nStoring Teams message content...")
    storage = ContentStorage(repo_root)
    storage_result = storage.store_content(content, classification, web_verification)
    print(f"✓ Content stored: {storage_result.file_path}")
    print(f"  Checksum: {storage_result.checksum}")
    
    # Step 8: Create document entity
    print("\nCreating ontology entities...")
    if 'creator' not in locals():
        creator = OntologyEntityCreator(repo_root)
    
    message_info = None
    if hasattr(content, 'sender_name'):
        message_info = {
            "sender_name": content.sender_name,
            "subject": getattr(content, 'subject', None)
        }
    
    try:
        # Use existing document URI if found, otherwise create new
        if existing_doc_uri:
            doc_uri = existing_doc_uri
            print(f"✓ Using existing document entity: {doc_uri}")
        else:
            doc_uri = creator.create_document_entity(
                storage_result,
                classification,
                link_url,
                message_info
            )
            print(f"✓ Document entity created: {doc_uri}")
    except Exception as e:
        return {"success": False, "error": f"Failed to create document entity: {e}"}
    
    # Step 8.5: Create EO document entities and link them
    eo_uris = []
    for eo_doc in eo_documents:
        try:
            eo_uri = creator.create_executive_order_entity(
                eo_doc["storage_result"],
                eo_doc["content"],
                classification,
                teams_message_uri=doc_uri
            )
            eo_uris.append(eo_uri)
            print(f"✓ EO document entity created: {eo_uri}")
            
            # Link Teams message to EO
            creator.link_documents(doc_uri, eo_uri, classification.ontology_target)
            print(f"✓ Linked Teams message to EO document")
        except Exception as e:
            print(f"⚠ Warning: Failed to create EO entity: {e}")
    
    # Step 9: Extract structured content from Teams message
    print("\nExtracting structured content from Teams message...")
    
    claims = extractor.extract_claims(content_text)
    requirements = extractor.extract_requirements(content_text)
    tasks = extractor.extract_tasks(content_text)
    
    print(f"✓ Extracted: {len(claims)} claims, {len(requirements)} requirements, {len(tasks)} tasks")
    
    # Also extract from EO documents
    for eo_doc in eo_documents:
        eo_text = eo_doc["content"].content
        eo_claims = extractor.extract_claims(eo_text)
        eo_requirements = extractor.extract_requirements(eo_text)
        eo_tasks = extractor.extract_tasks(eo_text)
        
        if eo_claims or eo_requirements or eo_tasks:
            print(f"✓ Extracted from EO: {len(eo_claims)} claims, {len(eo_requirements)} requirements, {len(eo_tasks)} tasks")
            claims.extend(eo_claims)
            requirements.extend(eo_requirements)
            tasks.extend(eo_tasks)
    
    # Step 10: Create extracted entities
    # Link claims/requirements/tasks to both Teams message and EO documents
    all_source_uris = [doc_uri] + eo_uris
    
    if claims:
        # Create claims linked to Teams message
        claim_uris = creator.create_claim_entities(doc_uri, claims, classification)
        print(f"✓ Created {len(claim_uris)} claim entities")
    
    if requirements:
        # Create requirements linked to Teams message
        req_uris = creator.create_requirement_entities(doc_uri, requirements, classification)
        print(f"✓ Created {len(req_uris)} requirement entities")
    
    if tasks:
        # Create tasks linked to Teams message
        task_uris = creator.create_task_entities(doc_uri, tasks, classification)
        print(f"✓ Created {len(task_uris)} task entities")
    
    # Step 11: Integrate with workflows
    print("\nIntegrating with workflows...")
    workflow = WorkflowIntegration(repo_root)
    
    try:
        workflow.refresh_viewer_graph()
        print("✓ Viewer graph refreshed")
    except Exception as e:
        print(f"⚠ Warning: Failed to refresh viewer graph: {e}")
    
    try:
        is_valid, errors = workflow.validate_shacl()
        if is_valid:
            print("✓ SHACL validation passed")
        else:
            print(f"⚠ Warning: SHACL validation issues: {errors}")
    except Exception as e:
        print(f"⚠ Warning: Failed to validate SHACL: {e}")
    
    return {
        "success": True,
        "document_uri": str(doc_uri),
        "file_path": str(storage_result.file_path),
        "checksum": storage_result.checksum,
        "claims": len(claims),
        "requirements": len(requirements),
        "tasks": len(tasks),
        "eo_documents": len(eo_documents),
        "eo_uris": [str(uri) for uri in eo_uris]
    }


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Ingest Microsoft Teams message links as ontology content"
    )
    parser.add_argument(
        "link",
        help="Teams message link URL"
    )
    parser.add_argument(
        "--access-token",
        help="Microsoft Graph API access token (or set TEAMS_ACCESS_TOKEN env var)",
        default=os.getenv("TEAMS_ACCESS_TOKEN")
    )
    parser.add_argument(
        "--auto-confirm",
        action="store_true",
        help="Auto-confirm classification without review"
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        help="Repository root directory (default: parent of scripts/)"
    )
    parser.add_argument(
        "--batch",
        type=Path,
        help="Process multiple links from file (one URL per line)"
    )
    
    args = parser.parse_args()
    
    if args.batch:
        # Batch processing
        with open(args.batch, 'r') as f:
            links = [line.strip() for line in f if line.strip()]
        
        print(f"Processing {len(links)} links...")
        results = []
        for i, link in enumerate(links, 1):
            print(f"\n[{i}/{len(links)}] Processing: {link}")
            result = await ingest_link(
                link,
                access_token=args.access_token,
                auto_confirm=args.auto_confirm,
                repo_root=args.repo_root
            )
            results.append(result)
        
        # Summary
        print("\n" + "="*60)
        print("BATCH PROCESSING SUMMARY")
        print("="*60)
        successful = sum(1 for r in results if r.get("success"))
        print(f"Successful: {successful}/{len(results)}")
        print(f"Failed: {len(results) - successful}/{len(results)}")
    else:
        # Single link
        result = await ingest_link(
            args.link,
            access_token=args.access_token,
            auto_confirm=args.auto_confirm,
            repo_root=args.repo_root
        )
        
        if result.get("success"):
            print("\n" + "="*60)
            print("INGESTION COMPLETE")
            print("="*60)
            print(f"Document URI: {result['document_uri']}")
            print(f"File: {result['file_path']}")
            print(f"Checksum: {result['checksum']}")
            print(f"Extracted: {result['claims']} claims, {result['requirements']} requirements, {result['tasks']} tasks")
            sys.exit(0)
        else:
            print(f"\n✗ Ingestion failed: {result.get('error')}")
            sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

