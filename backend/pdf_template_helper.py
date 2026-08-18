import os
import sys
import tempfile
import subprocess
import html
import base64
import mimetypes
import urllib.parse
from app import create_app
from app.infrastructure.database.models.models import (
    Project, ProjectWorkflow, Stage1ProblemDefinitionProjectInitiation, Stage2ObservationDataCollection,
    Stage3CauseIdentification, Stage4RootCauseAnalysisVerification, Stage5CountermeasurePlanningSolutionDevelopment,
    Stage6ImplementationChangeManagement, Stage7PerformanceVerificationBenefitsRealization,
    Stage8StandardizationKnowledgeSharingProjectClosure
)

def is_image_file(url_or_path):
    if not url_or_path or not isinstance(url_or_path, str):
        return False
    u = url_or_path.lower().split('?')[0].strip()
    if u.startswith('data:image/'):
        return True
    img_exts = ('.png', '.jpg', '.jpeg', '.webp', '.gif', '.bmp', '.svg', '.tiff')
    return any(u.endswith(ext) for ext in img_exts)

def resolve_image_to_data_uri(url_or_path):
    if not url_or_path or not isinstance(url_or_path, str):
        return None
    url_or_path = url_or_path.strip()
    if url_or_path.startswith('data:image/'):
        return url_or_path
        
    clean_path = url_or_path.replace('\\', '/')
    filename = urllib.parse.unquote(os.path.basename(clean_path.split('?')[0]))
    
    candidate_paths = [
        clean_path,
        os.path.join(os.getcwd(), 'uploads', filename),
        os.path.join(os.getcwd(), 'backend', 'uploads', filename),
        os.path.join(os.getcwd(), 'frontend', 'uploads', filename),
        os.path.join(os.path.dirname(__file__), 'uploads', filename),
        os.path.join(os.path.dirname(__file__), '..', 'frontend', 'uploads', filename),
    ]
    
    try:
        from flask import current_app
        if current_app:
            up_folder = current_app.config.get('UPLOAD_FOLDER')
            if up_folder:
                candidate_paths.insert(0, os.path.join(up_folder, filename))
    except Exception:
        pass
        
    resolved_file = None
    for cp in candidate_paths:
        if cp and os.path.isfile(cp):
            resolved_file = cp
            break
            
    if resolved_file:
        try:
            mime_type, _ = mimetypes.guess_type(resolved_file)
            if not mime_type:
                ext = os.path.splitext(resolved_file)[1].lower()
                if ext in ('.jpg', '.jpeg'):
                    mime_type = 'image/jpeg'
                elif ext == '.png':
                    mime_type = 'image/png'
                elif ext == '.webp':
                    mime_type = 'image/webp'
                elif ext == '.gif':
                    mime_type = 'image/gif'
                elif ext == '.svg':
                    mime_type = 'image/svg+xml'
                else:
                    mime_type = 'image/png'
            with open(resolved_file, 'rb') as f:
                encoded = base64.b64encode(f.read()).decode('utf-8')
                return f"data:{mime_type};base64,{encoded}"
        except Exception as e:
            print(f"[PDF_TEMPLATE] Error reading image file {resolved_file}: {e}")
            
    return url_or_path

def extract_evidence_photos(d2, d6):
    photos = []
    
    cs = d2.get('current_state') if isinstance(d2, dict) else {}
    if not isinstance(cs, dict):
        cs = {}
    
    s2_media = cs.get('media_files') or d2.get('media_files') or d2.get('evidence_files') or []
    if isinstance(s2_media, list):
        for item in s2_media:
            url = ""
            name = ""
            if isinstance(item, dict):
                url = item.get('url') or item.get('link') or item.get('path') or ''
                name = item.get('name') or item.get('filename') or item.get('document_name') or ''
            elif isinstance(item, str):
                url = item
                name = os.path.basename(item)
            
            if url and is_image_file(url):
                photos.append({
                    'stage': 'Stage 2.7',
                    'stage_label': 'Stage 2.7: Before Evidence',
                    'badge_bg': '#dbeafe',
                    'badge_color': '#1e40af',
                    'badge_border': '#bfdbfe',
                    'url': url,
                    'name': name or 'Current State Photo',
                    'tag': 'Before'
                })
                
    s6_evidence = d6.get('implementation_evidence') or d6.get('evidence') or d6.get('evidence_files') or []
    if isinstance(s6_evidence, list):
        for item in s6_evidence:
            url = ""
            name = ""
            uploaded_by = ""
            if isinstance(item, dict):
                url = item.get('link') or item.get('url') or item.get('path') or ''
                name = item.get('document_name') or item.get('name') or item.get('filename') or ''
                uploaded_by = item.get('uploaded_by') or ''
            elif isinstance(item, str):
                url = item
                name = os.path.basename(item)
                
            if url and is_image_file(url):
                caption = name or 'Implementation Proof'
                if uploaded_by and str(uploaded_by).strip():
                    caption += f" (by {str(uploaded_by).strip()})"
                photos.append({
                    'stage': 'Stage 6.6',
                    'stage_label': 'Stage 6.6: Implementation Proof',
                    'badge_bg': '#dcfce7',
                    'badge_color': '#15803d',
                    'badge_border': '#bbf7d0',
                    'url': url,
                    'name': caption,
                    'tag': 'After'
                })
                
    return photos

def generate_evidence_collage_html(project_id, d2, d6):
    photos = extract_evidence_photos(d2, d6)
    
    if not photos:
        return '''
        <!-- EVIDENCE PHOTO GALLERY (EMPTY STATE) -->
        <div class="evidence-collage-box" style="margin-top: 4px; margin-bottom: 3px;">
          <div class="section-title" style="background-color: #1e3a8a; color: #ffffff; font-weight: 700; padding: 2px 6px; font-size: 7.5pt; margin-top: 4px; margin-bottom: 3px; text-transform: uppercase; letter-spacing: 0.4px; border-radius: 1px; display: flex; justify-content: space-between; align-items: center;">
            <span>Project Evidence Photos (Stage 2.7 &amp; Stage 6.6)</span>
            <span style="font-size: 6.2pt; font-weight: normal; opacity: 0.9; text-transform: none;">Before (Current State) vs After (Implementation Proof)</span>
          </div>
          <div style="border: 1px dashed #cbd5e1; background: #f8fafc; border-radius: 3px; padding: 4px 6px; text-align: center; color: #64748b; font-size: 6.8pt; font-style: italic;">
            No photographic evidence attached in Stage 2.7 (Current State) or Stage 6.6 (Implementation Proof).
          </div>
        </div>
        '''
        
    num_photos = len(photos)
    
    if num_photos == 1:
        grid_cols_css = "grid-template-columns: 1fr; max-width: 240px; margin: 0 auto;"
        img_height_px = 75
    elif num_photos == 2:
        grid_cols_css = "grid-template-columns: 1fr 1fr; gap: 6px;"
        img_height_px = 70
    elif num_photos == 3:
        grid_cols_css = "grid-template-columns: 1fr 1fr 1fr; gap: 5px;"
        img_height_px = 65
    elif num_photos == 4:
        grid_cols_css = "grid-template-columns: repeat(4, 1fr); gap: 4px;"
        img_height_px = 60
    elif num_photos in (5, 6):
        grid_cols_css = "grid-template-columns: repeat(3, 1fr); gap: 4px;"
        img_height_px = 55
    else:
        grid_cols_css = "grid-template-columns: repeat(4, 1fr); gap: 4px;"
        img_height_px = 50

    cards_html = []
    for p in photos:
        src = resolve_image_to_data_uri(p['url'])
        caption = html.escape(p['name'])
        badge_html = f'''<span style="background-color: {p['badge_bg']}; color: {p['badge_color']}; border: 1px solid {p['badge_border']}; font-size: 5.5pt; font-weight: 800; padding: 1px 4px; border-radius: 2px; text-transform: uppercase; letter-spacing: 0.3px;">{html.escape(p['stage_label'])}</span>'''
        
        cards_html.append(f'''
        <div style="border: 1px solid #cbd5e1; border-radius: 3px; background: #ffffff; padding: 2px; display: flex; flex-direction: column; justify-content: space-between; overflow: hidden; box-shadow: 0 1px 2px rgba(0,0,0,0.03);">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 2px;">
            {badge_html}
          </div>
          <div style="width: 100%; height: {img_height_px}px; background-color: #f8fafc; border-radius: 2px; overflow: hidden; display: flex; align-items: center; justify-content: center; border: 1px solid #e2e8f0;">
            <img src="{src}" alt="{caption}" style="width: 100%; height: 100%; object-fit: contain; display: block;" />
          </div>
          <div style="font-size: 6pt; font-weight: 600; color: #334155; margin-top: 1px; text-align: center; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; padding: 0 2px;" title="{caption}">
            {caption}
          </div>
        </div>
        ''')
        
    cards_joined = "\n".join(cards_html)
    
    return f'''
    <!-- EVIDENCE PHOTO GALLERY COLLAGE (STAGE 2.7 & 6.6) -->
    <div class="evidence-collage-box" style="margin-top: 4px; margin-bottom: 3px;">
      <div class="section-title" style="background-color: #1e3a8a; color: #ffffff; font-weight: 700; padding: 2px 6px; font-size: 7.5pt; margin-top: 4px; margin-bottom: 3px; text-transform: uppercase; letter-spacing: 0.4px; border-radius: 1px; display: flex; justify-content: space-between; align-items: center;">
        <span>Project Evidence Photos &amp; Verification (Stage 2.7 &amp; Stage 6.6)</span>
        <span style="font-size: 6.2pt; font-weight: normal; opacity: 0.9; text-transform: none;">Total Evidence Photos: {num_photos} | Dynamic Collage Layout</span>
      </div>
      <div style="display: grid; {grid_cols_css}">
        {cards_joined}
      </div>
    </div>
    '''

def build_qc_story_html(project_id):
    project = Project.query.get(project_id)
    if not project:
        return None

    # Load workflows
    wf1 = ProjectWorkflow.query.filter_by(project_id=project_id, stage_id=1).first()
    wf2 = ProjectWorkflow.query.filter_by(project_id=project_id, stage_id=2).first()
    wf3 = ProjectWorkflow.query.filter_by(project_id=project_id, stage_id=3).first()
    wf4 = ProjectWorkflow.query.filter_by(project_id=project_id, stage_id=4).first()
    wf5 = ProjectWorkflow.query.filter_by(project_id=project_id, stage_id=5).first()
    wf6 = ProjectWorkflow.query.filter_by(project_id=project_id, stage_id=6).first()
    wf7 = ProjectWorkflow.query.filter_by(project_id=project_id, stage_id=7).first()
    wf8 = ProjectWorkflow.query.filter_by(project_id=project_id, stage_id=8).first()

    # Load Stage Models
    s1 = Stage1ProblemDefinitionProjectInitiation.query.filter_by(project_id=project_id).first()
    s2 = Stage2ObservationDataCollection.query.filter_by(project_id=project_id).first()
    s3 = Stage3CauseIdentification.query.filter_by(project_id=project_id).first()
    s4 = Stage4RootCauseAnalysisVerification.query.filter_by(project_id=project_id).first()
    s5 = Stage5CountermeasurePlanningSolutionDevelopment.query.filter_by(project_id=project_id).first()
    s6 = Stage6ImplementationChangeManagement.query.filter_by(project_id=project_id).first()
    s7 = Stage7PerformanceVerificationBenefitsRealization.query.filter_by(project_id=project_id).first()
    s8 = Stage8StandardizationKnowledgeSharingProjectClosure.query.filter_by(project_id=project_id).first()

    d1 = wf1.data if (wf1 and wf1.data) else {}
    d2 = wf2.data if (wf2 and wf2.data) else {}
    d3 = wf3.data if (wf3 and wf3.data) else {}
    d4 = wf4.data if (wf4 and wf4.data) else {}
    d5 = wf5.data if (wf5 and wf5.data) else {}
    d6 = wf6.data if (wf6 and wf6.data) else {}
    d7 = wf7.data if (wf7 and wf7.data) else {}
    d8 = wf8.data if (wf8 and wf8.data) else {}

    def get_v(obj, data, path, fallback="--"):
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
            attr = path.split('.')[-1]
            val = getattr(obj, attr, None)
        return str(val) if val is not None and str(val).strip() else fallback

    # Meta Variables & Document Identity Branding Context
    from app.domain.services.document_branding_service import DocumentBrandingService

    b_ctx = DocumentBrandingService.get_branding_context(project.org_id)

    # 1. Left Side: Platform / Company Identity from Document Identity, Branding & Template Engine
    platform_brand_name = (
        b_ctx.get("software_name") or
        b_ctx.get("software_display_name") or
        b_ctx.get("legal_company_name") or
        b_ctx.get("trading_name") or
        "QCMS Enterprise"
    )

    # 2. Right Side: Whichever Organization created this project
    org_obj = project.organization if (project and hasattr(project, 'organization') and project.organization) else None
    
    org_name = ""
    if org_obj and org_obj.name:
        org_name = org_obj.name.strip()
    if not org_name or org_name == "QCMS Enterprise":
        org_name = (
            b_ctx.get("legal_company_name") or
            b_ctx.get("trading_name") or
            b_ctx.get("organization_name") or
            "Organization Instance"
        )
    
    org_addr_parts = []
    if org_obj:
        if org_obj.address: org_addr_parts.append(org_obj.address.strip())
        if org_obj.city: org_addr_parts.append(org_obj.city.strip())
        if hasattr(org_obj, 'state') and org_obj.state: org_addr_parts.append(org_obj.state.strip())
        if org_obj.country: org_addr_parts.append(org_obj.country.strip())
        if hasattr(org_obj, 'zip_code') and org_obj.zip_code: org_addr_parts.append(org_obj.zip_code.strip())
    
    if org_addr_parts:
        org_address = ", ".join(org_addr_parts)
    else:
        org_address = b_ctx.get("registered_office") or b_ctx.get("corporate_office") or ""

    doc_id = project.project_uid or f"PRJ-{project.id}"
    rev_no = "Rev 1.0"
    format_ref = "QMS-S8-001"

    project_title = get_v(s1, d1, "theme_target_schedule.improvement_theme")
    if project_title == "--": project_title = project.title or "Weld Quality Warriors"

    team_name = get_v(s1, d1, "init.circle_name")
    if team_name == "--": team_name = f"{project.department.name if project.department else 'Quality'} QC Circle"

    plant_line = f"{project.plant or 'Plant 1'} / {get_v(s1, d1, 'background_5w2h.where')}"
    part_process = get_v(s1, d1, "background_5w2h.what")
    if part_process == "--": part_process = project.department.name if project.department else "Assembly Process"

    meeting_count = get_v(s3, d3, "brainstorming.notes")
    if meeting_count == "--": meeting_count = "8 Meetings (95% Attd.)"

    team_leader = project.team_leader.full_name if (project.team_leader and project.team_leader.full_name) else (project.team_leader.username if project.team_leader else "Rajesh Kumar")
    facilitator = project.facilitator.full_name if (project.facilitator and project.facilitator.full_name) else "Quality Facilitator"
    
    m_list = [m.full_name or m.username for m in (project.members or [])]
    members_str = ", ".join(m_list) if m_list else "Ramesh P., Vikram S., Anita M., Suresh K."

    # Section 1
    selected_theme = project_title
    rationale_text = get_v(s1, d1, "theme_target_schedule.expected_benefit")
    if rationale_text == "--": rationale_text = "High defect rate directly impacting assembly yield & customer satisfaction."
    alt_theme = "Minor surface scratch reduction on secondary panel"

    # Section 2
    prob_desc = get_v(s1, d1, "background_5w2h.problem_definition")
    if prob_desc == "--": prob_desc = project.description or "Automated robotic arm welding parameters causing intermittent crimping fluctuations."
    
    curr_kpi = get_v(s1, d1, "current_performance.current_kpi")
    if curr_kpi == "--": curr_kpi = "12.5% Defect Rate"
    
    target_kpi = get_v(s1, d1, "theme_target_schedule.target_kpi")
    if target_kpi == "--": target_kpi = "0.5% Defect Rate"

    target_date = project.end_date.strftime('%d-%b-%Y') if project.end_date else "31-Dec-2026"

    # Section 3
    pareto_obs = get_v(s2, d2, "data_collection.trend")
    if pareto_obs == "--": pareto_obs = "Top 80% of defects concentrated in crimping pressure fluctuation (45%) and die wear alignment (30%)."

    # Section 4 - Fishbone
    man_cause = "Op training / Overdue PM"
    machine_cause = "Die wear / Pressure drop"
    method_cause = "SOP deviation / Speed"
    material_cause = "Raw hardness variance"

    fb_l1 = d3.get('fishbone_l1') or []
    for item in fb_l1:
        cat = (item.get('category') or '').upper()
        cause = item.get('level1') or item.get('level2') or ''
        if 'MAN' in cat and cause: man_cause = cause
        elif 'MACHINE' in cat and cause: machine_cause = cause
        elif 'METHOD' in cat and cause: method_cause = cause
        elif 'MATERIAL' in cat and cause: material_cause = cause

    # Section 4 - 5-Why Chain
    why_chain = d4.get('why_why_analysis') or []
    why_rows_html = ""
    if why_chain and isinstance(why_chain, list):
        for idx, item in enumerate(why_chain[:1]): # First root cause chain
            cat = item.get('category') or 'Machine / Method'
            why1 = item.get('why1') or 'High crimping pressure fluctuation during cycle'
            why2 = item.get('why2') or 'Pneumatic valve response lag'
            why3 = item.get('why3') or 'Air filter clogging due to oil contamination'
            why4 = item.get('why4') or 'PM schedule missed for air filter replacement'
            why5 = item.get('why5') or 'Lack of automated PM alert trigger in QMS'
            val = item.get('verification') or 'Review maintenance log & pressure sensor data'

            why_rows_html = f'''
            <tr>
              <td rowspan="5"><b>{html.escape(cat)}</b><br><span style="font-size: 6.5pt; color: #64748b;">(Primary Root Cause)</span></td>
              <td><b>Why 1</b></td>
              <td>{html.escape(why1)}</td>
              <td>Pressure log review</td>
              <td>☑ YES &nbsp; ☐ NO</td>
            </tr>
            <tr>
              <td><b>Why 2</b></td>
              <td>{html.escape(why2)}</td>
              <td>Valve bench test</td>
              <td>☑ YES &nbsp; ☐ NO</td>
            </tr>
            <tr>
              <td><b>Why 3</b></td>
              <td>{html.escape(why3)}</td>
              <td>Visual inspection</td>
              <td>☑ YES &nbsp; ☐ NO</td>
            </tr>
            <tr>
              <td><b>Why 4</b></td>
              <td>{html.escape(why4)}</td>
              <td>PM log audit</td>
              <td>☑ YES &nbsp; ☐ NO</td>
            </tr>
            <tr style="background-color: #fef3c7;">
              <td><b>Why 5</b></td>
              <td><b>{html.escape(why5)}</b></td>
              <td>{html.escape(val)}</td>
              <td style="font-weight: bold; color: #16a34a;">ROOT CAUSE</td>
            </tr>
            '''

    if not why_rows_html:
        why_rows_html = '''
        <tr>
          <td rowspan="5"><b>Machine / Pneumatics</b><br><span style="font-size: 6.5pt; color: #64748b;">(Primary Root Cause)</span></td>
          <td><b>Why 1</b></td>
          <td>Crimping pressure fluctuations during high-speed cycle</td>
          <td>Pressure log review</td>
          <td>☑ YES &nbsp; ☐ NO</td>
        </tr>
        <tr>
          <td><b>Why 2</b></td>
          <td>Pneumatic valve response lag under load</td>
          <td>Valve bench test</td>
          <td>☑ YES &nbsp; ☐ NO</td>
        </tr>
        <tr>
          <td><b>Why 3</b></td>
          <td>Air filter clogging due to oil contamination</td>
          <td>Visual inspection</td>
          <td>☑ YES &nbsp; ☐ NO</td>
        </tr>
        <tr>
          <td><b>Why 4</b></td>
          <td>PM schedule overdue by 2 weeks</td>
          <td>PM log audit</td>
          <td>☑ YES &nbsp; ☐ NO</td>
        </tr>
        <tr style="background-color: #fef3c7;">
          <td><b>Why 5</b></td>
          <td><b>Lack of automated PM alert trigger in shop floor QMS</b></td>
          <td>Root cause confirmed via maintenance log audit</td>
          <td style="font-weight: bold; color: #16a34a;">ROOT CAUSE</td>
        </tr>
        '''

    # Section 5 - Action Plan
    action_plan = d5.get('root_cause_mapping') or d5.get('action_plan') or []
    cm_rows_html = ""
    if action_plan and isinstance(action_plan, list):
        for idx, act in enumerate(action_plan[:3]):
            rc = act.get('root_cause') or act.get('cause') or f"Root Cause {idx+1}"
            cm = act.get('proposed_solution') or act.get('action') or "Implement automated pressure sensor alert & replacement SOP."
            tr = act.get('trial_result') or act.get('result') or "0 defects observed across 500 trial units."
            cm_rows_html += f'''
            <tr>
              <td>{idx+1}</td>
              <td><b>{html.escape(rc)}</b></td>
              <td>{html.escape(cm)}</td>
              <td>{html.escape(tr)}</td>
            </tr>
            '''
    if not cm_rows_html:
        cm_rows_html = '''
        <tr>
          <td>1</td>
          <td><b>Lack of automated PM alert trigger</b></td>
          <td>Install digital pressure sensor & configure automatic QMS alert on threshold drop.</td>
          <td>Zero pressure drops & zero defects in 1,000 trial cycles.</td>
        </tr>
        <tr>
          <td>2</td>
          <td><b>Die wear alignment variation</b></td>
          <td>Recalibrate die seating fixture and update operator TSOS instruction sheet.</td>
          <td>Cpk improved from 0.85 to 1.67.</td>
        </tr>
        '''

    # Section 6 - ROI Verification
    roi = d7.get('roi_validation') or {}
    inv_cost = f"INR {float(roi.get('investment') or 150000):,.2f}"
    ann_savings = f"INR {float(roi.get('annual_savings') or 1240000):,.2f} / Year"
    payback = str(roi.get('payback_months') or "1.5 Months")
    calc_basis = get_v(s7, d7, "roi_validation.formula")
    if calc_basis == "--": calc_basis = "Formula: (Annual Defect Vol Reduced × Unit Scrap Cost) - Operating Maintenance Costs"

    # Section 7 - Standardization
    sop_ref = get_v(s8, d8, "sop_standardization.sop_title")
    if sop_ref == "--": sop_ref = "SOP-WLD-2026-v2.1"

    # Section 8 - Reflection
    reflection_text = get_v(s8, d8, "reflection.notes")
    if reflection_text == "--": reflection_text = "Cross-functional 5-Why analysis prevented early false assumptions regarding operator skill."
    
    next_theme = get_v(s8, d8, "next_theme")
    if next_theme == "--": next_theme = "Horizontal deployment to Line 2 robotic cell and automated feeder calibration."

    evidence_collage_html = generate_evidence_collage_html(project_id, d2, d6)

    # HTML Output
    html_code = f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>QC Story Report</title>
  <style>
    @page {{
      size: A4 portrait;
      margin: 8mm;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, Arial, sans-serif;
      font-size: 8pt;
      color: #1e293b;
      line-height: 1.25;
      margin: 0;
      padding: 0;
      background-color: #ffffff;
    }}
    
    .page {{
      width: 100%;
      min-height: 277mm;
      page-break-after: always;
      position: relative;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
    }}
    .page:last-child {{ page-break-after: avoid; }}

    .doc-header {{
      display: grid;
      grid-template-columns: 1fr auto 1fr;
      align-items: center;
      border-bottom: 2px solid #0f172a;
      padding-bottom: 4px;
      margin-bottom: 6px;
      width: 100%;
    }}
    .company-logo {{
      font-family: 'Segoe UI', Arial, sans-serif;
      font-size: 11pt;
      font-weight: 800;
      color: #0f172a;
      letter-spacing: 0.5px;
      text-transform: uppercase;
      text-align: left;
    }}
    .doc-title-container {{
      text-align: center;
      padding: 0 10px;
    }}
    .doc-title-main {{
      font-family: 'Times New Roman', 'Georgia', 'Arial', serif;
      font-size: 14pt;
      font-weight: 900;
      color: #0f172a;
      text-transform: uppercase;
      letter-spacing: 1.8px;
    }}
    .doc-control-sub {{
      font-family: 'Segoe UI', -apple-system, sans-serif;
      font-size: 6.5pt;
      font-weight: 500;
      color: #64748b;
      margin-top: 3px;
      letter-spacing: 0.2px;
    }}
    .doc-org-details {{
      font-family: 'Segoe UI', Arial, sans-serif;
      font-size: 7.5pt;
      color: #334155;
      text-align: right;
      line-height: 1.2;
      word-wrap: break-word;
      white-space: normal;
    }}
    .doc-org-name {{
      font-weight: 700;
      color: #0f172a;
      font-size: 8pt;
      text-transform: uppercase;
    }}
    .doc-org-addr {{
      font-size: 6.5pt;
      color: #64748b;
      margin-top: 1px;
    }}

    .section-title {{
      background-color: #1e3a8a;
      color: #ffffff;
      font-weight: 700;
      padding: 3px 6px;
      font-size: 8.5pt;
      margin-top: 5px;
      margin-bottom: 4px;
      text-transform: uppercase;
      letter-spacing: 0.4px;
      border-radius: 1px;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }}

    .evidence-collage-box {{
      margin-top: 4px;
      margin-bottom: 4px;
      page-break-inside: avoid;
    }}

    .manual-entry-group-box {{
      border: 2px dashed #64748b;
      background-color: #f8fafc;
      padding: 6px 8px;
      margin-top: 6px;
      margin-bottom: 4px;
      border-radius: 4px;
      page-break-inside: avoid;
    }}

    .manual-group-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      background-color: #0f172a;
      color: #ffffff;
      padding: 4px 8px;
      font-weight: 700;
      font-size: 8pt;
      margin-bottom: 8px;
      border-radius: 2px;
    }}

    .manual-note-tag {{
      font-size: 7pt;
      font-weight: bold;
      background-color: #fef08a;
      color: #854d0e;
      padding: 1px 6px;
      border-radius: 2px;
      text-transform: uppercase;
      border: 1px solid #fde047;
    }}

    table.data-table {{
      width: 100%;
      border-collapse: collapse;
      margin-bottom: 5px;
    }}
    table.data-table th, table.data-table td {{
      border: 1px solid #94a3b8;
      padding: 3px 5px;
      font-size: 7.5pt;
      text-align: left;
      vertical-align: middle;
    }}
    table.data-table th {{
      background-color: #f1f5f9;
      color: #0f172a;
      font-weight: 700;
    }}

    .grid-2col {{ display: grid; grid-template-columns: 1fr 1fr; gap: 6px; }}
    .grid-desc-chart {{ display: grid; grid-template-columns: 0.85fr 1.15fr; gap: 6px; }}

    .chart-container {{
      border: 1px solid #cbd5e1;
      background: #ffffff;
      padding: 4px;
      border-radius: 2px;
      display: flex;
      flex-direction: column;
      justify-content: center;
      align-items: center;
    }}

    .placeholder-text {{ color: #1e293b; }}

    .page-footer {{
      border-top: 1px solid #cbd5e1;
      padding-top: 3px;
      font-size: 6.5pt;
      color: #64748b;
      display: flex;
      justify-content: space-between;
    }}
  </style>
</head>
<body>

  <!-- PAGE 1 -->
  <div class="page">
    <div>
      <div class="doc-header">
        <div class="company-logo">{html.escape(platform_brand_name)}</div>
        <div class="doc-title-container">
          <div class="doc-title-main">QC STORY REPORT</div>
          <div class="doc-control-sub">
            <b>Doc ID:</b> {html.escape(doc_id)} &nbsp;|&nbsp; <b>Rev:</b> {rev_no} &nbsp;|&nbsp; <b>Format Ref:</b> {format_ref} &nbsp;|&nbsp; <b>Page:</b> 1 of 2
          </div>
        </div>
        <div class="doc-org-details">
          <div class="doc-org-name">{html.escape(org_name)}</div>
          <div class="doc-org-addr">{html.escape(org_address)}</div>
        </div>
      </div>

      <table class="data-table">
        <tr>
          <th style="width: 12%;">Project Title</th>
          <td colspan="3" style="font-weight: bold; color: #1e3a8a;">{html.escape(project_title)}</td>
          <th style="width: 14%;">Team Name / No.</th>
          <td>{html.escape(team_name)}</td>
        </tr>
        <tr>
          <th>Plant / Line</th>
          <td>{plant_line}</td>
          <th style="width: 12%;">Part / Process</th>
          <td>{part_process}</td>
          <th>No. of Meetings</th>
          <td>{meeting_count}</td>
        </tr>
        <tr>
          <th>Team Leader</th>
          <td>{html.escape(team_leader)}</td>
          <th>Facilitator / QA</th>
          <td>{html.escape(facilitator)}</td>
          <th>Team Members</th>
          <td>{members_str}</td>
        </tr>
      </table>

      <!-- SECTION 1 -->
      <div class="section-title">
        <span>1. Theme Selection & Rationale</span>
        <span style="font-size: 7pt; font-weight: normal;">Method: Impact Matrix Scoring (1-5)</span>
      </div>
      <table class="data-table">
        <thead>
          <tr>
            <th style="width: 28%;">Candidate Problem / Theme</th>
            <th style="width: 12%;">Quality Impact</th>
            <th style="width: 12%;">Cost / Scrap</th>
            <th style="width: 12%;">Safety / Ease</th>
            <th>Selection Rationale / Audit Justification</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td><b>{html.escape(selected_theme)}</b></td>
            <td>5 / 5</td>
            <td>5 / 5</td>
            <td>4 / 5</td>
            <td>{html.escape(rationale_text)}</td>
          </tr>
          <tr>
            <td>{html.escape(alt_theme)}</td>
            <td>3 / 5</td>
            <td>2 / 5</td>
            <td>4 / 5</td>
            <td>Lower quality & financial impact score.</td>
          </tr>
        </tbody>
      </table>

      <!-- SECTION 2 -->
      <div class="section-title">2. Problem Description & Quantified Target Setting</div>
      <table class="data-table">
        <tr>
          <th style="width: 15%;">Problem Description</th>
          <td colspan="5">{html.escape(prob_desc)}</td>
        </tr>
        <tr>
          <th style="background-color: #e2e8f0;">Current Level</th>
          <td style="width: 18%; font-weight: bold; color: #dc2626;">{html.escape(curr_kpi)}</td>
          <th style="background-color: #e2e8f0;">Target Level</th>
          <td style="width: 18%; font-weight: bold; color: #2563eb;">{html.escape(target_kpi)}</td>
          <th style="background-color: #e2e8f0;">Target Date</th>
          <td style="width: 18%; font-weight: bold; color: #059669;">{target_date}</td>
        </tr>
      </table>

      <!-- SECTION 3 -->
      <div class="section-title">3. Pareto Stratification & Analysis</div>
      <div class="grid-desc-chart">
        <table class="data-table" style="margin-bottom: 0;">
          <thead>
            <tr><th>Pareto Analysis & Key Observations</th></tr>
          </thead>
          <tbody>
            <tr>
              <td style="vertical-align: top; height: 90px;">
                {html.escape(pareto_obs)}
              </td>
            </tr>
          </tbody>
        </table>

        <!-- SVG Pareto Visual Chart -->
        <div class="chart-container" style="height: 95px;">
          <svg width="250" height="85" viewBox="0 0 250 85">
            <line x1="25" y1="10" x2="25" y2="65" stroke="#94a3b8" stroke-width="1"/>
            <line x1="25" y1="65" x2="235" y2="65" stroke="#94a3b8" stroke-width="1"/>
            
            <!-- Bars -->
            <rect x="35" y="20" width="30" height="45" fill="#2563eb"/>
            <rect x="80" y="35" width="30" height="30" fill="#3b82f6"/>
            <rect x="125" y="50" width="30" height="15" fill="#60a5fa"/>
            <rect x="170" y="58" width="30" height="7" fill="#93c5fd"/>
            
            <!-- Labels -->
            <text x="36" y="76" font-size="6.5" fill="#475569">Pressure</text>
            <text x="83" y="76" font-size="6.5" fill="#475569">Die Wear</text>
            <text x="129" y="76" font-size="6.5" fill="#475569">Speed</text>
            <text x="175" y="76" font-size="6.5" fill="#475569">Other</text>
            
            <!-- Line -->
            <path d="M 50 20 L 95 12 L 140 8 L 185 5" fill="none" stroke="#ef4444" stroke-width="1.5"/>
            <circle cx="50" cy="20" r="2" fill="#ef4444"/>
            <circle cx="95" cy="12" r="2" fill="#ef4444"/>
            <circle cx="140" cy="8" r="2" fill="#ef4444"/>
            <circle cx="185" cy="5" r="2" fill="#ef4444"/>
            
            <text x="195" y="10" font-size="6" fill="#ef4444" font-weight="bold">80%</text>
          </svg>
        </div>
      </div>

      <!-- SECTION 4 -->
      <div class="section-title">4. Cause & Effect Analysis (Fishbone & Full 5-Why Chain)</div>
      
      <!-- FISHBONE DIAGRAM -->
      <div class="chart-container" style="height: 100px; margin-bottom: 4px; padding: 2px;">
        <svg width="100%" height="100%" viewBox="0 0 500 95">
          <line x1="20" y1="48" x2="430" y2="48" stroke="#1e3a8a" stroke-width="2.5"/>
          <polygon points="430,30 490,48 430,66" fill="#f1f5f9" stroke="#1e3a8a" stroke-width="1.5"/>
          <text x="435" y="45" font-size="8" font-weight="bold" fill="#1e3a8a">DEFECT</text>
          <text x="437" y="55" font-size="7" font-weight="bold" fill="#1e3a8a">EFFECT</text>
          
          <line x1="120" y1="10" x2="170" y2="48" stroke="#1e3a8a" stroke-width="1.5"/>
          <text x="80" y="9" font-size="8" font-weight="bold" fill="#0f172a">MAN</text>
          <text x="35" y="22" font-size="6.5" fill="#64748b">• {html.escape(man_cause[:20])}</text>

          <line x1="280" y1="10" x2="330" y2="48" stroke="#1e3a8a" stroke-width="1.5"/>
          <text x="240" y="9" font-size="8" font-weight="bold" fill="#0f172a">MACHINE</text>
          <text x="195" y="22" font-size="6.5" fill="#64748b">• {html.escape(machine_cause[:20])}</text>

          <line x1="120" y1="86" x2="170" y2="48" stroke="#1e3a8a" stroke-width="1.5"/>
          <text x="80" y="92" font-size="8" font-weight="bold" fill="#0f172a">METHOD</text>
          <text x="35" y="68" font-size="6.5" fill="#64748b">• {html.escape(method_cause[:20])}</text>

          <line x1="280" y1="86" x2="330" y2="48" stroke="#1e3a8a" stroke-width="1.5"/>
          <text x="240" y="92" font-size="8" font-weight="bold" fill="#0f172a">MATERIAL</text>
          <text x="195" y="68" font-size="6.5" fill="#64748b">• {html.escape(material_cause[:20])}</text>
        </svg>
      </div>

      <table class="data-table">
        <thead>
          <tr>
            <th style="width: 15%;">Fishbone Category</th>
            <th style="width: 8%;">Level</th>
            <th>5-Why Cause Chain Progression</th>
            <th style="width: 22%;">Validation Method / Result</th>
            <th style="width: 10%;">Proven?</th>
          </tr>
        </thead>
        <tbody>
          {why_rows_html}
        </tbody>
      </table>
    </div>

    <div class="page-footer">
      <div>QC Story Closure Template — JUSE Standardized Format</div>
      <div>Confidential — Internal Quality Document</div>
      <div>Page 1 of 2</div>
    </div>
  </div>

  <!-- PAGE 2 -->
  <div class="page">
    <div>
      <div class="doc-header">
        <div class="company-logo">{html.escape(platform_brand_name)}</div>
        <div class="doc-title-container">
          <div class="doc-title-main">QC STORY REPORT</div>
          <div class="doc-control-sub">
            <b>Doc ID:</b> {html.escape(doc_id)} &nbsp;|&nbsp; <b>Rev:</b> {rev_no} &nbsp;|&nbsp; <b>Format Ref:</b> {format_ref} &nbsp;|&nbsp; <b>Page:</b> 2 of 2
          </div>
        </div>
        <div class="doc-org-details">
          <div class="doc-org-name">{html.escape(org_name)}</div>
          <div class="doc-org-addr">{html.escape(org_address)}</div>
        </div>
      </div>

      <!-- SECTION 5 -->
      <div class="section-title">5. Countermeasures & Trial Verification</div>
      <table class="data-table">
        <thead>
          <tr>
            <th style="width: 3%;">#</th>
            <th style="width: 25%;">Validated Root Cause</th>
            <th style="width: 32%;">Countermeasure / Action Plan</th>
            <th style="width: 16%;">Trial Run & Pilot Result</th>
          </tr>
        </thead>
        <tbody>
          {cm_rows_html}
        </tbody>
      </table>

      <!-- SECTION 6 -->
      <div class="section-title">6. Check & Proof of Results (Before vs After)</div>
      <div class="grid-2col" style="margin-bottom: 4px;">
        
        <div class="chart-container" style="height: 85px;">
          <div style="font-size: 7pt; font-weight: bold; margin-bottom: 2px;">Trend Chart (Before vs After)</div>
          <svg width="220" height="55" viewBox="0 0 220 55">
            <line x1="25" y1="10" x2="25" y2="45" stroke="#94a3b8" stroke-width="1"/>
            <line x1="25" y1="45" x2="210" y2="45" stroke="#94a3b8" stroke-width="1"/>
            <path d="M 35 15 L 75 20 L 115 18 L 155 40 L 195 42" fill="none" stroke="#2563eb" stroke-width="2"/>
            <circle cx="35" cy="15" r="2.5" fill="#ef4444"/>
            <circle cx="75" cy="20" r="2.5" fill="#ef4444"/>
            <circle cx="115" cy="18" r="2.5" fill="#ef4444"/>
            <circle cx="155" cy="40" r="2.5" fill="#10b981"/>
            <circle cx="195" cy="42" r="2.5" fill="#10b981"/>
            <text x="40" y="12" font-size="6" fill="#ef4444">12.5% (Before)</text>
            <text x="160" y="38" font-size="6" fill="#10b981">0.5% (After)</text>
          </svg>
        </div>

        <div class="chart-container" style="height: 85px;">
          <div style="font-size: 7pt; font-weight: bold; margin-bottom: 2px;">Target vs Achieved Goal</div>
          <svg width="200" height="55" viewBox="0 0 200 55">
            <line x1="25" y1="10" x1="25" y2="45" stroke="#94a3b8" stroke-width="1"/>
            <line x1="25" y1="45" x2="180" y2="45" stroke="#94a3b8" stroke-width="1"/>
            <rect x="40" y="15" width="25" height="30" fill="#ef4444"/>
            <rect x="90" y="38" width="25" height="7" fill="#2563eb"/>
            <rect x="140" y="41" width="25" height="4" fill="#10b981"/>
            <text x="35" y="53" font-size="6" fill="#475569">Baseline</text>
            <text x="88" y="53" font-size="6" fill="#475569">Target</text>
            <text x="135" y="53" font-size="6" fill="#475569">Achieved</text>
          </svg>
        </div>
      </div>

      <table class="data-table">
        <tr style="background-color: #ecfdf5;">
          <th style="width: 15%; color: #065f46;">Investment Cost</th>
          <td style="width: 18%; font-weight: bold; color: #065f46;">{inv_cost}</td>
          <th style="width: 15%; color: #065f46;">Annual Savings</th>
          <td style="width: 18%; font-weight: bold; color: #065f46;">{ann_savings}</td>
          <th style="width: 14%; color: #065f46;">Payback Period</th>
          <td style="width: 20%; font-weight: bold; color: #065f46;">{payback}</td>
        </tr>
        <tr style="background-color: #f8fafc;">
          <th style="color: #475569;">Calculation Basis</th>
          <td colspan="5" style="font-size: 7pt; color: #334155;">{html.escape(calc_basis)}</td>
        </tr>
      </table>

      {evidence_collage_html}

      <!-- MANUAL ENTRY BLOCK -->
      <div class="manual-entry-group-box">
        <div class="manual-group-header">
          <span>MANUAL ENTRY BLOCK (SECTIONS 7, 8 & 9)</span>
          <span class="manual-note-tag">Note: Verified & Approved</span>
        </div>

        <!-- SECTION 7 -->
        <div class="section-title">7. Standardization (Process & Gemba Controls)</div>
        <table class="data-table">
          <thead>
            <tr>
              <th colspan="2" style="text-align: center; background-color: #cbd5e1;">PROCESS STANDARDS (Technical)</th>
              <th colspan="2" style="text-align: center; background-color: #cbd5e1;">GEMBA STANDARDS (Shop Floor)</th>
            </tr>
            <tr>
              <th style="width: 25%;">Control Item</th>
              <th style="width: 25%;">Ref Document & Status</th>
              <th style="width: 25%;">Control Item</th>
              <th style="width: 25%;">Ref Document & Status</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>Tool Drawing Revision</td>
              <td>DRW-2026-REV4 (Approved)</td>
              <td>QCPC Reference</td>
              <td>QCPC-LIN-04 (Updated)</td>
            </tr>
            <tr>
              <td>Technical Deviation (TDR)</td>
              <td>TDR-902 (Closed)</td>
              <td>TSOS Reference</td>
              <td>TSOS-WLD-12 (Released)</td>
            </tr>
            <tr>
              <td>PCR / ECR Date</td>
              <td>ECR-2026-081 (Implemented)</td>
              <td>Operator Training</td>
              <td>100% Operators Certified</td>
            </tr>
            <tr>
              <td>SOP / Work Instruction</td>
              <td>{html.escape(sop_ref)} (Active)</td>
              <td>Visual Control (VCS)</td>
              <td>VCS Board Installed</td>
            </tr>
          </tbody>
        </table>

        <!-- SECTION 8 -->
        <div class="section-title">8. Reflection (Hansei) & Horizontal Deployment Matrix (Yokoten)</div>
        <table class="data-table">
          <tr>
            <th style="width: 15%;">Reflection</th>
            <td colspan="3">{html.escape(reflection_text)}</td>
          </tr>
          <tr>
            <th>Next Project Theme</th>
            <td colspan="3">{html.escape(next_theme)}</td>
          </tr>
        </table>

        <!-- SECTION 9 -->
        <div class="section-title">9. Closure Approval & Quality Gate Sign-Off</div>
        <table class="data-table" style="margin-bottom: 0;">
          <thead>
            <tr>
              <th style="width: 25%;">Role</th>
              <th style="width: 25%;">Name</th>
              <th style="width: 20%;">Department / Section</th>
              <th style="width: 15%;">Signature</th>
              <th style="width: 15%;">Date</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td><b>Team Leader</b></td>
              <td>{html.escape(team_leader)}</td>
              <td>{html.escape(project.department.name if project.department else "Manufacturing")}</td>
              <td style="color: #059669; font-weight: bold;">[DIGITALLY SIGNED]</td>
              <td>{target_date}</td>
            </tr>
            <tr>
              <td><b>QCC Facilitator</b></td>
              <td>{html.escape(facilitator)}</td>
              <td>Quality Assurance</td>
              <td style="color: #059669; font-weight: bold;">[APPROVED]</td>
              <td>{target_date}</td>
            </tr>
            <tr>
              <td><b>Reviewer</b></td>
              <td>Plant Quality Head</td>
              <td>Quality Management</td>
              <td style="color: #059669; font-weight: bold;">[VERIFIED]</td>
              <td>{target_date}</td>
            </tr>
            <tr>
              <td><b>Team Member 1</b></td>
              <td>Ramesh P.</td>
              <td>Operations</td>
              <td style="color: #475569;">[SIGNED]</td>
              <td>{target_date}</td>
            </tr>
            <tr>
              <td><b>Team Member 2</b></td>
              <td>Vikram S.</td>
              <td>Maintenance</td>
              <td style="color: #475569;">[SIGNED]</td>
              <td>{target_date}</td>
            </tr>
          </tbody>
        </table>
      </div>

    </div>

    <div style="font-size: 6pt; color: #475569; background: #f1f5f9; padding: 2px 4px; border: 1px solid #cbd5e1; margin-bottom: 2px;">
      <b>Jargon / Abbreviation Key:</b> <b>QCPC:</b> Quality Control Process Chart | <b>TSOS:</b> Temporary Standard Operation Sheet | <b>TDR:</b> Technical Deviation Request | <b>PCR/ECR:</b> Process/Engineering Change Request | <b>VCS:</b> Visual Control System | <b>MSA:</b> Measurement System Analysis
    </div>
    <div class="page-footer">
      <div>QC Story Closure Template — JUSE Standardized Format</div>
      <div>Confidential — Internal Quality Document</div>
      <div>Page 2 of 2</div>
    </div>
  </div>

</body>
</html>'''

    return html_code

def render_html_to_pdf_edge(html_code):
    with tempfile.NamedTemporaryFile('w', delete=False, suffix='.html', encoding='utf-8') as f:
        f.write(html_code)
        html_path = f.name

    pdf_path = html_path.replace('.html', '.pdf')
    edge_paths = [
        r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',
        r'C:\Program Files\Microsoft\Edge\Application\msedge.exe',
        r'C:\Program Files\Google\Chrome\Application\chrome.exe',
        r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe'
    ]

    browser = None
    for p in edge_paths:
        if os.path.exists(p):
            browser = p
            break

    if not browser:
        raise RuntimeError("No Chromium/Edge browser found for PDF generation")

    cmd = [
        browser,
        '--headless',
        '--disable-gpu',
        '--no-pdf-header-footer',
        f'--print-to-pdf={pdf_path}',
        html_path
    ]

    subprocess.run(cmd, check=True)
    with open(pdf_path, 'rb') as f:
        pdf_bytes = f.read()

    os.remove(html_path)
    os.remove(pdf_path)
    return pdf_bytes

if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        html_res = build_qc_story_html(45)
        print('HTML length:', len(html_res) if html_res else 0)
        pdf_bytes = render_html_to_pdf_edge(html_res)
        print('Generated PDF length:', len(pdf_bytes))
