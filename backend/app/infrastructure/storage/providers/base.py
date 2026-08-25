# QCMS Base Storage Provider Abstract Class
from abc import ABC, abstractmethod
from typing import Optional, Tuple, Any, Dict

class BaseStorageProvider(ABC):
    """
    Abstract contract for QCMS storage providers (Local, Azure Blob, Supabase).
    """

    @abstractmethod
    def save_file(
        self,
        file_data: Any,
        filename: Optional[str] = None,
        subfolder: str = "",
        content_type: Optional[str] = None,
        acl: str = "private"
    ) -> Dict[str, Any]:
        """
        Saves a file to the storage provider.
        Returns a dict containing:
          - filename: safe base filename
          - path: provider-independent relative storage path/key
          - url: public/proxied download URL
          - backend: provider identifier ('local', 'azure', 'supabase')
          - size_bytes: total bytes saved
          - content_type: MIME type
        """
        pass

    @abstractmethod
    def get_file_bytes(self, filename_or_path: str, subfolder: str = "") -> Tuple[Optional[bytes], Optional[str]]:
        """
        Retrieves file contents and content type as a tuple: (bytes_content, content_type).
        Returns (None, None) if file is not found.
        """
        pass

    @abstractmethod
    def generate_signed_url(self, blob_path: str, expiry_minutes: int = 15) -> Optional[str]:
        """
        Generates a temporary, secure signed URL for short-lived access to a private file.
        Returns None if not supported by the provider.
        """
        pass

    @abstractmethod
    def delete_file(self, filename_or_path: str, subfolder: str = "") -> bool:
        """
        Deletes a file from the storage provider.
        Returns True if deleted, False if file did not exist or deletion could not proceed.
        """
        pass

    @abstractmethod
    def exists(self, filename_or_path: str, subfolder: str = "") -> bool:
        """
        Checks whether the specified file exists in the storage provider.
        """
        pass

    @abstractmethod
    def get_info(self) -> Dict[str, Any]:
        """
        Returns metadata about the provider state, configuration, and readiness.
        """
        pass
