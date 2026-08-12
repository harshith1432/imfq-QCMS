from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.infrastructure.database.models.models import (
    db, User, PlatformIdentityConfig, CompanyInformationConfig, CompanyContactsConfig,
    CompanyAddressesConfig, BrandingAssetsConfig, DocumentTemplateConfig, SettingUsageMap
)
from app.domain.services.document_branding_service import DocumentBrandingService
from app.domain.services.setting_usage_scanner_service import SettingUsageScannerService
from app.presentation.middleware.middleware import super_admin_required

document_branding_bp = Blueprint('document_branding', __name__, url_prefix='/api/document-identity')

def _get_user_and_org_id():
    try:
        identity = get_jwt_identity()
        if isinstance(identity, dict):
            u_id = identity.get('id') or identity.get('user_id')
        else:
            u_id = int(identity)
        user = db.session.get(User, int(u_id)) if u_id else None
        org_id = user.org_id if (user and hasattr(user, 'role') and user.role and user.role.name != 'SuperAdmin') else None
        return user, org_id
    except Exception:
        db.session.rollback()
        return None, None

@document_branding_bp.route('/all', methods=['GET'])
@jwt_required()
def get_all_document_identity():
    """Retrieve all 10 Document Identity & Branding configuration sections."""
    user, org_id = _get_user_and_org_id()

    # Ensure defaults are seeded
    SettingUsageScannerService.seed_initial_defaults()

    ctx = DocumentBrandingService.get_branding_context(org_id)
    templates = DocumentTemplateConfig.query.filter_by(org_id=org_id).all()
    if not templates:
        templates = DocumentTemplateConfig.query.filter_by(org_id=None).all()

    tmpl_dict = {}
    for t in templates:
        tmpl_dict[t.template_key] = {
            "template_name": t.template_name,
            "header_title": t.header_title,
            "subtitle": t.subtitle,
            "header_text": t.header_text,
            "footer_text": t.footer_text,
            "watermark_text": t.watermark_text,
            "confidential_text": t.confidential_text,
            "terms_and_conditions": t.terms_and_conditions,
            "enable_qr_verification": t.enable_qr_verification,
            "enable_digital_signature": t.enable_digital_signature
        }

    return jsonify({
        "status": "success",
        "branding_context": ctx,
        "templates": tmpl_dict
    }), 200


@document_branding_bp.route('/update', methods=['POST'])
@jwt_required()
def update_document_identity():
    """Save & update document identity configuration sections."""
    try:
        user, org_id = _get_user_and_org_id()

        data = request.json or {}
        section = data.get('section', 'platform')
        payload = data.get('payload', {})

        if section == 'platform':
            cfg = PlatformIdentityConfig.query.filter_by(org_id=org_id).first()
            if not cfg:
                cfg = PlatformIdentityConfig(org_id=org_id)
                db.session.add(cfg)

            for k, v in payload.items():
                if hasattr(cfg, k):
                    setattr(cfg, k, v)

        elif section == 'company':
            cfg = CompanyInformationConfig.query.filter_by(org_id=org_id).first()
            if not cfg:
                cfg = CompanyInformationConfig(org_id=org_id)
                db.session.add(cfg)

            for k, v in payload.items():
                if hasattr(cfg, k):
                    setattr(cfg, k, v)

        elif section == 'contacts':
            cfg = CompanyContactsConfig.query.filter_by(org_id=org_id).first()
            if not cfg:
                cfg = CompanyContactsConfig(org_id=org_id)
                db.session.add(cfg)

            for k, v in payload.items():
                if k == 'emergency_phone':
                    cfg.emergency_contact = v
                elif hasattr(cfg, k):
                    setattr(cfg, k, v)

        elif section == 'addresses':
            cfg = CompanyAddressesConfig.query.filter_by(org_id=org_id).first()
            if not cfg:
                cfg = CompanyAddressesConfig(org_id=org_id)
                db.session.add(cfg)

            for k, v in payload.items():
                if k == 'city_pin' and v:
                    if '-' in v:
                        parts = v.split('-', 1)
                        cfg.city = parts[0].strip()
                        cfg.pin = parts[1].strip()
                    else:
                        cfg.city = v.strip()
                elif hasattr(cfg, k):
                    setattr(cfg, k, v)

        elif section == 'template':
            template_key = payload.get('template_key')
            if template_key:
                tmpl = DocumentTemplateConfig.query.filter_by(template_key=template_key, org_id=org_id).first()
                if not tmpl:
                    tmpl = DocumentTemplateConfig(org_id=org_id, template_key=template_key, template_name=payload.get('template_name', template_key.title()))
                    db.session.add(tmpl)

                for k, v in payload.items():
                    if hasattr(tmpl, k):
                        setattr(tmpl, k, v)

        db.session.commit()
        DocumentBrandingService.invalidate_cache()

        ctx = DocumentBrandingService.get_branding_context(org_id)

        return jsonify({
            "status": "success",
            "message": f"Document identity section '{section}' updated successfully.",
            "branding_context": ctx
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@document_branding_bp.route('/upload-logo', methods=['POST'])
@jwt_required()
def upload_platform_logo():
    """Upload custom platform / organization logo image."""
    import os, time
    from werkzeug.utils import secure_filename
    from flask import current_app

    user_id = get_jwt_identity()
    user = db.session.get(User, int(user_id))
    org_id = user.org_id if user and user.role.name != 'SuperAdmin' else None

    if 'logo_file' not in request.files:
        return jsonify({'status': 'error', 'message': 'No file uploaded'}), 400

    file = request.files['logo_file']
    if not file or file.filename == '':
        return jsonify({'status': 'error', 'message': 'No file selected'}), 400

    allowed_exts = {'png', 'jpg', 'jpeg', 'svg', 'webp', 'gif'}
    ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
    if ext not in allowed_exts:
        return jsonify({'status': 'error', 'message': 'Invalid file type. Allowed: PNG, JPG, JPEG, SVG, WEBP'}), 400

    filename = f"logo_{int(time.time())}_{secure_filename(file.filename)}"

    # Save to backend & frontend uploads directory
    upload_dir_backend = os.path.join(current_app.root_path, '..', '..', 'frontend', 'uploads', 'branding')
    os.makedirs(upload_dir_backend, exist_ok=True)
    file_path = os.path.join(upload_dir_backend, filename)
    file.save(file_path)

    relative_url = f"/uploads/branding/{filename}"

    # Update BrandingAssetsConfig
    assets = BrandingAssetsConfig.query.filter_by(org_id=org_id).first()
    if not assets:
        assets = BrandingAssetsConfig(org_id=org_id)
        db.session.add(assets)

    assets.logo_url = relative_url
    assets.print_logo_url = relative_url
    assets.pdf_logo_url = relative_url

    # Only update the org's logo_url when an org-level user uploads —
    # SuperAdmin logo uploads are platform-level only and must NOT touch any org's logo_url
    if org_id and user.organization:
        user.organization.logo_url = relative_url

    db.session.commit()
    DocumentBrandingService.invalidate_cache()

    ctx = DocumentBrandingService.get_branding_context(org_id)

    return jsonify({
        "status": "success",
        "message": "Platform logo uploaded successfully!",
        "logo_url": relative_url,
        "branding_context": ctx
    }), 200


@document_branding_bp.route('/remove-logo', methods=['POST'])
@jwt_required()
def remove_platform_logo():
    """Reset platform / organization logo back to default."""
    user_id = get_jwt_identity()
    user = db.session.get(User, int(user_id))
    org_id = user.org_id if user and user.role.name != 'SuperAdmin' else None

    assets = BrandingAssetsConfig.query.filter_by(org_id=org_id).first()
    if assets:
        assets.logo_url = "/assets/img/logo.png"
        assets.print_logo_url = "/assets/img/logo-print.png"
        assets.pdf_logo_url = "/assets/img/logo-pdf.png"

    if org_id and user.organization:
        user.organization.logo_url = None

    db.session.commit()
    DocumentBrandingService.invalidate_cache()

    ctx = DocumentBrandingService.get_branding_context(org_id)

    return jsonify({
        "status": "success",
        "message": "Platform logo reset to default successfully!",
        "logo_url": "/assets/img/logo.png",
        "branding_context": ctx
    }), 200


@document_branding_bp.route('/usage-map', methods=['GET'])
@jwt_required()
def get_usage_mapping_matrix():
    """Retrieve all setting usage dependency mappings."""
    SettingUsageScannerService.seed_initial_defaults()
    records = SettingUsageMap.query.all()
    return jsonify({
        "status": "success",
        "total_count": len(records),
        "usage_map": [r.to_dict() for r in records]
    }), 200


@document_branding_bp.route('/impact-analysis', methods=['GET'])
@jwt_required()
def get_impact_analysis():
    """Calculate impact analysis for a specific setting_key."""
    setting_key = request.args.get('setting_key', '')
    analysis = SettingUsageScannerService.get_impact_analysis(setting_key)
    return jsonify({
        "status": "success",
        "impact_analysis": analysis
    }), 200


@document_branding_bp.route('/dependency-graph', methods=['GET'])
@jwt_required()
def get_dependency_graph():
    """Retrieve interactive dependency graph data."""
    graph = SettingUsageScannerService.get_dependency_graph()
    return jsonify({
        "status": "success",
        "graph": graph
    }), 200


@document_branding_bp.route('/scan-dependencies', methods=['POST'])
@jwt_required()
@super_admin_required()
def trigger_dependency_scan():
    """Manually trigger code scanner to index new dependencies."""
    SettingUsageScannerService.scan_and_sync_dependencies()
    count = SettingUsageMap.query.count()
    return jsonify({
        "status": "success",
        "message": f"Codebase dependency scan completed successfully! Registered {count} active usage points."
    }), 200


@document_branding_bp.route('/preview', methods=['POST'])
@jwt_required()
def generate_live_preview():
    """Generate live HTML rendering preview for Invoices, QC Story Reports, Certificates, and Email Templates."""
    data = request.json or {}
    preview_type = data.get('type', 'invoice')
    user_id = get_jwt_identity()
    user = db.session.get(User, int(user_id))
    org_id = user.org_id if user and user.role.name != 'SuperAdmin' else None

    ctx = DocumentBrandingService.get_branding_context(org_id)
    tmpl = DocumentBrandingService.get_template_config(preview_type, org_id)
    meta = DocumentBrandingService.generate_verification_metadata(preview_type, 9901, user.username if user else "Admin", org_id)

    if preview_type == 'platform':
        logo_img = f'<img src="{ctx["logo_url"]}" style="max-height:48px; max-width:180px; object-fit:contain;" />' if ctx.get("logo_url") else '<div style="background:#2563eb; color:#fff; padding:8px 12px; border-radius:6px; font-weight:bold;">QCMS</div>'
        html = f"""
        <div style="font-family: Inter, system-ui, sans-serif; padding: 24px; border: 1px solid #cbd5e1; border-radius: 12px; background: #ffffff; color: #0f172a;">
            <div style="display:flex; justify-content:space-between; align-items:center; border-bottom: 2px solid #2563eb; padding-bottom: 16px; margin-bottom: 20px;">
                <div style="display:flex; align-items:center; gap:12px;">
                    {logo_img}
                    <div>
                        <h2 style="margin:0; font-size:20px; font-weight:700; color:#0f172a;">{ctx['platform_title']}</h2>
                        <span style="font-size:12px; font-weight:600; color:#2563eb; background:#eff6ff; padding:2px 8px; border-radius:4px;">{ctx['software_short_name']} {ctx['edition']}</span>
                    </div>
                </div>
                <div style="text-align:right;">
                    <span style="font-size:12px; font-weight:bold; color:#64748b;">SYSTEM VERSION</span>
                    <p style="margin:2px 0 0 0; font-size:14px; font-weight:700; color:#1e293b;">{ctx['version']}</p>
                </div>
            </div>

            <div style="display:grid; grid-template-columns: 1fr 1fr; gap:16px; margin-bottom:20px;">
                <div style="padding:16px; background:#f8fafc; border:1px solid #e2e8f0; border-radius:8px;">
                    <span style="font-size:11px; font-weight:700; color:#64748b; text-transform:uppercase;">Software Name</span>
                    <p style="margin:4px 0 0 0; font-size:15px; font-weight:600; color:#0f172a;">{ctx['software_name']}</p>
                </div>
                <div style="padding:16px; background:#f8fafc; border:1px solid #e2e8f0; border-radius:8px;">
                    <span style="font-size:11px; font-weight:700; color:#64748b; text-transform:uppercase;">Platform Subtitle</span>
                    <p style="margin:4px 0 0 0; font-size:14px; color:#334155;">{ctx['platform_subtitle']}</p>
                </div>
                <div style="padding:16px; background:#f8fafc; border:1px solid #e2e8f0; border-radius:8px;">
                    <span style="font-size:11px; font-weight:700; color:#64748b; text-transform:uppercase;">Tagline</span>
                    <p style="margin:4px 0 0 0; font-size:13px; font-style:italic; color:#475569;">"{ctx['tagline']}"</p>
                </div>
                <div style="padding:16px; background:#f8fafc; border:1px solid #e2e8f0; border-radius:8px;">
                    <span style="font-size:11px; font-weight:700; color:#64748b; text-transform:uppercase;">Website & Support</span>
                    <p style="margin:4px 0 0 0; font-size:13px; color:#2563eb;">{ctx['website']} | {ctx['support_portal']}</p>
                </div>
            </div>

            <div style="padding:16px; background:#f1f5f9; border-radius:8px; font-size:12px; color:#475569; display:flex; justify-content:space-between; align-items:center;">
                <span><strong>Footer Copyright:</strong> {ctx.get('footer_copyright', '')}</span>
                <span style="font-weight:600; color:#0f172a;">Default Currency: {ctx.get('default_currency', 'INR (₹)')}</span>
            </div>
        </div>
        """

    elif preview_type == 'company':
        html = f"""
        <div style="font-family: Arial, sans-serif; padding: 28px; border: 1px solid #cbd5e1; border-radius: 12px; background: #ffffff; color: #0f172a;">
            <div style="border-bottom: 2px dashed #94a3b8; padding-bottom: 16px; margin-bottom: 20px; text-align:center;">
                <h2 style="margin:0; color:#0f172a; font-size:22px;">{ctx['legal_company_name']}</h2>
                <p style="margin:4px 0 0 0; font-size:13px; color:#64748b;">Trading Name: <strong style="color:#0f172a;">{ctx['trading_name']}</strong></p>
            </div>

            <table style="width:100%; border-collapse:collapse; margin-bottom:20px; font-size:13px; color:#0f172a;">
                <tbody>
                    <tr><td style="padding:8px; font-weight:bold; color:#475569; width:30%; border-bottom:1px solid #e2e8f0;">GSTIN / Tax ID:</td><td style="padding:8px; border-bottom:1px solid #e2e8f0; font-family:monospace; font-weight:bold; color:#0f172a;">{ctx['gstin']}</td></tr>
                    <tr><td style="padding:8px; font-weight:bold; color:#475569; border-bottom:1px solid #e2e8f0;">PAN Number:</td><td style="padding:8px; border-bottom:1px solid #e2e8f0; font-family:monospace; font-weight:bold; color:#0f172a;">{ctx['pan']}</td></tr>
                    <tr><td style="padding:8px; font-weight:bold; color:#475569; border-bottom:1px solid #e2e8f0;">Corporate Identification (CIN):</td><td style="padding:8px; border-bottom:1px solid #e2e8f0; font-family:monospace; font-weight:bold; color:#0f172a;">{ctx['cin']}</td></tr>
                </tbody>
            </table>

            <div style="display:flex; justify-content:space-around; align-items:center; padding-top:20px; border-top:1px solid #e2e8f0;">
                <div style="text-align:center;">
                    <img src="{ctx['official_seal_url']}" style="width:70px; height:70px; object-fit:contain; display:block; margin:0 auto 4px;" onerror="this.style.display='none'" />
                    <span style="font-size:11px; font-weight:bold; color:#475569;">Official Corporate Seal</span>
                </div>
                <div style="text-align:center;">
                    <img src="{ctx['digital_signature_url']}" style="max-width:140px; height:45px; object-fit:contain; display:block; margin:0 auto 4px;" onerror="this.style.display='none'" />
                    <span style="font-size:11px; font-weight:bold; color:#475569;">Authorized Digital Signatory</span>
                </div>
            </div>
        </div>
        """

    elif preview_type == 'address':
        html = f"""
        <div style="font-family: Arial, sans-serif; padding: 24px; border: 1px solid #cbd5e1; border-radius: 12px; background: #ffffff; color: #0f172a;">
            <h3 style="margin:0 0 16px 0; color:#1e293b; border-bottom:2px solid #3b82f6; padding-bottom:8px;">Office Addresses & Location Directory</h3>
            
            <div style="margin-bottom:20px; padding:16px; background:#eff6ff; border-left:4px solid #2563eb; border-radius:4px;">
                <h4 style="margin:0 0 4px 0; color:#1e40af; font-size:14px; font-weight:700;">REGISTERED OFFICE ADDRESS</h4>
                <p style="margin:0; font-size:13px; color:#1e293b; line-height:1.5;">{ctx['registered_office']}</p>
            </div>

            <div style="padding:16px; background:#f8fafc; border-left:4px solid #64748b; border-radius:4px;">
                <h4 style="margin:0 0 4px 0; color:#334155; font-size:14px; font-weight:700;">CORPORATE HEADQUARTERS</h4>
                <p style="margin:0; font-size:13px; color:#1e293b; line-height:1.5;">{ctx['corporate_office']}</p>
            </div>
        </div>
        """

    elif preview_type == 'contacts':
        html = f"""
        <div style="font-family: Arial, sans-serif; padding: 24px; border: 1px solid #cbd5e1; border-radius: 12px; background: #ffffff; color: #0f172a;">
            <h3 style="margin:0 0 16px 0; color:#1e293b; border-bottom:2px solid #10b981; padding-bottom:8px;">Official Contact Directory</h3>
            <div style="display:grid; grid-template-columns: 1fr 1fr; gap:12px; font-size:13px; color:#0f172a;">
                <div style="padding:12px; background:#f8fafc; border-radius:6px; color:#0f172a;"><strong style="color:#334155;">General Email:</strong> <span style="color:#2563eb;">{ctx['general_email']}</span></div>
                <div style="padding:12px; background:#f8fafc; border-radius:6px; color:#0f172a;"><strong style="color:#334155;">Support Email:</strong> <span style="color:#2563eb;">{ctx['support_email']}</span></div>
                <div style="padding:12px; background:#f8fafc; border-radius:6px; color:#0f172a;"><strong style="color:#334155;">Billing Email:</strong> <span style="color:#2563eb;">{ctx['billing_email']}</span></div>
                <div style="padding:12px; background:#f8fafc; border-radius:6px; color:#0f172a;"><strong style="color:#334155;">Sales Email:</strong> <span style="color:#2563eb;">{ctx['sales_email']}</span></div>
                <div style="padding:12px; background:#f8fafc; border-radius:6px; color:#0f172a;"><strong style="color:#334155;">General Hotline:</strong> <span style="color:#0f172a;">{ctx['general_phone']}</span></div>
                <div style="padding:12px; background:#f8fafc; border-radius:6px; color:#0f172a;"><strong style="color:#334155;">Support Hotline:</strong> <span style="color:#0f172a;">{ctx['support_phone']}</span></div>
            </div>
        </div>
        """

    elif preview_type == 'usage_map':
        html = f"""
        <div style="font-family: Arial, sans-serif; padding: 20px; border: 1px solid #cbd5e1; border-radius: 12px; background: #ffffff; color: #0f172a;">
            <h3 style="margin:0 0 12px 0; color:#0f172a;">Setting Dependency Usage Mapping Matrix</h3>
            <p style="margin:0 0 16px 0; font-size:13px; color:#64748b;">Centralized identity settings trace automatically across all code files, generators, and exports.</p>
            <div style="padding:12px; background:#f8fafc; border-radius:8px; font-size:12px; color:#0f172a;">
                <p style="margin:0 0 6px 0; color:#0f172a;"><strong style="color:#1e293b;">Active Export Targets:</strong> PDF Reports, Excel Worksheets, CSV Files, HTML Emails</p>
                <p style="margin:0 0 6px 0; color:#0f172a;"><strong style="color:#1e293b;">Backend Services:</strong> DocumentBrandingService, ReportGenerator, PDFTemplateEngine</p>
                <p style="margin:0; color:#0f172a;"><strong style="color:#1e293b;">Registered Dependencies:</strong> 12 Active System Setting Key Mappings</p>
            </div>
        </div>
        """

    elif preview_type == 'invoice':
        html = f"""
        <div style="font-family: Arial, sans-serif; padding: 24px; border: 1px solid #cbd5e1; border-radius: 8px; background: #ffffff; color: #0f172a;">
            <div style="display:flex; justify-content:space-between; border-bottom: 2px solid #2563eb; padding-bottom: 16px;">
                <div>
                    <h2 style="margin:0; color:#1e293b;">{ctx['software_display_name']}</h2>
                    <p style="margin:4px 0; color:#64748b; font-size:13px;">{ctx['legal_company_name']} | GSTIN: {ctx['gstin']}</p>
                    <p style="margin:0; color:#64748b; font-size:12px;">{ctx['registered_office']}</p>
                </div>
                <div style="text-align:right;">
                    <h3 style="margin:0; color:#2563eb;">{tmpl['header_title']}</h3>
                    <p style="margin:4px 0; font-size:13px; font-weight:bold; color:#0f172a;">INVOICE #INV-2026-9901</p>
                    <p style="margin:0; font-size:12px; color:#64748b;">Date: {meta['generated_at']}</p>
                </div>
            </div>
            <div style="margin: 20px 0; padding: 12px; background: #f8fafc; border-radius: 6px;">
                <p style="margin:0 0 4px 0; font-size:12px; font-weight:bold; color:#475569;">BILLED TO:</p>
                <p style="margin:0; font-size:14px; font-weight:bold; color:#0f172a;">{ctx['organization_name']}</p>
                <p style="margin:4px 0 0 0; font-size:13px; color:#64748b;">Enterprise Subscription Plan — Monthly Billing</p>
            </div>
            <table style="width:100%; border-collapse:collapse; margin-bottom: 20px; font-size:13px; color:#0f172a;">
                <thead>
                    <tr style="background:#f1f5f9; text-align:left; color:#0f172a;">
                        <th style="padding:8px; color:#0f172a;">Item Description</th>
                        <th style="padding:8px; color:#0f172a;">Qty</th>
                        <th style="padding:8px; color:#0f172a;">Rate</th>
                        <th style="padding:8px; text-align:right; color:#0f172a;">Amount</th>
                    </tr>
                </thead>
                <tbody>
                    <tr style="color:#0f172a;">
                        <td style="padding:8px; border-bottom:1px solid #e2e8f0; color:#0f172a;">{ctx['software_name']} License Tier (Unlimited Users)</td>
                        <td style="padding:8px; border-bottom:1px solid #e2e8f0; color:#0f172a;">1</td>
                        <td style="padding:8px; border-bottom:1px solid #e2e8f0; color:#0f172a;">₹49,999.00</td>
                        <td style="padding:8px; border-bottom:1px solid #e2e8f0; text-align:right; color:#0f172a;">₹49,999.00</td>
                    </tr>
                    <tr style="color:#0f172a;">
                        <td colspan="3" style="padding:8px; text-align:right; font-weight:bold; color:#0f172a;">GST (18%):</td>
                        <td style="padding:8px; text-align:right; font-weight:bold; color:#0f172a;">₹8,999.82</td>
                    </tr>
                    <tr style="background:#eff6ff; color:#0f172a;">
                        <td colspan="3" style="padding:8px; text-align:right; font-weight:bold; font-size:15px; color:#0f172a;">TOTAL AMOUNT:</td>
                        <td style="padding:8px; text-align:right; font-weight:bold; font-size:15px; color:#2563eb;">₹58,998.82</td>
                    </tr>
                </tbody>
            </table>
            <div style="display:flex; justify-content:space-between; align-items:center; border-top:1px solid #e2e8f0; padding-top:16px; font-size:12px; color:#64748b;">
                <div>
                    <p style="margin:0; font-weight:bold; color:#334155;">Terms & Conditions:</p>
                    <p style="margin:2px 0 0 0; color:#475569;">{tmpl['terms_and_conditions']}</p>
                    <p style="margin:6px 0 0 0; font-size:11px; color:#64748b;">{tmpl['footer_text']}</p>
                </div>
                <div style="text-align:center;">
                    <img src="{meta['qr_image_url']}" style="width:70px; height:70px; display:block; margin:0 auto;" />
                    <span style="font-size:10px; color:#94a3b8;">Hash: {meta['document_hash']}</span>
                </div>
            </div>
        </div>
        """

    elif preview_type == 'qc_story':
        html = f"""
        <div style="font-family: Arial, sans-serif; padding: 24px; border: 1px solid #cbd5e1; border-radius: 8px; background: #ffffff; color: #0f172a;">
            <div style="border-bottom: 2px solid #10b981; padding-bottom: 12px; display:flex; justify-content:space-between; align-items:center;">
                <div>
                    <h3 style="margin:0; color:#065f46;">{tmpl['header_title']}</h3>
                    <p style="margin:4px 0 0 0; font-size:13px; color:#64748b;">{tmpl['subtitle']} — {ctx['organization_name']}</p>
                </div>
                <span style="background:#ecfdf5; color:#047857; padding:4px 10px; border-radius:4px; font-size:12px; font-weight:bold;">ISO 9001 VERIFIED</span>
            </div>
            <div style="margin:16px 0; padding:12px; background:#fafafa; border-left:4px solid #10b981; color:#0f172a;">
                <p style="margin:0; font-size:13px; color:#0f172a;"><strong style="color:#047857;">Project Name:</strong> Quality Improvement & Scrap Reduction Cycle</p>
                <p style="margin:4px 0 0 0; font-size:12px; color:#64748b;">Generated By: {meta['generated_by']} | Engine: {meta['software']} ({meta['version']})</p>
            </div>
            <div style="border:1px dashed #e2e8f0; padding:16px; text-align:center; color:#64748b; font-style:italic; margin-bottom:16px;">
                [{tmpl['watermark_text']} — QC Story Problem-Solving Methodology Steps 1-7 Content]
            </div>
            <div style="border-top:1px solid #e2e8f0; padding-top:12px; font-size:11px; color:#64748b; display:flex; justify-content:space-between;">
                <span>{tmpl['confidential_text']}</span>
                <span>{tmpl['footer_text']}</span>
            </div>
        </div>
        """

    elif preview_type == 'certificate':
        html = f"""
        <div style="font-family: 'Georgia', serif; padding: 32px; border: 4px double #d97706; border-radius: 12px; background: #fffbf0; color: #78350f; text-align: center;">
            <p style="margin:0; font-size:13px; font-weight:bold; letter-spacing:2px; color:#b45309;">{ctx['legal_company_name']}</p>
            <h2 style="margin:12px 0 4px 0; color:#78350f; font-size:24px;">{tmpl['header_title']}</h2>
            <p style="margin:0; font-size:13px; color:#92400e; font-style:italic;">{tmpl['subtitle']}</p>
            
            <div style="margin: 24px 0;">
                <p style="margin:0; font-size:13px; color:#78350f;">This is to certify that</p>
                <h3 style="margin:8px 0; font-size:20px; color:#1e293b;">{user.username if user else "Sample Admin User"}</h3>
                <p style="margin:0; font-size:13px; color:#78350f;">has successfully completed training on <strong>Standard Operating Procedure (SOP-QUAL-001)</strong></p>
            </div>
            
            <div style="display:flex; justify-content:space-around; align-items:center; margin-top: 30px; padding-top: 16px; border-top: 1px solid #fde68a;">
                <div>
                    <p style="margin:0; font-size:11px; font-weight:bold; color:#78350f;">OFFICIAL DIGITAL SEAL</p>
                    <span style="font-size:10px; color:#b45309;">Verified Electronic Authority</span>
                </div>
                <div>
                    <img src="{meta['qr_image_url']}" style="width:60px; height:60px;" />
                    <p style="margin:2px 0 0 0; font-size:9px; color:#92400e;">Hash: {meta['document_hash']}</p>
                </div>
            </div>
        </div>
        """

    else:
        html = f"""
        <div style="font-family: Arial, sans-serif; padding: 20px; border:1px solid #e2e8f0; border-radius:6px; background:#ffffff; color:#0f172a;">
            <h3 style="margin:0 0 8px 0; color:#0f172a;">{tmpl.get('header_title', 'Live Preview')}</h3>
            <p style="color:#475569;">{tmpl.get('subtitle', '')}</p>
            <hr style="border-color:#e2e8f0;">
            <p style="font-size:13px; color:#475569;">Live preview generated dynamically by DocumentBrandingService engine for <strong style="color:#0f172a;">{ctx['software_name']}</strong>.</p>
        </div>
        """

    return jsonify({
        "status": "success",
        "preview_html": html,
        "metadata": meta
    }), 200
