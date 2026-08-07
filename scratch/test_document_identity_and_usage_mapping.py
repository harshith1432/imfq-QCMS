import sys
import os

sys.path.insert(0, os.path.join(os.getcwd(), 'backend'))

from app import create_app
from app.infrastructure.database.models.models import (
    db, PlatformIdentityConfig, CompanyInformationConfig, CompanyContactsConfig,
    CompanyAddressesConfig, BrandingAssetsConfig, DocumentTemplateConfig,
    SettingUsageMap, User
)
from app.domain.services.document_branding_service import DocumentBrandingService
from app.domain.services.setting_usage_scanner_service import SettingUsageScannerService

app = create_app()

with app.app_context():
    print("1. Creating database tables...")
    db.create_all()
    print("Database tables created successfully!")

    print("\n2. Testing seed_initial_defaults...")
    SettingUsageScannerService.seed_initial_defaults()

    plat = PlatformIdentityConfig.query.filter_by(org_id=None).first()
    comp = CompanyInformationConfig.query.filter_by(org_id=None).first()
    cont = CompanyContactsConfig.query.filter_by(org_id=None).first()
    tmpl_count = DocumentTemplateConfig.query.count()
    map_count = SettingUsageMap.query.count()

    print(f" - Software Name: {plat.software_name}")
    print(f" - Legal Company Name: {comp.legal_company_name}")
    print(f" - Support Email: {cont.support_email}")
    print(f" - Document Templates Count: {tmpl_count}")
    print(f" - Setting Usage Mappings Count: {map_count}")

    assert plat is not None, "Platform Identity config missing!"
    assert comp is not None, "Company Information config missing!"
    assert tmpl_count >= 5, "Default document templates missing!"
    assert map_count >= 10, "Setting usage mappings missing!"

    print("\n3. Testing DocumentBrandingService context resolution...")
    ctx = DocumentBrandingService.get_branding_context(None)
    print("Branding Context:", {
        "software_name": ctx["software_name"],
        "organization_name": ctx["organization_name"],
        "support_email": ctx["support_email"],
        "copyright_text": ctx["copyright_text"]
    })

    tmpl_invoice = DocumentBrandingService.get_template_config('invoice')
    print("Invoice Template Config:", tmpl_invoice["header_title"])

    meta = DocumentBrandingService.generate_verification_metadata('invoice', 9901, 'TestAdmin')
    print("Document Verification Hash:", meta["document_hash"])

    print("\n4. Testing Flask Client Endpoints...")
    client = app.test_client()

    user = User.query.filter_by(email='harshithkd6@gmail.com').first() or User.query.first()
    if user:
        from flask_jwt_extended import create_access_token
        token = create_access_token(identity=str(user.id))
        headers = {'Authorization': f'Bearer {token}'}

        res = client.get('/api/document-identity/all', headers=headers)
        print(f"GET /api/document-identity/all -> {res.status_code}")
        assert res.status_code == 200

        res_map = client.get('/api/document-identity/usage-map', headers=headers)
        print(f"GET /api/document-identity/usage-map -> {res_map.status_code}")
        assert res_map.status_code == 200

        res_impact = client.get('/api/document-identity/impact-analysis?setting_key=software_name', headers=headers)
        print(f"GET /api/document-identity/impact-analysis -> {res_impact.status_code}")
        print("Impact Analysis Result:", res_impact.get_json()["impact_analysis"]["total_dependencies"], "dependencies mapped.")

        res_preview = client.post('/api/document-identity/preview', headers=headers, json={"type": "invoice"})
        print(f"POST /api/document-identity/preview -> {res_preview.status_code}")
        assert res_preview.status_code == 200

    print("\nSUCCESS: All Document Identity and Usage Mapping tests passed cleanly!")
