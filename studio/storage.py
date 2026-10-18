"""Django storage backend for Vercel Blob (used when BLOB_READ_WRITE_TOKEN is set).

Files are public: Instagram has to download them when publishing. Names are random, so they can't be guessed.
"""

import base64
import os
import hashlib
import hmac
import json
import mimetypes
import time

import requests
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import Storage
from django.utils.deconstruct import deconstructible
os.environ.setdefault("VERCEL_TELEMETRY_DISABLED", "1")
from vercel import blob  # noqa: E402


def _token():
    return settings.BLOB_READ_WRITE_TOKEN


def store_id():
    # Tokens look like vercel_blob_rw_<storeId>_<secret>
    parts = _token().split("_")
    return parts[3] if len(parts) > 3 else ""


def public_url(name):
    return f"https://{store_id().lower()}.public.blob.vercel-storage.com/{name.lstrip('/')}"


def client_upload_token(pathname, *, allowed_content_types, maximum_size_in_bytes, valid_for_seconds=3600):
    """A short-lived token that lets the browser upload one file straight to Blob (bypassing the 4.5 MB
    request limit of serverless functions). Same format as @vercel/blob's generateClientTokenFromReadWriteToken."""
    payload = base64.b64encode(json.dumps({
        "pathname": pathname,
        "allowedContentTypes": allowed_content_types,
        "maximumSizeInBytes": maximum_size_in_bytes,
        "addRandomSuffix": False,
        "allowOverwrite": False,
        "validUntil": int((time.time() + valid_for_seconds) * 1000),
    }, separators=(",", ":")).encode()).decode()
    signature = hmac.new(_token().encode(), payload.encode(), hashlib.sha256).hexdigest()
    secured = base64.b64encode(f"{signature}.{payload}".encode()).decode()
    return f"vercel_blob_client_{store_id()}_{secured}"


@deconstructible
class VercelBlobStorage(Storage):
    def _save(self, name, content):
        content.seek(0)
        content_type = getattr(content, "content_type", None) or mimetypes.guess_type(name)[0]
        blob.put(name, content.read(), access="public", content_type=content_type, overwrite=True, token=_token())
        return name

    def _open(self, name, mode="rb"):
        resp = requests.get(self.url(name), timeout=120)
        resp.raise_for_status()
        return ContentFile(resp.content, name=name)

    def get_available_name(self, name, max_length=None):
        return name  # upload paths already contain a random UUID

    def exists(self, name):
        try:
            blob.head(self.url(name), token=_token())
            return True
        except blob.BlobNotFoundError:
            return False

    def delete(self, name):
        if name:
            blob.delete(self.url(name), token=_token())

    def size(self, name):
        return blob.head(self.url(name), token=_token()).size

    def url(self, name):
        return public_url(name)
