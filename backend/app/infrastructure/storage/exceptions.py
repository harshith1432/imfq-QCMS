# QCMS Provider-Independent Storage Exceptions

class StorageError(Exception):
    """Base exception for all storage errors in QCMS."""
    def __init__(self, message: str, original_error: Exception = None):
        super().__init__(message)
        self.message = message
        self.original_error = original_error


class StorageUploadError(StorageError):
    """Raised when a file upload fails."""
    pass


class StorageDownloadError(StorageError):
    """Raised when a file download or retrieval fails."""
    pass


class StorageDeleteError(StorageError):
    """Raised when a file deletion fails."""
    pass


class StorageNotFoundError(StorageError):
    """Raised when a requested file is not found in the storage backend."""
    pass


class StoragePermissionError(StorageError):
    """Raised when an operation on a storage object is forbidden."""
    pass


class StorageConfigurationError(StorageError):
    """Raised when a storage backend configuration is invalid or missing required credentials."""
    pass
