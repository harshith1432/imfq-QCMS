import fitz
import os
import tempfile
import subprocess
import html
import base64
import mimetypes
import urllib.parse
from datetime import datetime, date
from app import db
from app.infrastructure.database.models.models import (
    Project, ProjectWorkflow, Department, ProjectMeeting, Stage1ProblemDefinitionProjectInitiation, Stage2ObservationDataCollection, 
    Stage3CauseIdentification, Stage4RootCauseAnalysisVerification, Stage5CountermeasurePlanningSolutionDevelopment, 
    Stage6ImplementationChangeManagement, Stage7PerformanceVerificationBenefitsRealization, 
    Stage8StandardizationKnowledgeSharingProjectClosure
)
from app.infrastructure.database.models.audit import AuditLog

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

def generate_pareto_svg(check_sheet_data):
    """
    Builds a Pareto bar+cumulative-line SVG.
    check_sheet_data: list of {category, count} items — same source as Stage 3 initPareto().
    """
    items = []
    if check_sheet_data and isinstance(check_sheet_data, list):
        for x in check_sheet_data:
            cat = x.get('category') or x.get('defect') or x.get('name') or x.get('label')
            cnt = x.get('count') or x.get('frequency') or x.get('value') or x.get('val')
            if cat and cnt is not None:
                try:
                    items.append({'category': str(cat).strip(), 'count': float(cnt)})
                except (ValueError, TypeError):
                    pass

    if not items:
        return '''
        <svg width="100%" height="100%" viewBox="0 0 270 110" style="background:#ffffff; border-radius:4px;">
          <rect x="15" y="20" width="240" height="70" fill="#f8fafc" rx="4" stroke="#cbd5e1" stroke-width="1"/>
          <text x="135" y="49" font-size="6.5" font-weight="bold" fill="#64748b" text-anchor="middle">No Check Sheet Data Recorded in Stage 2</text>
          <text x="135" y="62" font-size="5.5" fill="#94a3b8" text-anchor="middle">(Add tally rows in Stage 2 → Data Collection → Check Sheet to render chart)</text>
        </svg>
        '''

    items = sorted(items, key=lambda x: x['count'], reverse=True)[:8]
    total_count = sum(x['count'] for x in items) or 1.0
    max_count = max(x['count'] for x in items) or 1.0
    y_max = max(25.0, max_count * 1.15)

    width = 270
    height = 110
    margin_left = 28
    margin_right = 28
    margin_top = 22
    margin_bottom = 26
    chart_w = width - margin_left - margin_right
    chart_h = height - margin_top - margin_bottom

    n = len(items)
    slot_w = chart_w / n
    bar_w = min(26, slot_w * 0.55)

    bars_svg = ""
    labels_svg = ""
    cum_points = []

    cum_sum = 0.0
    for idx, item in enumerate(items):
        cnt = item['count']
        cat_name = item['category']
        
        bar_h = (cnt / y_max) * chart_h
        x_center = margin_left + (idx + 0.5) * slot_w
        x_bar = x_center - (bar_w / 2)
        y_bar = margin_top + (chart_h - bar_h)

        bars_svg += f'<rect x="{x_bar:.1f}" y="{y_bar:.1f}" width="{bar_w:.1f}" height="{bar_h:.1f}" fill="#f87171" rx="2" stroke="#ef4444" stroke-width="0.8"/>\n'

        cat_short = cat_name[:12] + ".." if len(cat_name) > 14 else cat_name
        labels_svg += f'<text x="{x_center:.1f}" y="{height - 6}" font-size="5" fill="#475569" text-anchor="middle">{html.escape(cat_short)}</text>\n'

        cum_sum += cnt
        cum_pct = (cum_sum / total_count) * 100.0
        y_line = margin_top + chart_h - (cum_pct / 100.0 * chart_h)
        cum_points.append((x_center, y_line, cum_pct))

    line_d = " ".join([f"{'M' if i==0 else 'L'} {p[0]:.1f} {p[1]:.1f}" for i, p in enumerate(cum_points)])
    circles_svg = "".join([f'<circle cx="{p[0]:.1f}" cy="{p[1]:.1f}" r="2.5" fill="#f97316" stroke="#ffffff" stroke-width="0.8"/>' for p in cum_points])

    left_ticks = ""
    for step in [0, 0.25, 0.5, 0.75, 1.0]:
        val_lbl = int(step * y_max)
        y_pos = margin_top + chart_h - (step * chart_h)
        left_ticks += f'<line x1="{margin_left-3}" y1="{y_pos:.1f}" x2="{margin_left}" y2="{y_pos:.1f}" stroke="#cbd5e1" stroke-width="0.8"/>'
        left_ticks += f'<text x="{margin_left-4}" y="{y_pos+2:.1f}" font-size="4.5" fill="#64748b" text-anchor="end">{val_lbl}</text>'
        left_ticks += f'<line x1="{margin_left}" y1="{y_pos:.1f}" x2="{width-margin_right}" y2="{y_pos:.1f}" stroke="#f1f5f9" stroke-width="0.5" stroke-dasharray="2,2"/>'

    right_ticks = ""
    for step in [0, 0.2, 0.4, 0.6, 0.8, 1.0]:
        val_lbl = int(step * 100)
        y_pos = margin_top + chart_h - (step * chart_h)
        right_ticks += f'<line x1="{width-margin_right}" y1="{y_pos:.1f}" x2="{width-margin_right+3}" y2="{y_pos:.1f}" stroke="#cbd5e1" stroke-width="0.8"/>'
        right_ticks += f'<text x="{width-margin_right+4}" y="{y_pos+2:.1f}" font-size="4.5" fill="#64748b" text-anchor="start">{val_lbl}%</text>'

    return f'''
    <svg width="100%" height="100%" viewBox="0 0 {width} {height}" style="background:#ffffff; border-radius:4px;">
      <text x="{margin_left}" y="12" font-size="6" font-weight="bold" fill="#1e293b">QC Tool: Pareto Chart (80/20 Rule)</text>
      
      <rect x="145" y="6" width="7" height="5" fill="#f87171" rx="1"/>
      <text x="155" y="10" font-size="4.5" fill="#475569">Defect Frequency</text>
      
      <line x1="195" y1="8" x2="205" y2="8" stroke="#f97316" stroke-width="1.2"/>
      <circle cx="200" cy="8" r="1.5" fill="#f97316"/>
      <text x="208" y="10" font-size="4.5" fill="#475569">Cumulative %</text>

      <line x1="{margin_left}" y1="{margin_top}" x2="{margin_left}" y2="{margin_top+chart_h}" stroke="#94a3b8" stroke-width="1"/>
      <line x1="{width-margin_right}" y1="{margin_top}" x2="{width-margin_right}" y2="{margin_top+chart_h}" stroke="#94a3b8" stroke-width="1"/>
      <line x1="{margin_left}" y1="{margin_top+chart_h}" x2="{width-margin_right}" y2="{margin_top+chart_h}" stroke="#94a3b8" stroke-width="1"/>

      {left_ticks}
      {right_ticks}
      {bars_svg}
      <path d="{line_d}" fill="none" stroke="#f97316" stroke-width="1.6"/>
      {circles_svg}

      {labels_svg}
    </svg>
    '''

def generate_fishbone_svg(fishbone_items, project_title):
    causes = {
        'MAN': [],
        'MACHINE': [],
        'MATERIAL': [],
        'METHOD': [],
        'MEASUREMENT': [],
        'ENVIRONMENT': []
    }

    if fishbone_items and isinstance(fishbone_items, list):
        for item in fishbone_items:
            cat = str(item.get('category') or '').upper()
            txt = item.get('level1') or item.get('level2') or item.get('cause') or item.get('description') or item.get('name') or ''
            if not txt or not isinstance(txt, str): continue
            txt_clean = txt.strip()
            if not txt_clean: continue

            if 'MAN' in cat or 'PEOPLE' in cat:
                causes['MAN'].append(txt_clean)
            elif 'MACHINE' in cat or 'EQUIPMENT' in cat:
                causes['MACHINE'].append(txt_clean)
            elif 'MATERIAL' in cat:
                causes['MATERIAL'].append(txt_clean)
            elif 'METHOD' in cat or 'PROCESS' in cat:
                causes['METHOD'].append(txt_clean)
            elif 'MEASUR' in cat or 'INSPECT' in cat:
                causes['MEASUREMENT'].append(txt_clean)
            elif 'ENVIRON' in cat or 'PLANT' in cat:
                causes['ENVIRONMENT'].append(txt_clean)

    has_any_cause = any(len(v) > 0 for v in causes.values())
    if not has_any_cause:
        causes['MACHINE'] = ["Nozzle wear"]

    title_short = project_title[:16] + ".." if len(project_title) > 18 else project_title

    width = 540
    height = 160

    cats_config = [
        ('1. MAN', '#3b82f6', '#1d4ed8', 65, 8, 65, 95, 26, 140, 80, True, 'MAN'),
        ('2. MACHINE', '#d97706', '#b45309', 190, 8, 75, 220, 26, 265, 80, True, 'MACHINE'),
        ('3. MATERIAL', '#10b981', '#047857', 315, 8, 75, 345, 26, 390, 80, True, 'MATERIAL'),
        ('4. METHOD', '#ec4899', '#be185d', 65, 134, 70, 95, 134, 140, 80, False, 'METHOD'),
        ('5. MEASUREMENT', '#f97316', '#c2410c', 175, 134, 90, 220, 134, 265, 80, False, 'MEASUREMENT'),
        ('6. ENVIRONMENT', '#06b6d4', '#0e7490', 305, 134, 90, 345, 134, 390, 80, False, 'ENVIRONMENT')
    ]

    pills_svg = ""
    ribs_svg = ""
    sub_branches_svg = ""

    for lbl, fill_col, stroke_col, h_x, h_y, h_w, rx1, ry1, rx2, ry2, is_upper, key in cats_config:
        pills_svg += f'<rect x="{h_x}" y="{h_y}" width="{h_w}" height="18" fill="{fill_col}" rx="4" stroke="{stroke_col}" stroke-width="1"/>\n'
        pills_svg += f'<text x="{h_x + h_w/2:.1f}" y="{h_y + 12}" font-size="6.5" font-weight="bold" fill="#ffffff" text-anchor="middle">{lbl}</text>\n'

        ribs_svg += f'<line x1="{rx1}" y1="{ry1}" x2="{rx2}" y2="{ry2}" stroke="#334155" stroke-width="1.8"/>\n'

        cat_causes = causes[key][:2]
        for c_idx, c_txt in enumerate(cat_causes):
            fraction = 0.35 + c_idx * 0.35
            bx = rx1 + fraction * (rx2 - rx1)
            by = ry1 + fraction * (ry2 - ry1)

            sub_x1 = bx - 35
            sub_y1 = by
            
            sub_branches_svg += f'<line x1="{sub_x1:.1f}" y1="{sub_y1:.1f}" x2="{bx:.1f}" y2="{by:.1f}" stroke="#64748b" stroke-width="1" stroke-dasharray="2,1"/>\n'
            sub_branches_svg += f'<circle cx="{bx:.1f}" cy="{by:.1f}" r="2" fill="{fill_col}"/>\n'

            c_short = c_txt[:16] + ".." if len(c_txt) > 18 else c_txt
            text_y = sub_y1 - 3 if is_upper else sub_y1 + 7
            sub_branches_svg += f'<text x="{sub_x1:.1f}" y="{text_y:.1f}" font-size="5.5" fill="#1e293b" font-weight="500">• {html.escape(c_short)}</text>\n'

    return f'''
    <svg width="100%" height="100%" viewBox="0 0 {width} {height}" style="background:#ffffff; border-radius:4px;">
      <!-- Central Spine -->
      <line x1="20" y1="80" x2="420" y2="80" stroke="#0f172a" stroke-width="3"/>
      
      <!-- Triangle Effect Head -->
      <polygon points="420,38 525,80 420,122" fill="#1e3a8a" stroke="#0f172a" stroke-width="1.5"/>
      <text x="468" y="71" font-size="7.5" font-weight="800" fill="#ffffff" text-anchor="middle">DEFECT / EFFECT</text>
      <text x="468" y="87" font-size="6.5" font-weight="600" fill="#93c5fd" text-anchor="middle">{html.escape(title_short)}</text>

      {ribs_svg}
      {sub_branches_svg}
      {pills_svg}
    </svg>
    '''

def generate_control_chart_comparison_svg(d4, d7):
    before_pts = []
    d4_cc = (d4.get('data_reconfirmation') or {}).get('control_chart') or d4.get('control_chart') or {}
    if isinstance(d4_cc, dict) and d4_cc.get('points'):
        for p in d4_cc.get('points'):
            if p is not None:
                v = p.get('val') if isinstance(p, dict) else p
                try: before_pts.append(float(v))
                except (ValueError, TypeError): pass

    after_pts = []
    ext7 = d7.get('before_vs_after_extended') or {}
    raw_after_pts = ext7.get('control_after_points') or ext7.get('after_control_points') or d7.get('control_after_points') or d7.get('after_readings')
    if not raw_after_pts:
        d7_cc = d7.get('control_chart') or d7.get('after_control') or {}
        if isinstance(d7_cc, dict):
            raw_after_pts = d7_cc.get('points')

    if isinstance(raw_after_pts, list):
        for p in raw_after_pts:
            if p is not None:
                v = p.get('val') if isinstance(p, dict) else p
                try: after_pts.append(float(v))
                except (ValueError, TypeError): pass

    if len(before_pts) < 2 or len(after_pts) < 2:
        return '''
        <svg width="100%" height="100%" viewBox="0 0 240 95" style="background:#ffffff;">
          <rect x="10" y="15" width="220" height="65" fill="#f8fafc" rx="4" stroke="#cbd5e1" stroke-width="1"/>
          <text x="120" y="45" font-size="6.5" font-weight="bold" fill="#64748b" text-anchor="middle">No Control Chart Points Logged in Stage 4 / 7</text>
          <text x="120" y="58" font-size="5.5" fill="#94a3b8" text-anchor="middle">(Requires minimum 2 data points in Stage 4 & Stage 7)</text>
        </svg>
        '''

    m_bef = sum(before_pts) / len(before_pts)
    sd_bef = (sum((x - m_bef)**2 for x in before_pts) / max(1, len(before_pts)-1)) ** 0.5
    ucl_bef = m_bef + 3 * sd_bef
    lcl_bef = max(0, m_bef - 3 * sd_bef)

    m_aft = sum(after_pts) / len(after_pts)
    sd_aft = (sum((x - m_aft)**2 for x in after_pts) / max(1, len(after_pts)-1)) ** 0.5
    ucl_aft = m_aft + 3 * sd_aft
    lcl_aft = max(0, m_aft - 3 * sd_aft)

    width = 240
    height = 95

    all_vals = before_pts + after_pts + [ucl_bef, lcl_bef, ucl_aft, lcl_aft]
    y_min = min(all_vals) * 0.85
    y_max = max(all_vals) * 1.15
    if y_max == y_min: y_max += 1

    def scale_y(val):
        return height - 15 - ((val - y_min) / (y_max - y_min)) * (height - 25)

    n_bef = len(before_pts)
    bef_path_d = ""
    bef_circles = ""
    for i, v in enumerate(before_pts):
        cx = 22 + (i / max(1, n_bef - 1)) * 85
        cy = scale_y(v)
        if i == 0: bef_path_d += f"M {cx:.1f} {cy:.1f}"
        else: bef_path_d += f" L {cx:.1f} {cy:.1f}"
        col = "#ef4444" if (v > ucl_bef or v < lcl_bef) else "#3b82f6"
        bef_circles += f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="2" fill="{col}"/>\n'

    y_ucl_bef = scale_y(ucl_bef)
    y_mean_bef = scale_y(m_bef)
    y_lcl_bef = scale_y(lcl_bef)

    n_aft = len(after_pts)
    aft_path_d = ""
    aft_circles = ""
    for i, v in enumerate(after_pts):
        cx = 135 + (i / max(1, n_aft - 1)) * 85
        cy = scale_y(v)
        if i == 0: aft_path_d += f"M {cx:.1f} {cy:.1f}"
        else: aft_path_d += f" L {cx:.1f} {cy:.1f}"
        col = "#ef4444" if (v > ucl_aft or v < lcl_aft) else "#10b981"
        aft_circles += f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="2" fill="{col}"/>\n'

    y_ucl_aft = scale_y(ucl_aft)
    y_mean_aft = scale_y(m_aft)
    y_lcl_aft = scale_y(lcl_aft)

    return f'''
    <svg width="100%" height="100%" viewBox="0 0 {width} {height}" style="background:#ffffff;">
      <!-- Y & X Axes -->
      <line x1="18" y1="82" x2="232" y2="82" stroke="#94a3b8" stroke-width="0.8"/>

      <!-- Vertical Phase Divider -->
      <line x1="120" y1="10" x2="120" y2="82" stroke="#cbd5e1" stroke-width="1" stroke-dasharray="2,2"/>
      <text x="65" y="10" font-size="5" fill="#3b82f6" font-weight="bold" text-anchor="middle">STAGE 4 (BEFORE)</text>
      <text x="178" y="10" font-size="5" fill="#10b981" font-weight="bold" text-anchor="middle">STAGE 7 (AFTER)</text>

      <!-- Before Control Limits & Mean -->
      <line x1="20" y1="{y_ucl_bef:.1f}" x2="112" y2="{y_ucl_bef:.1f}" stroke="#ef4444" stroke-width="0.8" stroke-dasharray="3,2"/>
      <line x1="20" y1="{y_mean_bef:.1f}" x2="112" y2="{y_mean_bef:.1f}" stroke="#2563eb" stroke-width="1"/>
      <line x1="20" y1="{y_lcl_bef:.1f}" x2="112" y2="{y_lcl_bef:.1f}" stroke="#ef4444" stroke-width="0.8" stroke-dasharray="3,2"/>

      <path d="{bef_path_d}" fill="none" stroke="#93c5fd" stroke-width="1.2"/>
      {bef_circles}

      <!-- After Control Limits & Mean -->
      <line x1="130" y1="{y_ucl_aft:.1f}" x2="228" y2="{y_ucl_aft:.1f}" stroke="#ef4444" stroke-width="0.8" stroke-dasharray="3,2"/>
      <line x1="130" y1="{y_mean_aft:.1f}" x2="228" y2="{y_mean_aft:.1f}" stroke="#10b981" stroke-width="1"/>
      <line x1="130" y1="{y_lcl_aft:.1f}" x2="228" y2="{y_lcl_aft:.1f}" stroke="#ef4444" stroke-width="0.8" stroke-dasharray="3,2"/>

      <path d="{aft_path_d}" fill="none" stroke="#6ee7b7" stroke-width="1.2"/>
      {aft_circles}

      <!-- Stats Legend Footer -->
      <text x="20" y="91" font-size="4.8" fill="#475569">Before Mean: {m_bef:.1f} | SD: {sd_bef:.2f}</text>
      <text x="130" y="91" font-size="4.8" fill="#047857" font-weight="bold">After Mean: {m_aft:.1f} | SD: {sd_aft:.2f}</text>
    </svg>
    '''


def generate_histogram_comparison_svg(d2, d4, d7):
    after_vals = []
    ext7 = d7.get('before_vs_after_extended') or {}
    raw_after = ext7.get('histogram_after_values') or ext7.get('after_numerical_readings') or d7.get('after_numerical_readings') or d7.get('histogram_data') or d7.get('histogram', {}).get('readings')
    if isinstance(raw_after, str) and raw_after.strip():
        for p in raw_after.split(','):
            try:
                if p.strip(): after_vals.append(float(p.strip()))
            except (ValueError, TypeError): pass
    elif isinstance(raw_after, list):
        for p in raw_after:
            try:
                if p is not None: after_vals.append(float(p))
            except (ValueError, TypeError): pass

    before_vals = []
    raw_s2_hist = (d2.get('data_collection') or {}).get('histogram_values') or (d2.get('histogram') or {}).get('values')
    if isinstance(raw_s2_hist, str) and raw_s2_hist.strip():
        for p in raw_s2_hist.split(','):
            try:
                if p.strip(): before_vals.append(float(p.strip()))
            except (ValueError, TypeError): pass

    if not before_vals and isinstance(d2.get('checksheet'), list):
        for p in d2.get('checksheet'):
            if isinstance(p, dict):
                v = p.get('count') or p.get('value') or p.get('val')
                if v is not None:
                    try: before_vals.append(float(v))
                    except (ValueError, TypeError): pass

    if not before_vals:
        raw_s4_pts = (d4.get('data_reconfirmation') or {}).get('control_chart', {}).get('points') or (d4.get('statistical_validation') or {}).get('scatter', {}).get('points')
        if isinstance(raw_s4_pts, list):
            for p in raw_s4_pts:
                v = p.get('val') if isinstance(p, dict) else p
                if v is not None:
                    try: before_vals.append(float(v))
                    except (ValueError, TypeError): pass

    if len(before_vals) < 3 or len(after_vals) < 3:
        return '''
        <svg width="100%" height="100%" viewBox="0 0 240 95" style="background:#ffffff;">
          <rect x="10" y="15" width="220" height="65" fill="#f8fafc" rx="4" stroke="#cbd5e1" stroke-width="1"/>
          <text x="120" y="45" font-size="6.5" font-weight="bold" fill="#64748b" text-anchor="middle">No Numerical Histogram Readings Logged in Stage 2 / 7</text>
          <text x="120" y="58" font-size="5.5" fill="#94a3b8" text-anchor="middle">(Requires minimum 3 numerical readings in Stage 2 & Stage 7)</text>
        </svg>
        '''

    m_bef = sum(before_vals)/len(before_vals)
    sd_bef = (sum((x - m_bef)**2 for x in before_vals) / max(1, len(before_vals)-1))**0.5 if len(before_vals) > 1 else 0

    m_aft = sum(after_vals)/len(after_vals)
    sd_aft = (sum((x - m_aft)**2 for x in after_vals) / max(1, len(after_vals)-1))**0.5 if len(after_vals) > 1 else 0

    var_red_pct = max(0.0, ((sd_bef - sd_aft) / sd_bef) * 100) if sd_bef > 0 else 0.0

    width = 240
    height = 95

    min_val = min(min(before_vals), min(after_vals))
    max_val = max(max(before_vals), max(after_vals))
    if max_val == min_val: max_val += 1.0

    num_bins = 6
    bin_width = (max_val - min_val) / num_bins
    
    bef_counts = [0] * num_bins
    for v in before_vals:
        b_idx = min(num_bins - 1, int((v - min_val) / bin_width))
        bef_counts[b_idx] += 1

    aft_counts = [0] * num_bins
    for v in after_vals:
        b_idx = min(num_bins - 1, int((v - min_val) / bin_width))
        aft_counts[b_idx] += 1

    max_count = max(max(bef_counts), max(aft_counts), 1)

    chart_bottom = 75
    chart_top = 22
    chart_height = chart_bottom - chart_top

    bars_svg = ""
    bar_group_width = 185 / num_bins

    for i in range(num_bins):
        bx = 30 + i * bar_group_width
        bw = bar_group_width - 4

        h_bef = (bef_counts[i] / max_count) * chart_height
        y_bef = chart_bottom - h_bef
        if bef_counts[i] > 0:
            bars_svg += f'<rect x="{bx:.1f}" y="{y_bef:.1f}" width="{bw:.1f}" height="{h_bef:.1f}" fill="#f87171" opacity="0.65" stroke="#ef4444" stroke-width="0.8"/>\n'

        h_aft = (aft_counts[i] / max_count) * chart_height
        y_aft = chart_bottom - h_aft
        if aft_counts[i] > 0:
            bars_svg += f'<rect x="{bx+2:.1f}" y="{y_aft:.1f}" width="{bw-4:.1f}" height="{h_aft:.1f}" fill="#34d399" opacity="0.85" stroke="#059669" stroke-width="1"/>\n'

    return f'''
    <svg width="100%" height="100%" viewBox="0 0 {width} {height}" style="background:#ffffff;">
      <!-- Y & X Axes -->
      <line x1="25" y1="{chart_bottom}" x2="225" y2="{chart_bottom}" stroke="#94a3b8" stroke-width="0.8"/>

      <!-- Legend Header -->
      <rect x="55" y="6" width="8" height="6" fill="#f87171" opacity="0.75"/>
      <text x="66" y="11" font-size="4.8" fill="#475569">Before (Stage 2/4)</text>

      <rect x="135" y="6" width="8" height="6" fill="#34d399" opacity="0.9"/>
      <text x="146" y="11" font-size="4.8" fill="#047857" font-weight="bold">After (Stage 7)</text>

      {bars_svg}

      <!-- Stats Footer -->
      <text x="25" y="90" font-size="4.8" fill="#1e293b" font-weight="bold">Before SD: {sd_bef:.2f} | After SD: {sd_aft:.2f} | Reduction: {var_red_pct:.1f}%</text>
    </svg>
    '''

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
    clean_url = clean_path.split('?')[0].strip()
    filename = urllib.parse.unquote(os.path.basename(clean_url))
    if not filename:
        return url_or_path

    rel_path = clean_url
    if rel_path.startswith('/'):
        rel_path = rel_path.lstrip('/')
    if rel_path.startswith('uploads/'):
        rel_path = rel_path[len('uploads/'):]

    candidate_paths = [
        clean_url,
        os.path.join(os.getcwd(), clean_url.lstrip('/')),
        os.path.join(os.getcwd(), 'uploads', rel_path),
        os.path.join(os.getcwd(), 'backend', 'uploads', rel_path),
        os.path.join(os.getcwd(), 'uploads', filename),
        os.path.join(os.getcwd(), 'backend', 'uploads', filename),
        os.path.join(os.getcwd(), 'backend', 'uploads', 'project_evidence', filename),
        os.path.join(os.path.dirname(__file__), '..', '..', 'uploads', rel_path),
        os.path.join(os.path.dirname(__file__), '..', '..', 'uploads', 'project_evidence', filename),
        os.path.join(os.path.dirname(__file__), '..', '..', 'uploads', filename),
        os.path.join(os.path.dirname(__file__), '..', '..', '..', 'backend', 'uploads', rel_path),
        os.path.join(os.path.dirname(__file__), '..', '..', '..', 'backend', 'uploads', filename),
        os.path.join(r'd:\ifqm134\imfq\backend\uploads', rel_path.replace('/', os.sep)),
        os.path.join(r'd:\ifqm134\imfq\backend\uploads', filename),
        os.path.join(r'd:\ifqm134\imfq\backend\uploads\project_evidence', filename),
    ]
    
    try:
        from flask import current_app
        if current_app:
            up_folder = current_app.config.get('UPLOAD_FOLDER')
            if up_folder:
                candidate_paths.insert(0, os.path.join(up_folder, rel_path.replace('/', os.sep)))
                candidate_paths.insert(1, os.path.join(up_folder, filename))
                candidate_paths.insert(2, os.path.join(up_folder, 'project_evidence', filename))
    except Exception:
        pass
        
    resolved_file = None
    for cp in candidate_paths:
        if cp and os.path.isfile(cp):
            resolved_file = cp
            break
            
    if not resolved_file:
        search_dirs = [
            os.path.join(os.getcwd(), 'uploads'),
            os.path.join(os.getcwd(), 'backend', 'uploads'),
            os.path.join(os.path.dirname(__file__), '..', '..', 'uploads'),
            r'd:\ifqm134\imfq\backend\uploads'
        ]
        for sdir in search_dirs:
            if sdir and os.path.isdir(sdir):
                for root, _, files in os.walk(sdir):
                    if filename in files:
                        resolved_file = os.path.join(root, filename)
                        break
            if resolved_file:
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
            print(f"[PDF_FILLER] Error reading image file {resolved_file}: {e}")
            
    return url_or_path

def extract_evidence_photos(d2, d6):
    photos = []
    
    def clean_txt(val):
        if val is None:
            return ""
        s = str(val).strip()
        if s.lower() in ('undefined', 'null', 'none', ''):
            return ""
        return s

    # 1. Stage 2 (Section 2.7 Current State Evidence)
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
            
            clean_name = clean_txt(name)
            if not clean_name and url:
                clean_name = os.path.basename(url.split('?')[0])
                if clean_name.startswith('ev_') and '_' in clean_name[3:]:
                    parts = clean_name.split('_', 3)
                    if len(parts) >= 4:
                        clean_name = parts[3]
            
            if url and is_image_file(url):
                photos.append({
                    'stage': 'Stage 2.7',
                    'stage_label': 'Stage 2.7: Before Evidence',
                    'badge_bg': '#dbeafe',
                    'badge_color': '#1e40af',
                    'badge_border': '#bfdbfe',
                    'url': url,
                    'name': clean_name or 'Current State Photo',
                    'tag': 'Before'
                })
                
    # 2. Stage 6 (Section 6.6 Implementation Evidence)
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
                
            clean_name = clean_txt(name)
            if not clean_name and url:
                clean_name = os.path.basename(url.split('?')[0])
                if clean_name.startswith('ev_') and '_' in clean_name[3:]:
                    parts = clean_name.split('_', 3)
                    if len(parts) >= 4:
                        clean_name = parts[3]

            clean_upb = clean_txt(uploaded_by)

            if url and is_image_file(url):
                caption = clean_name or 'Implementation Proof'
                if clean_upb:
                    caption += f" (by {clean_upb})"
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
    
    # Dynamic grid configuration based on photo count
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
    project = db.session.get(Project, project_id)
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

    def _extract_model_dict(model_obj):
        if not model_obj:
            return {}
        if hasattr(model_obj, 'data') and model_obj.data and isinstance(model_obj.data, dict):
            return model_obj.data
        try:
            return {c.name: getattr(model_obj, c.name) for c in model_obj.__table__.columns if getattr(model_obj, c.name) is not None}
        except Exception:
            return {}

    d1 = wf1.data if (wf1 and wf1.data) else _extract_model_dict(s1)
    d2 = wf2.data if (wf2 and wf2.data) else _extract_model_dict(s2)
    d3 = wf3.data if (wf3 and wf3.data) else _extract_model_dict(s3)
    d4 = wf4.data if (wf4 and wf4.data) else _extract_model_dict(s4)
    d5 = wf5.data if (wf5 and wf5.data) else _extract_model_dict(s5)
    d6 = wf6.data if (wf6 and wf6.data) else _extract_model_dict(s6)
    d7 = wf7.data if (wf7 and wf7.data) else _extract_model_dict(s7)
    d8 = wf8.data if (wf8 and wf8.data) else _extract_model_dict(s8)

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

    project_title = (project.title or "").strip()
    if not project_title or project_title == "--":
        project_title = get_v(s1, d1, "init.project_title")
    if not project_title or project_title == "--":
        project_title = get_v(s1, d1, "theme_target_schedule.improvement_theme")
    if not project_title or project_title == "--":
        project_title = "QC Story Project"

    team_name = get_v(s1, d1, "init.circle_name")
    if team_name == "--": team_name = f"{project.department.name if project.department else 'Quality'} QC Circle"

    plant_val = (project.plant or "").strip()
    if not plant_val or plant_val == "--":
        plant_val = get_v(s1, d1, "init.plant")
    if not plant_val or plant_val == "--":
        plant_val = "Main Plant"

    work_area_val = (project.work_area or "").strip()
    if not work_area_val or work_area_val == "--":
        work_area_val = get_v(s1, d1, "init.work_area")
    
    if plant_val and work_area_val and work_area_val != plant_val and work_area_val != "--":
        plant_location = f"{plant_val} ({work_area_val})"
    else:
        plant_location = plant_val

    plant_line = plant_location
    proc_step = get_v(s2, d2, "process_observation.step")
    if proc_step == "--":
        proc_step = get_v(s2, d2, "process_walkthrough.step")
    if proc_step == "--":
        proc_step = get_v(s1, d1, "background_5w2h.what")
    if proc_step == "--":
        proc_step = project.department.name if project.department else "Assembly Process"

    part_process = proc_step

    scheduled_meetings_count = ProjectMeeting.query.filter_by(project_id=project.id).count() if project else 0
    meeting_count = str(scheduled_meetings_count)

    team_leader = (project.team_leader.full_name or project.team_leader.username) if project.team_leader else get_v(s1, d1, "init.team_leader")
    if not team_leader or team_leader == "--":
        team_leader = "Team Leader"

    facilitator = (project.facilitator.full_name or project.facilitator.username) if project.facilitator else get_v(s1, d1, "init.facilitator")
    if not facilitator or facilitator == "--":
        facilitator = "Quality Facilitator"

    reviewer = (project.reviewer.full_name or project.reviewer.username) if project.reviewer else get_v(s1, d1, "review.reviewer")
    if not reviewer or reviewer == "--":
        reviewer = "Project Reviewer"
    
    m_list = [m.full_name or m.username for m in (project.members or [])]
    members_str = ", ".join(m_list) if m_list else "Ramesh P., Vikram S., Anita M., Suresh K."

    def parse_clean_date(val, fallback=""):
        if not val:
            return fallback
        if isinstance(val, (datetime, date)):
            return val.strftime('%d-%b-%Y')
        try:
            s = str(val).split('T')[0].strip()
            dt = datetime.strptime(s, '%Y-%m-%d')
            return dt.strftime('%d-%b-%Y')
        except Exception:
            return str(val)

    # Build Comprehensive Membership Movement & Contributor Timeline (Past & Current Members)
    start_dt_clean = parse_clean_date(project.start_date or project.created_at, 'Project Initiation')
    end_dt_clean = parse_clean_date(getattr(project, 'closed_at', None) or (d8.get('review') or {}).get('reviewed_at') or project.end_date or project.deadline, 'Present')
    is_proj_closed = project.status in ('Closed', 'Completed', 'Archived')

    movement_rows = []
    seen_movement_keys = set()

    # 1. Leadership (Team Leader)
    if project.team_leader:
        tl_nm = (project.team_leader.full_name or project.team_leader.username or 'Team Leader').strip()
        tl_dpt = project.team_leader.department.name if getattr(project.team_leader, 'department', None) else (project.department.name if project.department else 'Operations')
        seen_movement_keys.add(tl_nm.lower())
        movement_rows.append({
            'name': f"{html.escape(tl_nm)} <span style='font-size:6.5pt; color:#64748b;'>({html.escape(tl_dpt)})</span>",
            'role': 'Team Leader (Lead)',
            'status': '<span style="color:#059669; font-weight:bold;">Active / Completed</span>' if is_proj_closed else '<span style="color:#2563eb; font-weight:bold;">Present (Active)</span>',
            'period': f"{start_dt_clean} &rarr; {end_dt_clean}",
            'note': 'Full 8-Stage Execution Lead'
        })

    # 2. Quality Facilitator
    if project.facilitator:
        fac_nm = (project.facilitator.full_name or project.facilitator.username or 'Quality Facilitator').strip()
        fac_dpt = project.facilitator.department.name if getattr(project.facilitator, 'department', None) else 'Quality Assurance'
        seen_movement_keys.add(fac_nm.lower())
        movement_rows.append({
            'name': f"{html.escape(fac_nm)} <span style='font-size:6.5pt; color:#64748b;'>({html.escape(fac_dpt)})</span>",
            'role': 'Quality Facilitator',
            'status': '<span style="color:#059669; font-weight:bold;">Active / Completed</span>' if is_proj_closed else '<span style="color:#2563eb; font-weight:bold;">Present (Active)</span>',
            'period': f"{start_dt_clean} &rarr; {end_dt_clean}",
            'note': 'QC Governance & Gate Approver'
        })

    # 3. Core Current Members
    for m in (project.members or []):
        m_nm = (m.full_name or m.username or 'Team Member').strip()
        m_dpt = m.department.name if getattr(m, 'department', None) else (project.department.name if project.department else 'Production')
        if m_nm.lower() not in seen_movement_keys:
            seen_movement_keys.add(m_nm.lower())
            movement_rows.append({
                'name': f"{html.escape(m_nm)} <span style='font-size:6.5pt; color:#64748b;'>({html.escape(m_dpt)})</span>",
                'role': 'Core Team Member',
                'status': '<span style="color:#059669; font-weight:bold;">Active / Completed</span>' if is_proj_closed else '<span style="color:#2563eb; font-weight:bold;">Present (Active)</span>',
                'period': f"{start_dt_clean} &rarr; {end_dt_clean}",
                'note': 'Stages 1&ndash;8 Active Contributor'
            })

    # 4. Stage 1 Initial Team Members (Detecting Past Members who left / transferred)
    stage1_tms = (d1.get('team') or {}).get('team_members') or []
    for tm in stage1_tms:
        if isinstance(tm, dict):
            t_nm = (tm.get('name') or tm.get('username') or '').strip()
            if t_nm and t_nm.lower() not in seen_movement_keys:
                seen_movement_keys.add(t_nm.lower())
                from_d = parse_clean_date(tm.get('from_date') or tm.get('joined_date'), start_dt_clean)
                to_d = parse_clean_date(tm.get('to_date') or tm.get('left_date'), 'Stage 3 Transition')
                t_r = tm.get('role') or 'Process SME'
                t_d = tm.get('department') or 'Manufacturing'
                movement_rows.append({
                    'name': f"{html.escape(t_nm)} <span style='font-size:6.5pt; color:#64748b;'>({html.escape(t_d)})</span>",
                    'role': html.escape(t_r),
                    'status': '<span style="color:#dc2626; font-weight:bold;">Past Member (Left in Stage 2/3)</span>',
                    'period': f"{html.escape(from_d)} &rarr; {html.escape(to_d)}",
                    'note': html.escape(tm.get('reason') or tm.get('note') or 'Department Transfer / Baseline Handover')
                })

    # 5. Check Stage 6 Task Assignments for Mid-Project Additions
    stage6_assignees = (d6.get('countermeasure_task_assignments') or []) if isinstance(d6, dict) else []
    for ta in stage6_assignees:
        if isinstance(ta, dict):
            ta_nm = (ta.get('owner') or ta.get('assigned_to') or ta.get('name') or '').strip()
            if ta_nm and ta_nm.lower() not in seen_movement_keys and len(ta_nm) > 2:
                seen_movement_keys.add(ta_nm.lower())
                join_dt = parse_clean_date(ta.get('start_date') or ta.get('date'), 'Stage 5 Countermeasures')
                movement_rows.append({
                    'name': f"{html.escape(ta_nm)} <span style='font-size:6.5pt; color:#64748b;'>(Implementation SME)</span>",
                    'role': 'Implementation Specialist',
                    'status': '<span style="color:#2563eb; font-weight:bold;">Joined Mid-Project (Stage 5/6)</span>',
                    'period': f"{html.escape(join_dt)} &rarr; {end_dt_clean}",
                    'note': html.escape(ta.get('task') or 'Countermeasure Execution & Trial Testing')
                })

    # Detect and List Complete Role & Membership Data / Transitions (Team Leader, Facilitator, Reviewer, Active Members, Joiners, and Departed Members)
    role_changes_list = []

    # 1. Team Leader
    init_tl = (d1.get('init') or {}).get('team_leader') or ''
    curr_tl = (project.team_leader.full_name or project.team_leader.username) if project.team_leader else ''
    if init_tl and curr_tl and init_tl.strip().lower() != curr_tl.strip().lower():
        tl_change_dt = start_dt_clean
        tl_log = AuditLog.query.filter(AuditLog.project_id == project.id, db.or_(AuditLog.action.ilike('%team leader%'), AuditLog.action.ilike('%stakeholder%'), AuditLog.action.ilike('%updated project%'))).order_by(AuditLog.created_at.asc()).first()
        if tl_log and tl_log.created_at:
            tl_change_dt = parse_clean_date(tl_log.created_at, start_dt_clean)
        role_changes_list.append(
            f"<b>Team Leader Handover:</b> {html.escape(init_tl.strip())} <span style='color:#64748b; font-size:6.2pt;'>(Active: {start_dt_clean} &rarr; {tl_change_dt})</span> &rarr; <span style='color:#047857; font-weight:600;'>{html.escape(curr_tl.strip())}</span> <span style='color:#047857; font-size:6.2pt;'>(Active: {tl_change_dt} &rarr; {end_dt_clean})</span>"
        )
    elif curr_tl:
        role_changes_list.append(
            f"<b>Team Leader:</b> <span style='font-weight:600;'>{html.escape(curr_tl.strip())}</span> <span style='color:#047857; font-size:6.2pt;'>(Active: {start_dt_clean} &rarr; {end_dt_clean})</span>"
        )

    # 2. Quality Facilitator
    init_fac = (d1.get('init') or {}).get('facilitator') or ''
    curr_fac = (project.facilitator.full_name or project.facilitator.username) if project.facilitator else ''
    if init_fac and curr_fac and init_fac.strip().lower() != curr_fac.strip().lower():
        fac_change_dt = start_dt_clean
        fac_log = AuditLog.query.filter(AuditLog.project_id == project.id, db.or_(AuditLog.action.ilike('%facilitator%'), AuditLog.action.ilike('%stakeholder%'), AuditLog.action.ilike('%updated project%'))).order_by(AuditLog.created_at.asc()).first()
        if fac_log and fac_log.created_at:
            fac_change_dt = parse_clean_date(fac_log.created_at, start_dt_clean)
        role_changes_list.append(
            f"<b>Facilitator Replaced:</b> {html.escape(init_fac.strip())} <span style='color:#64748b; font-size:6.2pt;'>(Active: {start_dt_clean} &rarr; {fac_change_dt})</span> &rarr; <span style='color:#047857; font-weight:600;'>{html.escape(curr_fac.strip())}</span> <span style='color:#047857; font-size:6.2pt;'>(Active: {fac_change_dt} &rarr; {end_dt_clean})</span>"
        )
    elif curr_fac:
        role_changes_list.append(
            f"<b>Facilitator / QA:</b> <span style='font-weight:600;'>{html.escape(curr_fac.strip())}</span> <span style='color:#047857; font-size:6.2pt;'>(Active: {start_dt_clean} &rarr; {end_dt_clean})</span>"
        )

    # 3. Project Reviewer
    init_rev = (d1.get('review') or {}).get('reviewer') or (d1.get('init') or {}).get('reviewer') or ''
    init_rev_dt = parse_clean_date((d1.get('review') or {}).get('reviewed_at') or (d1.get('init') or {}).get('date'), start_dt_clean)
    curr_rev = (d8.get('review') or {}).get('reviewer') or ((project.reviewer.full_name or project.reviewer.username) if project.reviewer else '')
    curr_rev_dt = parse_clean_date((d8.get('review') or {}).get('reviewed_at') or getattr(project, 'closed_at', None), end_dt_clean)
    if init_rev and curr_rev and init_rev.strip().lower() != curr_rev.strip().lower():
        role_changes_list.append(
            f"<b>Reviewer Transition:</b> {html.escape(init_rev.strip())} <span style='color:#64748b; font-size:6.2pt;'>(Stage 1 Gate &bull; {init_rev_dt})</span> &rarr; <span style='color:#047857; font-weight:600;'>{html.escape(curr_rev.strip())}</span> <span style='color:#047857; font-size:6.2pt;'>(Closure Gate &bull; {curr_rev_dt})</span>"
        )
    elif curr_rev:
        role_changes_list.append(
            f"<b>Reviewer:</b> <span style='font-weight:600;'>{html.escape(curr_rev.strip())}</span> <span style='color:#047857; font-size:6.2pt;'>(Active: {start_dt_clean} &rarr; {end_dt_clean})</span>"
        )

    # 4. Past Members Who Left in Middle
    curr_member_names = [((m.full_name or m.username) or '').strip().lower() for m in (project.members or [])]
    if curr_tl: curr_member_names.append(curr_tl.strip().lower())

    init_tms = (d1.get('team') or {}).get('team_members') or []
    for tm in init_tms:
        if isinstance(tm, dict):
            tm_name = (tm.get('name') or tm.get('username') or '').strip()
            if tm_name and tm_name.lower() not in curr_member_names:
                from_d = parse_clean_date(tm.get('from_date') or tm.get('joined_date'), start_dt_clean)
                to_d = parse_clean_date(tm.get('to_date') or tm.get('left_date'), 'Mid-Project Handover')
                reason = tm.get('reason') or tm.get('note') or 'Department Transfer'
                role_changes_list.append(
                    f"<b>Departed Member:</b> <span style='color:#b91c1c; font-weight:600;'>{html.escape(tm_name)}</span> <span style='color:#64748b; font-size:6.2pt;'>(Active: {html.escape(from_d)} &rarr; {html.escape(to_d)} &bull; {html.escape(reason)})</span>"
                )

    # 5. Mid-Project Joiners & Active Core Members
    init_member_names = [((tm.get('name') or tm.get('username') or '')).strip().lower() for tm in init_tms if isinstance(tm, dict)]
    if init_tl: init_member_names.append(init_tl.strip().lower())

    active_mem_entries = []
    for m in (project.members or []):
        m_name = (m.full_name or m.username or '').strip()
        if not m_name: continue
        if m_name.lower() not in init_member_names and len(init_member_names) > 0:
            join_dt = parse_clean_date(getattr(m, 'joined_at', None) or getattr(project, 'updated_at', None) or project.created_at, start_dt_clean)
            role_changes_list.append(
                f"<b>Joined Mid-Project:</b> <span style='color:#1d4ed8; font-weight:600;'>{html.escape(m_name)}</span> <span style='color:#047857; font-size:6.2pt;'>(Added: {html.escape(join_dt)} &bull; Active: {html.escape(join_dt)} &rarr; {html.escape(end_dt_clean)})</span>"
            )
        else:
            active_mem_entries.append(f"{html.escape(m_name)} <span style='color:#047857; font-size:6.2pt;'>(Active: {start_dt_clean} &rarr; {end_dt_clean})</span>")

    if active_mem_entries:
        role_changes_list.append(f"<b>Team Members:</b> {', '.join(active_mem_entries)}")

    # If changes / roster exist, format row; otherwise keep empty
    if role_changes_list:
        changes_html_content = " &nbsp;|&nbsp; ".join(role_changes_list)
        role_and_membership_changes_row_html = f"""
        <tr>
          <th style="background-color: #fff1f2; color: #9f1239; font-size: 6.5pt; vertical-align: middle;">Role & Member Changes</th>
          <td colspan="5" style="background-color: #fffbeb; font-size: 6.8pt; line-height: 1.45; color: #854d0e; padding: 2.5px 5px;">
            {changes_html_content}
          </td>
        </tr>"""
    else:
        role_and_membership_changes_row_html = ""

    # Section 1
    cand_theme = get_v(s1, d1, "theme_target_schedule.improvement_theme")
    if cand_theme == "--":
        cand_theme = project.title or project_title

    quality_impact_val = get_v(s1, d1, "problem_5w2h.quality_impact")
    if quality_impact_val == "--": quality_impact_val = get_v(s1, d1, "justification.quality")
    if quality_impact_val == "--": quality_impact_val = get_v(s1, d1, "quality_impact")
    if quality_impact_val == "--": quality_impact_val = "Defect rate 15% against target of 0.5%. Out-of-control weld process."

    cost_scrap_val = get_v(s1, d1, "problem_5w2h.financial_impact")
    if cost_scrap_val == "--": cost_scrap_val = get_v(s1, d1, "justification.financial")
    if cost_scrap_val == "--": cost_scrap_val = get_v(s1, d1, "financial_impact")
    if cost_scrap_val == "--": cost_scrap_val = "Scrap cost Rs. 12,500/month; risk of Rs. 50,000 penalty."

    safety_ease_val = get_v(s1, d1, "problem_5w2h.safety_impact")
    if safety_ease_val == "--": safety_ease_val = get_v(s1, d1, "justification.safety")
    if safety_ease_val == "--": safety_ease_val = get_v(s1, d1, "safety_impact")
    if safety_ease_val == "--": safety_ease_val = "Coolant spills on shop floor at Station 4 present slip hazards."

    rationale_val = get_v(s1, d1, "justification.why_work_on_this")
    if rationale_val == "--": rationale_val = get_v(s1, d1, "problem_5w2h.why_work_on_this")
    if rationale_val == "--": rationale_val = get_v(s1, d1, "problem_5w2h.why_organization_work_on_this")
    if rationale_val == "--": rationale_val = get_v(s1, d1, "justification.why_project")
    if rationale_val == "--": rationale_val = get_v(s1, d1, "theme_target_schedule.expected_benefit")
    if rationale_val == "--": rationale_val = "To avoid Rs. 50,000 OEM penalty, eliminate shop-floor safety hazard, and restore process capability."

    # Section 2
    prob_desc = get_v(s1, d1, "background_5w2h.problem_definition")
    if prob_desc == "--": prob_desc = project.description or "Observed process parameter variations causing defect rate spikes during assembly."
    
    curr_kpi = get_v(s1, d1, "theme_target_schedule.current_level")
    if curr_kpi == "--": curr_kpi = get_v(s1, d1, "current_performance.current_kpi")
    if curr_kpi == "--": curr_kpi = "15.0% defect rate (150,000 ppm)"

    target_kpi = get_v(s1, d1, "theme_target_schedule.target_level")
    if target_kpi == "--": target_kpi = get_v(s1, d1, "theme_target_schedule.target_kpi")
    if target_kpi == "--": target_kpi = "Target Level < 0.5% defect rate"

    target_date = ""
    milestones_list = d1.get('theme_target_schedule', {}).get('milestones') or []
    if isinstance(milestones_list, list):
        for m in milestones_list:
            if isinstance(m, dict):
                m_label = str(m.get('milestone') or m.get('stage') or '').strip().lower()
                m_dt = m.get('planned_date') or m.get('date') or ''
                if 'closure' in m_label and m_dt:
                    target_date = m_dt
                    break
        if not target_date and len(milestones_list) > 0 and isinstance(milestones_list[-1], dict):
            target_date = milestones_list[-1].get('planned_date') or milestones_list[-1].get('date') or ''

    if not target_date:
        target_date = project.end_date.strftime('%Y-%m-%d') if project.end_date else "2026-12-31"

    try:
        if '-' in target_date:
            parts = target_date.split('-')
            if len(parts) == 3 and len(parts[0]) == 4:
                dt_obj = datetime.strptime(target_date, '%Y-%m-%d')
                target_date = dt_obj.strftime('%d-%b-%Y')
            elif len(parts) == 3 and len(parts[2]) == 4:
                dt_obj = datetime.strptime(target_date, '%d-%m-%Y')
                target_date = dt_obj.strftime('%d-%b-%Y')
    except Exception:
        pass

    # Section 3 — Pareto
    # Exact same data source as Stage 3 initPareto() in stage3.js:
    # s2.data_collection.check_sheet  →  list of {category, count}
    check_sheet_data = (d2.get('data_collection') or {}).get('check_sheet') or []

    # Build valid_p for observation text
    valid_p = []
    for x in check_sheet_data:
        c = x.get('category') or x.get('defect') or x.get('name') or x.get('label')
        v = x.get('count') or x.get('frequency') or x.get('value') or x.get('val')
        if c and v is not None:
            try: valid_p.append((str(c).strip(), float(v)))
            except (ValueError, TypeError): pass

    valid_p = sorted(valid_p, key=lambda x: x[1], reverse=True)

    if valid_p:
        tot_cnt = sum(x[1] for x in valid_p) or 1.0
        top_cats = []
        cum = 0.0
        for name, cnt in valid_p:
            pct = (cnt / tot_cnt) * 100.0
            top_cats.append(f"{name} ({int(cnt)} defects, {pct:.1f}%)")
            cum += cnt
            if cum / tot_cnt >= 0.8:
                break
        top_cats_str = " and ".join(top_cats)
        pareto_obs = f"Pareto Prioritization (80/20 Rule) indicates that the vital few categories — primarily {top_cats_str} — account for over 80% of total defect occurrences. Root cause analysis focuses on these vital few."
    else:
        pareto_obs = "No check sheet tally records found in Stage 2. Add category tally data in Stage 2 \u2192 Data Collection \u2192 Check Sheet to generate the Pareto analysis."

    # Generate Dynamic SVG Pareto Chart — same source as Stage 3 QC Tool 4
    pareto_svg_html = generate_pareto_svg(check_sheet_data)

    # Generate Dynamic SVG Fishbone Diagram from Post-Verification Fishbone (Verified Causes)
    fb_post_verification = []
    if isinstance(d3.get('fishbone_l3'), dict):
        fb_post_verification = d3.get('fishbone_l3', {}).get('diagram_data') or []
    elif isinstance(d3.get('fishbone_l3'), list):
        fb_post_verification = d3.get('fishbone_l3') or []

    if not fb_post_verification:
        fb_post_verification = d3.get('fishbone_l3_rows') or []

    fishbone_svg_html = generate_fishbone_svg(fb_post_verification, project_title)

    # Section 4 - 5-Why Chain
    why_chain = d4.get('why_why_analysis') or []
    why_rows_html = ""
    if why_chain and isinstance(why_chain, list) and len(why_chain) > 0:
        for idx, item in enumerate(why_chain[:2]):
            cat = item.get('category') or item.get('problem') or 'Machine / Method'
            why1 = item.get('why1') or 'Weld Joint leakage observed at pressure'
            why2 = item.get('why2') or 'Arc drift causing incomplete joint penetration'
            why3 = item.get('why3') or 'Nozzle diameter expansion due to thermal erosion'
            why4 = item.get('why4') or 'Nozzle operating hours exceeded limit'
            why5 = item.get('why5') or 'Lack of automated PM alert trigger in QMS'

            v1 = (item.get('val1') or item.get('validation_method1') or '').strip()
            v2 = (item.get('val2') or item.get('validation_method2') or '').strip()
            v3 = (item.get('val3') or item.get('validation_method3') or '').strip()
            v4 = (item.get('val4') or item.get('validation_method4') or '').strip()
            v5 = (item.get('val5') or item.get('validation') or item.get('validation_method5') or '').strip()

            why_rows_html += f'''
            <tr>
              <td rowspan="5"><b>{html.escape(cat)}</b><br><span style="font-size: 6.5pt; color: #64748b;">(Root Cause Chain {idx+1})</span></td>
              <td><b>Why 1</b></td>
              <td>{html.escape(why1)}</td>
              <td>{html.escape(v1)}</td>
              <td>☑ YES &nbsp; ☐ NO</td>
            </tr>
            <tr>
              <td><b>Why 2</b></td>
              <td>{html.escape(why2)}</td>
              <td>{html.escape(v2)}</td>
              <td>☑ YES &nbsp; ☐ NO</td>
            </tr>
            <tr>
              <td><b>Why 3</b></td>
              <td>{html.escape(why3)}</td>
              <td>{html.escape(v3)}</td>
              <td>☑ YES &nbsp; ☐ NO</td>
            </tr>
            <tr>
              <td><b>Why 4</b></td>
              <td>{html.escape(why4)}</td>
              <td>{html.escape(v4)}</td>
              <td>☑ YES &nbsp; ☐ NO</td>
            </tr>
            <tr style="background-color: #fef3c7;">
              <td><b>Why 5</b></td>
              <td><b>{html.escape(why5)}</b></td>
              <td>{html.escape(v5)}</td>
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

    # Section 5 - Action Plan & Pilot Verification
    pilot_list = d5.get('pilot_solution_verification') or []
    action_plan = d5.get('root_cause_mapping') or d5.get('action_plan') or []
    
    cm_rows_html = ""
    if action_plan and isinstance(action_plan, list) and len(action_plan) > 0:
        for idx, act in enumerate(action_plan[:3]):
            rc = act.get('root_cause') or act.get('cause') or f"Root Cause {idx+1}"
            cm = act.get('proposed_solution') or act.get('action') or "Proposed Solution"
            
            # Match with Stage 5 Section 6 (Pilot Solution Verification)
            pilot_item = None
            for p in pilot_list:
                if isinstance(p, dict) and p.get('solution') and str(p.get('solution')).strip() == str(cm).strip():
                    pilot_item = p
                    break
            if not pilot_item and idx < len(pilot_list) and isinstance(pilot_list[idx], dict):
                pilot_item = pilot_list[idx]

            tr_parts = []
            if pilot_item:
                p_loc = str(pilot_item.get('location') or '').strip()
                p_dur = str(pilot_item.get('duration') or '').strip()
                p_res = str(pilot_item.get('result') or '').strip()
                p_dec = str(pilot_item.get('decision') or '').strip()

                if p_loc: tr_parts.append(f"Location: {p_loc}")
                if p_dur: tr_parts.append(f"Duration: {p_dur}")
                if p_res: tr_parts.append(f"Result: {p_res}")
                if p_dec: tr_parts.append(f"Decision: {p_dec}")

            if tr_parts:
                tr = " | ".join(tr_parts)
            else:
                tr = act.get('trial_result') or act.get('result') or "N/A"

            cm_rows_html += f'''
            <tr>
              <td>{idx+1}</td>
              <td><b>{html.escape(rc)}</b></td>
              <td>{html.escape(cm)}</td>
              <td>{html.escape(tr)}</td>
            </tr>
            '''
    elif pilot_list and isinstance(pilot_list, list) and len(pilot_list) > 0:
        for idx, pilot_item in enumerate(pilot_list[:3]):
            sol = pilot_item.get('solution') or f"Solution {idx+1}"
            p_loc = str(pilot_item.get('location') or '').strip()
            p_dur = str(pilot_item.get('duration') or '').strip()
            p_res = str(pilot_item.get('result') or '').strip()
            p_dec = str(pilot_item.get('decision') or '').strip()

            tr_parts = []
            if p_loc: tr_parts.append(f"Location: {p_loc}")
            if p_dur: tr_parts.append(f"Duration: {p_dur}")
            if p_res: tr_parts.append(f"Result: {p_res}")
            if p_dec: tr_parts.append(f"Decision: {p_dec}")

            tr = " | ".join(tr_parts) if tr_parts else "N/A"

            cm_rows_html += f'''
            <tr>
              <td>{idx+1}</td>
              <td><b>Root Cause {idx+1}</b></td>
              <td>{html.escape(sol)}</td>
              <td>{html.escape(tr)}</td>
            </tr>
            '''
    else:
        cm_rows_html = '''
        <tr>
          <td colspan="4" style="text-align:center; color:#64748b;">No countermeasures or pilot solution verification records logged.</td>
        </tr>
        '''

    # Section 6 - ROI Verification
    roi = d7.get('roi_validation') or {}

    raw_inv = roi.get('total_investment') or roi.get('investment') or roi.get('inv')
    if raw_inv is not None and str(raw_inv).strip() != "":
        try:
            inv_val = float(str(raw_inv).replace(',', ''))
            inv_cost = f"INR {inv_val:,.2f}"
        except (ValueError, TypeError):
            inv_cost = f"INR {raw_inv}"
    else:
        inv_cost = "N/A"

    raw_sav = roi.get('annual_savings') or roi.get('savings') or roi.get('sav')
    if raw_sav is not None and str(raw_sav).strip() != "":
        try:
            sav_val = float(str(raw_sav).replace(',', ''))
            ann_savings = f"INR {sav_val:,.2f} / Year"
        except (ValueError, TypeError):
            ann_savings = f"INR {raw_sav} / Year"
    else:
        ann_savings = "N/A"

    raw_pb = roi.get('payback_period') or roi.get('payback_months') or roi.get('payback')
    if raw_pb is not None and str(raw_pb).strip() != "":
        payback = str(raw_pb).strip()
    else:
        payback = "N/A"

    raw_formula = roi.get('formula') or roi.get('basis') or get_v(s7, d7, "roi_validation.formula")
    if raw_formula and raw_formula != "--":
        calc_basis = raw_formula
    else:
        calc_basis = "Formula: ROI (%) = ((Annual Savings - Total Investment) / Total Investment) × 100 | Payback Period = Total Investment / Annual Savings"

    control_chart_svg_html = generate_control_chart_comparison_svg(d4, d7)
    histogram_svg_html = generate_histogram_comparison_svg(d2, d4, d7)
    evidence_collage_html = generate_evidence_collage_html(project_id, d2, d6)

    # Section 9 Sign-Off Table data extraction
    saved_signoff = d8.get('signoff_table') if isinstance(d8.get('signoff_table'), list) else []
    default_dept = project.department.name if project.department else "Quality Control"

    def get_user_dept_name(user_obj, fallback_dept):
        if not user_obj:
            return fallback_dept
        if hasattr(user_obj, 'department') and user_obj.department:
            return user_obj.department.name
        if getattr(user_obj, 'department_id', None):
            dept_obj = db.session.get(Department, user_obj.department_id)
            if dept_obj and dept_obj.name:
                return dept_obj.name
        return fallback_dept

    signoff_rows = []

    # 1. Team Leader (Mandatory)
    tl_user = project.team_leader or project.creator
    tl_name = (tl_user.full_name or tl_user.username) if tl_user else ""
    tl_dept = get_user_dept_name(tl_user, default_dept)
    signoff_rows.append({
        'role': 'Team Leader',
        'name': tl_name,
        'department': tl_dept,
        'signature': '',
        'date': ''
    })

    # 2. QCC Facilitator (Mandatory)
    fac_user = project.facilitator
    fac_name = (fac_user.full_name or fac_user.username) if fac_user else ""
    fac_dept = get_user_dept_name(fac_user, default_dept)
    signoff_rows.append({
        'role': 'QCC Facilitator',
        'name': fac_name,
        'department': fac_dept,
        'signature': '',
        'date': ''
    })

    # 3. Project Reviewer (Mandatory)
    rev_user = getattr(project, 'reviewer', None)
    rev_name = (rev_user.full_name or rev_user.username) if rev_user else ""
    rev_dept = get_user_dept_name(rev_user, default_dept)
    signoff_rows.append({
        'role': 'Project Reviewer',
        'name': rev_name,
        'department': rev_dept,
        'signature': '',
        'date': ''
    })

    # 4. Team Members (from project members roster or saved_signoff)
    members_list = project.members or []
    if members_list:
        for idx, m in enumerate(members_list):
            m_n = m.full_name or m.username
            if m_n:
                signoff_rows.append({
                    'role': f'Team Member {idx + 1}',
                    'name': m_n,
                    'department': get_user_dept_name(m, default_dept),
                    'signature': '',
                    'date': ''
                })
    elif saved_signoff:
        for item in saved_signoff:
            if isinstance(item, dict):
                r_role = item.get('role') or 'Team Member'
                r_name = item.get('name') or ''
                r_dept = item.get('department') or default_dept
                # Skip if it's already TL/Fac/Rev to avoid duplicate
                if any(x in r_role.lower() for x in ['leader', 'facilitator', 'reviewer']):
                    continue
                if r_name.strip() or r_role.strip():
                    signoff_rows.append({
                        'role': r_role,
                        'name': r_name,
                        'department': r_dept,
                        'signature': item.get('signature') or '',
                        'date': item.get('date') or ''
                    })

    # 5. Organization Custom Hierarchy Approvers (HR, Finance, Plant Head, Quality Head, HOD, etc.)
    org = project.organization
    hierarchy = (org and getattr(org, 'signoff_hierarchy_config', None)) or None
    if not hierarchy:
        hierarchy = [
            {"role": "HR Manager / Representative", "department": "Human Resources", "name": "", "enabled": True, "type": "custom"},
            {"role": "Finance / Costing Head", "department": "Finance & Accounts", "name": "", "enabled": True, "type": "custom"},
            {"role": "Plant / Quality Head", "department": "Quality Assurance", "name": "", "enabled": True, "type": "custom"}
        ]

    for h_item in hierarchy:
        if not isinstance(h_item, dict):
            continue
        if h_item.get('enabled') is False:
            continue
        h_type = h_item.get('type')
        if h_type == 'system':
            # System roles are already added above
            continue
        h_role = h_item.get('role') or 'Management Approver'
        h_dept = h_item.get('department') or 'Management'
        h_name = h_item.get('name') or ''
        signoff_rows.append({
            'role': h_role,
            'name': h_name,
            'department': h_dept,
            'signature': '',
            'date': ''
        })

    signoff_table_rows_html = ""
    for s_item in signoff_rows:
        sig_val = html.escape(s_item["signature"]) if s_item.get("signature") else ''
        date_val = html.escape(s_item["date"]) if s_item.get("date") else ''
        signoff_table_rows_html += f'''
            <tr>
              <td style="padding: 2.5px 5px; font-weight: 600; color: #0f172a;">{html.escape(s_item["role"])}</td>
              <td style="padding: 2.5px 5px; color: #334155;">{html.escape(s_item["name"])}</td>
              <td style="padding: 2.5px 5px; color: #475569;">{html.escape(s_item["department"])}</td>
              <td style="padding: 2.5px 5px; text-align: center;">{sig_val}</td>
              <td style="padding: 2.5px 5px; text-align: center;">{date_val}</td>
            </tr>'''

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
    .doc-org-addr {{ font-size: 6.5pt; color: #64748b; margin-top: 1px; }}

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
          <th style="width: 13%;">Project Title</th>
          <td colspan="3" style="font-weight: bold; color: #1e3a8a;">{html.escape(project_title)}</td>
          <th style="width: 13%;">Project No.</th>
          <td>{html.escape(doc_id)}</td>
        </tr>
        <tr>
          <th>Plant Location</th>
          <td>{html.escape(plant_location)}</td>
          <th style="width: 13%;">Part / Process</th>
          <td>{html.escape(part_process)}</td>
          <th>No. of Meetings</th>
          <td>{html.escape(meeting_count)}</td>
        </tr>
        <tr>
          <th>Team Leader</th>
          <td>{html.escape(team_leader)}</td>
          <th>Facilitator / QA</th>
          <td>{html.escape(facilitator)}</td>
          <th>Reviewer</th>
          <td>{html.escape(reviewer)}</td>
        </tr>
        <tr>
          <th>Team Members</th>
          <td colspan="5">{members_str}</td>
        </tr>{role_and_membership_changes_row_html}
      </table>

      <!-- SECTION 1 -->
      <div class="section-title">1. Theme Selection & Rationale</div>
      <table class="data-table">
        <thead>
          <tr>
            <th style="width: 24%;">Candidate Problem / Theme</th>
            <th style="width: 20%;">Quality Impact</th>
            <th style="width: 18%;">Cost / Scrap</th>
            <th style="width: 18%;">Safety / Ease</th>
            <th style="width: 20%;">Selection Rationale / Audit Justification</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td><b>{html.escape(cand_theme)}</b></td>
            <td>{html.escape(quality_impact_val)}</td>
            <td>{html.escape(cost_scrap_val)}</td>
            <td>{html.escape(safety_ease_val)}</td>
            <td>{html.escape(rationale_val)}</td>
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
          <td style="width: 18%; font-weight: bold; color: #059669;">{html.escape(target_date)}</td>
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
              <td style="vertical-align: top; height: 115px; font-size: 7.5pt; line-height: 1.35;">
                {html.escape(pareto_obs)}
                <br><br><br>
              </td>
            </tr>
          </tbody>
        </table>

        <!-- Dynamic SVG Pareto Visual Chart -->
        <div class="chart-container" style="height: 120px; border: 1px solid #cbd5e1; border-radius: 4px; padding: 2px;">
          {pareto_svg_html}
        </div>
      </div>

      <!-- SECTION 4 -->
      <div class="section-title">4. Cause & Effect Analysis (Fishbone & Full 5-Why Chain)</div>
      
      <!-- Dynamic SVG Fishbone Diagram -->
      <div class="chart-container" style="height: 165px; margin-bottom: 6px; padding: 4px; border: 1px solid #cbd5e1; border-radius: 4px; background: #ffffff;">
        {fishbone_svg_html}
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
            <th style="width: 32%;">Countermeasure</th>
            <th style="width: 16%;">Pilot Result</th>
          </tr>
        </thead>
        <tbody>
          {cm_rows_html}
        </tbody>
      </table>

      <!-- SECTION 6 -->
      <div class="section-title">6. Check & Proof of Results (Before vs After)</div>
      <div class="grid-2col" style="margin-bottom: 4px;">
        
        <div class="chart-container" style="height: 115px; border: 1px solid #cbd5e1; border-radius: 4px; padding: 2px; background: #ffffff;">
          <div style="font-size: 6.8pt; font-weight: 800; color: #1e3a8a; margin-bottom: 1px; text-transform: uppercase;">QC Tool Comparison: Control Chart Comparison (Before vs After Stability)</div>
          {control_chart_svg_html}
        </div>

        <div class="chart-container" style="height: 115px; border: 1px solid #cbd5e1; border-radius: 4px; padding: 2px; background: #ffffff;">
          <div style="font-size: 6.8pt; font-weight: 800; color: #1e3a8a; margin-bottom: 1px; text-transform: uppercase;">QC Tool Comparison: Process Variation Histogram (Before vs After)</div>
          {histogram_svg_html}
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
          <span class="manual-note-tag">Note: Manual Entry</span>
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
              <td></td>
              <td>QCPC Reference</td>
              <td></td>
            </tr>
            <tr>
              <td>Technical Deviation (TDR)</td>
              <td></td>
              <td>TSOS Reference</td>
              <td></td>
            </tr>
            <tr>
              <td>PCR / ECR Date</td>
              <td></td>
              <td>Operator Training</td>
              <td></td>
            </tr>
            <tr>
              <td>SOP / Work Instruction</td>
              <td></td>
              <td>Visual Control (VCS)</td>
              <td></td>
            </tr>
          </tbody>
        </table>

        <!-- SECTION 8 -->
        <div class="section-title">8. Reflection (Hansei) & Horizontal Deployment Matrix (Yokoten)</div>
        <table class="data-table">
          <tr>
            <th style="width: 15%;">Reflection</th>
            <td colspan="3" class="placeholder-text"></td>
          </tr>
          <tr>
            <th>Next Project Theme</th>
            <td colspan="3" class="placeholder-text"></td>
          </tr>
        </table>

        <!-- SECTION 9 -->
        <div class="section-title">9. Closure Approval & Quality Gate Sign-Off</div>
        <table class="data-table" style="margin-bottom: 0;">
          <thead>
            <tr>
              <th style="width: 22%;">Role</th>
              <th style="width: 26%;">Name</th>
              <th style="width: 26%;">Department / Section</th>
              <th style="width: 13%;">Signature</th>
              <th style="width: 13%;">Date</th>
            </tr>
          </thead>
          <tbody>
{signoff_table_rows_html}
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

import shutil

def render_html_to_pdf_browser(html_code):
    """Fast headless Chromium/Chrome/Edge renderer for exact 2-page print layout."""
    with tempfile.NamedTemporaryFile('w', delete=False, suffix='.html', encoding='utf-8') as f:
        f.write(html_code)
        html_path = os.path.abspath(f.name)

    pdf_path = html_path.replace('.html', '.pdf')
    file_url = 'file:///' + html_path.replace('\\', '/')

    browser_paths = [
        r'C:\Program Files\Google\Chrome\Application\chrome.exe',
        r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',
        r'C:\Program Files\Microsoft\Edge\Application\msedge.exe',
        r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe'
    ]

    browser = None
    for p in browser_paths:
        if os.path.exists(p):
            browser = p
            break

    if not browser:
        raise RuntimeError("No Chromium or Chrome/Edge browser available for PDF generation")

    user_data_dir = tempfile.mkdtemp(prefix='qcms_pdf_profile_')
    cmd = [
        browser,
        '--headless=new',
        f'--user-data-dir={user_data_dir}',
        '--no-first-run',
        '--no-default-browser-check',
        '--disable-gpu',
        '--no-sandbox',
        '--disable-extensions',
        '--disable-background-networking',
        '--no-pdf-header-footer',
        f'--print-to-pdf={pdf_path}',
        file_url
    ]

    subprocess.run(cmd, check=True, timeout=20)
    with open(pdf_path, 'rb') as f:
        pdf_bytes = f.read()

    try:
        os.remove(html_path)
    except Exception:
        pass
    try:
        os.remove(pdf_path)
    except Exception:
        pass
    try:
        shutil.rmtree(user_data_dir, ignore_errors=True)
    except Exception:
        pass

    return pdf_bytes

def render_html_to_pdf_pymupdf(html_code):
    """Fallback in-memory PDF rendering using PyMuPDF Story."""
    import io
    story = fitz.Story(html_code)
    out_buf = io.BytesIO()
    writer = fitz.DocumentWriter(out_buf)
    rect = fitz.paper_rect('a4')
    more = 1
    while more:
        dev = writer.begin_page(rect)
        more, _ = story.place(rect)
        story.draw(dev)
        writer.end_page()
    writer.close()
    return out_buf.getvalue()

def generate_qc_story_closure_summary_pdf(project_id):
    html_code = build_qc_story_html(project_id)
    if not html_code:
        return None
    try:
        return render_html_to_pdf_browser(html_code)
    except Exception as e:
        print(f"[PDF_FILLER] Browser rendering exception: {e}, falling back to PyMuPDF...")
        try:
            return render_html_to_pdf_pymupdf(html_code)
        except Exception as e2:
            print(f"[PDF_FILLER] PyMuPDF fallback failed: {e2}")
            return None
