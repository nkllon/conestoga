"""
Example: Google Cloud Storage Integration

This example demonstrates how to use Google Cloud Storage with the Conestoga project.
"""

import os
from dotenv import load_dotenv
from google.cloud import storage


def list_buckets():
    """List all GCS buckets in the configured project."""
    load_dotenv()
    
    # Initialize GCS client
    try:
        client = storage.Client()
        
        print("📦 Available GCS Buckets:")
        for bucket in client.list_buckets():
            print(f"  - {bucket.name}")
    except Exception as e:
        print(f"❌ Error accessing GCS: {e}")
        print("💡 Make sure GOOGLE_APPLICATION_CREDENTIALS is set in your .env file")


def upload_rdf_to_gcs(graph_data: str, bucket_name: str, blob_name: str, content_type: str = 'application/rdf+xml'):
    """
    Upload RDF data to Google Cloud Storage.
    
    Args:
        graph_data: RDF data as string
        bucket_name: GCS bucket name
        blob_name: Name for the blob in GCS
        content_type: MIME type for the RDF data (default: 'application/rdf+xml')
                     Common types: 'text/turtle', 'application/n-triples', 'application/ld+json'
    """
    load_dotenv()
    
    try:
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        
        blob.upload_from_string(graph_data, content_type=content_type)
        
        print(f"✅ Uploaded RDF data to gs://{bucket_name}/{blob_name}")
    except Exception as e:
        print(f"❌ Error uploading to GCS: {e}")


def download_rdf_from_gcs(bucket_name: str, blob_name: str) -> str:
    """
    Download RDF data from Google Cloud Storage.
    
    Args:
        bucket_name: GCS bucket name
        blob_name: Name of the blob in GCS
        
    Returns:
        RDF data as string
    """
    load_dotenv()
    
    try:
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        
        data = blob.download_as_text()
        print(f"✅ Downloaded RDF data from gs://{bucket_name}/{blob_name}")
        return data
    except Exception as e:
        print(f"❌ Error downloading from GCS: {e}")
        return ""


if __name__ == "__main__":
    print("🔧 GCS Integration Example\n")
    
    # Example: List buckets
    list_buckets()
    
    # Example usage (uncomment and configure):
    # bucket = os.getenv("GCS_BUCKET_NAME")
    # if bucket:
    #     # Upload example
    #     rdf_data = "<rdf:RDF>...</rdf:RDF>"
    #     upload_rdf_to_gcs(rdf_data, bucket, "ontology.rdf")
    #     
    #     # Download example
    #     data = download_rdf_from_gcs(bucket, "ontology.rdf")
    #     print(data)
