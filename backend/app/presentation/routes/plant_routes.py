from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.infrastructure.database.models.models import db, User, Plant, Department, AuditLog
from app.presentation.routes.admin_routes import admin_required, log_action
from datetime import datetime

plant_bp = Blueprint('plant_bp', __name__)

def get_current_user():
    try:
        uid = get_jwt_identity()
        if isinstance(uid, dict):
            uid = uid.get('id')
        if uid and str(uid).isdigit():
            uid = int(uid)
        return User.query.get(uid)
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

        plants = Plant.query.filter_by(org_id=current_user.org_id).order_by(Plant.name).all()
        
        result = []
        for p in plants:
            dept_count = Department.query.filter_by(plant_id=p.id, org_id=current_user.org_id).count()
            user_count = User.query.filter_by(plant_id=p.id, org_id=current_user.org_id).count()
            result.append({
                "id": p.id,
                "org_id": p.org_id,
                "name": p.name,
                "code": p.code or "",
                "location": p.location or "",
                "created_at": p.created_at.strftime('%Y-%m-%d %H:%M:%S') if p.created_at else "",
                "department_count": dept_count,
                "user_count": user_count
            })
            
        return jsonify({"status": "success", "plants": result}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500

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

        # Check duplicate name within organization
        existing = Plant.query.filter_by(org_id=current_user.org_id, name=name).first()
        if existing:
            return jsonify({"status": "error", "message": f"Plant location '{name}' already exists"}), 400

        new_plant = Plant(
            org_id=current_user.org_id,
            name=name,
            code=code,
            location=location,
            created_at=datetime.utcnow()
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
        return jsonify({"status": "error", "message": str(e)}), 500

@plant_bp.route('/<int:plant_id>', methods=['PUT'])
@jwt_required()
@admin_required
def update_plant(plant_id):
    """Update a plant location."""
    try:
        current_user = get_current_user()
        if not current_user:
            return jsonify({"status": "error", "message": "User context not found"}), 404

        plant = Plant.query.filter_by(id=plant_id, org_id=current_user.org_id).first()
        if not plant:
            return jsonify({"status": "error", "message": "Plant location not found"}), 404

        data = request.get_json() or {}
        name = (data.get('name') or '').strip()
        code = (data.get('code') or '').strip()
        location = (data.get('location') or '').strip()

        if name:
            # Check duplicate name
            dup = Plant.query.filter(
                Plant.org_id == current_user.org_id,
                Plant.name == name,
                Plant.id != plant_id
            ).first()
            if dup:
                return jsonify({"status": "error", "message": f"Another plant location already uses the name '{name}'"}), 400
            plant.name = name

        if 'code' in data:
            plant.code = code
        if 'location' in data:
            plant.location = location

        db.session.commit()

        log_action(current_user.id, "UPDATE_PLANT", current_user.org_id, "plants", plant.id, data)

        return jsonify({
            "status": "success",
            "message": "Plant location updated successfully",
            "plant": {
                "id": plant.id,
                "name": plant.name,
                "code": plant.code,
                "location": plant.location
            }
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500

@plant_bp.route('/<int:plant_id>', methods=['DELETE'])
@jwt_required()
@admin_required
def delete_plant(plant_id):
    """Delete a plant location."""
    try:
        current_user = get_current_user()
        if not current_user:
            return jsonify({"status": "error", "message": "User context not found"}), 404

        plant = Plant.query.filter_by(id=plant_id, org_id=current_user.org_id).first()
        if not plant:
            return jsonify({"status": "error", "message": "Plant location not found"}), 404

        # Disassociate departments and users
        departments = Department.query.filter_by(plant_id=plant_id, org_id=current_user.org_id).all()
        for d in departments:
            d.plant_id = None

        users = User.query.filter_by(plant_id=plant_id, org_id=current_user.org_id).all()
        for u in users:
            u.plant_id = None

        db.session.delete(plant)
        db.session.commit()

        log_action(current_user.id, "DELETE_PLANT", current_user.org_id, "plants", plant_id, {"deleted_plant_id": plant_id})

        return jsonify({"status": "success", "message": "Plant location deleted successfully"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500
