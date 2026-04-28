from google.cloud import storage
from google.oauth2 import service_account
import uuid
import os
import json
import base64
from datetime import timedelta

def _get_client():
    creds_b64 = os.getenv("GCS_CREDENTIALS_BASE64")
    if creds_b64:
        creds_json = json.loads(base64.b64decode(creds_b64).decode("utf-8"))
        credentials = service_account.Credentials.from_service_account_info(creds_json)
        return storage.Client(credentials=credentials)
    return storage.Client()  # fallback to default credentials (local dev)

def upload_to_gcs(file_path: str) -> str:
    bucket_name = os.getenv("GCS_BUCKET_NAME")
    if not bucket_name:
        raise ValueError("GCS_BUCKET_NAME not set in environment")
    client = _get_client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(f"images/{uuid.uuid4()}.jpg")
    blob.upload_from_filename(file_path)
    return blob.generate_signed_url(expiration=timedelta(hours=1), version="v4")
