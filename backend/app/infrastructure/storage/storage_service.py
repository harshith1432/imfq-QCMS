import os
import logging
from typing import Optional, Tuple, Any, Dict

from app.infrastructure.storage.providers.base import BaseStorageProvider
from app.infrastructure.storage.providers.local_provider import LocalStorageProvider
from app.infrastructure.storage.providers.azure_provider import AzureBlobStorageProvider
from app.infrastructure.storage.providers.supabase_provider import SupabaseStorageProvider
from app.infrastructure.storage.exceptions import (
    StorageError, StorageConfigurationError
)

logger = logging.getLogger("QCMS.Storage")

class StorageService:
    """
    Enterprise Unified Storage Service Facade.
    Provides a provider-independent interface delegating to:
    - STORAGE_BACKEND=supabase (Development & Testing on Supabase Storage bucket 'ifqmqc')
    - STORAGE_BACKEND=azure (Production Azure Blob Storage)
    - STORAGE_BACKEND=local (Local filesystem storage for offline development & testing)
    """

    def __init__(self, app=None):
        self.app = app
        self.backend = "local"
        self.provider: BaseStorageProvider = None
        self.init_storage()

    def init_storage(self):
        requested_backend = (os.getenv("STORAGE_BACKEND") or "local").strip().lower()

        # ── 1. Supabase Storage (Development / Testing) ──────────────────────
        if requested_backend == "supabase":
            supabase_url = os.getenv("SUPABASE_URL")
            service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
            bucket = os.getenv("SUPABASE_STORAGE_BUCKET") or "ifqmqc"

            if not supabase_url or not service_key:
                logger.warning(
                    "[StorageService] STORAGE_BACKEND=supabase configured, but SUPABASE_URL or "
                    "SUPABASE_SERVICE_ROLE_KEY is missing. Falling back to local storage."
                )
                self.provider = LocalStorageProvider()
                self.backend = "local"
                return

            try:
                self.provider = SupabaseStorageProvider(
                    supabase_url=supabase_url,
                    service_role_key=service_key,
                    bucket_name=bucket
                )
                self.backend = "supabase"
                logger.info(f"[StorageService] Initialized Supabase Storage Provider (Bucket: {bucket}).")
            except Exception as e:
                logger.error(f"[StorageService] Failed to initialize Supabase Storage: {e}. Falling back to local storage.")
                self.provider = LocalStorageProvider()
                self.backend = "local"

        # ── 2. Azure Blob Storage (Production) ───────────────────────────────
        elif requested_backend == "azure":
            conn_str = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
            container = (os.getenv("AZURE_STORAGE_CONTAINER_NAME") or "qcms-uploads").strip()

            if not conn_str:
                logger.warning(
                    "[StorageService] STORAGE_BACKEND=azure configured, but "
                    "AZURE_STORAGE_CONNECTION_STRING is missing. Falling back to local storage."
                )
                self.provider = LocalStorageProvider()
                self.backend = "local"
                return

            try:
                self.provider = AzureBlobStorageProvider(
                    connection_string=conn_str,
                    container_name=container
                )
                self.backend = "azure"
                logger.info(f"[StorageService] Initialized Azure Blob Storage Provider (Container: {container}).")
            except Exception as e:
                logger.error(f"[StorageService] Failed to initialize Azure Blob Storage: {e}. Falling back to local storage.")
                self.provider = LocalStorageProvider()
                self.backend = "local"

        # ── 3. Local Filesystem (Default) ────────────────────────────────────
        else:
            self.provider = LocalStorageProvider()
            self.backend = "local"
            logger.info("[StorageService] Initialized Local Storage Provider.")

    def set_provider(self, provider: BaseStorageProvider, backend_name: str):
        """Allows injecting custom or mocked storage provider for testing."""
        self.provider = provider
        self.backend = backend_name

    def save_file(
        self,
        file_data: Any,
        filename: Optional[str] = None,
        subfolder: str = "",
        content_type: Optional[str] = None,
        acl: str = "private"
    ) -> Dict[str, Any]:
        """Saves a file using the active storage provider."""
        return self.provider.save_file(
            file_data=file_data,
            filename=filename,
            subfolder=subfolder,
            content_type=content_type,
            acl=acl
        )

    def upload(self, *args, **kwargs) -> Dict[str, Any]:
        """Generic alias for save_file."""
        return self.save_file(*args, **kwargs)

    def get_file_bytes(self, filename_or_path: str, subfolder: str = "") -> Tuple[Optional[bytes], Optional[str]]:
        """Retrieves file bytes and MIME type."""
        return self.provider.get_file_bytes(filename_or_path, subfolder=subfolder)

    def download(self, *args, **kwargs) -> Tuple[Optional[bytes], Optional[str]]:
        """Generic alias for get_file_bytes."""
        return self.get_file_bytes(*args, **kwargs)

    def generate_signed_url(self, blob_path: str, expiry_minutes: int = 15) -> Optional[str]:
        """Generates a secure, short-lived signed access URL."""
        return self.provider.generate_signed_url(blob_path, expiry_minutes=expiry_minutes)

    def get_url(self, *args, **kwargs) -> Optional[str]:
        """Generic alias for generate_signed_url."""
        return self.generate_signed_url(*args, **kwargs)

    def delete_file(self, filename_or_path: str, subfolder: str = "") -> bool:
        """Deletes a file from the active storage backend."""
        return self.provider.delete_file(filename_or_path, subfolder=subfolder)

    def delete(self, *args, **kwargs) -> bool:
        """Generic alias for delete_file."""
        return self.delete_file(*args, **kwargs)

    def exists(self, filename_or_path: str, subfolder: str = "") -> bool:
        """Checks if a file exists in the active storage backend."""
        return self.provider.exists(filename_or_path, subfolder=subfolder)

    def get_info(self) -> Dict[str, Any]:
        """Returns metadata about the active storage provider."""
        info = self.provider.get_info() if self.provider else {}
        info["backend"] = self.backend
        return info


# Global singleton storage instance
storage = StorageService()
