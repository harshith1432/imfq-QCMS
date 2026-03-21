import pandas as pd
from fpdf import FPDF
import io

def generate_excel_report(projects):
    data = [{
        "UID": p.project_uid,
        "Title": p.title,
        "Stage": p.current_stage,
        "Status": p.status,
        "Start Date": p.start_date
    } for p in projects]
    
    df = pd.DataFrame(data)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Projects')
    return output.getvalue()

class QCMS_PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'QCMS - Project Final Report', 0, 1, 'C')
        self.ln(10)

def generate_pdf_summary(project, kpi):
    pdf = QCMS_PDF()
    pdf.add_page()
    pdf.set_font('Arial', '', 12)
    pdf.cell(0, 10, f"Project ID: {project.project_uid}", 0, 1)
    pdf.cell(0, 10, f"Title: {project.title}", 0, 1)
    pdf.cell(0, 10, f"Status: {project.status}", 0, 1)
    pdf.ln(5)
    pdf.cell(0, 10, "Business Impact:", 0, 1, 'B')
    pdf.cell(0, 10, f"Cost Savings: ${kpi.cost_saving}", 0, 1)
    pdf.cell(0, 10, f"Productivity Gain: {kpi.productivity_gain}%", 0, 1)
    return pdf.output()
