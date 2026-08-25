import io
import os
import sys
import json
import pytest
from unittest.mock import MagicMock, patch

from app.infrastructure.storage import (
    storage, StorageService,
    LocalStorageProvider, AzureBlobStorageProvider, SupabaseStorageProvider,
    StorageError, StorageUploadError, StorageDownloadError, StorageDeleteError,
    StorageConfigurationError
)
from app.infrastructure.database.models.models import User, Organization, Project
from flask_jwt_extended import create_access_token


class TestLocalStorageProvider:
    def test_local_storage_lifecycle(self, tmp_path):
        provider = LocalStorageProvider(upload_folder=str(tmp_path))

        # 1. Save file
        data = io.BytesIO(b"QCMS local storage test content")
        result = provider.save_file(data, filename="test_doc.pdf", subfolder="projects/org_55")

        assert result["backend"] == "local"
        assert result["path"] == f"projects/org_55/{result['filename']}"
        assert result["size_bytes"] == len(b"QCMS local storage test content")
        assert result["content_type"] == "application/pdf"

        # 2. Exists
        assert provider.exists(result["path"]) is True
        assert provider.exists("non_existent_file.pdf") is False

        # 3. Download bytes
        content, content_type = provider.get_file_bytes(result["path"])
        assert content == b"QCMS local storage test content"
        assert content_type == "application/pdf"

        # 4. Signed URL proxy
        url = provider.generate_signed_url(result["path"])
        assert url == f"/api/storage/download/{result['path']}"

        # 5. Delete file
        assert provider.delete_file(result["path"]) is True
        assert provider.exists(result["path"]) is False
        assert provider.delete_file(result["path"]) is False


class TestSupabaseStorageProvider:
    @patch("requests.get")
    def test_supabase_initialization(self, mock_get):
        mock_get.return_value.status_code = 200

        provider = SupabaseStorageProvider(
            supabase_url="https://xyzproject.supabase.co",
            service_role_key="secret-service-role-key",
            bucket_name="ifqmqc"
        )
        assert provider.supabase_url == "https://xyzproject.supabase.co"
        assert provider.bucket_name == "ifqmqc"

        info = provider.get_info()
        assert info["backend"] == "supabase"
        assert info["bucket"] == "ifqmqc"
        assert info["connected"] is True

    def test_supabase_missing_credentials_raises(self):
        with pytest.raises(StorageConfigurationError):
            SupabaseStorageProvider(supabase_url="", service_role_key="")

    @patch("requests.get")
    @patch("requests.post")
    def test_supabase_save_file(self, mock_post, mock_get):
        mock_get.return_value.status_code = 200
        mock_post.return_value.status_code = 200

        provider = SupabaseStorageProvider(
            supabase_url="https://xyzproject.supabase.co",
            service_role_key="secret-service-role-key",
            bucket_name="ifqmqc"
        )

        data = io.BytesIO(b"Supabase file payload")
        result = provider.save_file(data, filename="evidence.png", subfolder="projects/org_55/proj_1")

        assert result["backend"] == "supabase"
        assert result["size_bytes"] == len(b"Supabase file payload")
        assert "projects/org_55/proj_1" in result["path"]
        assert mock_post.called

        # Verify headers sent to Supabase
        call_args, call_kwargs = mock_post.call_args
        headers = call_kwargs.get("headers", {})
        assert headers.get("Authorization") == "Bearer secret-service-role-key"
        assert headers.get("apikey") == "secret-service-role-key"

    @patch("requests.get")
    @patch("requests.post")
    def test_supabase_generate_signed_url(self, mock_post, mock_get):
        mock_get.return_value.status_code = 200
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            "signedURL": "/storage/v1/object/sign/ifqmqc/projects/org_55/file.pdf?token=abc123signed"
        }

        provider = SupabaseStorageProvider(
            supabase_url="https://xyzproject.supabase.co",
            service_role_key="secret-service-role-key",
            bucket_name="ifqmqc"
        )

        signed_url = provider.generate_signed_url("projects/org_55/file.pdf", expiry_minutes=15)
        assert signed_url is not None
        assert "https://xyzproject.supabase.co/storage/v1/object/sign/ifqmqc/projects/org_55/file.pdf?token=abc123signed" == signed_url

    @patch("requests.get")
    @patch("requests.delete")
    def test_supabase_delete_file(self, mock_delete, mock_get):
        mock_get.return_value.status_code = 200
        mock_delete.return_value.status_code = 200

        provider = SupabaseStorageProvider(
            supabase_url="https://xyzproject.supabase.co",
            service_role_key="secret-service-role-key",
            bucket_name="ifqmqc"
        )

        deleted = provider.delete_file("projects/org_55/file.pdf")
        assert deleted is True
        assert mock_delete.called

    @patch("requests.get")
    def test_supabase_get_file_bytes(self, mock_get):
        mock_get.side_effect = [
            MagicMock(status_code=200),  # init bucket check
            MagicMock(status_code=200, content=b"Supabase file content", headers={"Content-Type": "application/pdf"})  # download
        ]

        provider = SupabaseStorageProvider(
            supabase_url="https://xyzproject.supabase.co",
            service_role_key="secret-service-role-key",
            bucket_name="ifqmqc"
        )

        content, mime = provider.get_file_bytes("projects/org_55/file.pdf")
        assert content == b"Supabase file content"
        assert mime == "application/pdf"


class TestAzureBlobStorageProvider:
    def test_azure_missing_connection_string_raises(self):
        with pytest.raises(StorageConfigurationError):
            AzureBlobStorageProvider(connection_string="")

    def test_azure_provider_mocked(self):
        mock_azure = MagicMock()
        mock_blob_module = MagicMock()
        mock_bsc_cls = MagicMock()
        mock_client_instance = MagicMock()
        mock_container = MagicMock()

        mock_bsc_cls.from_connection_string.return_value = mock_client_instance
        mock_client_instance.get_container_client.return_value = mock_container
        mock_client_instance.account_name = "testqcms"
        mock_container.exists.return_value = True

        mock_blob_module.BlobServiceClient = mock_bsc_cls

        with patch.dict(sys.modules, {"azure": mock_azure, "azure.storage": MagicMock(), "azure.storage.blob": mock_blob_module}):
            provider = AzureBlobStorageProvider(
                connection_string="DefaultEndpointsProtocol=https;AccountName=testqcms;AccountKey=fakekey==;EndpointSuffix=core.windows.net",
                container_name="qcms-uploads"
            )

            # 1. Save file
            mock_blob = MagicMock()
            mock_container.get_blob_client.return_value = mock_blob
            res = provider.save_file(b"Azure test blob content", filename="report.pdf", subfolder="invoices/org_55")
            assert res["backend"] == "azure"
            assert "invoices/org_55" in res["path"]
            assert mock_blob.upload_blob.called

            # 2. Exists
            mock_blob.exists.return_value = True
            assert provider.exists(res["path"]) is True

            # 3. Delete
            assert provider.delete_file(res["path"]) is True
            assert mock_blob.delete_blob.called


class TestStorageServiceFacade:
    def test_storage_service_provider_switching(self, tmp_path):
        service = StorageService()

        # Switch to Local
        local_p = LocalStorageProvider(upload_folder=str(tmp_path))
        service.set_provider(local_p, "local")
        assert service.backend == "local"

        saved = service.save_file(b"Facade file test", filename="facade_test.txt")
        assert saved["backend"] == "local"
        assert service.exists(saved["path"]) is True

        content, _ = service.get_file_bytes(saved["path"])
        assert content == b"Facade file test"

        assert service.delete(saved["path"]) is True
        assert service.exists(saved["path"]) is False


class TestStorageRoutesIntegration:
    @pytest.fixture(autouse=True)
    def setup_local_storage(self, tmp_path):
        orig_provider = storage.provider
        orig_backend = storage.backend
        storage.set_provider(LocalStorageProvider(upload_folder=str(tmp_path)), "local")
        yield
        storage.set_provider(orig_provider, orig_backend)

    def test_storage_info_endpoint(self, client, app):
        with app.app_context():
            import uuid
            admin = User.query.filter_by(email="gelala@fxzig.com").first()
            token = create_access_token(identity=str(admin.id), additional_claims={"session_id": str(uuid.uuid4())})

            res = client.get("/api/storage/info", headers={"Authorization": f"Bearer {token}"})
            assert res.status_code == 200
            data = res.get_json()
            assert "backend" in data

    def test_storage_delete_endpoint_authorized(self, client, app, tmp_path):
        with app.app_context():
            import uuid
            admin = User.query.filter_by(email="gelala@fxzig.com").first()
            token = create_access_token(identity=str(admin.id), additional_claims={"session_id": str(uuid.uuid4())})

            # Create a test file in storage for Org 55 invoice
            res_save = storage.save_file(b"Delete test invoice content", filename="inv_del.pdf", subfolder="invoices/org_55")
            file_path = res_save["path"]
            assert storage.exists(file_path) is True

            # Admin deletes Org 55 invoice -> 200 OK
            del_res = client.delete(f"/api/storage/{file_path}", headers={"Authorization": f"Bearer {token}"})
            assert del_res.status_code == 200
            assert del_res.get_json()["status"] == "success"
            assert storage.exists(file_path) is False

    def test_storage_delete_endpoint_cross_tenant_forbidden(self, client, app):
        with app.app_context():
            import uuid
            admin = User.query.filter_by(email="gelala@fxzig.com").first()  # Org 55
            token = create_access_token(identity=str(admin.id), additional_claims={"session_id": str(uuid.uuid4())})

            # Attempt to delete Org 99 file
            del_res = client.delete("/api/storage/invoices/org_99/file.pdf", headers={"Authorization": f"Bearer {token}"})
            assert del_res.status_code == 403
            assert "CROSS_TENANT_FORBIDDEN" in del_res.get_json()["message"]
