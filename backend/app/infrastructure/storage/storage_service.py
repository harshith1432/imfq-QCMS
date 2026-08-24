import os
import io
import mimetypes
import logging
from typing import Optional
from datetime import datetime
from werkzeug.utils import secure_filename

logger = logging.getLogger("QCMS.Storage")

class StorageService:
    """
    Enterprise Unified Storage Service
    Supports:
    - STORAGE_BACKEND=local (default for local & Hostinger VPS/cPanel disk)
    - STORAGE_BACKEND=azure (Azure Blob Storage with graceful local fallback)
    """

    def __init__(self, app=None):
        self.app = app
        self.backend = "local"
        self.azure_client = None
        self.container_client = None
        self.container_name = "qcms-uploads"
        self.upload_folder = None
        self.azure_blob_base_url = None
        self.init_storage()

    def init_storage(self):
        requested_backend = (os.getenv("STORAGE_BACKEND") or "local").strip().lower()
        self.container_name = (os.getenv("AZURE_STORAGE_CONTAINER_NAME") or "qcms-uploads").strip()
        self.azure_blob_base_url = os.getenv("AZURE_STORAGE_BLOB_URL")

        default_uploads = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "uploads"))
        self.upload_folder = os.getenv("UPLOAD_FOLDER", default_uploads)
        try:
            os.makedirs(self.upload_folder, exist_ok=True)
        except Exception as e:
            logger.warning(f"[Storage] Could not create local upload folder {self.upload_folder}: {e}")

        if requested_backend == "azure":
            conn_str = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
            if not conn_str:
                logger.warning("[Storage] STORAGE_BACKEND=azure requested, but AZURE_STORAGE_CONNECTION_STRING is missing. Gracefully falling back to LOCAL storage.")
                self.backend = "local"
                return

            try:
                from azure.storage.blob import BlobServiceClient
                self.azure_client = BlobServiceClient.from_connection_string(conn_str)
                self.container_client = self.azure_client.get_container_client(self.container_name)
                try:
                    if not self.container_client.exists():
                        # Private container by default (no public_access argument)
                        self.container_client.create_container()
                except Exception as ce:
                    logger.warning(f"[Storage] Azure container check notice: {ce}")
                self.backend = "azure"
                logger.info(f"[Storage] Azure Blob Storage initialized successfully as PRIVATE (Container: {self.container_name}).")
            except ImportError:
                logger.warning("[Storage] azure-storage-blob package is not installed. Gracefully falling back to LOCAL storage.")
                self.backend = "local"
            except Exception as e:
                logger.error(f"[Storage] Failed to initialize Azure Blob Storage: {e}. Gracefully falling back to LOCAL storage.")
                self.backend = "local"
        else:
            self.backend = "local"
            logger.info(f"[Storage] Local file storage initialized at: {self.upload_folder}")

    def generate_signed_url(self, blob_path: str, expiry_minutes: int = 15) -> Optional[str]:
        """
        Generates a secure, short-lived SAS URL for private blob access.
        """
        if self.backend != "azure" or not self.azure_client:
            return None
        try:
            from datetime import datetime, timedelta, timezone
            from azure.storage.blob import generate_blob_sas, BlobSasPermissions

            account_name = self.azure_client.account_name
            # Extract key from connection string if possible
            account_key = getattr(self.azure_client.credential, 'account_key', None)
            if not account_key:
                conn_str = os.getenv("AZURE_STORAGE_CONNECTION_STRING", "")
                for part in conn_str.split(';'):
                    if part.startswith('AccountKey='):
                        account_key = part.split('AccountKey=', 1)[1]
                        break

            if not account_key or not account_name:
                return None

            clean_blob = blob_path.lstrip('/')
            expiry = datetime.now(timezone.utc) + timedelta(minutes=expiry_minutes)
            sas_token = generate_blob_sas(
                account_name=account_name,
                container_name=self.container_name,
                blob_name=clean_blob,
                account_key=account_key,
                permission=BlobSasPermissions(read=True),
                expiry=expiry,
            )
            return f"https://{account_name}.blob.core.windows.net/{self.container_name}/{clean_blob}?{sas_token}"
        except Exception as exc:
            logger.error(f"[Storage] Failed to generate signed URL for {blob_path}: {exc}")
            return None

    def save_file(self, file_data, filename=None, subfolder="", content_type=None, acl="private") -> dict:
        """
        Saves a file to the active storage backend (Azure Blob or Local Hostinger/Disk).
        Supports Flask FileStorage, BytesIO, or raw bytes. Defaults to private access.
        """
        if hasattr(file_data, "filename") and not filename:
            filename = file_data.filename

        if not filename:
            filename = f"file_{datetime.now().strftime('%Y%m%d_%H%M%S')}.bin"

        safe_name = secure_filename(filename)
        if not safe_name:
            safe_name = f"upload_{datetime.now().strftime('%Y%m%d_%H%M%S')}.dat"

        if not safe_name.startswith("20") and "_" not in safe_name[:16]:
            final_filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{safe_name}"
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

        # 1. Attempt Azure Blob Upload if active
        if self.backend == "azure" and self.container_client:
            try:
                from azure.storage.blob import ContentSettings
                blob_client = self.container_client.get_blob_client(blob_path)
                blob_client.upload_blob(
                    file_bytes,
                    overwrite=True,
                    content_settings=ContentSettings(content_type=content_type)
                )

                # Return the local proxy URL or signed URL for private access
                serve_url = f"/uploads/{blob_path}"

                return {
                    "filename": final_filename,
                    "path": blob_path,
                    "url": serve_url,
                    "backend": "azure",
                    "size_bytes": file_size,
                    "content_type": content_type
                }
            except Exception as e:
                logger.error(f"[Storage] Azure Blob upload failed for {blob_path}: {e}. Falling back to local disk storage.")

        # 2. Local Disk Storage (Default & Fallback)
        target_dir = os.path.join(self.upload_folder, clean_sub) if clean_sub else self.upload_folder
        os.makedirs(target_dir, exist_ok=True)
        local_file_path = os.path.join(target_dir, final_filename)

        with open(local_file_path, "wb") as f:
            f.write(file_bytes)

        local_url = f"/uploads/{blob_path}"
        return {
            "filename": final_filename,
            "path": blob_path,
            "local_path": local_file_path,
            "url": local_url,
            "backend": "local",
            "size_bytes": file_size,
            "content_type": content_type
        }

    def get_file_bytes(self, filename_or_path, subfolder="") -> tuple:
        """
        Reads and returns (bytes_content, content_type) for a file.
        """
        clean_sub = subfolder.strip("/\\")
        target_path = f"{clean_sub}/{filename_or_path}" if clean_sub and not filename_or_path.startswith(clean_sub) else filename_or_path

        if self.backend == "azure" and self.container_client:
            try:
                blob_client = self.container_client.get_blob_client(target_path)
                props = blob_client.get_blob_properties()
                content = blob_client.download_blob().readall()
                return content, props.content_settings.content_type
            except Exception as e:
                logger.warning(f"[Storage] Azure get_file failed for {target_path}: {e}")

        local_path = os.path.join(self.upload_folder, target_path)
        if os.path.exists(local_path):
            guessed_type, _ = mimetypes.guess_type(local_path)
            with open(local_path, "rb") as f:
                return f.read(), (guessed_type or "application/octet-stream")

        return None, None

    def delete_file(self, filename_or_path, subfolder="") -> bool:
        """
        Deletes a file from the active storage backend.
        """
        clean_sub = subfolder.strip("/\\")
        target_path = f"{clean_sub}/{filename_or_path}" if clean_sub and not filename_or_path.startswith(clean_sub) else filename_or_path

        deleted = False
        if self.backend == "azure" and self.container_client:
            try:
                blob_client = self.container_client.get_blob_client(target_path)
                blob_client.delete_blob()
                deleted = True
            except Exception as e:
                logger.warning(f"[Storage] Azure delete_blob notice for {target_path}: {e}")

        local_path = os.path.join(self.upload_folder, target_path)
        if os.path.exists(local_path):
            try:
                os.remove(local_path)
                deleted = True
            except Exception as e:
                logger.warning(f"[Storage] Local remove notice for {local_path}: {e}")

        return deleted

    def exists(self, filename_or_path, subfolder="") -> bool:
        """
        Checks if a file exists.
        """
        clean_sub = subfolder.strip("/\\")
        target_path = f"{clean_sub}/{filename_or_path}" if clean_sub and not filename_or_path.startswith(clean_sub) else filename_or_path

        if self.backend == "azure" and self.container_client:
            try:
                blob_client = self.container_client.get_blob_client(target_path)
                if blob_client.exists():
                    return True
            except Exception:
                pass

        local_path = os.path.join(self.upload_folder, target_path)
        return os.path.exists(local_path)

    def get_info(self) -> dict:
        return {
            "backend": self.backend,
            "container": self.container_name if self.backend == "azure" else None,
            "upload_folder": self.upload_folder,
            "azure_connected": bool(self.azure_client)
        }

# Global singleton storage instance
storage = StorageService()
