from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.infrastructure.database.models.models import db, User, Notification
from datetime import datetime

notification_bp = Blueprint('notification', __name__)

@notification_bp.route('/notifications', methods=['GET'])
@jwt_required()
def get_notifications():
    user_id = int(get_jwt_identity())
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"msg": "User not found"}), 404

    notifications = Notification.query.filter_by(
        user_id=user.id,
        org_id=user.org_id
    ).order_by(Notification.created_at.desc()).all()

    return jsonify([{
        "id": n.id,
        "title": n.title,
        "message": n.message,
        "is_read": n.is_read,
        "created_at": n.created_at.isoformat() + "Z",
        "link": n.link
    } for n in notifications]), 200

@notification_bp.route('/notifications/read', methods=['POST'])
@jwt_required()
def mark_all_read():
    user_id = int(get_jwt_identity())
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"msg": "User not found"}), 404

    db.session.query(Notification).filter_by(
        user_id=user.id,
        org_id=user.org_id,
        is_read=False
    ).update({Notification.is_read: True}, synchronize_session=False)

    db.session.commit()
    return jsonify({"msg": "All notifications marked as read"}), 200

@notification_bp.route('/notifications/clear', methods=['POST'])
@jwt_required()
def clear_notifications():
    user_id = int(get_jwt_identity())
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"msg": "User not found"}), 404

    db.session.query(Notification).filter_by(
        user_id=user.id,
        org_id=user.org_id
    ).delete(synchronize_session=False)

    db.session.commit()
    return jsonify({"msg": "All notifications cleared"}), 200


def create_notification(org_id, user_id, title, message, link=None, commit=True):
    """Utility helper to create a user notification."""
    try:
        # Check if recipient exists
        user = db.session.get(User, user_id)
        if not user:
            return None

        notif = Notification(
            org_id=org_id,
            user_id=user_id,
            title=title,
            message=message,
            link=link
        )
        db.session.add(notif)
        if commit:
            db.session.commit()
        else:
            db.session.flush()
        return notif
    except Exception as e:
        db.session.rollback()
        print(f"[QCMS Notification Error] {str(e)}")
        return None
