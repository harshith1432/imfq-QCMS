import os
from datetime import datetime, timezone
from fpdf import FPDF


def generate_invoice_pdf_bytes(org_name, admin_name, admin_email, plan_name, billing_cycle, amount, transaction_id, payment_date=None, branding_context=None):
    """Generates a high-fidelity vector PDF Tax Invoice as bytes for email attachments."""
    ctx = branding_context or {}
    comp_legal = ctx.get('legal_company_name') or 'QCMS Technologies Pvt. Ltd.'
    comp_trading = ctx.get('trading_name') or 'Enterprise Licensing & Cloud Services'
    comp_gstin = ctx.get('gstin') or '27AAACQ1234F1Z9'
    comp_cin = ctx.get('cin') or 'U72200MH2026PTC123456'
    comp_email = ctx.get('billing_email') or 'billing@ifqm.org.in'
    header_title = 'TAX INVOICE'
    
    total_val = float(amount or 0.0)
    subtotal_val = total_val / 1.18 if total_val > 0 else 0.0
    gst_val = total_val - subtotal_val
    
    dt_str = payment_date.strftime('%Y-%m-%d') if isinstance(payment_date, datetime) else (str(payment_date) if payment_date else datetime.now(timezone.utc).replace(tzinfo=None).strftime('%Y-%m-%d'))
    tx_str = str(transaction_id or 'TXN-001')
    inv_no = f"INV-2026-{tx_str[-8:] if len(tx_str) > 8 else tx_str}"

    pdf = FPDF(orientation='P', unit='mm', format='A4')
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # 1. Top Document Header (Clean layout without dark navy box)
    pdf.set_font('Helvetica', 'B', 20)
    pdf.set_text_color(18, 33, 61) # Dark navy
    pdf.text(15, 22, header_title)
    
    pdf.set_font('Helvetica', 'B', 10)
    pdf.text(125, 18, f"Invoice No: {inv_no}")
    pdf.set_font('Helvetica', '', 9)
    pdf.text(125, 23, f"Invoice Date: {dt_str}")
    pdf.text(125, 28, f"Transaction Ref: {tx_str}")
    pdf.set_font('Helvetica', 'B', 9)
    pdf.set_text_color(16, 163, 74) # Green status
    pdf.text(125, 33, "Status: COMPLETED AND VERIFIED")
    
    # Divider Line 1
    pdf.set_draw_color(210, 220, 230)
    pdf.set_line_width(0.4)
    pdf.line(15, 38, 195, 38)
    
    # 2. Issued By & Billed To Section
    pdf.set_text_color(18, 33, 61)
    pdf.set_font('Helvetica', 'B', 10)
    pdf.text(15, 46, "ISSUED BY:")
    pdf.set_font('Helvetica', 'B', 9.5)
    pdf.text(15, 51, comp_legal)
    pdf.set_font('Helvetica', '', 8.5)
    pdf.text(15, 56, comp_trading)
    pdf.text(15, 60.5, f"GSTIN: {comp_gstin} | CIN: {comp_cin}")
    pdf.text(15, 65, f"Email: {comp_email}")
    
    pdf.set_font('Helvetica', 'B', 10)
    pdf.text(110, 46, "BILLED TO:")
    pdf.set_font('Helvetica', 'B', 9.5)
    pdf.text(110, 51, str(org_name or 'Organization Admin'))
    pdf.set_font('Helvetica', '', 8.5)
    pdf.text(110, 56, f"Attn: {admin_name or 'System Administrator'}")
    pdf.text(110, 60.5, f"Email: {admin_email or 'admin@company.com'}")
    pdf.text(110, 65, "Billing Region: India GST Inclusive")
    
    # 3. Table Header
    pdf.set_y(73)
    pdf.set_fill_color(237, 242, 250)
    pdf.set_draw_color(210, 220, 230)
    pdf.rect(15, 73, 180, 8, 'FD')
    
    pdf.set_font('Helvetica', 'B', 9)
    pdf.set_text_color(18, 33, 61)
    pdf.text(18, 78.5, "DESCRIPTION")
    pdf.text(95, 78.5, "QTY / DURATION")
    pdf.text(135, 78.5, "NET RATE")
    pdf.text(168, 78.5, "AMOUNT (INR)")
    
    # 4. Table Row Item
    pdf.set_y(84)
    pdf.set_font('Helvetica', 'B', 9.5)
    pdf.set_text_color(18, 33, 61)
    pdf.text(18, 89, f"{plan_name or 'Enterprise'} Plan Subscription")
    
    pdf.set_font('Helvetica', '', 8.5)
    pdf.set_text_color(100, 100, 100)
    pdf.text(18, 93.5, "Enterprise Access & Platform Features")
    
    pdf.set_font('Helvetica', '', 9)
    pdf.set_text_color(18, 33, 61)
    cycle_str = "1 Year (365 Days)" if str(billing_cycle) in ('Yearly', 'Annual') else "1 Month (30 Days)"
    pdf.text(95, 91, cycle_str)
    pdf.text(135, 91, f"INR {subtotal_val:,.2f}")
    pdf.set_font('Helvetica', 'B', 9.5)
    pdf.text(168, 91, f"INR {subtotal_val:,.2f}")
    
    # Table Row Bottom Line
    pdf.set_draw_color(225, 230, 238)
    pdf.line(15, 98, 195, 98)
    
    # 5. Summary Box & Stamp
    pdf.set_fill_color(245, 250, 255)
    pdf.set_draw_color(210, 220, 230)
    pdf.rect(110, 105, 85, 36, 'FD')
    
    pdf.set_font('Helvetica', '', 9)
    pdf.set_text_color(50, 50, 50)
    pdf.text(114, 112, "Subtotal Excl. Tax:")
    pdf.text(158, 112, f"INR {subtotal_val:,.2f}")
    
    pdf.text(114, 119, "GST / IGST 18%:")
    pdf.text(158, 119, f"INR {gst_val:,.2f}")
    
    pdf.set_draw_color(210, 220, 230)
    pdf.line(114, 123, 190, 123)
    
    pdf.set_font('Helvetica', 'B', 10)
    pdf.set_text_color(18, 33, 61)
    pdf.text(114, 131, "Total Amount Paid:")
    pdf.text(155, 131, f"INR {total_val:,.2f}")
    
    # Status Stamp Box
    pdf.set_draw_color(16, 163, 74)
    pdf.set_line_width(0.6)
    pdf.rect(15, 110, 75, 24, 'D')
    
    pdf.set_font('Helvetica', 'B', 9.5)
    pdf.set_text_color(16, 163, 74)
    pdf.text(20, 118, "STATUS: PAID AND VERIFIED")
    pdf.set_font('Helvetica', '', 8.5)
    pdf.text(20, 126, f"Payment Ref: {tx_str}")
    
    # 6. Footer
    pdf.set_draw_color(210, 220, 230)
    pdf.set_line_width(0.3)
    pdf.line(15, 270, 195, 270)
    
    pdf.set_font('Helvetica', '', 8)
    pdf.set_text_color(120, 120, 120)
    footer_text = ctx.get('footer_text') or 'This is an official computer-generated tax invoice and payment receipt. No physical signature required.'
    pdf.text(15, 275, footer_text)
    footer_brand = f"{ctx.get('software_name') or 'QCMS Enterprise OS'} | Support: {ctx.get('support_email') or 'billing@ifqm.org.in'}"
    pdf.text(15, 279, footer_brand)
    
    return bytes(pdf.output())
