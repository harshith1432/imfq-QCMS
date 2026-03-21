"""
Module 4: Digital QC Tools & Visualization Routes
POST/GET /api/project/<id>/stage3/<tool>
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import User, Project, ProjectMember, Stage3RCA, db
from functools import wraps
import math

qc_tools_bp = Blueprint('qc_tools', __name__)

def project_member_required(f):
    @wraps(f)
    @jwt_required()
    def decorated(*args, **kwargs):
        user_id = get_jwt_identity()
        project_id = kwargs.get('project_id')
        is_member = ProjectMember.query.filter_by(project_id=project_id, user_id=user_id).first()
        project = Project.query.get(project_id)
        if not is_member and (not project or str(project.creator_id) != str(user_id)):
            return jsonify({"msg": "Access denied: not a project member"}), 403
        return f(*args, **kwargs)
    return decorated

def get_or_create_rca(project_id):
    rca = Stage3RCA.query.filter_by(project_id=project_id).first()
    if not rca:
        rca = Stage3RCA(project_id=project_id)
        db.session.add(rca)
        db.session.flush()
    return rca

# ============================
# PARETO CHART
# ============================
@qc_tools_bp.route('/<int:project_id>/stage3/pareto', methods=['POST'])
@project_member_required
def save_pareto(project_id):
    data = request.json.get('data', [])
    if not isinstance(data, list) or len(data) == 0:
        return jsonify({"msg": "Data must be an array of {cause, freq}"}), 400
    
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
    
    rca = get_or_create_rca(project_id)
    rca.pareto_data = data
    db.session.commit()
    
    return jsonify({"msg": "Pareto data saved", "processed": data})

@qc_tools_bp.route('/<int:project_id>/stage3/pareto', methods=['GET'])
@project_member_required
def get_pareto(project_id):
    rca = Stage3RCA.query.filter_by(project_id=project_id).first()
    return jsonify({"data": rca.pareto_data if rca else []})

# ============================
# FISHBONE DIAGRAM
# ============================
@qc_tools_bp.route('/<int:project_id>/stage3/fishbone', methods=['POST'])
@project_member_required
def save_fishbone(project_id):
    data = request.json.get('data', {})
    categories = ['Man', 'Machine', 'Material', 'Method', 'Measurement', 'Environment']
    
    structured = {}
    for cat in categories:
        structured[cat] = data.get(cat, [])
    structured['effect'] = data.get('effect', '')
    
    rca = get_or_create_rca(project_id)
    rca.fishbone_data = structured
    db.session.commit()
    
    return jsonify({"msg": "Fishbone data saved", "processed": structured})

@qc_tools_bp.route('/<int:project_id>/stage3/fishbone', methods=['GET'])
@project_member_required
def get_fishbone(project_id):
    rca = Stage3RCA.query.filter_by(project_id=project_id).first()
    return jsonify({"data": rca.fishbone_data if rca else {}})

# ============================
# HISTOGRAM
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
    
    rca = get_or_create_rca(project_id)
    rca.histogram_data = processed
    db.session.commit()
    
    return jsonify({"msg": "Histogram processed", "processed": processed})

@qc_tools_bp.route('/<int:project_id>/stage3/histogram', methods=['GET'])
@project_member_required
def get_histogram(project_id):
    rca = Stage3RCA.query.filter_by(project_id=project_id).first()
    return jsonify({"data": rca.histogram_data if rca else {}})

# ============================
# CONTROL CHART
# ============================
@qc_tools_bp.route('/<int:project_id>/stage3/control-chart', methods=['POST'])
@project_member_required
def save_control_chart(project_id):
    values = request.json.get('values', [])
    
    if not values or len(values) < 3:
        return jsonify({"msg": "At least 3 data points required"}), 400
    
    values = [float(v) for v in values]
    n = len(values)
    mean = sum(values) / n
    std_dev = math.sqrt(sum((x - mean) ** 2 for x in values) / n) if n > 0 else 0
    
    ucl = round(mean + 3 * std_dev, 2)
    lcl = round(mean - 3 * std_dev, 2)
    
    out_of_control = [{"index": i, "value": round(v, 2)} for i, v in enumerate(values) if v > ucl or v < lcl]
    
    processed = {
        "values": [round(v, 2) for v in values],
        "mean": round(mean, 2),
        "ucl": ucl,
        "lcl": lcl,
        "std_dev": round(std_dev, 2),
        "out_of_control": out_of_control
    }
    
    rca = get_or_create_rca(project_id)
    rca.control_chart_data = processed
    db.session.commit()
    
    return jsonify({"msg": "Control chart processed", "processed": processed})

@qc_tools_bp.route('/<int:project_id>/stage3/control-chart', methods=['GET'])
@project_member_required
def get_control_chart(project_id):
    rca = Stage3RCA.query.filter_by(project_id=project_id).first()
    return jsonify({"data": rca.control_chart_data if rca else {}})

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
    
    processed = {
        "points": points,
        "correlation_r": r,
        "regression": {"slope": round(m, 4), "intercept": round(b, 4)},
        "strength": "Strong" if abs(r) > 0.7 else "Moderate" if abs(r) > 0.4 else "Weak"
    }
    
    rca = get_or_create_rca(project_id)
    rca.scatter_data = processed
    db.session.commit()
    
    return jsonify({"msg": "Scatter analysis complete", "processed": processed})

@qc_tools_bp.route('/<int:project_id>/stage3/scatter', methods=['GET'])
@project_member_required
def get_scatter(project_id):
    rca = Stage3RCA.query.filter_by(project_id=project_id).first()
    return jsonify({"data": rca.scatter_data if rca else {}})

# ============================
# CHECK SHEET
# ============================
@qc_tools_bp.route('/<int:project_id>/stage3/checksheet', methods=['POST'])
@project_member_required
def save_checksheet(project_id):
    data = request.json.get('data', [])
    
    rca = get_or_create_rca(project_id)
    rca.checksheet_data = data
    
    # Auto-populate Pareto data from checksheet tallies
    if isinstance(data, list) and len(data) > 0:
        pareto_auto = [{"cause": d.get("defect", d.get("item", "")), "freq": d.get("count", d.get("tally", 0))} for d in data]
        pareto_auto.sort(key=lambda x: x['freq'], reverse=True)
        total = sum(d['freq'] for d in pareto_auto)
        if total > 0:
            running = 0
            for d in pareto_auto:
                running += d['freq']
                d['cumulative_pct'] = round((running / total) * 100, 1)
            rca.pareto_data = pareto_auto
    
    db.session.commit()
    return jsonify({"msg": "Check sheet saved and Pareto auto-populated", "data": data})

@qc_tools_bp.route('/<int:project_id>/stage3/checksheet', methods=['GET'])
@project_member_required
def get_checksheet(project_id):
    rca = Stage3RCA.query.filter_by(project_id=project_id).first()
    return jsonify({"data": rca.checksheet_data if rca else []})

# ============================
# FLOWCHART (Mermaid.js format)
# ============================
@qc_tools_bp.route('/<int:project_id>/stage3/flowchart', methods=['POST'])
@project_member_required
def save_flowchart(project_id):
    steps = request.json.get('steps', [])
    
    # Convert to Mermaid.js format
    mermaid_lines = ["graph TD"]
    for i, step in enumerate(steps):
        node_id = f"S{i}"
        label = step.get('label', f'Step {i+1}')
        step_type = step.get('type', 'process')
        
        if step_type == 'decision':
            mermaid_lines.append(f'    {node_id}{{{{{label}}}}}')
        elif step_type == 'start' or step_type == 'end':
            mermaid_lines.append(f'    {node_id}([{label}])')
        else:
            mermaid_lines.append(f'    {node_id}[{label}]')
        
        if i > 0:
            connector = step.get('connector', '')
            mermaid_lines.append(f'    S{i-1} -->|{connector}| {node_id}')
    
    processed = {
        "steps": steps,
        "mermaid": "\n".join(mermaid_lines)
    }
    
    rca = get_or_create_rca(project_id)
    rca.flowchart_data = processed
    db.session.commit()
    
    return jsonify({"msg": "Flowchart saved", "processed": processed})

@qc_tools_bp.route('/<int:project_id>/stage3/flowchart', methods=['GET'])
@project_member_required
def get_flowchart(project_id):
    rca = Stage3RCA.query.filter_by(project_id=project_id).first()
    return jsonify({"data": rca.flowchart_data if rca else {}})

# ============================
# 5S AUDIT (Radar Chart)
# ============================
@qc_tools_bp.route('/<int:project_id>/stage3/fives', methods=['POST'])
@project_member_required
def save_fives(project_id):
    scores = request.json.get('scores', {})
    categories = ['sort', 'set_in_order', 'shine', 'standardize', 'sustain']
    
    validated = {}
    for cat in categories:
        val = float(scores.get(cat, 0))
        validated[cat] = min(max(val, 0), 5)  # Clamp 0-5
    
    avg_score = round(sum(validated.values()) / len(validated), 2)
    
    processed = {
        "scores": validated,
        "average": avg_score,
        "labels": ["Sort", "Set in Order", "Shine", "Standardize", "Sustain"],
        "values": [validated[c] for c in categories]
    }
    
    rca = get_or_create_rca(project_id)
    rca.fives_audit_data = processed
    db.session.commit()
    
    return jsonify({"msg": "5S audit saved", "processed": processed})

@qc_tools_bp.route('/<int:project_id>/stage3/fives', methods=['GET'])
@project_member_required
def get_fives(project_id):
    rca = Stage3RCA.query.filter_by(project_id=project_id).first()
    return jsonify({"data": rca.fives_audit_data if rca else {}})

# ============================
# POKA-YOKE LOG
# ============================
@qc_tools_bp.route('/<int:project_id>/stage3/pokayoke', methods=['POST'])
@project_member_required
def save_pokayoke(project_id):
    entries = request.json.get('entries', [])
    
    for entry in entries:
        effectiveness = entry.get('effectiveness', 1)
        entry['effectiveness'] = min(max(int(effectiveness), 1), 5)
    
    rca = get_or_create_rca(project_id)
    rca.pokayoke_data = entries
    db.session.commit()
    
    return jsonify({"msg": "Poka-Yoke log saved", "entries": entries})

@qc_tools_bp.route('/<int:project_id>/stage3/pokayoke', methods=['GET'])
@project_member_required
def get_pokayoke(project_id):
    rca = Stage3RCA.query.filter_by(project_id=project_id).first()
    return jsonify({"data": rca.pokayoke_data if rca else []})
