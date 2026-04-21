from google.cloud import storage
import uuid
import os
from datetime import timedelta

def upload_to_gcs(file_path: str) -> str:
    bucket_name = os.getenv("GCS_BUCKET_NAME")
    if not bucket_name:
        raise ValueError("GCS_BUCKET_NAME not set in environment")
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(f"images/{uuid.uuid4()}.jpg")
    blob.upload_from_filename(file_path)
    return blob.generate_signed_url(expiration=timedelta(hours=1), version="v4")
