import hashlib
import json
from datetime import datetime
from flask import request
from app.infrastructure.database.models.models import (
    db, PlatformIdentityConfig, CompanyInformationConfig, CompanyContactsConfig,
    CompanyAddressesConfig, BrandingAssetsConfig, DocumentTemplateConfig,
    SettingUsageMap, Organization
)

class DocumentBrandingService:
    """Centralized Document Identity, Branding & Template Management Engine."""

    _cache = {}

    @staticmethod
    def _normalize_email(val, default_prefix, fallback_domain="qcms.com"):
        """Returns the email address as entered by the user, or a fallback default if empty."""
        v = (val or '').strip()
        if not v:
            return f"{default_prefix}@{fallback_domain}"
        return v


    @classmethod
    def invalidate_cache(cls):
        """Invalidate in-memory branding cache so changes immediately take effect across all generators."""
        cls._cache.clear()

    @classmethod
    def load(cls, org_id=None):
        """Unified entry point for loading branding context."""
        return cls.get_branding_context(org_id)

    @classmethod
    def get_branding_context(cls, org_id=None):
        """Fetch unified branding configuration with hierarchical fallback (Org Override -> Global Default)."""
        cache_key = f"context:{org_id}"
        if cache_key in cls._cache:
            return cls._cache[cache_key]

        # Fetch Global Defaults
        platform = PlatformIdentityConfig.query.filter_by(org_id=None).first()
        company = CompanyInformationConfig.query.filter_by(org_id=None).first()
        contacts = CompanyContactsConfig.query.filter_by(org_id=None).first()
        addresses = CompanyAddressesConfig.query.filter_by(org_id=None).first()
        assets = BrandingAssetsConfig.query.filter_by(org_id=None).first()

        # If org_id provided, check for custom org identity overrides
        org_obj = None
        if org_id:
            org_obj = db.session.get(Organization, org_id)
            org_plat = PlatformIdentityConfig.query.filter_by(org_id=org_id).first()
            org_comp = CompanyInformationConfig.query.filter_by(org_id=org_id).first()
            org_cont = CompanyContactsConfig.query.filter_by(org_id=org_id).first()
            org_addr = CompanyAddressesConfig.query.filter_by(org_id=org_id).first()
            org_assets = BrandingAssetsConfig.query.filter_by(org_id=org_id).first()

            if org_plat: platform = org_plat
            if org_comp: company = org_comp
            if org_cont: contacts = org_cont
            if org_addr: addresses = org_addr
            if org_assets: assets = org_assets

        org_name = (company.legal_company_name if company and company.legal_company_name else (company.trading_name if company and company.trading_name else (org_obj.name if org_obj else "QCMS Technologies Pvt Ltd")))

        # Determine dynamic active email domain fallback from connected integrations
        fallback_domain = "qcms.com"
        try:
            from app.infrastructure.database.models.models import IntegrationConfig
            cfg = IntegrationConfig.query.filter(
                IntegrationConfig.category == 'Communication',
                IntegrationConfig.status == 'Connected',
                IntegrationConfig.provider_id.in_(['zeptomail', 'resend'])
            ).first()
            if cfg and cfg.settings and cfg.settings.get('sender_email'):
                se = cfg.settings.get('sender_email').strip()
                if '<' in se and '>' in se:
                    se = se.split('<')[1].split('>')[0].strip()
                if '@' in se:
                    fallback_domain = se.split('@')[-1].strip()
                elif '.' in se:
                    fallback_domain = se.strip()
        except Exception:
            pass

        norm = lambda raw, prefix: DocumentBrandingService._normalize_email(raw, prefix, fallback_domain)

        res = {
            "software_name": (platform.software_name if platform and platform.software_name else "QCMS Enterprise OS"),
            "software_short_name": (platform.software_short_name if platform and platform.software_short_name else "QCMS"),
            "software_display_name": (platform.software_display_name if platform and platform.software_display_name else "QCMS Enterprise Platform"),
            "platform_title": (platform.platform_title if platform and platform.platform_title else "QCMS Quality Management System"),
            "platform_subtitle": (platform.platform_subtitle if platform and platform.platform_subtitle else "Enterprise Quality & Compliance Management System"),
            "tagline": (platform.tagline if platform and platform.tagline else "Accelerating Enterprise Excellence & Compliance"),
            "version": (platform.version if platform and platform.version else "v4.8.2-PROD"),
            "edition": (platform.edition if platform and platform.edition else "Enterprise Cloud Edition"),
            "website": (platform.website if platform and platform.website else "https://qcms.io"),
            "support_portal": (platform.support_portal if platform and platform.support_portal else "https://support.qcms.io"),
            "copyright_text": (platform.copyright_text if platform and platform.copyright_text else "© 2026 QCMS Enterprise Solutions. All rights reserved."),
            "footer_copyright": (platform.footer_copyright if platform and platform.footer_copyright else "Confidential & Proprietary — Generated by QCMS Enterprise OS"),
            
            # Company Info
            "legal_company_name": (company.legal_company_name if company and company.legal_company_name else "QCMS Technologies Pvt Ltd"),
            "organization_name": org_name,
            "trading_name": (company.trading_name if company and company.trading_name else "QCMS Solutions"),
            "gstin": (company.gstin if company and company.gstin else "27AAACQ1234F1Z9"),
            "pan": (company.pan if company and company.pan else "AAACQ1234F"),
            "cin": (company.cin if company and company.cin else "U72200MH2026PTC123456"),
            "official_seal_url": (company.official_seal_url if company and company.official_seal_url else "/assets/img/official_seal.png"),
            "digital_signature_url": (company.digital_signature_url if company and company.digital_signature_url else "/assets/img/digital_signature.png"),

            # Contacts & Sender Display Labels
            "general_email": norm(contacts.general_email if contacts else None, "info"),
            "general_sender_name": (getattr(contacts, 'general_sender_name', None) or "QCMS General Info"),
            "support_email": norm(contacts.support_email if contacts else None, "support"),
            "support_sender_name": (getattr(contacts, 'support_sender_name', None) or "QCMS Customer Support"),
            "billing_email": norm(contacts.billing_email if contacts else None, "billing"),
            "billing_sender_name": (getattr(contacts, 'billing_sender_name', None) or "QCMS Accounts & Billing"),
            "otp_email": norm(getattr(contacts, 'otp_email', None) if contacts else None, "otp-auth"),
            "otp_sender_name": (getattr(contacts, 'otp_sender_name', None) or "QCMS OTP Verification"),
            "contact_email": norm(getattr(contacts, 'contact_email', None) if contacts else None, "contact"),
            "contact_sender_name": (getattr(contacts, 'contact_sender_name', None) or "QCMS Business Inquiries"),
            "alerts_email": norm(getattr(contacts, 'alerts_email', None) if contacts else None, "alerts"),
            "alerts_sender_name": (getattr(contacts, 'alerts_sender_name', None) or "QCMS System Alerts"),
            "feedback_email": norm(getattr(contacts, 'feedback_email', None) if contacts else None, "feedback"),
            "feedback_sender_name": (getattr(contacts, 'feedback_sender_name', None) or "QCMS Product Feedback"),
            "onboarding_email": norm(getattr(contacts, 'onboarding_email', None) if contacts else None, "onboarding"),
            "onboarding_sender_name": (getattr(contacts, 'onboarding_sender_name', None) or "QCMS User Onboarding"),
            "sales_email": norm(contacts.sales_email if contacts else None, "sales"),
            "legal_email": norm(contacts.legal_email if contacts else None, "legal"),
            "general_phone": (contacts.general_phone if contacts and contacts.general_phone else "+1 (800) 555-0199"),
            "support_phone": (contacts.support_phone if contacts and contacts.support_phone else "+1 (800) 555-0100"),
            "emergency_phone": (contacts.emergency_contact if contacts and contacts.emergency_contact else "+91 98765 43210"),

            # Addresses
            "registered_office": (addresses.registered_office if addresses and addresses.registered_office else "Suite 800, Innovation Tower, BKC, Mumbai, MH 400051, India"),
            "corporate_office": (addresses.corporate_office if addresses and addresses.corporate_office else "Tech Park Phase 2, Whitefield, Bengaluru, KA 560066, India"),
            "country": (addresses.country if addresses and addresses.country else "India"),
            "state": (addresses.state if addresses and addresses.state else "Maharashtra"),
            "city": (addresses.city if (addresses and addresses.city) else ""),
            "pin": (addresses.pin if (addresses and addresses.pin) else ""),
            "city_pin": (
                addresses.city if (addresses and addresses.city and (not addresses.pin or addresses.pin in addresses.city))
                else (f"{addresses.city} - {addresses.pin}" if (addresses and addresses.city and addresses.pin)
                else (addresses.city if (addresses and addresses.city) else (addresses.pin if (addresses and addresses.pin) else "")))
            ),

            # Assets
            "logo_url": (assets.logo_url if assets and assets.logo_url else "/assets/img/logo.png"),
            "print_logo_url": (assets.print_logo_url if assets and assets.print_logo_url else "/assets/img/logo-print.png"),
            "pdf_logo_url": (assets.pdf_logo_url if assets and assets.pdf_logo_url else "/assets/img/logo-pdf.png"),
            "watermark_logo_url": (assets.watermark_logo_url if assets and assets.watermark_logo_url else "/assets/img/watermark.png")
        }
        cls._cache[cache_key] = res
        return res

    @classmethod
    def get_template_config(cls, template_key, org_id=None):
        """Fetch template-specific branding parameters (Invoice, QC Story, Certificates, Reports)."""
        cache_key = f"template:{template_key}:{org_id}"
        if cache_key in cls._cache:
            return cls._cache[cache_key]

        tmpl = DocumentTemplateConfig.query.filter_by(template_key=template_key, org_id=org_id).first()
        if not tmpl:
            tmpl = DocumentTemplateConfig.query.filter_by(template_key=template_key, org_id=None).first()
        
        ctx = cls.get_branding_context(org_id)
        
        if not tmpl:
            res = {
                "template_key": template_key,
                "header_title": ctx["platform_title"],
                "subtitle": ctx["platform_subtitle"],
                "header_text": ctx["software_display_name"],
                "footer_text": ctx["footer_copyright"],
                "watermark_text": "CONFIDENTIAL",
                "confidential_text": "STRICTLY CONFIDENTIAL — INTERNAL USE ONLY",
                "terms_and_conditions": "Payment due within 30 days. Standard SLA terms apply.",
                "disclaimer_text": "Generated electronically by certified QCMS Enterprise engine.",
                "enable_qr_verification": True,
                "enable_digital_signature": True
            }
        else:
            res = {
                "template_key": tmpl.template_key,
                "template_name": tmpl.template_name,
                "header_title": tmpl.header_title or ctx["platform_title"],
                "subtitle": tmpl.subtitle or ctx["platform_subtitle"],
                "header_text": tmpl.header_text or ctx["software_display_name"],
                "footer_text": tmpl.footer_text or ctx["footer_copyright"],
                "watermark_text": tmpl.watermark_text or "CONFIDENTIAL",
                "confidential_text": tmpl.confidential_text or "STRICTLY CONFIDENTIAL — INTERNAL USE ONLY",
                "terms_and_conditions": tmpl.terms_and_conditions or tmpl.footer_text or "Payment due within 30 days. Standard SLA terms apply.",
                "disclaimer_text": tmpl.disclaimer_text or "Generated electronically by certified QCMS Enterprise engine.",
                "enable_qr_verification": tmpl.enable_qr_verification,
                "enable_digital_signature": tmpl.enable_digital_signature,
                "settings_json": tmpl.settings_json or {}
            }

        cls._cache[cache_key] = res
        return res

    @staticmethod
    def generate_verification_metadata(doc_type, doc_id, user_name="System", org_id=None):
        """Generate verification QR code data, hash string, and document metadata."""
        ctx = DocumentBrandingService.get_branding_context(org_id)
        timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
        raw_token = f"{doc_type}:{doc_id}:{timestamp}:{ctx['software_name']}"
        doc_hash = hashlib.sha256(raw_token.encode('utf-8')).hexdigest()[:16].upper()
        
        verification_url = f"{ctx['website']}/verify-doc?type={doc_type}&id={doc_id}&hash={doc_hash}"
        
        try:
            import qrcode, io, base64
            qr = qrcode.QRCode(version=1, box_size=4, border=1)
            qr.add_data(verification_url)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            buf = io.BytesIO()
            img.save(buf, format='PNG')
            b64_qr = base64.b64encode(buf.getvalue()).decode('utf-8')
            qr_image_url = f"data:image/png;base64,{b64_qr}"
        except Exception as e:
            qr_image_url = f"https://api.qrserver.com/v1/create-qr-code/?size=150x150&data={verification_url}"

        return {
            "document_hash": doc_hash,
            "verification_url": verification_url,
            "qr_image_url": qr_image_url,
            "generated_at": timestamp,
            "generated_by": user_name,
            "software": ctx["software_name"],
            "version": ctx["version"],
            "organization": ctx["organization_name"],
            "author": f"{user_name} via {ctx['software_name']}"
        }

    @staticmethod
    def wrap_email_html(body_html, title="QCMS Notification", org_id=None, include_header=True, include_footer=False):
        """Wrap email content with centralized corporate email branding header/footer."""
        ctx = DocumentBrandingService.get_branding_context(org_id)
        legal = (ctx.get('legal_company_name') or '').strip()
        org_name = (ctx.get('organization_name') or '').strip()
        if legal and org_name and legal.lower() != org_name.lower():
            company_footer_hdr = f"{legal} | {org_name}"
        else:
            company_footer_hdr = legal or org_name or 'QCMS Solutions'

        header_block = ""
        if include_header:
            header_block = f"""
                <div class="email-header">
                    <h1>{ctx['software_display_name']}</h1>
                    <p>{title}</p>
                </div>
            """

        footer_block = ""
        if include_footer:
            footer_block = f"""
                <div class="email-footer">
                    <p style="margin:0 0 6px 0; font-weight:600;">{company_footer_hdr}</p>
                    <p style="margin:0 0 6px 0;">{ctx['registered_office']}</p>
                    <p style="margin:0;">Support: <a href="mailto:{ctx['support_email']}">{ctx['support_email']}</a> | <a href="{ctx['website']}">{ctx['website']}</a></p>
                    <p style="margin:10px 0 0 0; font-size:11px; color:#94a3b8;">{ctx['copyright_text']}</p>
                </div>
            """

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f4f6f9; margin: 0; padding: 20px; color: #1e293b; }}
                .email-container {{ max-width: 640px; margin: 0 auto; background: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.05); }}
                .email-header {{ background: #1e293b; color: #ffffff; padding: 24px; text-align: center; border-bottom: 3px solid #2563eb; }}
                .email-header h1 {{ margin: 0; font-size: 20px; font-weight: 600; letter-spacing: 0.5px; }}
                .email-header p {{ margin: 4px 0 0 0; font-size: 12px; color: #94a3b8; }}
                .email-body {{ padding: 0; font-size: 15px; line-height: 1.6; color: #334155; }}
                .email-footer {{ background: #f8fafc; padding: 20px 24px; text-align: center; font-size: 12px; color: #64748b; border-top: 1px solid #e2e8f0; }}
                .email-footer a {{ color: #2563eb; text-decoration: none; }}
            </style>
        </head>
        <body>
            <div class="email-container">
                {header_block}
                <div class="email-body">
                    {body_html}
                </div>
                {footer_block}
            </div>
        </body>
        </html>
        """

