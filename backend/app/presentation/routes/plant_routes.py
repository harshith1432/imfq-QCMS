from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.infrastructure.database.models.models import db, User, Plant, Department, AuditLog
from app.presentation.routes.admin_routes import admin_required, log_action
from datetime import datetime, timezone
from app.presentation.routes.error_helpers import internal_server_error

plant_bp = Blueprint('plant_bp', __name__)

def get_current_user():
    try:
        uid = get_jwt_identity()
        if isinstance(uid, dict):
            uid = uid.get('id')
        if uid and str(uid).isdigit():
            uid = int(uid)
        return db.session.get(User, uid)
    except Exception:
        return None

@plant_bp.route('', methods=['GET'])
@plant_bp.route('/', methods=['GET'])
@jwt_required()
def get_plants():
    """List all plant locations for the current user's organization."""
    try:
        current_user = get_current_user()
        if not current_user:
            return jsonify({"status": "error", "message": "User context not found"}), 404

        from app.infrastructure.database.models.models import Project, ProjectMember
        plants = Plant.query.filter_by(org_id=current_user.org_id).order_by(Plant.name).all()
        all_org_users = User.query.filter_by(org_id=current_user.org_id).all()
        all_depts = Department.query.filter_by(org_id=current_user.org_id).all()

        # Collect distinct user IDs participating in QC projects
        projects = Project.query.filter_by(org_id=current_user.org_id).all()
        project_ids = [pr.id for pr in projects]
        qc_user_ids = set()
        for pr in projects:
            if pr.creator_id: qc_user_ids.add(pr.creator_id)
            if pr.team_leader_id: qc_user_ids.add(pr.team_leader_id)
            if pr.facilitator_id: qc_user_ids.add(pr.facilitator_id)
            if pr.reviewer_id: qc_user_ids.add(pr.reviewer_id)

        if project_ids:
            members = ProjectMember.query.filter(ProjectMember.project_id.in_(project_ids)).all()
            for m in members:
                qc_user_ids.add(m.user_id)

        total_org_qc_users = len([u for u in all_org_users if u.id in qc_user_ids])
        
        result = []
        for p in plants:
            p_depts = [d for d in all_depts if d.plant_id == p.id]
            p_users = [u for u in all_org_users if u.plant_id == p.id]
            p_qc_users = [u for u in p_users if u.id in qc_user_ids]
            result.append({
                "id": p.id,
                "org_id": p.org_id,
                "name": p.name,
                "code": p.code or "",
                "location": p.location or "",
                "created_at": p.created_at.strftime('%Y-%m-%d %H:%M:%S') if p.created_at else "",
                "department_count": len(p_depts),
                "user_count": len(p_users),
                "employee_count": len(p_users),
                "qc_user_count": len(p_qc_users),
                "qc_employee_count": len(p_qc_users)
            })
            
        return jsonify({
            "status": "success", 
            "plants": result,
            "total_employees": len(all_org_users),
            "total_qc_employees": total_org_qc_users
        }), 200
    except Exception as e:
        db.session.rollback()
        return internal_server_error(e, "An internal server error occurred.")

@plant_bp.route('', methods=['POST'])
@plant_bp.route('/', methods=['POST'])
@jwt_required()
@admin_required
def create_plant():
    """Create a new plant location."""
    try:
        current_user = get_current_user()
        if not current_user:
            return jsonify({"status": "error", "message": "User context not found"}), 404

        data = request.get_json() or {}
        name = (data.get('name') or '').strip()
        code = (data.get('code') or '').strip()
        location = (data.get('location') or '').strip()

        if not name:
            return jsonify({"status": "error", "message": "Plant location name is required"}), 400

        # Check SaaS Subscription Plan Location Limit
        from app.domain.services.subscription_service import SubscriptionManager
        can_add, limit_msg = SubscriptionManager.check_location_limit(current_user.org_id)
        if not can_add:
            return jsonify({
                "status": "error",
                "message": limit_msg,
                "error_code": "LOCATION_LIMIT_REACHED"
            }), 403

        # Case-insensitive duplicate name check within the same organisation
        from sqlalchemy import func as sqlfunc
        existing = Plant.query.filter(
            Plant.org_id == current_user.org_id,
            sqlfunc.lower(Plant.name) == name.lower()
        ).first()
        if existing:
            return jsonify({
                "status": "error",
                "message": f"A plant location named '{existing.name}' already exists in your organisation. "
                           "Plant names must be unique (case-insensitive)."
            }), 409

        new_plant = Plant(
            org_id=current_user.org_id,
            name=name,
            code=code,
            location=location,
            created_at=datetime.now(timezone.utc).replace(tzinfo=None)
        )
        db.session.add(new_plant)
        db.session.commit()

        log_action(current_user.id, "CREATE_PLANT", current_user.org_id, "plants", new_plant.id, {"name": name, "code": code})

        return jsonify({
            "status": "success",
            "message": "Plant location created successfully",
            "plant": {
                "id": new_plant.id,
                "name": new_plant.name,
                "code": new_plant.code,
                "location": new_plant.location
            }
        }), 201
    except Exception as e:
        db.session.rollback()
        return internal_server_error(e, "An internal server error occurred.")

# ==============================================================================
# [DEAD CODE - UNUSED BY FRONTEND / REMOVED FEATURE]
# Function: update_plant (Lines 150-206)
# Reason: Direct plant update route. Frontend uses /plants (POST/GET).
# ==============================================================================
# @plant_bp.route('/<int:plant_id>', methods=['PUT'])
# @jwt_required()
# @admin_required
# def update_plant(plant_id):
#     """Update a plant location."""
#     try:
#         current_user = get_current_user()
#         if not current_user:
#             return jsonify({"status": "error", "message": "User context not found"}), 404

#         plant = Plant.query.filter_by(id=plant_id, org_id=current_user.org_id).first()
#         if not plant:
#             return jsonify({"status": "error", "message": "Plant location not found"}), 404

#         data = request.get_json() or {}
#         name = (data.get('name') or '').strip()
#         code = (data.get('code') or '').strip()
#         location = (data.get('location') or '').strip()

#         if name:
#             # Case-insensitive duplicate check (exclude self)
#             from sqlalchemy import func as sqlfunc
#             dup = Plant.query.filter(
#                 Plant.org_id == current_user.org_id,
#                 sqlfunc.lower(Plant.name) == name.lower(),
#                 Plant.id != plant_id
#             ).first()
#             if dup:
#                 return jsonify({
#                     "status": "error",
#                     "message": f"A plant location named '{dup.name}' already exists in your organisation. "
#                                "Plant names must be unique (case-insensitive)."
#                 }), 409
#             plant.name = name

#         if 'code' in data:
#             plant.code = code
#         if 'location' in data:
#             plant.location = location

#         db.session.commit()

#         log_action(current_user.id, "UPDATE_PLANT", current_user.org_id, "plants", plant.id, data)

#         return jsonify({
#             "status": "success",
#             "message": "Plant location updated successfully",
#             "plant": {
#                 "id": plant.id,
#                 "name": plant.name,
#                 "code": plant.code,
#                 "location": plant.location
#             }
#         }), 200
#     except Exception as e:
#         db.session.rollback()
#         return internal_server_error(e, "An internal server error occurred.")
# [END DEAD CODE: update_plant]


# ==============================================================================
# [DEAD CODE - UNUSED BY FRONTEND / REMOVED FEATURE]
# Function: get_plant_stats (Lines 208-229)
# Reason: Plant-specific stat route. Frontend loads plant analytics in /analytics/dashboard.
# ==============================================================================
# @plant_bp.route('/<int:plant_id>/stats', methods=['GET'])
# @jwt_required()
# @admin_required
# def get_plant_stats(plant_id):
#     """Return dept + user counts for the deletion confirmation dialog."""
#     try:
#         current_user = get_current_user()
#         if not current_user:
#             return jsonify({"status": "error", "message": "User context not found"}), 404
#         plant = Plant.query.filter_by(id=plant_id, org_id=current_user.org_id).first()
#         if not plant:
#             return jsonify({"status": "error", "message": "Plant not found"}), 404
#         dept_count = Department.query.filter_by(plant_id=plant_id, org_id=current_user.org_id).count()
#         user_count = User.query.filter_by(plant_id=plant_id, org_id=current_user.org_id).count()
#         return jsonify({
#             "plant_id": plant_id,
#             "plant_name": plant.name,
#             "dept_count": dept_count,
#             "user_count": user_count
#         }), 200
#     except Exception as e:
#         return internal_server_error(e, "An internal server error occurred.")
# [END DEAD CODE: get_plant_stats]


# ==============================================================================
# [DEAD CODE - UNUSED BY FRONTEND / REMOVED FEATURE]
# Function: delete_plant (Lines 231-345)
# Reason: Plant delete route.
# ==============================================================================
# @plant_bp.route('/<int:plant_id>', methods=['DELETE'])
# @jwt_required()
# @admin_required
# def delete_plant(plant_id):
#     """
#     Smart plant delete.
#     Body JSON params:
#       action          : 'delete_all' | 'move_to_plant' | 'new_plant'
#       target_plant_id : (required for move_to_plant) existing plant id
#       new_plant_name  : (required for new_plant) name for the new plant
#       new_plant_code  : (optional for new_plant) code for the new plant
#     """
#     try:
#         current_user = get_current_user()
#         if not current_user:
#             return jsonify({"status": "error", "message": "User context not found"}), 404

#         plant = Plant.query.filter_by(id=plant_id, org_id=current_user.org_id).first()
#         if not plant:
#             return jsonify({"status": "error", "message": "Plant location not found"}), 404

#         data   = request.get_json(silent=True) or {}
#         action = data.get('action', '').strip()

#         departments = Department.query.filter_by(plant_id=plant_id, org_id=current_user.org_id).all()
#         users       = User.query.filter_by(plant_id=plant_id, org_id=current_user.org_id).all()

#         if not action:
#             # Legacy: just unlink and delete
#             for d in departments:
#                 d.plant_id = None
#             for u in users:
#                 u.plant_id = None

#         elif action == 'delete_all':
#             from app.presentation.routes.admin_routes import disassociate_and_delete_user
#             try:
#                 db.session.execute(db.text("ALTER TABLE audit_logs ALTER COLUMN user_id DROP NOT NULL;"))
#                 db.session.commit()
#             except Exception:
#                 db.session.rollback()

#             deleted_user_ids = set()
#             for u in users:
#                 if u.id not in deleted_user_ids:
#                     disassociate_and_delete_user(u, admin_user_id=current_user.id)
#                     deleted_user_ids.add(u.id)

#             for d in departments:
#                 dept_users = User.query.filter_by(department_id=d.id, org_id=current_user.org_id).all()
#                 for du in dept_users:
#                     if du.id not in deleted_user_ids:
#                         disassociate_and_delete_user(du, admin_user_id=current_user.id)
#                         deleted_user_ids.add(du.id)
#                 db.session.delete(d)

#         elif action == 'move_to_plant':
#             target_id = data.get('target_plant_id')
#             if not target_id:
#                 return jsonify({"status": "error", "message": "'target_plant_id' is required."}), 400
#             target_plant = Plant.query.filter_by(id=int(target_id), org_id=current_user.org_id).first()
#             if not target_plant:
#                 return jsonify({"status": "error", "message": "Target plant not found."}), 404

#             for d in departments:
#                 d.plant_id = target_plant.id
#                 dept_users = User.query.filter_by(department_id=d.id, org_id=current_user.org_id).all()
#                 for du in dept_users:
#                     du.plant_id = target_plant.id

#             for u in users:
#                 u.plant_id = target_plant.id

#         elif action == 'new_plant':
#             new_name = (data.get('new_plant_name') or '').strip()
#             if not new_name:
#                 return jsonify({"status": "error", "message": "'new_plant_name' is required."}), 400
#             from sqlalchemy import func as sqlfunc
#             clash = Plant.query.filter(
#                 Plant.org_id == current_user.org_id,
#                 sqlfunc.lower(Plant.name) == new_name.lower()
#             ).first()
#             if clash:
#                 return jsonify({"status": "error",
#                                 "message": f"A plant named '{clash.name}' already exists."}), 409
#             new_plant = Plant(
#                 org_id=current_user.org_id,
#                 name=new_name,
#                 code=(data.get('new_plant_code') or '').strip(),
#                 created_at=datetime.now(timezone.utc).replace(tzinfo=None)
#             )
#             db.session.add(new_plant)
#             db.session.flush()

#             for d in departments:
#                 d.plant_id = new_plant.id
#                 dept_users = User.query.filter_by(department_id=d.id, org_id=current_user.org_id).all()
#                 for du in dept_users:
#                     du.plant_id = new_plant.id

#             for u in users:
#                 u.plant_id = new_plant.id
#         else:
#             return jsonify({"status": "error", "message": f"Unknown action '{action}'."}), 400

#         db.session.delete(plant)
#         db.session.commit()

#         log_action(current_user.id, "DELETE_PLANT", current_user.org_id, "plants", plant_id,
#                    {"action": action, "depts_affected": len(departments), "users_affected": len(users)})

#         return jsonify({"status": "success", "message": "Plant location deleted successfully"}), 200
#     except Exception as e:
#         db.session.rollback()
#         return internal_server_error(e, "An internal server error occurred.")
# [END DEAD CODE: delete_plant]

