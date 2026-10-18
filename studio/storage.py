"""Django storage backend for Vercel Blob (used when BLOB_READ_WRITE_TOKEN is set).

Files are public: Instagram has to download them when publishing. Names are random, so they can't be guessed.
"""

import base64
import os
import hashlib
import hmac
import json
import logging
import mimetypes
import time

import requests
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import Storage
from django.utils.deconstruct import deconstructible
os.environ.setdefault("VERCEL_TELEMETRY_DISABLED", "1")
from vercel import blob  # noqa: E402


log = logging.getLogger(__name__)


class BlobDownloadError(OSError):
    pass


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


def blob_get(url, stream=False):
    """GET a stored file. Requests from inside Vercel are sometimes refused (403) even though the file is public,
    so retry with the store token and past the CDN cache before giving up. Returns an open requests.Response."""
    attempts = [
        ({}, {}),
        ({"authorization": f"Bearer {_token()}"}, {}),
        ({"authorization": f"Bearer {_token()}"}, {"cache": "0"}),
    ]
    problems = []
    for headers, params in attempts:
        resp = requests.get(url, headers={"user-agent": "Postmanager/1.0", **headers}, params=params,
                            stream=stream, timeout=120)
        if resp.status_code == 200:
            return resp
        problems.append(f"{resp.status_code} {resp.text[:150].strip()}".strip())
        resp.close()
    log.warning("Blob download of %s failed: %s", url, problems)
    raise BlobDownloadError(f"Storage refused the download ({' | '.join(problems)})")


@deconstructible
class VercelBlobStorage(Storage):
    def _save(self, name, content):
        content.seek(0)
        content_type = getattr(content, "content_type", None) or mimetypes.guess_type(name)[0]
        blob.put(name, content.read(), access="public", content_type=content_type, overwrite=True, token=_token())
        return name

    def _open(self, name, mode="rb"):
        return ContentFile(blob_get(self.url(name)).content, name=name)

    def download(self, name, dest):
        with blob_get(self.url(name), stream=True) as resp, open(dest, "wb") as fh:
            for chunk in resp.iter_content(1 << 20):
                fh.write(chunk)

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
