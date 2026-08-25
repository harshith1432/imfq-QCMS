# QCMS Azure Blob Storage Provider
import os
import mimetypes
import logging
from typing import Optional, Tuple, Any, Dict
from datetime import datetime, timedelta, timezone
from werkzeug.utils import secure_filename

from app.infrastructure.storage.providers.base import BaseStorageProvider
from app.infrastructure.storage.exceptions import (
    StorageUploadError, StorageDownloadError, StorageDeleteError,
    StorageConfigurationError
)

logger = logging.getLogger("QCMS.Storage.Azure")

class AzureBlobStorageProvider(BaseStorageProvider):
    """
    Production Azure Blob Storage provider.
    Maintains full compatibility with existing Azure Blob storage configurations and SAS signed URLs.
    """

    def __init__(
        self,
        connection_string: Optional[str] = None,
        container_name: Optional[str] = None,
        blob_base_url: Optional[str] = None
    ):
        self.connection_string = connection_string or os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        self.container_name = (container_name or os.getenv("AZURE_STORAGE_CONTAINER_NAME") or "qcms-uploads").strip()
        self.blob_base_url = blob_base_url or os.getenv("AZURE_STORAGE_BLOB_URL")
        self.blob_service_client = None
        self.container_client = None

        if not self.connection_string:
            raise StorageConfigurationError("AZURE_STORAGE_CONNECTION_STRING is required for STORAGE_BACKEND=azure.")

        self._init_client()

    def _init_client(self):
        try:
            from azure.storage.blob import BlobServiceClient
            self.blob_service_client = BlobServiceClient.from_connection_string(self.connection_string)
            self.container_client = self.blob_service_client.get_container_client(self.container_name)
            try:
                if not self.container_client.exists():
                    self.container_client.create_container()
            except Exception as ce:
                logger.info(f"[AzureBlobStorageProvider] Container check notice: {ce}")
            logger.info(f"[AzureBlobStorageProvider] Initialized successfully for container: {self.container_name}")
        except ImportError as ie:
            raise StorageConfigurationError("azure-storage-blob package is not installed.", original_error=ie)
        except Exception as e:
            logger.error(f"[AzureBlobStorageProvider] Failed to connect to Azure: {e}")
            raise StorageConfigurationError(f"Azure Blob initialization error: {str(e)}", original_error=e)

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

        try:
            from azure.storage.blob import ContentSettings
            blob_client = self.container_client.get_blob_client(blob_path)
            blob_client.upload_blob(
                file_bytes,
                overwrite=True,
                content_settings=ContentSettings(content_type=content_type)
            )
            return {
                "filename": final_filename,
                "path": blob_path,
                "url": f"/uploads/{blob_path}",
                "backend": "azure",
                "size_bytes": file_size,
                "content_type": content_type
            }
        except Exception as e:
            logger.error(f"[AzureBlobStorageProvider] Upload failed for {blob_path}: {e}")
            raise StorageUploadError(f"Azure upload failed: {str(e)}", original_error=e)

    def get_file_bytes(self, filename_or_path: str, subfolder: str = "") -> Tuple[Optional[bytes], Optional[str]]:
        clean_sub = subfolder.strip("/\\")
        target_path = f"{clean_sub}/{filename_or_path}" if clean_sub and not filename_or_path.startswith(clean_sub) else filename_or_path

        try:
            blob_client = self.container_client.get_blob_client(target_path)
            if not blob_client.exists():
                return None, None
            props = blob_client.get_blob_properties()
            content = blob_client.download_blob().readall()
            mime = getattr(props.content_settings, 'content_type', None) or "application/octet-stream"
            return content, mime
        except Exception as e:
            logger.warning(f"[AzureBlobStorageProvider] Error fetching blob {target_path}: {e}")
            raise StorageDownloadError(f"Azure download failed: {str(e)}", original_error=e)

    def generate_signed_url(self, blob_path: str, expiry_minutes: int = 15) -> Optional[str]:
        if not self.blob_service_client:
            return None
        try:
            from azure.storage.blob import generate_blob_sas, BlobSasPermissions

            account_name = self.blob_service_client.account_name
            account_key = getattr(self.blob_service_client.credential, 'account_key', None)
            if not account_key:
                for part in self.connection_string.split(';'):
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
            logger.error(f"[AzureBlobStorageProvider] Failed to generate signed URL for {blob_path}: {exc}")
            return None

    def delete_file(self, filename_or_path: str, subfolder: str = "") -> bool:
        clean_sub = subfolder.strip("/\\")
        target_path = f"{clean_sub}/{filename_or_path}" if clean_sub and not filename_or_path.startswith(clean_sub) else filename_or_path

        try:
            blob_client = self.container_client.get_blob_client(target_path)
            if blob_client.exists():
                blob_client.delete_blob()
                return True
            return False
        except Exception as e:
            logger.warning(f"[AzureBlobStorageProvider] Delete notice for {target_path}: {e}")
            raise StorageDeleteError(f"Azure delete failed: {str(e)}", original_error=e)

    def exists(self, filename_or_path: str, subfolder: str = "") -> bool:
        clean_sub = subfolder.strip("/\\")
        target_path = f"{clean_sub}/{filename_or_path}" if clean_sub and not filename_or_path.startswith(clean_sub) else filename_or_path
        try:
            blob_client = self.container_client.get_blob_client(target_path)
            return bool(blob_client.exists())
        except Exception:
            return False

    def get_info(self) -> Dict[str, Any]:
        return {
            "backend": "azure",
            "container": self.container_name,
            "connected": bool(self.blob_service_client)
        }
