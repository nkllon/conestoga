"""
Conestoga - A project with ontology management tools and GCP integration.

This is the main entry point for the Conestoga application.
"""

import os

from rdflib import Graph, Literal, Namespace
from rdflib.namespace import RDF, RDFS

from conestoga.config import load_configuration


def main():
    """Main application entry point."""
    # Load environment variables
    load_configuration()

    print("🚀 Conestoga - Ontology Management & Cloud Tools")
    print("=" * 50)

    # Check environment configuration
    check_environment()

    # Demonstrate RDF functionality
    demonstrate_rdf()

    print("\n✅ Application initialized successfully!")
    print("\n🎮 Starting Conestoga Game...")
    print("=" * 50)

    from conestoga.game.runner import main as game_main

    game_main()


def check_environment():
    """Check and display environment configuration."""
    print("\n📋 Environment Configuration:")

    # Check for GCP configuration
    gcp_creds = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    gcp_project = os.getenv("GCP_PROJECT_ID")
    gcs_bucket = os.getenv("GCS_BUCKET_NAME")

    if gcp_creds:
        print(f"  ✓ GCP Credentials: {gcp_creds}")
    if gcp_project:
        print(f"  ✓ GCP Project ID: {gcp_project}")
    if gcs_bucket:
        print(f"  ✓ GCS Bucket: {gcs_bucket}")

    # Check for 1Password configuration
    op_token = os.getenv("OP_SERVICE_ACCOUNT_TOKEN")
    op_host = os.getenv("OP_CONNECT_HOST")

    if op_token:
        print("  ✓ 1Password Service Account configured")
    if op_host:
        print(f"  ✓ 1Password Connect Host: {op_host}")

    if not any([gcp_creds, gcp_project, gcs_bucket, op_token, op_host]):
        print("  ℹ️  No environment variables configured (copy .env.example to .env)")


def demonstrate_rdf():
    """Demonstrate RDF/ontology capabilities."""
    print("\n📚 RDF Graph Demonstration:")

    # Create a new RDF graph
    g = Graph()

    # Define a namespace for our ontology
    EX = Namespace("http://example.org/")

    # Add some triples to the graph
    g.add((EX.Conestoga, RDF.type, EX.Project))
    g.add((EX.Conestoga, RDFS.label, Literal("Conestoga Ontology Management")))
    g.add((EX.Conestoga, EX.hasFeature, Literal("RDF Support")))
    g.add((EX.Conestoga, EX.hasFeature, Literal("OWL Reasoning")))
    g.add((EX.Conestoga, EX.hasFeature, Literal("GCP Integration")))

    print(f"  ✓ Created RDF graph with {len(g)} triples")
    print("\n  Sample triples:")
    for s, p, o in list(g)[:3]:
        print(f"    {s.split('/')[-1]} -> {p.split('/')[-1]} -> {o}")


if __name__ == "__main__":
    main()
