import io
from fpdf import FPDF
from app.domain.services.document_branding_service import DocumentBrandingService

def generate_excel_report(projects, org_id=None):
    ctx = DocumentBrandingService.get_branding_context(org_id)
    tmpl = DocumentBrandingService.get_template_config('export', org_id)

    data = [{
        "Software": ctx["software_name"],
        "Organization": ctx["organization_name"],
        "UID": p.project_uid,
        "Title": p.title,
        "Stage": p.current_stage,
        "Status": p.status,
        "Start Date": p.start_date
    } for p in projects]
    
    try:
        import pandas as pd
        df = pd.DataFrame(data)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Projects')
        return output.getvalue()
    except Exception:
        import csv
        output = io.StringIO()
        if data:
            writer = csv.DictWriter(output, fieldnames=list(data[0].keys()))
            writer.writeheader()
            writer.writerows(data)
        return output.getvalue().encode('utf-8')

class DynamicBrandedPDF(FPDF):
    def __init__(self, org_id=None, template_key='project'):
        super().__init__()
        self.org_id = org_id
        self.ctx = DocumentBrandingService.get_branding_context(org_id)
        self.tmpl = DocumentBrandingService.get_template_config(template_key, org_id)

    def header(self):
        self.set_font('Arial', 'B', 14)
        self.cell(0, 10, f"{self.ctx['software_name']} — {self.tmpl['header_title']}", 0, 1, 'C')
        self.set_font('Arial', 'I', 9)
        self.cell(0, 5, f"{self.ctx['legal_company_name']} | {self.ctx['organization_name']}", 0, 1, 'C')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f"{self.tmpl['footer_text']} | Page {self.page_no()}", 0, 0, 'C')

def generate_pdf_summary(project, kpi, org_id=None):
    pdf = DynamicBrandedPDF(org_id=org_id, template_key='project')
    pdf.add_page()
    pdf.set_font('Arial', '', 11)
    pdf.cell(0, 10, f"Organization: {pdf.ctx['organization_name']}", 0, 1)
    pdf.cell(0, 10, f"Project ID: {project.project_uid}", 0, 1)
    pdf.cell(0, 10, f"Title: {project.title}", 0, 1)
    pdf.cell(0, 10, f"Status: {project.status}", 0, 1)
    pdf.ln(5)
    pdf.cell(0, 10, "Business Impact Summary:", 0, 1, 'B')
    pdf.cell(0, 10, f"Cost Savings: {pdf.ctx['default_currency']} {kpi.cost_saving}", 0, 1)
    pdf.cell(0, 10, f"Productivity Gain: {kpi.productivity_gain}%", 0, 1)
    return pdf.output()

def generate_qc_plots(project_id, s2, d2):
    import os
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import pandas as pd
    import numpy as np

    # Retrieve observations list
    obs = []
    if d2 and isinstance(d2, dict):
        obs = d2.get('data_collection', {}).get('observations') or []
    if not obs and s2 is not None:
        obs = (s2.data_collection or {}).get('observations') or []
        
    if not obs:
        return {}

    # Convert to DataFrame
    df = pd.DataFrame(obs)
    if df.empty or 'category' not in df.columns or 'value' not in df.columns:
        return {}
        
    # Ensure value column is numeric
    df['value'] = pd.to_numeric(df['value'], errors='coerce').fillna(0)
    
    plot_paths = {}
    temp_dir = os.path.join(os.getcwd(), 'temp_plots')
    os.makedirs(temp_dir, exist_ok=True)
    
    # 1. Pareto Chart
    try:
        pareto_df = df.groupby('category')['value'].sum().reset_index()
        pareto_df = pareto_df.sort_values(by='value', ascending=False)
        pareto_df['cum_percentage'] = 100 * pareto_df['value'].cumsum() / pareto_df['value'].sum()
        
        fig, ax1 = plt.subplots(figsize=(6, 3.5))
        ax1.bar(pareto_df['category'], pareto_df['value'], color='#3b82f6')
        ax1.set_ylabel('Defect Count', color='#3b82f6')
        ax1.tick_params(axis='y', labelcolor='#3b82f6')
        ax1.set_xticks(range(len(pareto_df['category'])))
        ax1.set_xticklabels(pareto_df['category'], rotation=30, ha='right', fontsize=8)
        
        ax2 = ax1.twinx()
        ax2.plot(pareto_df['category'], pareto_df['cum_percentage'], color='#ef4444', marker='o', ms=4, lw=2)
        ax2.set_ylabel('Cumulative Percentage (%)', color='#ef4444')
        ax2.tick_params(axis='y', labelcolor='#ef4444')
        ax2.set_ylim(0, 110)
        
        plt.title('QC Tool: Pareto Chart (Defect Frequency)', fontsize=10, fontweight='bold', pad=8)
        plt.tight_layout()
        path = os.path.join(temp_dir, f'pareto_{project_id}.png')
        plt.savefig(path, dpi=150)
        plt.close()
        plot_paths['pareto'] = path
    except Exception as e:
        print(f"[QCMS Report Gen] Pareto Plot Error: {str(e)}")
        
    # 2. Trend Chart (defect count over time/date)
    try:
        df_trend = df.copy()
        if 'time' in df_trend.columns:
            # Parse time and group by date
            df_trend['date'] = pd.to_datetime(df_trend['time'], errors='coerce').dt.date
            trend_grouped = df_trend.groupby('date')['value'].sum().reset_index()
            trend_grouped = trend_grouped.sort_values(by='date')
            
            fig, ax = plt.subplots(figsize=(6, 3))
            ax.plot(trend_grouped['date'].astype(str), trend_grouped['value'], color='#10b981', marker='s', lw=2)
            ax.set_ylabel('Defect Count')
            ax.set_xticks(range(len(trend_grouped['date'])))
            ax.set_xticklabels(trend_grouped['date'].astype(str), rotation=20, ha='right', fontsize=8)
            plt.title('QC Tool: Trend Analysis (Defects Over Time)', fontsize=10, fontweight='bold', pad=8)
            plt.tight_layout()
            path = os.path.join(temp_dir, f'trend_{project_id}.png')
            plt.savefig(path, dpi=150)
            plt.close()
            plot_paths['trend'] = path
    except Exception as e:
        print(f"[QCMS Report Gen] Trend Plot Error: {str(e)}")
        
    # 3. Stratification Chart (By Location or Shift)
    try:
        strat_col = 'location' if 'location' in df.columns else ('shift' if 'shift' in df.columns else None)
        if strat_col:
            strat_df = df.groupby(['category', strat_col])['value'].sum().unstack(fill_value=0)
            
            fig, ax = plt.subplots(figsize=(6, 3.5))
            strat_df.plot(kind='bar', stacked=True, ax=ax, colormap='viridis')
            ax.set_ylabel('Defect Count')
            ax.set_xticks(range(len(strat_df.index)))
            ax.set_xticklabels(strat_df.index, rotation=30, ha='right', fontsize=8)
            plt.title(f'QC Tool: Stratification (By {strat_col.capitalize()})', fontsize=10, fontweight='bold', pad=8)
            plt.legend(title=strat_col.capitalize(), fontsize='x-small')
            plt.tight_layout()
            path = os.path.join(temp_dir, f'strat_{project_id}.png')
            plt.savefig(path, dpi=150)
            plt.close()
            plot_paths['stratification'] = path
    except Exception as e:
        print(f"[QCMS Report Gen] Stratification Plot Error: {str(e)}")
        
    # 4. Histogram Chart
    try:
        vals = df['value'].tolist()
        if len(vals) >= 3:
            fig, ax = plt.subplots(figsize=(6, 3))
            ax.hist(vals, bins='auto', color='#8b5cf6', edgecolor='black', alpha=0.7)
            ax.set_xlabel('Value / Measurement')
            ax.set_ylabel('Frequency')
            plt.title('QC Tool: Process Histogram', fontsize=10, fontweight='bold', pad=8)
            plt.tight_layout()
            path = os.path.join(temp_dir, f'hist_{project_id}.png')
            plt.savefig(path, dpi=150)
            plt.close()
            plot_paths['histogram'] = path
    except Exception as e:
        print(f"[QCMS Report Gen] Histogram Plot Error: {str(e)}")
        
    return plot_paths

def plot_process_map(project_id, steps):
    if not steps:
        return None
    import matplotlib.pyplot as plt
    import os
    fig, ax = plt.subplots(figsize=(7, 2.5))
    ax.axis('off')
    
    num_steps = len(steps)
    box_width = 1.8 / max(num_steps, 1)
    for i, step in enumerate(sorted(steps, key=lambda x: x.step_number)):
        x = i * (2.2 / max(num_steps, 1)) + 0.1
        y = 0.4
        rect = plt.Rectangle((x, y), box_width, 0.4, facecolor='#dbeafe', edgecolor='#2563eb', boxstyle="round,pad=0.1")
        ax.add_patch(rect)
        text_label = f"Step {step.step_number}\n{step.step_name}"
        ax.text(x + box_width/2, y + 0.2, text_label, ha='center', va='center', fontsize=7, color='#1e3a8a', weight='bold')
        if i < num_steps - 1:
            next_x = (i+1) * (2.2 / max(num_steps, 1)) + 0.1
            ax.annotate('', xy=(next_x, y+0.2), xytext=(x+box_width, y+0.2),
                        arrowprops=dict(arrowstyle="->", color='#2563eb', lw=1.5))
            
    ax.set_xlim(0, 2.4)
    ax.set_ylim(0, 1.2)
    plt.tight_layout()
    temp_dir = os.path.join(os.getcwd(), 'temp_plots')
    os.makedirs(temp_dir, exist_ok=True)
    path = os.path.join(temp_dir, f'process_map_{project_id}.png')
    plt.savefig(path, dpi=150)
    plt.close()
    return path

def plot_check_sheet(project_id, sheet_id, rows):
    if not rows:
        return None
    import matplotlib.pyplot as plt
    import os
    categories = [r.category_name for r in rows]
    counts = [r.total_count for r in rows]
    
    fig, ax = plt.subplots(figsize=(6, 3))
    ax.bar(categories, counts, color='#3b82f6', edgecolor='#1d4ed8', alpha=0.85)
    ax.set_ylabel('Defect Counts')
    ax.set_xticks(range(len(categories)))
    ax.set_xticklabels(categories, rotation=25, ha='right', fontsize=8)
    plt.title('Check Sheet Defect Tally', fontsize=10, fontweight='bold', pad=8)
    plt.tight_layout()
    
    temp_dir = os.path.join(os.getcwd(), 'temp_plots')
    os.makedirs(temp_dir, exist_ok=True)
    path = os.path.join(temp_dir, f'check_sheet_{sheet_id}.png')
    plt.savefig(path, dpi=150)
    plt.close()
    return path

def plot_pareto_chart(project_id, chart_id, items):
    if not items:
        return None
    import matplotlib.pyplot as plt
    import os
    causes = [i.cause_name for i in items]
    freqs = [i.frequency for i in items]
    cum_pcts = [i.cumulative_pct for i in items]
    
    fig, ax1 = plt.subplots(figsize=(6, 3.5))
    ax1.bar(causes, freqs, color='#3b82f6', edgecolor='#1d4ed8')
    ax1.set_ylabel('Frequency Count', color='#3b82f6')
    ax1.tick_params(axis='y', labelcolor='#3b82f6')
    ax1.set_xticks(range(len(causes)))
    ax1.set_xticklabels(causes, rotation=30, ha='right', fontsize=8)
    
    ax2 = ax1.twinx()
    ax2.plot(causes, cum_pcts, color='#ef4444', marker='o', ms=4, lw=2)
    ax2.set_ylabel('Cumulative Percentage (%)', color='#ef4444')
    ax2.tick_params(axis='y', labelcolor='#ef4444')
    ax2.set_ylim(0, 110)
    
    plt.title('Pareto Diagram (Defect Contribution)', fontsize=10, fontweight='bold', pad=8)
    plt.tight_layout()
    
    temp_dir = os.path.join(os.getcwd(), 'temp_plots')
    os.makedirs(temp_dir, exist_ok=True)
    path = os.path.join(temp_dir, f'pareto_{chart_id}.png')
    plt.savefig(path, dpi=150)
    plt.close()
    return path

def plot_fishbone(project_id, diag_id, effect, branches):
    import matplotlib.pyplot as plt
    import os
    
    fig, ax = plt.subplots(figsize=(7.5, 4))
    ax.axis('off')
    ax.set_xlim(0, 10)
    ax.set_ylim(-3, 3)
    
    ax.plot([1, 8.5], [0, 0], color='black', lw=3.5)
    
    rect = plt.Rectangle((8.5, -0.6), 1.4, 1.2, facecolor='#fee2e2', edgecolor='#ef4444', lw=2)
    ax.add_patch(rect)
    effect_str = effect[:15] + "..." if len(effect) > 15 else effect
    ax.text(9.2, 0, f"Effect:\n{effect_str}", ha='center', va='center', fontsize=7, color='#991b1b', fontweight='bold')
    
    categories = [
        ('Man', 2, 2.5, 0),
        ('Machine', 4, 4.5, 0),
        ('Material', 6, 6.5, 0),
        ('Method', 2, 1.5, 0),
        ('Measurement', 4, 3.5, 0),
        ('Environment', 6, 5.5, 0)
    ]
    
    for i, (cat, xb_start, x_spine, y_spine) in enumerate(categories):
        is_top = i < 3
        yb_start = 2 if is_top else -2
        ax.plot([xb_start, x_spine], [yb_start, y_spine], color='black', lw=2)
        label_y = yb_start + 0.15 if is_top else yb_start - 0.25
        ax.text(xb_start, label_y, cat, ha='center', va='center', fontsize=9, fontweight='bold', color='#1f2937')
        
        cat_branches = [b.text for b in branches if b.category.lower() == cat.lower()]
        for j, cb in enumerate(cat_branches[:3]):
            t = (j + 1) / 4.0
            x_pos = xb_start + (x_spine - xb_start) * t
            y_pos = yb_start + (y_spine - yb_start) * t
            
            length = 0.5
            x_line_start = x_pos - length
            ax.plot([x_line_start, x_pos], [y_pos, y_pos], color='#6b7280', lw=1)
            ax.text(x_line_start - 0.05, y_pos, cb[:12], ha='right', va='center', fontsize=6.5, color='#4b5563')
            
    plt.tight_layout()
    temp_dir = os.path.join(os.getcwd(), 'temp_plots')
    os.makedirs(temp_dir, exist_ok=True)
    path = os.path.join(temp_dir, f'fishbone_{diag_id}.png')
    plt.savefig(path, dpi=150)
    plt.close()
    return path

def plot_scatter_diagram(project_id, diag_id, x_label, y_label, points):
    if not points:
        return None
    import matplotlib.pyplot as plt
    import os
    xs = [p.x_value for p in points]
    ys = [p.y_value for p in points]
    
    fig, ax = plt.subplots(figsize=(6, 3))
    ax.scatter(xs, ys, color='#ec4899', edgecolor='#db2777', alpha=0.8, s=40)
    ax.set_xlabel(x_label or 'X')
    ax.set_ylabel(y_label or 'Y')
    
    try:
        import numpy as np
        if len(xs) > 1:
            fit = np.polyfit(xs, ys, 1)
            fit_fn = np.poly1d(fit)
            ax.plot(xs, fit_fn(xs), color='#6b7280', ls='--', lw=1.5)
    except Exception:
        pass
        
    plt.title('Scatter Diagram Correlation Analysis', fontsize=10, fontweight='bold', pad=8)
    plt.tight_layout()
    
    temp_dir = os.path.join(os.getcwd(), 'temp_plots')
    os.makedirs(temp_dir, exist_ok=True)
    path = os.path.join(temp_dir, f'scatter_{diag_id}.png')
    plt.savefig(path, dpi=150)
    plt.close()
    return path

def plot_control_chart(project_id, chart_id, mean, ucl, lcl, points):
    if not points:
        return None
    import matplotlib.pyplot as plt
    import os
    indices = [p.sample_index for p in points]
    values = [p.value for p in points]
    out_colors = ['#ef4444' if p.is_out_of_control else '#3b82f6' for p in points]
    
    fig, ax = plt.subplots(figsize=(6, 3.2))
    ax.plot(indices, values, color='#6b7280', ls='-', marker='o', ms=4, alpha=0.6)
    ax.scatter(indices, values, color=out_colors, zorder=5)
    
    if mean is not None:
        ax.axhline(mean, color='#10b981', ls='-', label=f'Mean: {mean:.3f}')
    if ucl is not None:
        ax.axhline(ucl, color='#ef4444', ls='--', label=f'UCL: {ucl:.3f}')
    if lcl is not None:
        ax.axhline(lcl, color='#ef4444', ls='--', label=f'LCL: {lcl:.3f}')
        
    ax.set_ylabel('Measurement Value')
    ax.set_xlabel('Sample Index')
    plt.title('Statistical Process Control (SPC) Chart', fontsize=10, fontweight='bold', pad=8)
    plt.legend(loc='upper right', fontsize='xx-small')
    plt.tight_layout()
    
    temp_dir = os.path.join(os.getcwd(), 'temp_plots')
    os.makedirs(temp_dir, exist_ok=True)
    path = os.path.join(temp_dir, f'control_{chart_id}.png')
    plt.savefig(path, dpi=150)
    plt.close()
    return path

def plot_stratification(project_id, strat_id, items):
    if not items:
        return None
    import matplotlib.pyplot as plt
    import os
    import pandas as pd
    
    data = [{'category': i.category_name, 'value': i.value, 'group': i.group_name or 'Default'} for i in items]
    df = pd.DataFrame(data)
    if df.empty:
        return None
        
    strat_df = df.groupby(['category', 'group'])['value'].sum().unstack(fill_value=0)
    
    fig, ax = plt.subplots(figsize=(6, 3.5))
    strat_df.plot(kind='bar', stacked=True, ax=ax, colormap='tab10')
    ax.set_ylabel('Values')
    ax.set_xticks(range(len(strat_df.index)))
    ax.set_xticklabels(strat_df.index, rotation=25, ha='right', fontsize=8)
    plt.title('Data Stratification Chart', fontsize=10, fontweight='bold', pad=8)
    plt.legend(title='Groups', fontsize='x-small')
    plt.tight_layout()
    
    temp_dir = os.path.join(os.getcwd(), 'temp_plots')
    os.makedirs(temp_dir, exist_ok=True)
    path = os.path.join(temp_dir, f'strat_{strat_id}.png')
    plt.savefig(path, dpi=150)
    plt.close()
    return path

def generate_8d_summary_report(project_id):
    from app.infrastructure.database.models.models import (
        Project, ProjectWorkflow, Stage1ProblemDefinitionProjectInitiation, Stage2ObservationDataCollection, Stage3CauseIdentification,
        Stage4RootCauseAnalysisVerification, Stage5CountermeasurePlanningSolutionDevelopment, Stage6ImplementationChangeManagement,
        Stage7PerformanceVerificationBenefitsRealization, Stage8StandardizationKnowledgeSharingProjectClosure,
        QCCheckSheet, QCCheckSheetRow, QCParetoChart, QCParetoItem, QCFishboneDiagram, QCFishboneBranch,
        QCScatterDiagram, QCScatterPoint, QCControlChart, QCControlPoint, QCStratification, QCStratificationItem,
        QCProcessMap, QCProcessStep
    )
    
    temp_files = []
    
    project = Project.query.get(project_id)
    if not project:
        return None
        
    s1 = Stage1ProblemDefinitionProjectInitiation.query.filter_by(project_id=project_id).first()
    s2 = Stage2ObservationDataCollection.query.filter_by(project_id=project_id).first()
    s3 = Stage3CauseIdentification.query.filter_by(project_id=project_id).first()
    s4 = Stage4RootCauseAnalysisVerification.query.filter_by(project_id=project_id).first()
    s5 = Stage5CountermeasurePlanningSolutionDevelopment.query.filter_by(project_id=project_id).first()
    s6 = Stage6ImplementationChangeManagement.query.filter_by(project_id=project_id).first()
    s7 = Stage7PerformanceVerificationBenefitsRealization.query.filter_by(project_id=project_id).first()
    s8 = Stage8StandardizationKnowledgeSharingProjectClosure.query.filter_by(project_id=project_id).first()

    wf1 = ProjectWorkflow.query.filter_by(project_id=project_id, stage_id=1).first()
    wf2 = ProjectWorkflow.query.filter_by(project_id=project_id, stage_id=2).first()
    wf3 = ProjectWorkflow.query.filter_by(project_id=project_id, stage_id=3).first()
    wf4 = ProjectWorkflow.query.filter_by(project_id=project_id, stage_id=4).first()
    wf5 = ProjectWorkflow.query.filter_by(project_id=project_id, stage_id=5).first()
    wf6 = ProjectWorkflow.query.filter_by(project_id=project_id, stage_id=6).first()
    wf7 = ProjectWorkflow.query.filter_by(project_id=project_id, stage_id=7).first()
    wf8 = ProjectWorkflow.query.filter_by(project_id=project_id, stage_id=8).first()

    d1 = wf1.data if (wf1 and wf1.data) else {}
    d2 = wf2.data if (wf2 and wf2.data) else {}
    d3 = wf3.data if (wf3 and wf3.data) else {}
    d4 = wf4.data if (wf4 and wf4.data) else {}
    d5 = wf5.data if (wf5 and wf5.data) else {}
    d6 = wf6.data if (wf6 and wf6.data) else {}
    d7 = wf7.data if (wf7 and wf7.data) else {}
    d8 = wf8.data if (wf8 and wf8.data) else {}
    
    pdf = DynamicBrandedPDF(org_id=project.org_id, template_key='qc_story')
    pdf.add_page()
    pdf.set_font('Helvetica', 'B', 16)
    pdf.cell(0, 10, f"{pdf.tmpl['header_title']}: {project.title}", 0, 1, 'C')
    pdf.set_font('Helvetica', '', 10)
    pdf.cell(0, 6, f"Project UID: {project.project_uid}  |  Category: {project.category or 'N/A'}", 0, 1, 'C')
    pdf.cell(0, 6, f"Generated At: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC", 0, 1, 'C')
    pdf.ln(10)
    
    def section_header(title):
        pdf.set_font('Helvetica', 'B', 12)
        pdf.set_fill_color(220, 220, 220)
        pdf.cell(0, 8, title, 0, 1, 'L', fill=True)
        pdf.ln(2)
        
    def add_field(label, val):
        pdf.set_font('Helvetica', 'B', 10)
        pdf.cell(60, 6, f"{label}:", 0, 0)
        pdf.set_font('Helvetica', '', 10)
        val_str = str(val) if val is not None else "N/A"
        pdf.multi_cell(0, 6, val_str)
        pdf.ln(1)

    def get_val_safe(obj, data, path, fallback_attr):
        val = None
        if data:
            parts = path.split('.')
            curr = data
            for p in parts:
                if isinstance(curr, dict):
                    curr = curr.get(p)
                else:
                    curr = None
                    break
            val = curr
        if val is None and obj is not None:
            val = getattr(obj, fallback_attr, None)
        return val

    def get_bool_safe(obj, data, path, fallback_attr):
        val = get_val_safe(obj, data, path, fallback_attr)
        if isinstance(val, bool):
            return val
        if isinstance(val, str):
            return val.lower() in ('true', 'yes', 'y', '1')
        return False
        
    def get_list_field(obj, data, attr_name):
        val = None
        if data and isinstance(data, dict):
            val = data.get(attr_name)
        if val is None and obj is not None:
            val = getattr(obj, attr_name, None)
        if isinstance(val, list):
            return val
        if isinstance(val, str):
            import json
            try:
                parsed = json.loads(val)
                if isinstance(parsed, list):
                    return parsed
            except Exception:
                pass
        return []
        
    # --- S0/S1: Plan & Establish Team ---
    section_header("S0 & S1: Plan & Establish Team")
    has_d1 = bool(s1 or d1)
    if has_d1:
        add_field("Project Title", get_val_safe(s1, d1, "init.project_title", "project_title") or project.title)
        add_field("Problem Category", get_val_safe(s1, d1, "init.problem_category", "problem_category") or project.category)
        add_field("Business Unit", get_val_safe(s1, d1, "init.business_unit", "business_unit") or project.work_area)
        add_field("Plant", get_val_safe(s1, d1, "init.plant", "plant") or project.plant)
        add_field("Department", get_val_safe(s1, d1, "init.department", "department") or (project.department.name if project.department else None))
        add_field("Planned Start Date", get_val_safe(s1, d1, "init.planned_start_date", "planned_start_date") or project.start_date)
        add_field("Planned End Date", get_val_safe(s1, d1, "init.planned_end_date", "planned_end_date") or project.end_date)
        add_field("Sponsor", get_val_safe(s1, d1, "init.sponsor_name", "sponsor_name") or project.sponsor)
        add_field("Facilitator", get_val_safe(s1, d1, "init.facilitator_name", "facilitator_name") or (project.facilitator.username if project.facilitator else None))
        add_field("Team Leader", get_val_safe(s1, d1, "init.team_leader_name", "team_leader_name") or (project.team_leader.username if project.team_leader else None))
        add_field("Business Impact", get_val_safe(s1, d1, "justification.financial", "business_impact") or get_val_safe(s1, d1, "justification.why_work_on_this", "business_impact"))
        add_field("Customer Impact", get_val_safe(s1, d1, "justification.customer", "customer_impact"))
        add_field("Quality Impact", get_val_safe(s1, d1, "justification.quality", "quality_impact"))
        add_field("Team Name", get_val_safe(s1, d1, "team.circle_name", "team_name"))
        
        t_members = get_val_safe(s1, d1, "team.team_members", "team_members")
        if t_members:
            pdf.set_font('Helvetica', 'B', 10)
            pdf.cell(0, 6, "Team Members:", 0, 1)
            pdf.set_font('Helvetica', '', 9)
            for m in t_members:
                if isinstance(m, dict):
                    pdf.cell(0, 5, f"- {m.get('name', '')} ({m.get('department', '')}) - Role: {m.get('designation', '')}", 0, 1)
    else:
        pdf.cell(0, 6, "No data available for S0/S1", 0, 1)
    pdf.ln(5)
    
    # --- S2: Define the Problem ---
    section_header("S2: Define and Describe the Problem")
    has_d2 = bool(s2 or d2)
    if has_d2:
        add_field("What Happened", get_val_safe(s2, d2, "background_5w2h.what", "what_happened") or get_val_safe(s1, d1, "background_5w2h.what", "what_happened"))
        add_field("Where Happened", get_val_safe(s2, d2, "background_5w2h.where", "where_happened") or get_val_safe(s1, d1, "background_5w2h.where", "where_happened"))
        add_field("When Happened", get_val_safe(s2, d2, "background_5w2h.when", "when_happened") or get_val_safe(s1, d1, "background_5w2h.when", "when_happened"))
        add_field("Who is Affected", get_val_safe(s2, d2, "background_5w2h.who", "who_is_affected") or get_val_safe(s1, d1, "background_5w2h.who", "who_is_affected"))
        add_field("Why is it a Problem", get_val_safe(s2, d2, "background_5w2h.why", "why_is_it_a_problem") or get_val_safe(s1, d1, "background_5w2h.why", "why_is_it_a_problem"))
        add_field("How was it Discovered", get_val_safe(s2, d2, "background_5w2h.how_discovered", "how_was_it_discovered") or get_val_safe(s1, d1, "background_5w2h.how_discovered", "how_was_it_discovered"))
        add_field("Impact (How much)", get_val_safe(s2, d2, "background_5w2h.how_big", "how_much_impact") or get_val_safe(s1, d1, "background_5w2h.how_big", "how_much_impact"))
        add_field("Gemba Observations", get_val_safe(s2, d2, "process_observation.finding_desc", "gemba_observation") or get_val_safe(s2, d2, "five_g.gemba_notes", "gemba_observation"))
        add_field("Process Walkthrough", get_val_safe(s2, d2, "process_observation.notes", "process_walkthrough"))
        
        def_qty = get_val_safe(s2, d2, "data_collection.histogram_stats.mean", "defective_quantity")
        if not def_qty:
            def_qty = get_val_safe(s2, d2, "current_performance.defect_rate", "defective_quantity")
        add_field("Defective Quantity", def_qty)
        add_field("Defect Rate", get_val_safe(s2, d2, "current_performance.defect_rate", "defect_rate"))
        
        # Process Map
        maps = QCProcessMap.query.filter_by(project_id=project_id).all()
        for m in maps:
            pdf.ln(4)
            pdf.set_font('Helvetica', 'B', 10)
            pdf.cell(0, 6, f"Process Map: {m.title}", 0, 1)
            pdf.set_font('Helvetica', '', 9)
            pdf.multi_cell(0, 5, f"Description: {m.description or 'N/A'}")
            
            steps = QCProcessStep.query.filter_by(process_map_id=m.id).all()
            if steps:
                p_path = plot_process_map(project_id, steps)
                if p_path:
                    pdf.image(p_path, x=15, w=180)
                    pdf.ln(2)
                    temp_files.append(p_path)
                
                pdf.set_font('Helvetica', 'B', 9)
                pdf.cell(20, 6, "Step #", 1, 0)
                pdf.cell(50, 6, "Step Name", 1, 0)
                pdf.cell(30, 6, "Step Type", 1, 0)
                pdf.cell(90, 6, "Description", 1, 1)
                
                pdf.set_font('Helvetica', '', 9)
                for st in sorted(steps, key=lambda x: x.step_number):
                    pdf.cell(20, 6, str(st.step_number), 1, 0)
                    pdf.cell(50, 6, str(st.step_name), 1, 0)
                    pdf.cell(30, 6, str(st.step_type), 1, 0)
                    pdf.multi_cell(90, 6, str(st.description or ''))
                    pdf.ln(1)
            
        # Check Sheets
        sheets = QCCheckSheet.query.filter_by(project_id=project_id).all()
        for s in sheets:
            pdf.ln(4)
            pdf.set_font('Helvetica', 'B', 10)
            pdf.cell(0, 6, f"Check Sheet: {s.name}", 0, 1)
            pdf.set_font('Helvetica', '', 9)
            pdf.multi_cell(0, 5, f"Description: {s.description or 'N/A'}")
            
            rows = QCCheckSheetRow.query.filter_by(check_sheet_id=s.id).all()
            if rows:
                p_path = plot_check_sheet(project_id, s.id, rows)
                if p_path:
                    pdf.image(p_path, x=15, w=150)
                    pdf.ln(2)
                    temp_files.append(p_path)
                
                pdf.set_font('Helvetica', 'B', 9)
                pdf.cell(80, 6, "Category/Defect", 1, 0)
                pdf.cell(40, 6, "Total Count", 1, 0)
                pdf.cell(70, 6, "Notes", 1, 1)
                
                pdf.set_font('Helvetica', '', 9)
                for r in rows:
                    pdf.cell(80, 6, str(r.category_name), 1, 0)
                    pdf.cell(40, 6, str(r.total_count), 1, 0)
                    pdf.cell(70, 6, str(r.notes or ''), 1, 1)
                pdf.ln(2)

        # Stratification
        strats = QCStratification.query.filter_by(project_id=project_id).all()
        for st in strats:
            pdf.ln(4)
            pdf.set_font('Helvetica', 'B', 10)
            pdf.cell(0, 6, f"Stratification: {st.title}", 0, 1)
            pdf.set_font('Helvetica', '', 9)
            pdf.multi_cell(0, 5, f"Description: {st.description or 'N/A'}")
            
            items = QCStratificationItem.query.filter_by(stratification_id=st.id).all()
            if items:
                p_path = plot_stratification(project_id, st.id, items)
                if p_path:
                    pdf.image(p_path, x=15, w=150)
                    pdf.ln(2)
                    temp_files.append(p_path)
                
                pdf.set_font('Helvetica', 'B', 9)
                pdf.cell(70, 6, "Category Name", 1, 0)
                pdf.cell(40, 6, "Value", 1, 0)
                pdf.cell(80, 6, "Group Name", 1, 1)
                
                pdf.set_font('Helvetica', '', 9)
                for it in items:
                    pdf.cell(70, 6, str(it.category_name), 1, 0)
                    pdf.cell(40, 6, str(it.value), 1, 0)
                    pdf.cell(80, 6, str(it.group_name or ''), 1, 1)
                pdf.ln(2)
    else:
        pdf.cell(0, 6, "No data available for S2", 0, 1)
    pdf.ln(5)
    
    # Plot QC Tools if available
    plots = generate_qc_plots(project_id, s2, d2)
    if plots:
        for p in plots.values():
            temp_files.append(p)
        pdf.add_page()
        pdf.set_font('Helvetica', 'B', 12)
        pdf.set_fill_color(220, 220, 220)
        pdf.cell(0, 8, "QC Tools & Graphical Analysis", 0, 1, 'L', fill=True)
        pdf.ln(4)
        
        count = 0
        for name, path in plots.items():
            if count == 2:
                pdf.add_page()
                pdf.set_font('Helvetica', 'B', 12)
                pdf.set_fill_color(220, 220, 220)
                pdf.cell(0, 8, "QC Tools & Graphical Analysis (Continued)", 0, 1, 'L', fill=True)
                pdf.ln(4)
                count = 0
            
            pdf.image(path, x=15, w=180)
            pdf.ln(4)
            count += 1
        pdf.ln(5)
    
    # --- S3: Develop Interim Containment Plan ---
    section_header("S3: Develop and Execute Interim Containment Plan")
    er = d1.get('emergency_response') if isinstance(d1, dict) else {}
    
    escape_details = get_val_safe(s3, d3, "escape_point_details", "escape_point_details")
    sorting = get_bool_safe(s3, d3, "sorting_required", "sorting_required")
    qty_sorted = get_val_safe(s3, d3, "quantity_sorted", "quantity_sorted")
    defects_found = get_val_safe(s3, d3, "defect_found_qty", "defect_found_qty")
    cust_notified = get_bool_safe(s3, d3, "customer_notified", "customer_notified")
    
    c_actions_summary = []
    if er and isinstance(er, dict) and er.get('required') == 'yes':
        action = er.get('action') or ''
        resp = er.get('responsible') or 'N/A'
        sdt = er.get('start_date') or 'N/A'
        cdt = er.get('completion_date') or 'N/A'
        stat = er.get('status') or 'Planned'
        if action:
            c_actions_summary.append(f"- [Emergency Containment] {action} (Owner: {resp}, Start: {sdt}, End: {cdt}) - Status: {stat}")
            
    c_actions = get_val_safe(s3, d3, "containment_actions", "containment_actions")
    if c_actions and isinstance(c_actions, list):
        for a in c_actions:
            if isinstance(a, dict):
                act = a.get('action') or ''
                owner = a.get('owner') or 'N/A'
                dt = a.get('implementation_date') or 'N/A'
                stat = a.get('status') or 'Completed'
                if act:
                    c_actions_summary.append(f"- {act} (Owner: {owner}, Date: {dt}) - Status: {stat}")

    has_d3 = bool(er or escape_details or sorting or qty_sorted or defects_found or cust_notified or c_actions)
    if has_d3:
        add_field("Escape Point Identified", "Yes" if escape_details else ("Yes" if sorting else "No"))
        add_field("Escape Point Details", escape_details)
        add_field("Sorting Required", "Yes" if sorting else "No")
        add_field("Quantity Sorted", qty_sorted)
        add_field("Defects Found Quantity", defects_found)
        add_field("Customer Notified", "Yes" if cust_notified else "No")
        
        if c_actions_summary:
            pdf.set_font('Helvetica', 'B', 10)
            pdf.cell(0, 6, "Containment Actions Log:", 0, 1)
            pdf.set_font('Helvetica', '', 9)
            for item in c_actions_summary:
                pdf.multi_cell(0, 5, item)
                pdf.ln(1)
    else:
        pdf.cell(0, 6, "No data available for S3", 0, 1)
    pdf.ln(5)
    
    # --- S4: Identify Root Causes ---
    section_header("S4: Determine, Identify and Verify Root Causes")
    has_d4 = bool(s4 or d4)
    if has_d4:
        add_field("Occurrence Root Cause", get_val_safe(s4, d4, "occurrence_root_cause", "occurrence_root_cause"))
        add_field("Escape Root Cause", get_val_safe(s4, d4, "escape_root_cause", "escape_root_cause"))
        
        # 5-Why Analysis
        pdf.set_font('Helvetica', 'B', 10)
        pdf.cell(0, 6, "5-Why Analysis:", 0, 1)
        pdf.set_font('Helvetica', '', 9)
        why_analysis = get_val_safe(s4, d4, "why_why_analysis", "why_why_analysis")
        if why_analysis and isinstance(why_analysis, list) and len(why_analysis) > 0:
            first_why = why_analysis[0]
            pdf.cell(0, 5, f"Why 1: {first_why.get('why1') or 'N/A'}", 0, 1)
            pdf.cell(0, 5, f"Why 2: {first_why.get('why2') or 'N/A'}", 0, 1)
            pdf.cell(0, 5, f"Why 3: {first_why.get('why3') or 'N/A'}", 0, 1)
            pdf.cell(0, 5, f"Why 4: {first_why.get('why4') or 'N/A'}", 0, 1)
            pdf.cell(0, 5, f"Why 5: {first_why.get('why5') or 'N/A'}", 0, 1)
        else:
            pdf.cell(0, 5, f"Why 1: {get_val_safe(s4, d4, 'why1', 'why1') or 'N/A'}", 0, 1)
            pdf.cell(0, 5, f"Why 2: {get_val_safe(s4, d4, 'why2', 'why2') or 'N/A'}", 0, 1)
            pdf.cell(0, 5, f"Why 3: {get_val_safe(s4, d4, 'why3', 'why3') or 'N/A'}", 0, 1)
            pdf.cell(0, 5, f"Why 4: {get_val_safe(s4, d4, 'why4', 'why4') or 'N/A'}", 0, 1)
            pdf.cell(0, 5, f"Why 5: {get_val_safe(s4, d4, 'why5', 'why5') or 'N/A'}", 0, 1)
        
        v_causes = get_val_safe(s4, d4, "verified_root_causes", "verified_root_causes") or get_val_safe(s4, d4, "verified_causes", "verified_root_causes")
        if v_causes:
            pdf.set_font('Helvetica', 'B', 10)
            pdf.cell(0, 6, "Verified Root Causes:", 0, 1)
            pdf.set_font('Helvetica', '', 9)
            for cause in v_causes:
                if isinstance(cause, dict):
                    pdf.cell(0, 5, f"- Cause: {cause.get('cause', '')} | Evidence: {cause.get('evidence', '')} | Verified by: {cause.get('verified_by', '')}", 0, 1)
                    
        # Pareto Charts
        pareto_charts = QCParetoChart.query.filter_by(project_id=project_id).all()
        for pc in pareto_charts:
            pdf.ln(4)
            pdf.set_font('Helvetica', 'B', 10)
            pdf.cell(0, 6, f"Pareto Chart: {pc.title}", 0, 1)
            pdf.set_font('Helvetica', '', 9)
            pdf.multi_cell(0, 5, f"Description: {pc.description or 'N/A'}")
            
            items = QCParetoItem.query.filter_by(pareto_chart_id=pc.id).order_by(QCParetoItem.priority_rank).all()
            if items:
                p_path = plot_pareto_chart(project_id, pc.id, items)
                if p_path:
                    pdf.image(p_path, x=15, w=150)
                    pdf.ln(2)
                    temp_files.append(p_path)
                
                pdf.set_font('Helvetica', 'B', 9)
                pdf.cell(80, 6, "Cause Name", 1, 0)
                pdf.cell(30, 6, "Frequency", 1, 0)
                pdf.cell(40, 6, "Cumulative %", 1, 0)
                pdf.cell(40, 6, "Rank", 1, 1)
                
                pdf.set_font('Helvetica', '', 9)
                for it in items:
                    pdf.cell(80, 6, str(it.cause_name), 1, 0)
                    pdf.cell(30, 6, str(it.frequency), 1, 0)
                    pdf.cell(40, 6, f"{it.cumulative_pct:.1f}%" if it.cumulative_pct else "0.0%", 1, 0)
                    pdf.cell(40, 6, str(it.priority_rank), 1, 1)
                pdf.ln(2)

        # Fishbone Diagrams
        fishbones = QCFishboneDiagram.query.filter_by(project_id=project_id).all()
        for fb in fishbones:
            pdf.ln(4)
            pdf.set_font('Helvetica', 'B', 10)
            pdf.cell(0, 6, f"Fishbone Diagram: {fb.effect}", 0, 1)
            
            branches = QCFishboneBranch.query.filter_by(fishbone_id=fb.id).all()
            if branches:
                p_path = plot_fishbone(project_id, fb.id, fb.effect, branches)
                if p_path:
                    pdf.image(p_path, x=15, w=180)
                    pdf.ln(2)
                    temp_files.append(p_path)
                
                categories = ['Man', 'Machine', 'Material', 'Method', 'Measurement', 'Environment']
                for cat in categories:
                    pdf.set_font('Helvetica', 'B', 9)
                    pdf.cell(0, 6, f"Category: {cat}", 0, 1)
                    pdf.set_font('Helvetica', '', 9)
                    cat_branches = [b for b in branches if b.category.lower() == cat.lower()]
                    if not cat_branches:
                        pdf.cell(0, 5, "  (None)", 0, 1)
                    for cb in cat_branches:
                        pdf.cell(0, 5, f"  - {cb.text}", 0, 1)
                    pdf.ln(1)
                pdf.ln(2)

        # Scatter Diagrams
        scatters = QCScatterDiagram.query.filter_by(project_id=project_id).all()
        for sc in scatters:
            pdf.ln(4)
            pdf.set_font('Helvetica', 'B', 10)
            pdf.cell(0, 6, f"Scatter Diagram: {sc.x_axis_label} vs {sc.y_axis_label}", 0, 1)
            pdf.set_font('Helvetica', '', 9)
            pdf.cell(0, 6, f"Correlation Coefficient (R): {sc.correlation_coefficient or 0.0} | Correlation Type: {sc.correlation_type or 'None'}", 0, 1)
            
            points = QCScatterPoint.query.filter_by(scatter_diagram_id=sc.id).all()
            if points:
                p_path = plot_scatter_diagram(project_id, sc.id, sc.x_axis_label, sc.y_axis_label, points)
                if p_path:
                    pdf.image(p_path, x=15, w=150)
                    pdf.ln(2)
                    temp_files.append(p_path)
                
                pdf.set_font('Helvetica', 'B', 9)
                pdf.cell(60, 6, f"X: {sc.x_axis_label}", 1, 0)
                pdf.cell(60, 6, f"Y: {sc.y_axis_label}", 1, 0)
                pdf.cell(70, 6, "Remarks", 1, 1)
                
                pdf.set_font('Helvetica', '', 9)
                for pt in points:
                    pdf.cell(60, 6, f"{pt.x_value:.2f}", 1, 0)
                    pdf.cell(60, 6, f"{pt.y_value:.2f}", 1, 0)
                    pdf.cell(70, 6, str(pt.remarks or ''), 1, 1)
                pdf.ln(2)
    else:
        pdf.cell(0, 6, "No data available for S4", 0, 1)
    pdf.ln(5)
    
    # --- S5: Permanent Corrections ---
    section_header("S5: Choose and Verify Permanent Corrections")
    has_d5 = bool(s5 or d5)
    if has_d5:
        mapping_list = get_list_field(s5, d5, "root_cause_mapping")
        mapping_summary = []
        for m in mapping_list:
            rc = m.get('root_cause') or ''
            sol = m.get('proposed_solution') or ''
            if rc or sol:
                mapping_summary.append(f"- Root Cause: {rc} -> Proposed Countermeasure: {sol}")

        eval_list = get_list_field(s5, d5, "solution_evaluation")
        eval_summary = []
        for e in eval_list:
            sol = e.get('solution') or ''
            eff = e.get('effectiveness') or 'N/A'
            cst = e.get('cost') or 'N/A'
            fea = e.get('feasibility') or 'N/A'
            tim = e.get('time') or 'N/A'
            tot = e.get('total_score') or 'N/A'
            if sol:
                eval_summary.append(f"- {sol} (Effectiveness: {eff}, Cost: {cst}, Feasibility: {fea}, Time: {tim}, Score: {tot})")
        
        cba_list = get_list_field(s5, d5, "cost_benefit_analysis")
        cba_summary = []
        for c in cba_list:
            sol = c.get('solution') or ''
            cst = c.get('estimated_cost') or 'N/A'
            ben = c.get('expected_benefit') or 'N/A'
            roi = c.get('roi') or 'N/A'
            if sol:
                cba_summary.append(f"- {sol} (Estimated Cost: {cst}, Benefit: {ben}, ROI: {roi})")
                
        se_list = get_list_field(s5, d5, "side_effect_analysis")
        se_summary = []
        for s in se_list:
            sol = s.get('solution') or ''
            risk = s.get('potential_risk') or 'N/A'
            plan = s.get('mitigation_plan') or 'N/A'
            if sol:
                se_summary.append(f"- {sol} (Potential Risk: {risk}, Mitigation: {plan})")

        feasibility = get_val_safe(s5, d5, "feasibility_score", "feasibility_score")
        cost_est = get_val_safe(s5, d5, "cost_estimate", "cost_estimate")
        risk_ass = get_val_safe(s5, d5, "risk_assessment", "risk_assessment")
        eff_est = get_val_safe(s5, d5, "effectiveness_estimate", "effectiveness_estimate")
        impl_cost = get_val_safe(s5, d5, "implementation_cost", "implementation_cost")
        ann_savings = get_val_safe(s5, d5, "annual_savings", "annual_savings")
        roi_val = get_val_safe(s5, d5, "roi_percentage", "roi_percentage")

        if mapping_summary:
            pdf.set_font('Helvetica', 'B', 10)
            pdf.cell(0, 6, "Proposed Countermeasures Mapping:", 0, 1)
            pdf.set_font('Helvetica', '', 9)
            for m in mapping_summary:
                pdf.multi_cell(0, 5, m)
                pdf.ln(1)
        else:
            p_actions = get_val_safe(s5, d5, "permanent_actions", "permanent_actions")
            if p_actions and isinstance(p_actions, list):
                pdf.set_font('Helvetica', 'B', 10)
                pdf.cell(0, 6, "Permanent Actions:", 0, 1)
                pdf.set_font('Helvetica', '', 9)
                for a in p_actions:
                    if isinstance(a, dict):
                        pdf.cell(0, 5, f"- {a.get('action', '') or a.get('solution', '')} (Status: {a.get('status', 'Selected')})", 0, 1)

        if eval_summary:
            pdf.set_font('Helvetica', 'B', 10)
            pdf.cell(0, 6, "Solutions Feasibility & Evaluation:", 0, 1)
            pdf.set_font('Helvetica', '', 9)
            for item in eval_summary:
                pdf.multi_cell(0, 5, item)
                pdf.ln(1)
        else:
            if feasibility:
                add_field("Feasibility Score", feasibility)
            if risk_ass:
                add_field("Risk Assessment", risk_ass)
            if eff_est:
                add_field("Effectiveness Estimate (%)", eff_est)

        if cba_summary:
            pdf.set_font('Helvetica', 'B', 10)
            pdf.cell(0, 6, "Cost Benefit & ROI Analysis:", 0, 1)
            pdf.set_font('Helvetica', '', 9)
            for item in cba_summary:
                pdf.multi_cell(0, 5, item)
                pdf.ln(1)
        else:
            if cost_est:
                add_field("Cost Estimate (INR)", cost_est)
            if impl_cost:
                add_field("Implementation Cost (INR)", impl_cost)
            if ann_savings:
                add_field("Annual Savings (INR)", ann_savings)
            if roi_val:
                add_field("ROI (%)", roi_val)

        if se_summary:
            pdf.set_font('Helvetica', 'B', 10)
            pdf.cell(0, 6, "Risk & Mitigation Analysis:", 0, 1)
            pdf.set_font('Helvetica', '', 9)
            for item in se_summary:
                pdf.multi_cell(0, 5, item)
                pdf.ln(1)
    else:
        pdf.cell(0, 6, "No data available for S5", 0, 1)
    pdf.ln(5)
    
    # --- S6: Implement Corrective Actions ---
    section_header("S6: Implement and Validate Corrective Actions")
    has_d6 = bool(s6 or d6)
    if has_d6:
        # Render Countermeasures
        cms = d6.get('countermeasures') or d6.get('implementation_execution') or []
        if cms:
            pdf.set_font('Helvetica', 'B', 10)
            pdf.cell(0, 6, "Countermeasures & Execution:", 0, 1)
            pdf.set_font('Helvetica', '', 9)
            for cm in cms:
                if isinstance(cm, dict):
                    name = cm.get('countermeasure') or cm.get('action') or ''
                    owner = cm.get('owner') or ''
                    sdt = cm.get('start_date') or cm.get('target_date') or ''
                    edt = cm.get('end_date') or cm.get('actual_date') or ''
                    status = cm.get('status') or ''
                    pdf.cell(0, 5, f"- {name} (Owner: {owner}, Start: {sdt}, End: {edt}) - Status: {status}", 0, 1)
            pdf.ln(2)

        # Render Task Assignments
        tasks = d6.get('countermeasure_task_assignments') or d6.get('task_management') or []
        if tasks:
            pdf.set_font('Helvetica', 'B', 10)
            pdf.cell(0, 6, "Countermeasure Task Assignments:", 0, 1)
            pdf.set_font('Helvetica', '', 9)
            for t in tasks:
                if isinstance(t, dict):
                    cm_ref = t.get('countermeasure_ref') or t.get('countermeasure') or ''
                    task_desc = t.get('task') or ''
                    assignee = t.get('assignee') or ''
                    due = t.get('due_date') or ''
                    pct = t.get('completion_pct') or ''
                    pdf.cell(0, 5, f"- [Ref: {cm_ref}] Task: {task_desc} (Assignee: {assignee}, Due: {due}, Completion: {pct}%)", 0, 1)
            pdf.ln(2)

        # Render Resource Deployment
        resources = d6.get('resource_deployment') or []
        if resources:
            pdf.set_font('Helvetica', 'B', 10)
            pdf.cell(0, 6, "Resource Deployment:", 0, 1)
            pdf.set_font('Helvetica', '', 9)
            for r in resources:
                if isinstance(r, dict):
                    res = r.get('resource') or ''
                    p_cost = r.get('planned_cost') or ''
                    a_cost = r.get('actual_cost') or ''
                    var = r.get('variance') or ''
                    pdf.cell(0, 5, f"- Resource: {res} | Planned Cost: {p_cost} | Actual Cost: {a_cost} | Variance: {var}", 0, 1)
            pdf.ln(2)

        # Render Change Management
        changes = d6.get('change_management') or []
        if changes:
            pdf.set_font('Helvetica', 'B', 10)
            pdf.cell(0, 6, "Change Management:", 0, 1)
            pdf.set_font('Helvetica', '', 9)
            for ch in changes:
                if isinstance(ch, dict):
                    desc = ch.get('change_description') or ''
                    sop = ch.get('sop_updated') or ''
                    dt = ch.get('date') or ''
                    pdf.cell(0, 5, f"- Change: {desc} (SOP Updated: {sop}, Date: {dt})", 0, 1)
            pdf.ln(2)

        # Render Risk & Resistance
        risks = d6.get('risk_resistance') or []
        if risks:
            pdf.set_font('Helvetica', 'B', 10)
            pdf.cell(0, 6, "Risk & Resistance Management:", 0, 1)
            pdf.set_font('Helvetica', '', 9)
            for rk in risks:
                if isinstance(rk, dict):
                    risk = rk.get('anticipated_risk') or ''
                    strategy = rk.get('strategy_executed') or ''
                    status = rk.get('status') or ''
                    pdf.cell(0, 5, f"- Risk: {risk} | Strategy: {strategy} | Status: {status}", 0, 1)
            pdf.ln(2)

        # Render Side Effects
        se = d6.get('side_effect_analysis') or []
        if se:
            pdf.set_font('Helvetica', 'B', 10)
            pdf.cell(0, 6, "Side Effect Analysis:", 0, 1)
            pdf.set_font('Helvetica', '', 9)
            for item in se:
                if isinstance(item, dict):
                    desc = item.get('description') or ''
                    impact = item.get('impact_level') or ''
                    mit = item.get('mitigation') or ''
                    mod = item.get('plan_modification_required') or 'N'
                    pdf.cell(0, 5, f"- Side Effect: {desc} (Impact: {impact}) | Mitigation: {mit} | Plan Mod Required: {mod}", 0, 1)
            pdf.ln(2)

        # Render Implementation Evidence
        evidence = d6.get('implementation_evidence') or []
        if evidence:
            pdf.set_font('Helvetica', 'B', 10)
            pdf.cell(0, 6, "Implementation Evidence:", 0, 1)
            pdf.set_font('Helvetica', '', 9)
            for ev in evidence:
                if isinstance(ev, dict):
                    doc_name = ev.get('document_name') or ''
                    link = ev.get('link') or ''
                    uploaded_by = ev.get('uploaded_by') or ''
                    pdf.cell(0, 5, f"- Doc: {doc_name} (Uploaded By: {uploaded_by}) | Link: {link}", 0, 1)
            pdf.ln(2)

        # Render Communication & Training
        comm_tr = d6.get('communication_training') or {}
        comms = comm_tr.get('communication_log') or d6.get('communication_log') or []
        trainings = comm_tr.get('training_awareness') or d6.get('training_awareness') or []
        
        if comms:
            pdf.set_font('Helvetica', 'B', 10)
            pdf.cell(0, 6, "Communication Log:", 0, 1)
            pdf.set_font('Helvetica', '', 9)
            for c in comms:
                if isinstance(c, dict):
                    stk = c.get('stakeholder') or ''
                    msg = c.get('message') or ''
                    dt = c.get('date') or ''
                    chn = c.get('channel') or ''
                    pdf.cell(0, 5, f"- Stakeholder: {stk} | Msg: {msg} (Date: {dt}, Channel: {chn})", 0, 1)
            pdf.ln(2)

        if trainings:
            pdf.set_font('Helvetica', 'B', 10)
            pdf.cell(0, 6, "Training & Awareness:", 0, 1)
            pdf.set_font('Helvetica', '', 9)
            for tr in trainings:
                if isinstance(tr, dict):
                    tgt = tr.get('target_group') or ''
                    mod_name = tr.get('training_module') or ''
                    dt = tr.get('date') or ''
                    att = tr.get('attendance_pct') or ''
                    pdf.cell(0, 5, f"- Target Group: {tgt} | Module: {mod_name} (Date: {dt}, Attendance: {att}%)", 0, 1)
            pdf.ln(2)

        # Render Readiness Verification
        readiness = d6.get('readiness_verification') or []
        if readiness:
            pdf.set_font('Helvetica', 'B', 10)
            pdf.cell(0, 6, "Readiness Verification Checklist:", 0, 1)
            pdf.set_font('Helvetica', '', 9)
            for rd in readiness:
                if isinstance(rd, dict):
                    itm = rd.get('item') or ''
                    ver = rd.get('verified_by') or ''
                    stat = rd.get('status') or ''
                    pdf.cell(0, 5, f"- Item: {itm} (Verified By: {ver}) - Status: {stat}", 0, 1)
            pdf.ln(2)
            
    else:
        pdf.cell(0, 6, "No data available for S6", 0, 1)
    pdf.ln(5)
    
    # --- S7: Take Preventive Measures ---
    section_header("S7: Take Preventive Measures")
    # Both D7 (preventive measures/standardization) and D8 (closure) are driven by Stage 8 data
    has_d7 = bool(s8 or d8)
    if has_d7:
        std_rows = get_list_field(s8, d8, 'standardization')
        
        def find_std_doc(keywords):
            for r in std_rows:
                doc_name = str(r.get('document') or '').lower()
                if any(k in doc_name for k in keywords):
                    prev_v = r.get('previous_version') or 'N/A'
                    new_v = r.get('new_version') or 'N/A'
                    dt = r.get('update_date') or 'N/A'
                    return f"{r.get('document')} (Prev: {prev_v} -> New: {new_v}) on {dt}"
            return None

        sop_ref = find_std_doc(['sop', 'standard', 'operating'])
        if not sop_ref:
            from app.infrastructure.database.models.models import SOP
            sop = SOP.query.filter_by(project_id=project_id).first()
            if sop:
                sop_ref = f"{sop.title} (UID: {sop.sop_uid})"
                
        cp_ref = find_std_doc(['control plan', 'cp', 'control'])
        pfmea_ref = find_std_doc(['pfmea', 'fmea'])
        drawing_ref = find_std_doc(['drawing', 'blueprint', 'layout'])
        checklist_ref = find_std_doc(['checklist', 'check sheet'])

        sop_evidence = None
        for r in std_rows:
            doc_val = str(r.get('document') or '')
            if doc_val.startswith('http://') or doc_val.startswith('https://'):
                sop_evidence = doc_val
                break
        if not sop_evidence:
            from app.infrastructure.database.models.models import SOP
            sop = SOP.query.filter_by(project_id=project_id).first()
            if sop:
                sop_evidence = f"/projects/standards.html?prefill_project_id={project_id}"

        training_rows = get_list_field(s8, d8, 'training_adoption')
        training_summary = None
        if training_rows:
            summaries = []
            for r in training_rows:
                grp = r.get('target_group') or ''
                dt = r.get('training_date') or 'N/A'
                att = r.get('attendance_pct') or '0'
                adp = r.get('adoption_status') or 'Pending'
                summaries.append(f"{grp} (Date: {dt}, Attendance: {att}%, Status: {adp})")
            training_summary = ", ".join(summaries)

        add_field("SOP Update Reference", sop_ref)
        add_field("Control Plan Update Reference", cp_ref)
        add_field("PFMEA Update Reference", pfmea_ref)
        add_field("Drawing Update Reference", drawing_ref)
        add_field("Checklist Update Reference", checklist_ref)
        add_field("SOP Evidence URL", sop_evidence)
        add_field("Training Records URL", training_summary)
        
        # Control Charts
        controls = QCControlChart.query.filter_by(project_id=project_id).all()
        for cc in controls:
            pdf.ln(4)
            pdf.set_font('Helvetica', 'B', 10)
            pdf.cell(0, 6, f"Control Chart: {cc.title} ({cc.chart_type})", 0, 1)
            pdf.set_font('Helvetica', '', 9)
            pdf.cell(0, 6, f"Mean: {cc.mean or 0.0:.3f} | UCL: {cc.ucl or 0.0:.3f} | LCL: {cc.lcl or 0.0:.3f}", 0, 1)
            
            points = QCControlPoint.query.filter_by(control_chart_id=cc.id).order_by(QCControlPoint.sample_index).all()
            if points:
                p_path = plot_control_chart(project_id, cc.id, cc.mean, cc.ucl, cc.lcl, points)
                if p_path:
                    pdf.image(p_path, x=15, w=150)
                    pdf.ln(2)
                    temp_files.append(p_path)
                
                pdf.set_font('Helvetica', 'B', 9)
                pdf.cell(60, 6, "Sample Index", 1, 0)
                pdf.cell(60, 6, "Value", 1, 0)
                pdf.cell(70, 6, "Out of Control?", 1, 1)
                
                pdf.set_font('Helvetica', '', 9)
                for pt in points:
                    pdf.cell(60, 6, str(pt.sample_index), 1, 0)
                    pdf.cell(60, 6, f"{pt.value:.3f}", 1, 0)
                    pdf.cell(70, 6, "YES" if pt.is_out_of_control else "No", 1, 1)
                pdf.ln(2)
    else:
        pdf.cell(0, 6, "No data available for S7", 0, 1)
    pdf.ln(5)
    
    # --- S8: Congratulate Team & Closure ---
    section_header("S8: Congratulate Team and Project Closure")
    has_d8 = bool(s8 or d8)
    if has_d8:
        lessons_rows = get_list_field(s8, d8, 'lessons_learned')
        what_worked_summary = None
        if lessons_rows:
            summaries = []
            for r in lessons_rows:
                cat = r.get('category') or ''
                les = r.get('lesson') or ''
                rec = r.get('future_recommendation') or ''
                summaries.append(f"{cat}: {les} (Recommendation: {rec})")
            what_worked_summary = "; ".join(summaries)

        opp_rows = get_list_field(s8, d8, 'remaining_opportunities')
        what_failed_summary = None
        if opp_rows:
            summaries = []
            for r in opp_rows:
                prob = r.get('identified_problem') or ''
                pri = r.get('priority') or 'N/A'
                nxt = r.get('next_steps') or ''
                summaries.append(f"Problem: {prob} (Priority: {pri}, Next Steps: {nxt})")
            what_failed_summary = "; ".join(summaries)

        team_rows = get_list_field(s8, d8, 'team_recognition')
        ee_summary = None
        if team_rows:
            summaries = []
            for r in team_rows:
                mem = r.get('member') or ''
                con = r.get('contribution') or ''
                awd = r.get('award') or 'None'
                summaries.append(f"{mem} - Contribution: {con} (Award: {awd})")
            ee_summary = "; ".join(summaries)

        repo_rows = get_list_field(s8, d8, 'knowledge_repository')
        ks_summary = None
        if repo_rows:
            summaries = []
            for r in repo_rows:
                kw = r.get('keyword') or ''
                sum_val = r.get('summary') or ''
                lnk = r.get('link') or 'N/A'
                summaries.append(f"{kw}: {sum_val} (Link: {lnk})")
            ks_summary = "; ".join(summaries)

        closure_data = None
        if d8 and isinstance(d8, dict):
            closure_data = d8.get('project_closure')
        if not closure_data and s8 is not None:
            closure_data = getattr(s8, 'project_closure', None)
        
        closure_summary = None
        if closure_data and isinstance(closure_data, dict):
            handover = closure_data.get('handover_to') or 'N/A'
            status_val = closure_data.get('final_status') or 'Closed'
            dt = closure_data.get('end_date') or 'N/A'
            closure_summary = f"Handover To: {handover} | Final Status: {status_val} | Date: {dt}"

        add_field("What Worked", what_worked_summary)
        add_field("What Failed", what_failed_summary)
        add_field("Best Practices", what_worked_summary)
        add_field("Employee Engagement", ee_summary)
        add_field("Teamwork Improvement", ee_summary)
        add_field("Knowledge Sharing", ks_summary)
        add_field("Congratulation Notes", ee_summary)
        add_field("Closure Report", closure_summary)
    else:
        pdf.cell(0, 6, "No data available for D8", 0, 1)
    
    pdf_bytes = pdf.output()
    for p in temp_files:
        try:
            import os
            if os.path.exists(p):
                os.remove(p)
        except Exception:
            pass
    return pdf_bytes

def generate_qc_tool_report(project_id, tool_name):
    from app.infrastructure.database.models.models import (
        Project, QCCheckSheet, QCCheckSheetRow, QCParetoChart, QCParetoItem,
        QCFishboneDiagram, QCFishboneBranch, QCScatterDiagram, QCScatterPoint,
        QCControlChart, QCControlPoint, QCStratification, QCStratificationItem,
        QCProcessMap, QCProcessStep
    )
    
    project = Project.query.get(project_id)
    if not project:
        return None
        
    pdf = DynamicBrandedPDF(org_id=project.org_id, template_key='qc_story')
    pdf.add_page()
    pdf.set_font('Helvetica', 'B', 16)
    pdf.cell(0, 10, f"{pdf.tmpl['header_title']}: {tool_name.upper()}", 0, 1, 'C')
    pdf.set_font('Helvetica', '', 11)
    pdf.cell(0, 6, f"Project: {project.title} (UID: {project.project_uid})", 0, 1, 'C')
    pdf.ln(10)
    
    tool_name = tool_name.lower()
    
    if tool_name == 'check_sheet' or tool_name == 'checksheet':
        sheets = QCCheckSheet.query.filter_by(project_id=project_id).all()
        if not sheets:
            pdf.cell(0, 10, "No Check Sheets found for this project.", 0, 1)
        for s in sheets:
            pdf.set_font('Helvetica', 'B', 12)
            pdf.cell(0, 8, f"Check Sheet: {s.name}", 0, 1)
            pdf.set_font('Helvetica', '', 10)
            pdf.cell(0, 6, f"Description: {s.description or 'N/A'}", 0, 1)
            pdf.ln(2)
            
            # Print table headers
            pdf.set_font('Helvetica', 'B', 10)
            pdf.cell(80, 8, "Category/Defect", 1, 0)
            pdf.cell(40, 8, "Total Count", 1, 0)
            pdf.cell(70, 8, "Notes", 1, 1)
            
            pdf.set_font('Helvetica', '', 10)
            rows = QCCheckSheetRow.query.filter_by(check_sheet_id=s.id).all()
            for r in rows:
                pdf.cell(80, 8, str(r.category_name), 1, 0)
                pdf.cell(40, 8, str(r.total_count), 1, 0)
                pdf.cell(70, 8, str(r.notes or ''), 1, 1)
            pdf.ln(10)
            
    elif tool_name == 'pareto':
        charts = QCParetoChart.query.filter_by(project_id=project_id).all()
        if not charts:
            pdf.cell(0, 10, "No Pareto Charts found for this project.", 0, 1)
        for c in charts:
            pdf.set_font('Helvetica', 'B', 12)
            pdf.cell(0, 8, f"Pareto Chart: {c.title}", 0, 1)
            pdf.set_font('Helvetica', '', 10)
            pdf.cell(0, 6, f"Description: {c.description or 'N/A'}", 0, 1)
            pdf.cell(0, 6, f"Total Defect Count: {c.total_count}", 0, 1)
            pdf.ln(2)
            
            # Headers
            pdf.set_font('Helvetica', 'B', 10)
            pdf.cell(70, 8, "Cause Name", 1, 0)
            pdf.cell(40, 8, "Frequency", 1, 0)
            pdf.cell(40, 8, "Cumulative %", 1, 0)
            pdf.cell(40, 8, "Rank", 1, 1)
            
            pdf.set_font('Helvetica', '', 10)
            items = QCParetoItem.query.filter_by(pareto_chart_id=c.id).order_by(QCParetoItem.priority_rank).all()
            for item in items:
                pdf.cell(70, 8, str(item.cause_name), 1, 0)
                pdf.cell(40, 8, str(item.frequency), 1, 0)
                pdf.cell(40, 8, f"{item.cumulative_pct:.1f}%" if item.cumulative_pct else "0.0%", 1, 0)
                pdf.cell(40, 8, str(item.priority_rank), 1, 1)
            pdf.ln(10)
            
    elif tool_name == 'fishbone':
        diags = QCFishboneDiagram.query.filter_by(project_id=project_id).all()
        if not diags:
            pdf.cell(0, 10, "No Fishbone Diagrams found for this project.", 0, 1)
        for d in diags:
            pdf.set_font('Helvetica', 'B', 12)
            pdf.cell(0, 8, f"Fishbone Effect: {d.effect}", 0, 1)
            pdf.ln(2)
            
            branches = QCFishboneBranch.query.filter_by(fishbone_id=d.id).all()
            categories = ['Man', 'Machine', 'Material', 'Method', 'Measurement', 'Environment']
            for cat in categories:
                pdf.set_font('Helvetica', 'B', 10)
                pdf.cell(0, 6, f"Category: {cat}", 0, 1)
                pdf.set_font('Helvetica', '', 10)
                cat_branches = [b for b in branches if b.category.lower() == cat.lower()]
                if not cat_branches:
                    pdf.cell(0, 5, "  (None)", 0, 1)
                for cb in cat_branches:
                    pdf.cell(0, 5, f"  - {cb.text}", 0, 1)
                pdf.ln(2)
            pdf.ln(10)
            
    elif tool_name == 'scatter':
        diags = QCScatterDiagram.query.filter_by(project_id=project_id).all()
        if not diags:
            pdf.cell(0, 10, "No Scatter Diagrams found for this project.", 0, 1)
        for d in diags:
            pdf.set_font('Helvetica', 'B', 12)
            pdf.cell(0, 8, "Scatter Diagram Analysis", 0, 1)
            pdf.set_font('Helvetica', '', 10)
            pdf.cell(0, 6, f"X-Axis Label: {d.x_axis_label or 'X'}", 0, 1)
            pdf.cell(0, 6, f"Y-Axis Label: {d.y_axis_label or 'Y'}", 0, 1)
            pdf.cell(0, 6, f"Correlation Coefficient (R): {d.correlation_coefficient or 0.0}", 0, 1)
            pdf.cell(0, 6, f"Correlation Type: {d.correlation_type or 'None'}", 0, 1)
            pdf.ln(2)
            
            # Print points
            pdf.set_font('Helvetica', 'B', 10)
            pdf.cell(60, 8, f"X Value ({d.x_axis_label or 'X'})", 1, 0)
            pdf.cell(60, 8, f"Y Value ({d.y_axis_label or 'Y'})", 1, 0)
            pdf.cell(70, 8, "Remarks", 1, 1)
            
            pdf.set_font('Helvetica', '', 10)
            points = QCScatterPoint.query.filter_by(scatter_diagram_id=d.id).all()
            for p in points:
                pdf.cell(60, 8, f"{p.x_value:.2f}", 1, 0)
                pdf.cell(60, 8, f"{p.y_value:.2f}", 1, 0)
                pdf.cell(70, 8, str(p.remarks or ''), 1, 1)
            pdf.ln(10)
            
    elif tool_name == 'control_chart' or tool_name == 'controlchart':
        charts = QCControlChart.query.filter_by(project_id=project_id).all()
        if not charts:
            pdf.cell(0, 10, "No Control Charts found for this project.", 0, 1)
        for c in charts:
            pdf.set_font('Helvetica', 'B', 12)
            pdf.cell(0, 8, f"Control Chart: {c.title}", 0, 1)
            pdf.set_font('Helvetica', '', 10)
            pdf.cell(0, 6, f"Chart Type: {c.chart_type}", 0, 1)
            pdf.cell(0, 6, f"Mean: {c.mean or 0.0:.3f}  |  UCL: {c.ucl or 0.0:.3f}  |  LCL: {c.lcl or 0.0:.3f}", 0, 1)
            pdf.ln(2)
            
            # Points
            pdf.set_font('Helvetica', 'B', 10)
            pdf.cell(60, 8, "Sample Index", 1, 0)
            pdf.cell(60, 8, "Value", 1, 0)
            pdf.cell(70, 8, "Out of Control?", 1, 1)
            
            pdf.set_font('Helvetica', '', 10)
            points = QCControlPoint.query.filter_by(control_chart_id=c.id).order_by(QCControlPoint.sample_index).all()
            for p in points:
                pdf.cell(60, 8, str(p.sample_index), 1, 0)
                pdf.cell(60, 8, f"{p.value:.3f}", 1, 0)
                pdf.cell(70, 8, "YES" if p.is_out_of_control else "No", 1, 1)
            pdf.ln(10)
            
    else:
        pdf.cell(0, 10, f"QC Tool report for '{tool_name}' is not currently formatted as standard tabular data.", 0, 1)
        
    return pdf.output()
def generate_sop_pdf_report(sop):
    org_id = getattr(sop, 'org_id', None)
    pdf = DynamicBrandedPDF(org_id=org_id, template_key='audit')
    pdf.add_page()
    pdf.set_font('Helvetica', 'B', 16)
    pdf.cell(0, 10, f"{pdf.tmpl['header_title']}: STANDARD OPERATING PROCEDURE (SOP)", 0, 1, 'C')
    pdf.set_font('Helvetica', '', 10)
    pdf.cell(0, 6, f"Document ID: {sop.sop_uid}  |  Version: {sop.version}  |  Status: {sop.status}", 0, 1, 'C')
    pdf.cell(0, 6, f"Generated At: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC", 0, 1, 'C')
    pdf.ln(10)

    def section_header(title):
        pdf.set_font('Helvetica', 'B', 12)
        pdf.set_fill_color(220, 220, 220)
        pdf.cell(0, 8, title, 0, 1, 'L', fill=True)
        pdf.ln(2)
        
    def add_field(label, val):
        pdf.set_font('Helvetica', 'B', 10)
        pdf.cell(60, 6, f"{label}:", 0, 0)
        pdf.set_font('Helvetica', '', 10)
        val_str = str(val) if val is not None else "N/A"
        pdf.multi_cell(0, 6, val_str)
        pdf.ln(1)

    # --- Document Metadata ---
    section_header("SOP General Metadata")
    add_field("SOP Title", sop.title)
    add_field("Category", sop.category)
    add_field("Department", sop.department.name if sop.department else "Organization")
    add_field("Process Name", sop.process_name)
    add_field("SOP Type", sop.sop_type)
    add_field("Description", sop.description)
    add_field("Effective Date", sop.effective_date.strftime('%Y-%m-%d') if sop.effective_date else "N/A")
    add_field("Review Date", sop.review_date.strftime('%Y-%m-%d') if sop.review_date else "N/A")
    add_field("Expiry Date", sop.expiry_date.strftime('%Y-%m-%d') if sop.expiry_date else "N/A")
    pdf.ln(5)

    # --- Roles & Responsibilities ---
    section_header("Owner and Approvals")
    author_name = sop.author.full_name or sop.author.username if sop.author else "System"
    owner_name = sop.owner.full_name or sop.owner.username if sop.owner else "System"
    reviewer_name = sop.reviewer.full_name or sop.reviewer.username if sop.reviewer else "N/A"
    approver_name = sop.approver.full_name or sop.approver.username if sop.approver else "N/A"
    add_field("Author", author_name)
    add_field("Owner", owner_name)
    add_field("Reviewer", reviewer_name)
    add_field("Approver", approver_name)
    pdf.ln(5)

    # --- Purpose & Scope ---
    section_header("Purpose, Scope & Applicability")
    add_field("Purpose", sop.purpose)
    add_field("Scope", sop.scope)
    add_field("Applicability", sop.applicability)
    add_field("Responsibilities", sop.responsibilities)
    pdf.ln(5)

    # --- Procedure Steps ---
    section_header("Procedure Steps")
    if sop.steps:
        # Sort steps by step_number
        sorted_steps = sorted(sop.steps, key=lambda x: x.step_number)
        for step in sorted_steps:
            pdf.set_font('Helvetica', 'B', 10)
            pdf.cell(0, 6, f"Step {step.step_number}: {step.step_title}", 0, 1)
            pdf.set_font('Helvetica', '', 10)
            pdf.multi_cell(0, 6, step.instructions)
            pdf.ln(2)
    else:
        pdf.cell(0, 6, "No steps defined for this SOP.", 0, 1)
        
    return pdf.output()

def generate_sop_training_certificate(training):
    org_id = getattr(training.user, 'org_id', None)
    ctx = DocumentBrandingService.get_branding_context(org_id)
    tmpl = DocumentBrandingService.get_template_config('certificate', org_id)

    pdf = FPDF(orientation='L', unit='mm', format='A4') # Landscape
    pdf.add_page()
    # Border
    pdf.set_line_width(2)
    pdf.rect(10, 10, 277, 190)
    pdf.set_line_width(0.5)
    pdf.rect(12, 12, 273, 186)
    
    # Organization Branding Header
    pdf.ln(12)
    pdf.set_font('Helvetica', 'B', 12)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(0, 8, ctx['legal_company_name'].upper(), 0, 1, 'C')

    # Title
    pdf.ln(4)
    pdf.set_font('Helvetica', 'B', 22)
    pdf.set_text_color(30, 41, 59)
    pdf.cell(0, 14, tmpl['header_title'].upper(), 0, 1, 'C')
    pdf.set_font('Helvetica', 'I', 11)
    pdf.set_text_color(71, 85, 105)
    pdf.cell(0, 6, tmpl['subtitle'], 0, 1, 'C')
    pdf.ln(5)
    
    # Body
    pdf.set_font('Helvetica', '', 14)
    pdf.set_text_color(51, 65, 85)
    pdf.cell(0, 10, "This is to certify that", 0, 1, 'C')
    pdf.ln(4)
    
    # User name
    pdf.set_font('Helvetica', 'B', 20)
    user_name = training.user.full_name or training.user.username
    pdf.cell(0, 12, user_name.upper(), 0, 1, 'C')
    if training.user.employee_id:
        pdf.set_font('Helvetica', 'I', 11)
        pdf.cell(0, 6, f"Employee ID: {training.user.employee_id}", 0, 1, 'C')
    pdf.ln(4)
    
    pdf.set_font('Helvetica', '', 14)
    pdf.cell(0, 10, "has successfully completed training on the Standard Operating Procedure:", 0, 1, 'C')
    pdf.ln(4)
    
    # SOP
    pdf.set_font('Helvetica', 'B', 16)
    pdf.cell(0, 10, f"\"{training.sop.title}\" ({training.sop.sop_uid})", 0, 1, 'C')
    pdf.ln(4)
    
    # Info
    pdf.set_font('Helvetica', '', 12)
    completed_date = training.completed_at.strftime('%Y-%m-%d') if training.completed_at else datetime.utcnow().strftime('%Y-%m-%d')
    score_str = f"Assessment Score: {training.assessment_score}%" if training.assessment_score is not None else "Assessment: Exempt"
    pdf.cell(0, 8, f"Date of Issue: {completed_date}  |  {score_str}", 0, 1, 'C')
    
    cert_no = f"CERT-{training.sop.sop_uid}-{training.id:05d}"
    pdf.cell(0, 8, f"Certificate ID: {cert_no}", 0, 1, 'C')
    pdf.ln(6)
    
    # Accreditation & Signature
    pdf.set_font('Helvetica', 'I', 9)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(0, 5, f"Quality Accreditation: {ctx['iso_certifications']}  |  {tmpl['footer_text']}", 0, 1, 'C')
    
    sig_text = "N/A"
    if training.acknowledgement_record:
        sig_text = training.acknowledgement_record.digital_signature
    pdf.set_font('Helvetica', 'I', 10)
    pdf.cell(0, 6, f"Digitally Signed By: {sig_text}", 0, 1, 'C')
    
    return pdf.output()

def generate_sop_audit_report(sop, trainings, report_type='Training Audit'):
    org_id = getattr(sop, 'org_id', None)
    pdf = DynamicBrandedPDF(org_id=org_id, template_key='audit')
    pdf.add_page()
    pdf.set_font('Helvetica', 'B', 16)
    pdf.cell(0, 10, f"{pdf.tmpl['header_title']}: SOP {report_type.upper()}", 0, 1, 'C')
    pdf.set_font('Helvetica', '', 10)
    pdf.cell(0, 6, f"SOP Title: {sop.title} ({sop.sop_uid})", 0, 1, 'C')
    pdf.cell(0, 6, f"Generated At: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC", 0, 1, 'C')
    pdf.ln(10)
    
    total = len(trainings)
    completed = sum(1 for t in trainings if t.status == 'Completed')
    pending = sum(1 for t in trainings if t.status in ('Not Started', 'In Progress', 'Acknowledged', 'Assessment Pending'))
    failed = sum(1 for t in trainings if t.status == 'Failed')
    overdue = sum(1 for t in trainings if t.status == 'Overdue')
    compliance_pct = (completed / total * 100) if total > 0 else 100.0
    
    pdf.set_font('Helvetica', 'B', 12)
    pdf.cell(0, 8, "Summary Metrics", 0, 1)
    pdf.set_font('Helvetica', '', 10)
    pdf.cell(50, 6, f"Total Assigned: {total}", 0, 0)
    pdf.cell(50, 6, f"Completed: {completed}", 0, 0)
    pdf.cell(50, 6, f"Compliance Rate: {compliance_pct:.1f}%", 0, 1)
    pdf.cell(50, 6, f"Pending: {pending}", 0, 0)
    pdf.cell(50, 6, f"Failed: {failed}", 0, 0)
    pdf.cell(50, 6, f"Overdue: {overdue}", 0, 1)
    pdf.ln(5)
    
    pdf.set_font('Helvetica', 'B', 12)
    pdf.cell(0, 8, "Trainee Detailed Status", 0, 1)
    pdf.set_font('Helvetica', 'B', 9)
    pdf.cell(50, 6, "Trainee Name", 1, 0, 'C')
    pdf.cell(30, 6, "Status", 1, 0, 'C')
    pdf.cell(25, 6, "Assigned Date", 1, 0, 'C')
    pdf.cell(20, 6, "Time (s)", 1, 0, 'C')
    pdf.cell(20, 6, "Read %", 1, 0, 'C')
    pdf.cell(20, 6, "Score", 1, 0, 'C')
    pdf.cell(25, 6, "Completed Date", 1, 1, 'C')
    
    pdf.set_font('Helvetica', '', 8)
    for t in trainings:
        name = t.user.full_name or t.user.username
        if len(name) > 25:
            name = name[:22] + "..."
        pdf.cell(50, 6, name, 1, 0, 'L')
        pdf.cell(30, 6, t.status, 1, 0, 'C')
        pdf.cell(25, 6, t.assigned_date.strftime('%Y-%m-%d'), 1, 0, 'C')
        pdf.cell(20, 6, str(t.total_reading_time), 1, 0, 'C')
        pdf.cell(20, 6, f"{t.reading_percentage:.0f}%", 1, 0, 'C')
        pdf.cell(20, 6, f"{t.assessment_score}%" if t.assessment_score is not None else "N/A", 1, 0, 'C')
        pdf.cell(25, 6, t.completed_at.strftime('%Y-%m-%d') if t.completed_at else "N/A", 1, 1, 'C')
        
    return pdf.output()
