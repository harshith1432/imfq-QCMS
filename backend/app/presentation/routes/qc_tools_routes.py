"""
Module 4: Digital QC Tools & Visualization Routes
POST/GET /api/project/<id>/stage3/<tool>
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.infrastructure.database.models.models import (
    User, Project, ProjectMember, ProjectWorkflow, ProjectStageTracker,
    QCCheckSheet, QCCheckSheetRow, QCCheckSheetEntry,
    QCParetoChart, QCParetoItem,
    QCStratification, QCStratificationItem,
    QCProcessMap, QCProcessStep,
    QCFishboneDiagram, QCFishboneBranch,
    QCScatterDiagram, QCScatterPoint,
    QCControlChart, QCControlPoint, 
    Stage1ProblemDefinitionProjectInitiation,
    Stage2ObservationDataCollection,
    Stage3CauseIdentification,
    Stage4RootCauseAnalysisVerification,
    db
)
from functools import wraps
import math
from datetime import datetime, timezone

qc_tools_bp = Blueprint('qc_tools', __name__)

def project_member_required(f):
    @wraps(f)
    @jwt_required()
    def decorated(*args, **kwargs):
        user_id = get_jwt_identity()
        project_id = kwargs.get('project_id')
        project = db.session.get(Project, project_id)
        
        user = db.session.get(User, user_id)
        if not user:
            return jsonify({"msg": "User not found"}), 404
            
        # For writing/editing (non-GET) QC tools data (which is Stage 3, and thus part of Stage 2-8):
        # Enforce that only Team Members can edit/add.
        if request.method != 'GET':
            if user.role.name != 'Team Member':
                return jsonify({"msg": "Access denied. Only Team Members can add/edit Stage 3 details."}), 403

        is_member = ProjectMember.query.filter_by(project_id=project_id, user_id=user_id).first()
        if is_member or (project and (str(project.creator_id) == str(user_id) or str(project.team_leader_id) == str(user_id))):
            return f(*args, **kwargs)
            
        # Bypass for GET requests by Admin, CEO, Reviewer of the same organization (or SuperAdmin)
        if request.method == 'GET':
            if user.role.name == 'SuperAdmin':
                return f(*args, **kwargs)
            if user.role.name in ['Admin', 'Reviewer', 'CEO'] and project and project.org_id == user.org_id:
                return f(*args, **kwargs)
                    
        return jsonify({"msg": "Access denied: not a project member"}), 403
    return decorated

def get_or_create_workflow_data(project_id, stage_id, org_id):
    wf = ProjectWorkflow.query.filter_by(project_id=project_id, stage_id=stage_id).first()
    if not wf:
        wf = ProjectWorkflow(project_id=project_id, stage_id=stage_id, org_id=org_id, data={})
        db.session.add(wf)
        db.session.flush()
    return wf

# ============================
# PARETO CHART
# ============================
@qc_tools_bp.route('/<int:project_id>/stage3/pareto', methods=['POST'])
@project_member_required
def save_pareto(project_id):
    data = request.json.get('data', [])
    if not isinstance(data, list) or len(data) == 0:
        return jsonify({"msg": "Data must be an array of {cause, freq}"}), 400
    
    project = Project.query.get_or_404(project_id)
    stage_id = project.current_stage
    
    # Sort descending by frequency
    data.sort(key=lambda x: x.get('freq', 0), reverse=True)
    total = sum(d.get('freq', 0) for d in data)
    
    if total == 0:
        return jsonify({"msg": "Total frequency cannot be zero"}), 400
    
    # Calculate cumulative %
    running = 0
    for d in data:
        running += d.get('freq', 0)
        d['cumulative_pct'] = round((running / total) * 100, 1)
        
    # Upsert QCParetoChart
    chart = QCParetoChart.query.filter_by(project_id=project_id, stage_id=stage_id).first()
    if not chart:
        chart = QCParetoChart(
            project_id=project_id,
            org_id=project.org_id,
            stage_id=stage_id,
            title="Pareto Chart",
            description="QC Tools Pareto Chart",
            total_count=total
        )
        db.session.add(chart)
        db.session.flush()
    else:
        chart.total_count = total
        # Delete old items
        QCParetoItem.query.filter_by(pareto_chart_id=chart.id).delete()
        
    for i, d in enumerate(data):
        item = QCParetoItem(
            pareto_chart_id=chart.id,
            cause_name=d.get('cause') or d.get('cause_name') or f"Cause {i+1}",
            frequency=d.get('freq', 0),
            cumulative_pct=d.get('cumulative_pct', 0.0),
            priority_rank=i+1
        )
        db.session.add(item)
        
    db.session.commit()
    return jsonify({"msg": "Pareto data saved", "processed": data})

@qc_tools_bp.route('/<int:project_id>/stage3/pareto', methods=['GET'])
@project_member_required
def get_pareto(project_id):
    project = Project.query.get_or_404(project_id)
    
    # Try Stage 2 Check Sheet first
    s2 = Stage2ObservationDataCollection.query.filter_by(project_id=project_id).first()
    if s2 and s2.data_collection and isinstance(s2.data_collection, dict) and 'check_sheet' in s2.data_collection:
        check_sheet = s2.data_collection['check_sheet']
        if check_sheet:
            sorted_items = sorted(check_sheet, key=lambda x: int(x.get('count', 0)), reverse=True)
            total = sum(int(item.get('count', 0)) for item in sorted_items)
            result = []
            if total > 0:
                running = 0
                for item in sorted_items:
                    count = int(item.get('count', 0))
                    running += count
                    pct = round((running / total) * 100, 1)
                    result.append({
                        "cause": item.get('category') or item.get('defect') or "Unknown",
                        "freq": count,
                        "cumulative_pct": pct
                    })
                return jsonify({"data": result})

    # Fallback to legacy Pareto chart
    chart = QCParetoChart.query.filter_by(project_id=project_id, stage_id=project.current_stage).first()
    if not chart:
        chart = QCParetoChart.query.filter_by(project_id=project_id).order_by(QCParetoChart.created_at.desc()).first()
        
    if not chart:
        return jsonify({"data": []})
        
    items = QCParetoItem.query.filter_by(pareto_chart_id=chart.id).order_by(QCParetoItem.priority_rank).all()
    result = [{"cause": item.cause_name, "freq": item.frequency, "cumulative_pct": item.cumulative_pct} for item in items]
    return jsonify({"data": result})

# ============================
# FISHBONE DIAGRAM
# ============================
@qc_tools_bp.route('/<int:project_id>/stage3/fishbone', methods=['POST'])
@project_member_required
def save_fishbone(project_id):
    data = request.json.get('data', {})
    categories = ['Man', 'Machine', 'Material', 'Method', 'Measurement', 'Environment']
    
    project = Project.query.get_or_404(project_id)
    stage_id = project.current_stage
    effect = data.get('effect') or "Defect Occurrence"
    
    # Upsert Fishbone Diagram
    diag = QCFishboneDiagram.query.filter_by(project_id=project_id).first()
    if not diag:
        diag = QCFishboneDiagram(
            project_id=project_id,
            org_id=project.org_id,
            stage_id=stage_id,
            effect=effect
        )
        db.session.add(diag)
        db.session.flush()
    else:
        diag.effect = effect
        # Delete existing branches
        QCFishboneBranch.query.filter_by(fishbone_id=diag.id).delete()
        
    structured = {}
    for cat in categories:
        causes = data.get(cat) or data.get(cat.lower()) or []
        structured[cat] = causes
        for text in causes:
            if text:
                branch = QCFishboneBranch(
                    fishbone_id=diag.id,
                    category=cat,
                    text=text
                )
                db.session.add(branch)
                
    structured['effect'] = effect
    
    # Sync with Stage3CauseIdentification.fishbone_level_1
    s3 = Stage3CauseIdentification.query.filter_by(project_id=project_id).first()
    if not s3:
        s3 = Stage3CauseIdentification(project_id=project_id, org_id=project.org_id)
        db.session.add(s3)
    s3.fishbone_level_1 = structured
    
    db.session.commit()
    return jsonify({"msg": "Fishbone data saved", "processed": structured})

@qc_tools_bp.route('/<int:project_id>/stage3/fishbone', methods=['GET'])
@project_member_required
def get_fishbone(project_id):
    project = Project.query.get_or_404(project_id)
    
    # Try Stage 3 Cause Identification model (fishbone_l2) first
    s3 = Stage3CauseIdentification.query.filter_by(project_id=project_id).first()
    if s3 and s3.fishbone_l2 and isinstance(s3.fishbone_l2, list):
        categories = ['Man', 'Machine', 'Material', 'Method', 'Measurement', 'Environment']
        data = {cat: [] for cat in categories}
        
        # Get effect from Stage 1
        effect = "Defect Occurrence"
        s1 = Stage1ProblemDefinitionProjectInitiation.query.filter_by(project_id=project_id).first()
        if s1:
            if s1.theme_target_schedule and isinstance(s1.theme_target_schedule, dict):
                effect = s1.theme_target_schedule.get("improvement_theme") or effect
            elif s1.problem_5w2h and isinstance(s1.problem_5w2h, dict):
                effect = s1.problem_5w2h.get("what") or effect
        if not effect or effect == "Defect Occurrence":
            effect = project.title or "Defect Occurrence"
            
        data['effect'] = effect
        
        for item in s3.fishbone_l2:
            cat = item.get("category", "")
            cat_key = cat.title()
            if cat_key in data:
                lvl1 = item.get("level1", "")
                lvl2 = item.get("level2", "")
                text = lvl1 + (f" ({lvl2})" if lvl2 else "")
                if text:
                    data[cat_key].append(text)
        return jsonify({"data": data})

    if s3 and s3.fishbone_level_1:
        return jsonify({"data": s3.fishbone_level_1})

    # Fallback to old model
    diag = QCFishboneDiagram.query.filter_by(project_id=project_id).first()
    if not diag:
        return jsonify({"data": {}})
        
    branches = QCFishboneBranch.query.filter_by(fishbone_id=diag.id).all()
    categories = ['Man', 'Machine', 'Material', 'Method', 'Measurement', 'Environment']
    data = {cat: [] for cat in categories}
    data['effect'] = diag.effect
    
    for b in branches:
        if b.category in data:
            data[b.category].append(b.text)
            
    return jsonify({"data": data})

# ============================
# HISTOGRAM (Stored in ProjectWorkflow JSON)
# ============================
@qc_tools_bp.route('/<int:project_id>/stage3/histogram', methods=['POST'])
@project_member_required
def save_histogram(project_id):
    values = request.json.get('values', [])
    num_bins = request.json.get('bins', 8)
    
    if not values or len(values) < 2:
        return jsonify({"msg": "At least 2 data points required"}), 400
    
    values = [float(v) for v in values]
    n = len(values)
    mean = sum(values) / n
    variance = sum((x - mean) ** 2 for x in values) / n
    std_dev = math.sqrt(variance) if variance > 0 else 0
    
    min_val, max_val = min(values), max(values)
    bin_width = (max_val - min_val) / num_bins if num_bins > 0 else 1
    
    bins = []
    for i in range(num_bins):
        low = min_val + i * bin_width
        high = low + bin_width
        count = sum(1 for v in values if low <= v < high or (i == num_bins - 1 and v == high))
        bins.append({"range": f"{round(low,2)}-{round(high,2)}", "count": count})
    
    processed = {
        "bins": bins,
        "mean": round(mean, 2),
        "std_dev": round(std_dev, 2),
        "n": n,
        "raw_values": values
    }
    
    project = Project.query.get_or_404(project_id)
    wf = get_or_create_workflow_data(project_id, project.current_stage, project.org_id)
    
    # Store in JSON data
    wf_data = dict(wf.data or {})
    wf_data['histogram_data'] = processed
    wf.data = wf_data
    
    db.session.commit()
    return jsonify({"msg": "Histogram processed", "processed": processed})

def compute_histogram_data(hist_values_raw, num_bins=8):
    if not hist_values_raw:
        return None
    try:
        if isinstance(hist_values_raw, str):
            vals = [float(v.strip()) for v in hist_values_raw.split(',') if v.strip()]
        elif isinstance(hist_values_raw, list):
            vals = [float(v) for v in hist_values_raw]
        else:
            return None
    except ValueError:
        return None

    if len(vals) < 2:
        return None

    n = len(vals)
    mean = sum(vals) / n
    variance = sum((x - mean) ** 2 for x in vals) / n
    std_dev = math.sqrt(variance) if variance > 0 else 0
    
    min_val, max_val = min(vals), max(vals)
    bin_width = (max_val - min_val) / num_bins if num_bins > 0 else 1
    
    bins = []
    for i in range(num_bins):
        low = min_val + i * bin_width
        high = low + bin_width
        count = sum(1 for v in vals if low <= v < high or (i == num_bins - 1 and v == high))
        bins.append({"range": f"{round(low,2)}-{round(high,2)}", "count": count})
        
    return {
        "bins": bins,
        "mean": round(mean, 2),
        "std_dev": round(std_dev, 2),
        "n": n,
        "raw_values": vals
    }

@qc_tools_bp.route('/<int:project_id>/stage3/histogram', methods=['GET'])
@project_member_required
def get_histogram(project_id):
    project = Project.query.get_or_404(project_id)
    
    # Try Stage 2 Observation model first
    s2 = Stage2ObservationDataCollection.query.filter_by(project_id=project_id).first()
    if s2 and s2.data_collection and isinstance(s2.data_collection, dict):
        hist_values_raw = s2.data_collection.get('histogram_values')
        if hist_values_raw:
            processed = compute_histogram_data(hist_values_raw)
            if processed:
                return jsonify({"data": processed})
                
    # Fallback to old workflow
    wf = ProjectWorkflow.query.filter_by(project_id=project_id, stage_id=project.current_stage).first()
    if not wf or 'histogram_data' not in (wf.data or {}):
        # Fallback to any workflow record containing histogram_data
        wf = ProjectWorkflow.query.filter(
            ProjectWorkflow.project_id == project_id,
            ProjectWorkflow.data.op('->>')('histogram_data').isnot(None)
        ).first()
        
    return jsonify({"data": wf.data.get('histogram_data') if wf and wf.data else {}})

# ============================
# CONTROL CHART
# ============================
# ==============================================================================
# [DEAD CODE - UNUSED BY FRONTEND / REMOVED FEATURE]
# Function: save_control_chart (Lines 385-449)
# Reason: Control chart removed from stage 3 QC tools in frontend.
# ==============================================================================
# @qc_tools_bp.route('/<int:project_id>/stage3/control-chart', methods=['POST'])
# @project_member_required
# def save_control_chart(project_id):
#     values = request.json.get('values', [])

#     if not values or len(values) < 3:
#         return jsonify({"msg": "At least 3 data points required"}), 400

#     values = [float(v) for v in values]
#     n = len(values)
#     mean = sum(values) / n
#     std_dev = math.sqrt(sum((x - mean) ** 2 for x in values) / n) if n > 0 else 0

#     ucl = round(mean + 3 * std_dev, 2)
#     lcl = round(mean - 3 * std_dev, 2)

#     out_of_control = [{"index": i, "value": round(v, 2)} for i, v in enumerate(values) if v > ucl or v < lcl]

#     processed = {
#         "values": [round(v, 2) for v in values],
#         "mean": round(mean, 2),
#         "ucl": ucl,
#         "lcl": lcl,
#         "std_dev": round(std_dev, 2),
#         "out_of_control": out_of_control
#     }

#     project = Project.query.get_or_404(project_id)
#     stage_id = project.current_stage

#     # Upsert Control Chart
#     chart = QCControlChart.query.filter_by(project_id=project_id, stage_id=stage_id).first()
#     if not chart:
#         chart = QCControlChart(
#             project_id=project_id,
#             org_id=project.org_id,
#             stage_id=stage_id,
#             title="Control Chart",
#             chart_type="Xbar-R",
#             mean=mean,
#             ucl=ucl,
#             lcl=lcl,
#             std_dev=std_dev
#         )
#         db.session.add(chart)
#         db.session.flush()
#     else:
#         chart.mean = mean
#         chart.ucl = ucl
#         chart.lcl = lcl
#         chart.std_dev = std_dev
#         # Delete old points
#         QCControlPoint.query.filter_by(control_chart_id=chart.id).delete()

#     for i, v in enumerate(values):
#         point = QCControlPoint(
#             control_chart_id=chart.id,
#             sample_index=i,
#             value=v,
#             is_out_of_control=(v > ucl or v < lcl)
#         )
#         db.session.add(point)

#     db.session.commit()
#     return jsonify({"msg": "Control chart processed", "processed": processed})
# [END DEAD CODE: save_control_chart]


# ==============================================================================
# [DEAD CODE - UNUSED BY FRONTEND / REMOVED FEATURE]
# Function: get_control_chart (Lines 451-506)
# Reason: Control chart getter.
# ==============================================================================
# @qc_tools_bp.route('/<int:project_id>/stage3/control', methods=['GET'])
# @qc_tools_bp.route('/<int:project_id>/stage3/control-chart', methods=['GET'])
# @project_member_required
# def get_control_chart(project_id):
#     project = Project.query.get_or_404(project_id)

#     # Try Stage 4 Root Cause Analysis model (data_reconfirmation) first
#     s4 = Stage4RootCauseAnalysisVerification.query.filter_by(project_id=project_id).first()
#     if s4 and s4.data_reconfirmation and isinstance(s4.data_reconfirmation, dict):
#         control_chart = s4.data_reconfirmation.get('control_chart')
#         if control_chart and isinstance(control_chart, dict):
#             points = control_chart.get('points', [])
#             vals = [float(p.get('val', 0)) for p in points if p.get('val') is not None]
#             if vals:
#                 n = len(vals)
#                 mean = sum(vals) / n
#                 if n > 1:
#                     variance = sum((x - mean) ** 2 for x in vals) / (n - 1)
#                     std_dev = math.sqrt(variance)
#                 else:
#                     std_dev = 0.0
#                 ucl = mean + 3 * std_dev
#                 lcl = max(0.0, mean - 3 * std_dev)
#                 out_of_control = [{"index": i, "value": round(v, 2)} for i, v in enumerate(vals) if v > ucl or v < lcl]

#                 result = {
#                     "values": [round(v, 2) for v in vals],
#                     "mean": round(mean, 2),
#                     "ucl": round(ucl, 2),
#                     "lcl": round(lcl, 2),
#                     "std_dev": round(std_dev, 2),
#                     "out_of_control": out_of_control
#                 }
#                 return jsonify({"data": result})

#     # Fallback to legacy Control Chart
#     chart = QCControlChart.query.filter_by(project_id=project_id, stage_id=project.current_stage).first()
#     if not chart:
#         chart = QCControlChart.query.filter_by(project_id=project_id).order_by(QCControlChart.created_at.desc()).first()

#     if not chart:
#         return jsonify({"data": {}})

#     points = QCControlPoint.query.filter_by(control_chart_id=chart.id).order_by(QCControlPoint.sample_index).all()
#     values = [p.value for p in points]
#     out_of_control = [{"index": p.sample_index, "value": p.value} for p in points if p.is_out_of_control]

#     result = {
#         "values": values,
#         "mean": chart.mean,
#         "ucl": chart.ucl,
#         "lcl": chart.lcl,
#         "std_dev": chart.std_dev,
#         "out_of_control": out_of_control
#     }
#     return jsonify({"data": result})
# [END DEAD CODE: get_control_chart]


# ============================
# SCATTER DIAGRAM
# ============================
@qc_tools_bp.route('/<int:project_id>/stage3/scatter', methods=['POST'])
@project_member_required
def save_scatter(project_id):
    points = request.json.get('points', [])
    
    if len(points) < 3:
        return jsonify({"msg": "At least 3 data points required"}), 400
    
    xs = [p['x'] for p in points]
    ys = [p['y'] for p in points]
    n = len(xs)
    
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    
    numerator = sum((xs[i] - mean_x) * (ys[i] - mean_y) for i in range(n))
    denom_x = math.sqrt(sum((x - mean_x) ** 2 for x in xs))
    denom_y = math.sqrt(sum((y - mean_y) ** 2 for y in ys))
    
    r = round(numerator / (denom_x * denom_y), 4) if denom_x > 0 and denom_y > 0 else 0
    
    # Linear regression: y = mx + b
    ss_xx = sum((x - mean_x) ** 2 for x in xs)
    m = numerator / ss_xx if ss_xx > 0 else 0
    b = mean_y - m * mean_x
    
    strength = "Strong" if abs(r) > 0.7 else "Moderate" if abs(r) > 0.4 else "Weak"
    
    processed = {
        "points": points,
        "correlation_r": r,
        "regression": {"slope": round(m, 4), "intercept": round(b, 4)},
        "strength": strength
    }
    
    project = Project.query.get_or_404(project_id)
    stage_id = project.current_stage
    
    # Upsert Scatter Diagram
    diag = QCScatterDiagram.query.filter_by(project_id=project_id, stage_id=stage_id).first()
    if not diag:
        diag = QCScatterDiagram(
            project_id=project_id,
            org_id=project.org_id,
            stage_id=stage_id,
            x_axis_label="X Axis",
            y_axis_label="Y Axis",
            correlation_coefficient=r,
            correlation_type=strength
        )
        db.session.add(diag)
        db.session.flush()
    else:
        diag.correlation_coefficient = r
        diag.correlation_type = strength
        # Delete old points
        QCScatterPoint.query.filter_by(scatter_diagram_id=diag.id).delete()
        
    for p in points:
        pt = QCScatterPoint(
            scatter_diagram_id=diag.id,
            x_value=p['x'],
            y_value=p['y'],
            remarks=p.get('remarks')
        )
        db.session.add(pt)
        
    db.session.commit()
    return jsonify({"msg": "Scatter analysis complete", "processed": processed})

@qc_tools_bp.route('/<int:project_id>/stage3/scatter', methods=['GET'])
@project_member_required
def get_scatter(project_id):
    project = Project.query.get_or_404(project_id)
    
    # Try Stage 4 Root Cause Analysis model (statistical_validation) first
    s4 = Stage4RootCauseAnalysisVerification.query.filter_by(project_id=project_id).first()
    if s4 and s4.statistical_validation and isinstance(s4.statistical_validation, dict):
        scatter = s4.statistical_validation.get('scatter')
        if scatter and isinstance(scatter, dict):
            pts = scatter.get('points', [])
            formatted_points = [{"x": float(p.get('x', 0)), "y": float(p.get('y', 0))} for p in pts if p.get('x') is not None and p.get('y') is not None]
            if formatted_points:
                xs = [p['x'] for p in formatted_points]
                ys = [p['y'] for p in formatted_points]
                n = len(xs)
                
                r, m, b = 0.0, 0.0, 0.0
                strength = "No Correlation"
                
                if n >= 3:
                    mean_x = sum(xs) / n
                    mean_y = sum(ys) / n
                    
                    numerator = sum((xs[i] - mean_x) * (ys[i] - mean_y) for i in range(n))
                    denom_x = math.sqrt(sum((x - mean_x) ** 2 for x in xs))
                    denom_y = math.sqrt(sum((y - mean_y) ** 2 for y in ys))
                    
                    r = numerator / (denom_x * denom_y) if denom_x > 0 and denom_y > 0 else 0.0
                    
                    ss_xx = sum((x - mean_x) ** 2 for x in xs)
                    m = numerator / ss_xx if ss_xx > 0 else 0.0
                    b = mean_y - m * mean_x
                    
                    abs_r = abs(r)
                    if abs_r >= 0.8:
                        strength = 'Strong Positive' if r > 0 else 'Strong Negative'
                    elif abs_r >= 0.5:
                        strength = 'Moderate Positive' if r > 0 else 'Moderate Negative'
                    elif abs_r >= 0.2:
                        strength = 'Weak Positive' if r > 0 else 'Weak Negative'
                        
                result = {
                    "points": formatted_points,
                    "correlation_r": round(r, 4),
                    "regression": {"slope": round(m, 4), "intercept": round(b, 4)},
                    "strength": strength
                }
                return jsonify({"data": result})

    # Fallback to legacy Scatter Chart
    diag = QCScatterDiagram.query.filter_by(project_id=project_id, stage_id=project.current_stage).first()
    if not diag:
        diag = QCScatterDiagram.query.filter_by(project_id=project_id).order_by(QCScatterDiagram.created_at.desc()).first()
        
    if not diag:
        return jsonify({"data": {}})
        
    pts = QCScatterPoint.query.filter_by(scatter_diagram_id=diag.id).all()
    points = [{"x": p.x_value, "y": p.y_value, "remarks": p.remarks} for p in pts]
    
    # Recalculate slope/intercept for presentation if points exist
    m, b = 0, 0
    if len(points) >= 3:
        xs = [p['x'] for p in points]
        ys = [p['y'] for p in points]
        n = len(xs)
        mean_x = sum(xs) / n
        mean_y = sum(ys) / n
        num = sum((xs[i] - mean_x) * (ys[i] - mean_y) for i in range(n))
        ss_xx = sum((x - mean_x) ** 2 for x in xs)
        m = num / ss_xx if ss_xx > 0 else 0
        b = mean_y - m * mean_x
        
    result = {
        "points": points,
        "correlation_r": diag.correlation_coefficient,
        "regression": {"slope": round(m, 4), "intercept": round(b, 4)},
        "strength": diag.correlation_type
    }
    return jsonify({"data": result})

# ============================
# CHECK SHEET
# ============================
@qc_tools_bp.route('/<int:project_id>/stage3/checksheet', methods=['POST'])
@project_member_required
def save_checksheet(project_id):
    data = request.json.get('data', [])
    project = Project.query.get_or_404(project_id)
    stage_id = project.current_stage
    
    # Upsert QCCheckSheet
    sheet = QCCheckSheet.query.filter_by(project_id=project_id, stage_id=stage_id).first()
    if not sheet:
        sheet = QCCheckSheet(
            project_id=project_id,
            org_id=project.org_id,
            stage_id=stage_id,
            name="Check Sheet",
            description="QC Tools Defect Check Sheet"
        )
        db.session.add(sheet)
        db.session.flush()
    else:
        # Delete old rows (which cascade deletes entries)
        QCCheckSheetRow.query.filter_by(check_sheet_id=sheet.id).delete()
        
    for d in data:
        category = d.get("defect") or d.get("item") or "Unknown"
        count = int(d.get("count") or d.get("tally") or 0)
        
        row = QCCheckSheetRow(
            check_sheet_id=sheet.id,
            category_name=category,
            total_count=count,
            notes=d.get("notes")
        )
        db.session.add(row)
        db.session.flush()
        
        # Insert entry
        entry = QCCheckSheetEntry(
            check_sheet_id=sheet.id,
            row_id=row.id,
            date=datetime.now(timezone.utc).replace(tzinfo=None).date(),
            count=count,
            remarks=d.get("notes")
        )
        db.session.add(entry)
        
    # Auto-populate Pareto data from checksheet tallies
    if isinstance(data, list) and len(data) > 0:
        pareto_auto = [{"cause": d.get("defect", d.get("item", "")), "freq": int(d.get("count", d.get("tally", 0)))} for d in data]
        pareto_auto.sort(key=lambda x: x['freq'], reverse=True)
        total = sum(d['freq'] for d in pareto_auto)
        if total > 0:
            running = 0
            for d in pareto_auto:
                running += d['freq']
                d['cumulative_pct'] = round((running / total) * 100, 1)
                
            # Upsert Pareto Chart
            chart = QCParetoChart.query.filter_by(project_id=project_id, stage_id=stage_id).first()
            if not chart:
                chart = QCParetoChart(
                    project_id=project_id,
                    org_id=project.org_id,
                    stage_id=stage_id,
                    title="Pareto Chart (Auto-Generated)",
                    description="Auto-generated from Check Sheet",
                    total_count=total
                )
                db.session.add(chart)
                db.session.flush()
            else:
                chart.total_count = total
                QCParetoItem.query.filter_by(pareto_chart_id=chart.id).delete()
                
            for idx, p_item in enumerate(pareto_auto):
                item = QCParetoItem(
                    pareto_chart_id=chart.id,
                    cause_name=p_item['cause'],
                    frequency=p_item['freq'],
                    cumulative_pct=p_item['cumulative_pct'],
                    priority_rank=idx+1
                )
                db.session.add(item)
                
    db.session.commit()
    return jsonify({"msg": "Check sheet saved and Pareto auto-populated", "data": data})

@qc_tools_bp.route('/<int:project_id>/stage3/checksheet', methods=['GET'])
@project_member_required
def get_checksheet(project_id):
    project = Project.query.get_or_404(project_id)
    
    # Try Stage 2 Check Sheet first
    s2 = Stage2ObservationDataCollection.query.filter_by(project_id=project_id).first()
    if s2 and s2.data_collection and isinstance(s2.data_collection, dict):
        check_sheet = s2.data_collection.get('check_sheet')
        if check_sheet:
            result = [{
                "defect": item.get('category') or item.get('defect') or "Unknown",
                "count": int(item.get('count', 0)),
                "notes": item.get('notes') or ""
            } for item in check_sheet]
            return jsonify({"data": result})

    # Fallback to legacy check sheet
    sheet = QCCheckSheet.query.filter_by(project_id=project_id, stage_id=project.current_stage).first()
    if not sheet:
        sheet = QCCheckSheet.query.filter_by(project_id=project_id).order_by(QCCheckSheet.created_at.desc()).first()
        
    if not sheet:
        return jsonify({"data": []})
        
    rows = QCCheckSheetRow.query.filter_by(check_sheet_id=sheet.id).all()
    result = [{"defect": r.category_name, "count": r.total_count, "notes": r.notes} for r in rows]
    return jsonify({"data": result})

# ============================
# FLOWCHART (Process Map)
# ============================
# ==============================================================================
# [DEAD CODE - UNUSED BY FRONTEND / REMOVED FEATURE]
# Function: save_flowchart (Lines 785-840)
# Reason: Flowchart QC tool removed from frontend.
# ==============================================================================
# @qc_tools_bp.route('/<int:project_id>/stage3/flowchart', methods=['POST'])
# @project_member_required
# def save_flowchart(project_id):
#     steps = request.json.get('steps', [])
#     project = Project.query.get_or_404(project_id)
#     stage_id = project.current_stage

#     # Convert to Mermaid.js format
#     mermaid_lines = ["graph TD"]
#     for i, step in enumerate(steps):
#         node_id = f"S{i}"
#         label = step.get('label', f'Step {i+1}')
#         step_type = step.get('type', 'process')

#         if step_type == 'decision':
#             mermaid_lines.append(f'    {node_id}{{{{{label}}}}}')
#         elif step_type == 'start' or step_type == 'end':
#             mermaid_lines.append(f'    {node_id}([{label}])')
#         else:
#             mermaid_lines.append(f'    {node_id}[{label}]')

#         if i > 0:
#             connector = step.get('connector', '')
#             mermaid_lines.append(f'    S{i-1} -->|{connector}| {node_id}')

#     processed = {
#         "steps": steps,
#         "mermaid": "\n".join(mermaid_lines)
#     }

#     # Upsert QCProcessMap
#     p_map = QCProcessMap.query.filter_by(project_id=project_id, stage_id=stage_id).first()
#     if not p_map:
#         p_map = QCProcessMap(
#             project_id=project_id,
#             org_id=project.org_id,
#             stage_id=stage_id,
#             title="Process Map"
#         )
#         db.session.add(p_map)
#         db.session.flush()
#     else:
#         QCProcessStep.query.filter_by(process_map_id=p_map.id).delete()

#     for i, step in enumerate(steps):
#         p_step = QCProcessStep(
#             process_map_id=p_map.id,
#             step_order=i,
#             name=step.get('label') or f"Step {i+1}",
#             type=step.get('type', 'process'),
#             description=step.get('connector')
#         )
#         db.session.add(p_step)

#     db.session.commit()
#     return jsonify({"msg": "Flowchart saved", "processed": processed})
# [END DEAD CODE: save_flowchart]


# ==============================================================================
# [DEAD CODE - UNUSED BY FRONTEND / REMOVED FEATURE]
# Function: get_flowchart (Lines 842-877)
# Reason: Flowchart getter.
# ==============================================================================
# @qc_tools_bp.route('/<int:project_id>/stage3/flowchart', methods=['GET'])
# @project_member_required
# def get_flowchart(project_id):
#     project = Project.query.get_or_404(project_id)
#     p_map = QCProcessMap.query.filter_by(project_id=project_id, stage_id=project.current_stage).first()
#     if not p_map:
#         p_map = QCProcessMap.query.filter_by(project_id=project_id).order_by(QCProcessMap.created_at.desc()).first()

#     if not p_map:
#         return jsonify({"data": {}})

#     steps = QCProcessStep.query.filter_by(process_map_id=p_map.id).order_by(QCProcessStep.step_order).all()

#     steps_list = []
#     mermaid_lines = ["graph TD"]
#     for i, s in enumerate(steps):
#         steps_list.append({
#             "label": s.name,
#             "type": s.type,
#             "connector": s.description
#         })
#         node_id = f"S{i}"
#         if s.type == 'decision':
#             mermaid_lines.append(f'    {node_id}{{{{{s.name}}}}}')
#         elif s.type == 'start' or s.type == 'end':
#             mermaid_lines.append(f'    {node_id}([{s.name}])')
#         else:
#             mermaid_lines.append(f'    {node_id}[{s.name}]')
#         if i > 0:
#             mermaid_lines.append(f'    S{i-1} -->|{s.description or ""}| {node_id}')

#     result = {
#         "steps": steps_list,
#         "mermaid": "\n".join(mermaid_lines)
#     }
#     return jsonify({"data": result})
# [END DEAD CODE: get_flowchart]


# ============================
# 5S AUDIT (Radar Chart) - Stored in ProjectWorkflow JSON
# ============================
# ==============================================================================
# [DEAD CODE - UNUSED BY FRONTEND / REMOVED FEATURE]
# Function: save_fives (Lines 882-911)
# Reason: 5S methodology tool removed from frontend.
# ==============================================================================
# @qc_tools_bp.route('/<int:project_id>/stage3/fives', methods=['POST'])
# @project_member_required
# def save_fives(project_id):
#     scores = request.json.get('scores', {})
#     categories = ['sort', 'set_in_order', 'shine', 'standardize', 'sustain']

#     validated = {}
#     for cat in categories:
#         val = float(scores.get(cat, 0))
#         validated[cat] = min(max(val, 0), 5)  # Clamp 0-5

#     avg_score = round(sum(validated.values()) / len(validated), 2)

#     processed = {
#         "scores": validated,
#         "average": avg_score,
#         "labels": ["Sort", "Set in Order", "Shine", "Standardize", "Sustain"],
#         "values": [validated[c] for c in categories]
#     }

#     project = Project.query.get_or_404(project_id)
#     wf = get_or_create_workflow_data(project_id, project.current_stage, project.org_id)

#     # Store in JSON data
#     wf_data = dict(wf.data or {})
#     wf_data['fives_audit_data'] = processed
#     wf.data = wf_data

#     db.session.commit()
#     return jsonify({"msg": "5S audit saved", "processed": processed})
# [END DEAD CODE: save_fives]


# ==============================================================================
# [DEAD CODE - UNUSED BY FRONTEND / REMOVED FEATURE]
# Function: get_fives (Lines 913-924)
# Reason: 5S getter.
# ==============================================================================
# @qc_tools_bp.route('/<int:project_id>/stage3/fives', methods=['GET'])
# @project_member_required
# def get_fives(project_id):
#     project = Project.query.get_or_404(project_id)
#     wf = ProjectWorkflow.query.filter_by(project_id=project_id, stage_id=project.current_stage).first()
#     if not wf or 'fives_audit_data' not in (wf.data or {}):
#         wf = ProjectWorkflow.query.filter(
#             ProjectWorkflow.project_id == project_id,
#             ProjectWorkflow.data.op('->>')('fives_audit_data').isnot(None)
#         ).first()

#     return jsonify({"data": wf.data.get('fives_audit_data') if wf and wf.data else {}})
# [END DEAD CODE: get_fives]


# ============================
# POKA-YOKE LOG - Stored in ProjectWorkflow JSON
# ============================
# ==============================================================================
# [DEAD CODE - UNUSED BY FRONTEND / REMOVED FEATURE]
# Function: save_pokayoke (Lines 929-947)
# Reason: Poka-Yoke error-proofing tool removed from frontend.
# ==============================================================================
# @qc_tools_bp.route('/<int:project_id>/stage3/pokayoke', methods=['POST'])
# @project_member_required
# def save_pokayoke(project_id):
#     entries = request.json.get('entries', [])

#     for entry in entries:
#         effectiveness = entry.get('effectiveness', 1)
#         entry['effectiveness'] = min(max(int(effectiveness), 1), 5)

#     project = Project.query.get_or_404(project_id)
#     wf = get_or_create_workflow_data(project_id, project.current_stage, project.org_id)

#     # Store in JSON data
#     wf_data = dict(wf.data or {})
#     wf_data['pokayoke_data'] = entries
#     wf.data = wf_data

#     db.session.commit()
#     return jsonify({"msg": "Poka-Yoke log saved", "entries": entries})
# [END DEAD CODE: save_pokayoke]


# ==============================================================================
# [DEAD CODE - UNUSED BY FRONTEND / REMOVED FEATURE]
# Function: get_pokayoke (Lines 949-960)
# Reason: Poka-Yoke getter.
# ==============================================================================
# @qc_tools_bp.route('/<int:project_id>/stage3/pokayoke', methods=['GET'])
# @project_member_required
# def get_pokayoke(project_id):
#     project = Project.query.get_or_404(project_id)
#     wf = ProjectWorkflow.query.filter_by(project_id=project_id, stage_id=project.current_stage).first()
#     if not wf or 'pokayoke_data' not in (wf.data or {}):
#         wf = ProjectWorkflow.query.filter(
#             ProjectWorkflow.project_id == project_id,
#             ProjectWorkflow.data.op('->>')('pokayoke_data').isnot(None)
#         ).first()

#     return jsonify({"data": wf.data.get('pokayoke_data') if wf and wf.data else []})
# [END DEAD CODE: get_pokayoke]


# ============================
# STRATIFICATION
# ============================
@qc_tools_bp.route('/<int:project_id>/stage3/stratification', methods=['POST'])
@project_member_required
def save_stratification(project_id):
    data = request.json.get('data', [])
    category_type = request.json.get('category_type', 'Shift')  # e.g., Shift, Machine, Material, Operator
    title = request.json.get('title', 'Stratification Diagram')
    description = request.json.get('description', '')
    
    if not isinstance(data, list) or len(data) == 0:
        return jsonify({"msg": "Data must be an array of {factor, count}"}), 400
        
    project = Project.query.get_or_404(project_id)
    stage_id = project.current_stage
    
    total = sum(int(d.get('count', 0)) for d in data)
    
    # Upsert QCStratification
    strat = QCStratification.query.filter_by(project_id=project_id, stage_id=stage_id).first()
    if not strat:
        strat = QCStratification(
            project_id=project_id,
            org_id=project.org_id,
            stage_id=stage_id,
            title=title,
            description=description,
            category_type=category_type
        )
        db.session.add(strat)
        db.session.flush()
    else:
        strat.title = title
        strat.description = description
        strat.category_type = category_type
        # Delete old items
        QCStratificationItem.query.filter_by(stratification_id=strat.id).delete()
        
    for d in data:
        count = int(d.get('count', 0))
        pct = round((count / total) * 100, 1) if total > 0 else 0.0
        item = QCStratificationItem(
            stratification_id=strat.id,
            factor_name=d.get('factor') or d.get('factor_name') or "Unknown",
            defect_count=count,
            percentage=pct
        )
        db.session.add(item)
        
    db.session.commit()
    return jsonify({"msg": "Stratification data saved", "processed": data})

@qc_tools_bp.route('/<int:project_id>/stage3/stratification', methods=['GET'])
@project_member_required
def get_stratification(project_id):
    project = Project.query.get_or_404(project_id)
    
    # Try Stage 2 Observation model first
    s2 = Stage2ObservationDataCollection.query.filter_by(project_id=project_id).first()
    if s2 and s2.stratification and isinstance(s2.stratification, list) and len(s2.stratification) > 0:
        first_type_full = s2.stratification[0].get("type", "By Shift")
        first_type = first_type_full.replace("By ", "").strip()
        type_items = []
        for item in s2.stratification:
            if item.get("type") == first_type_full:
                type_items.append({
                    "factor": item.get("category", "Unknown"),
                    "count": float(item.get("value", 0))
                })
        total = sum(x["count"] for x in type_items)
        for x in type_items:
            x["percentage"] = round((x["count"] / total) * 100, 1) if total > 0 else 0.0
            
        return jsonify({
            "data": type_items,
            "category_type": first_type,
            "title": f"Stratification by {first_type}",
            "description": f"Breakdown of observations grouped by {first_type}."
        })

    # Fallback to legacy stratification
    strat = QCStratification.query.filter_by(project_id=project_id, stage_id=project.current_stage).first()
    if not strat:
        strat = QCStratification.query.filter_by(project_id=project_id).order_by(QCStratification.created_at.desc()).first()
        
    if not strat:
        return jsonify({"data": [], "category_type": "Shift", "title": "Stratification Diagram", "description": ""})
        
    items = QCStratificationItem.query.filter_by(stratification_id=strat.id).all()
    result = [{"factor": item.factor_name, "count": item.defect_count, "percentage": item.percentage} for item in items]
    return jsonify({
        "data": result,
        "category_type": strat.category_type,
        "title": strat.title,
        "description": strat.description
    })
