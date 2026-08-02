import mimetypes
import os
import uuid

import boto3
from botocore.client import Config
from dotenv import load_dotenv

# Read env vars at import time regardless of when/whether the importer has
# already called load_dotenv() itself — this module needs to be self-sufficient.
load_dotenv()

R2_ACCOUNT_ID = os.environ.get('R2_ACCOUNT_ID')
R2_ACCESS_KEY_ID = os.environ.get('R2_ACCESS_KEY_ID')
R2_SECRET_ACCESS_KEY = os.environ.get('R2_SECRET_ACCESS_KEY')
R2_BUCKET_NAME = os.environ.get('R2_BUCKET_NAME')
R2_PUBLIC_URL = (os.environ.get('R2_PUBLIC_URL') or '').rstrip('/')

MAX_UPLOAD_BYTES = 8 * 1024 * 1024  # 8MB — client resizes before upload, this is a hard backstop
ALLOWED_CONTENT_TYPES = {'image/jpeg', 'image/png', 'image/webp'}

configured = bool(R2_ACCOUNT_ID and R2_ACCESS_KEY_ID and R2_SECRET_ACCESS_KEY and R2_BUCKET_NAME and R2_PUBLIC_URL)

_client = None
if configured:
    _client = boto3.client(
        's3',
        endpoint_url=f'https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com',
        aws_access_key_id=R2_ACCESS_KEY_ID,
        aws_secret_access_key=R2_SECRET_ACCESS_KEY,
        config=Config(signature_version='s3v4'),
        region_name='auto',
    )


def upload_image(file_storage, folder='uploads'):
    """Uploads a Werkzeug FileStorage to R2. Returns (public_url, errors)."""
    if not configured:
        return None, {'file': 'Image uploads are not configured on this server.'}

    content_type = file_storage.mimetype
    if content_type not in ALLOWED_CONTENT_TYPES:
        return None, {'file': 'Unsupported image type. Use JPEG, PNG, or WebP.'}

    data = file_storage.read()
    if len(data) > MAX_UPLOAD_BYTES:
        return None, {'file': 'Image is too large (max 8MB).'}

    extension = mimetypes.guess_extension(content_type) or ''
    key = f'{folder}/{uuid.uuid4().hex}{extension}'

    _client.put_object(
        Bucket=R2_BUCKET_NAME,
        Key=key,
        Body=data,
        ContentType=content_type,
        CacheControl='public, max-age=31536000, immutable',
    )

    return f'{R2_PUBLIC_URL}/{key}', {}
