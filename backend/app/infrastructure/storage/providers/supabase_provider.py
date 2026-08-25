# QCMS Supabase Storage Provider (Development / Testing)
import os
import mimetypes
import logging
import requests
from typing import Optional, Tuple, Any, Dict
from datetime import datetime, timezone
from werkzeug.utils import secure_filename

from app.infrastructure.storage.providers.base import BaseStorageProvider
from app.infrastructure.storage.exceptions import (
    StorageUploadError, StorageDownloadError, StorageDeleteError,
    StorageConfigurationError
)

logger = logging.getLogger("QCMS.Storage.Supabase")

class SupabaseStorageProvider(BaseStorageProvider):
    """
    Development & Testing Supabase Storage Provider.
    Operates strictly server-side using the SUPABASE_SERVICE_ROLE_KEY on the private bucket (default: ifqmqc).
    Never exposes service-role credentials to frontend or client payloads.
    """

    def __init__(
        self,
        supabase_url: Optional[str] = None,
        service_role_key: Optional[str] = None,
        bucket_name: Optional[str] = None,
        timeout_seconds: int = 30
    ):
        if supabase_url is not None:
            self.supabase_url = supabase_url.rstrip("/")
        else:
            self.supabase_url = (os.getenv("SUPABASE_URL") or "").rstrip("/")

        if service_role_key is not None:
            self.service_role_key = service_role_key
        else:
            self.service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or ""

        if bucket_name is not None:
            self.bucket_name = bucket_name.strip()
        else:
            self.bucket_name = (os.getenv("SUPABASE_STORAGE_BUCKET") or "ifqmqc").strip()

        self.timeout = timeout_seconds

        if not self.supabase_url:
            raise StorageConfigurationError("SUPABASE_URL is required for STORAGE_BACKEND=supabase.")

        if not self.service_role_key:
            raise StorageConfigurationError("SUPABASE_SERVICE_ROLE_KEY is required for STORAGE_BACKEND=supabase.")

        self._ensure_bucket_exists()

    def _get_headers(self, content_type: Optional[str] = None, upsert: bool = True) -> Dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self.service_role_key}",
            "apikey": self.service_role_key,
        }
        if content_type:
            headers["Content-Type"] = content_type
        if upsert:
            headers["x-upsert"] = "true"
        return headers

    def _ensure_bucket_exists(self):
        """
        Verifies that the private bucket exists; attempts to create it as PRIVATE if not found.
        """
        try:
            url = f"{self.supabase_url}/storage/v1/bucket/{self.bucket_name}"
            resp = requests.get(url, headers=self._get_headers(), timeout=self.timeout)
            if resp.status_code == 200:
                logger.info(f"[SupabaseStorageProvider] Connected to private bucket: '{self.bucket_name}'.")
                return
            elif resp.status_code == 404:
                # Create private bucket
                create_url = f"{self.supabase_url}/storage/v1/bucket"
                payload = {
                    "id": self.bucket_name,
                    "name": self.bucket_name,
                    "public": False  # Private bucket enforcement
                }
                c_resp = requests.post(create_url, json=payload, headers=self._get_headers("application/json"), timeout=self.timeout)
                if c_resp.status_code in (200, 201):
                    logger.info(f"[SupabaseStorageProvider] Created private bucket: '{self.bucket_name}'.")
                else:
                    logger.warning(f"[SupabaseStorageProvider] Bucket verification notice ({c_resp.status_code}): {c_resp.text}")
        except Exception as e:
            logger.warning(f"[SupabaseStorageProvider] Bucket check exception: {e}")

    def save_file(
        self,
        file_data: Any,
        filename: Optional[str] = None,
        subfolder: str = "",
        content_type: Optional[str] = None,
        acl: str = "private"
    ) -> Dict[str, Any]:
        if hasattr(file_data, "filename") and not filename:
            filename = file_data.filename

        if not filename:
            filename = f"file_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.bin"

        safe_name = secure_filename(filename)
        if not safe_name:
            safe_name = f"upload_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.dat"

        if not safe_name.startswith("20") and "_" not in safe_name[:16]:
            final_filename = f"{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{safe_name}"
        else:
            final_filename = safe_name

        clean_sub = subfolder.strip("/\\")
        blob_path = f"{clean_sub}/{final_filename}" if clean_sub else final_filename

        if hasattr(file_data, "read"):
            file_bytes = file_data.read()
            if hasattr(file_data, "seek"):
                try:
                    file_data.seek(0)
                except Exception:
                    pass
        elif isinstance(file_data, (bytes, bytearray)):
            file_bytes = bytes(file_data)
        else:
            file_bytes = str(file_data).encode("utf-8")

        if not content_type:
            if hasattr(file_data, "content_type") and file_data.content_type:
                content_type = file_data.content_type
            else:
                guessed_type, _ = mimetypes.guess_type(final_filename)
                content_type = guessed_type or "application/octet-stream"

        file_size = len(file_bytes)

        # Upload to Supabase Storage REST endpoint
        clean_path = blob_path.lstrip('/')
        upload_url = f"{self.supabase_url}/storage/v1/object/{self.bucket_name}/{clean_path}"
        headers = self._get_headers(content_type=content_type, upsert=True)

        try:
            resp = requests.post(upload_url, data=file_bytes, headers=headers, timeout=self.timeout)
            if resp.status_code not in (200, 201):
                logger.error(f"[SupabaseStorageProvider] Upload failed for {clean_path} (HTTP {resp.status_code}): {resp.text}")
                raise StorageUploadError(f"Supabase upload failed with status {resp.status_code}")

            return {
                "filename": final_filename,
                "path": blob_path,
                "url": f"/uploads/{blob_path}",
                "backend": "supabase",
                "size_bytes": file_size,
                "content_type": content_type
            }
        except StorageUploadError:
            raise
        except Exception as e:
            logger.error(f"[SupabaseStorageProvider] Upload exception for {clean_path}: {e}")
            raise StorageUploadError(f"Supabase upload failed: {str(e)}", original_error=e)

    def get_file_bytes(self, filename_or_path: str, subfolder: str = "") -> Tuple[Optional[bytes], Optional[str]]:
        clean_sub = subfolder.strip("/\\")
        target_path = f"{clean_sub}/{filename_or_path}" if clean_sub and not filename_or_path.startswith(clean_sub) else filename_or_path
        clean_path = target_path.lstrip('/')

        download_url = f"{self.supabase_url}/storage/v1/object/authenticated/{self.bucket_name}/{clean_path}"
        headers = self._get_headers()

        try:
            resp = requests.get(download_url, headers=headers, timeout=self.timeout)
            if resp.status_code == 200:
                content_type = resp.headers.get("Content-Type") or mimetypes.guess_type(clean_path)[0] or "application/octet-stream"
                return resp.content, content_type
            elif resp.status_code == 404:
                return None, None
            else:
                logger.warning(f"[SupabaseStorageProvider] Download response status {resp.status_code} for {clean_path}")
                return None, None
        except Exception as e:
            logger.error(f"[SupabaseStorageProvider] Download exception for {clean_path}: {e}")
            raise StorageDownloadError(f"Supabase download failed: {str(e)}", original_error=e)

    def generate_signed_url(self, blob_path: str, expiry_minutes: int = 15) -> Optional[str]:
        clean_path = blob_path.lstrip('/')
        sign_url = f"{self.supabase_url}/storage/v1/object/sign/{self.bucket_name}/{clean_path}"
        payload = {"expiresIn": expiry_minutes * 60}
        headers = self._get_headers("application/json")

        try:
            resp = requests.post(sign_url, json=payload, headers=headers, timeout=self.timeout)
            if resp.status_code == 200:
                data = resp.json()
                signed_subpath = data.get("signedURL")
                if signed_subpath:
                    if signed_subpath.startswith("http"):
                        return signed_subpath
                    if signed_subpath.startswith("/storage/v1"):
                        return f"{self.supabase_url}{signed_subpath}"
                    return f"{self.supabase_url}/storage/v1/{signed_subpath.lstrip('/')}"
            logger.warning(f"[SupabaseStorageProvider] Signed URL creation returned {resp.status_code} for {clean_path}: {resp.text}")
            return None
        except Exception as e:
            logger.error(f"[SupabaseStorageProvider] Failed to generate signed URL for {clean_path}: {e}")
            return None

    def delete_file(self, filename_or_path: str, subfolder: str = "") -> bool:
        clean_sub = subfolder.strip("/\\")
        target_path = f"{clean_sub}/{filename_or_path}" if clean_sub and not filename_or_path.startswith(clean_sub) else filename_or_path
        clean_path = target_path.lstrip('/')

        delete_url = f"{self.supabase_url}/storage/v1/object/{self.bucket_name}"
        payload = {"prefixes": [clean_path]}
        headers = self._get_headers("application/json")

        try:
            resp = requests.delete(delete_url, json=payload, headers=headers, timeout=self.timeout)
            if resp.status_code == 200:
                return True
            logger.warning(f"[SupabaseStorageProvider] Delete returned status {resp.status_code} for {clean_path}: {resp.text}")
            return False
        except Exception as e:
            logger.error(f"[SupabaseStorageProvider] Delete exception for {clean_path}: {e}")
            raise StorageDeleteError(f"Supabase deletion failed: {str(e)}", original_error=e)

    def exists(self, filename_or_path: str, subfolder: str = "") -> bool:
        clean_sub = subfolder.strip("/\\")
        target_path = f"{clean_sub}/{filename_or_path}" if clean_sub and not filename_or_path.startswith(clean_sub) else filename_or_path
        clean_path = target_path.lstrip('/')

        # Perform quick HEAD or list request
        url = f"{self.supabase_url}/storage/v1/object/authenticated/{self.bucket_name}/{clean_path}"
        headers = self._get_headers()
        try:
            resp = requests.head(url, headers=headers, timeout=self.timeout)
            return resp.status_code == 200
        except Exception:
            return False

    def get_info(self) -> Dict[str, Any]:
        return {
            "backend": "supabase",
            "bucket": self.bucket_name,
            "connected": bool(self.supabase_url and self.service_role_key)
        }
