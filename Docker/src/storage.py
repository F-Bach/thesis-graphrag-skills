
import json
import os
from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

def connect_to_blob_storage():
    """Connect to Azure Blob Storage"""
    connection_string = os.getenv("AZURE_CONNECTION_STRING")
    if not connection_string:
        raise ValueError("Azure connection string not found in environment variables.")
    blob_service_client = BlobServiceClient.from_connection_string(connection_string)
    container_client = blob_service_client.get_container_client("cv-storage")
    return container_client

def upload_cv_to_blob(cv_data, container_client, name, surname):
    """Upload CV data to Azure Blob Storage with formatted filename"""
    date_str = datetime.now().strftime("%Y-%m-%d")
    filename = f"{surname.lower()}_{name.lower()}_{date_str}.json"
    blob_client = container_client.get_blob_client(filename)
    blob_client.upload_blob(json.dumps(cv_data, indent=2), overwrite=True)
    