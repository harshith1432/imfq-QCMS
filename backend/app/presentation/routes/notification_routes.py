from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.infrastructure.database.models.models import db, User, Notification
from datetime import datetime, timezone

notification_bp = Blueprint('notification', __name__)

@notification_bp.route('/notifications', methods=['GET'])
@jwt_required()
def get_notifications():
    user_id = int(get_jwt_identity())
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"msg": "User not found"}), 404

    # Ensure is_starred column exists on DB table
    try:
        db.session.execute(db.text("ALTER TABLE notifications ADD COLUMN is_starred BOOLEAN DEFAULT FALSE;"))
        db.session.commit()
    except Exception:
        db.session.rollback()

    notifications = Notification.query.filter(
        db.or_(
            Notification.user_id == user.id,
            db.and_(Notification.org_id == user.org_id, Notification.user_id == None)
        )
    ).order_by(Notification.created_at.desc()).limit(200).all()

    result = []
    for n in notifications:
        title = n.title or ''
        link = n.link or ''
        is_ann = bool(title.startswith('📢') or '[Announcement]' in title or 'view=announcements' in link or 'announcements' in link)
        
        ann_id = None
        if 'ann=' in link:
            try:
                ann_id = int(link.split('ann=')[1].split('&')[0])
            except Exception:
                pass

        result.append({
            "id": n.id,
            "title": n.title,
            "message": n.message,
            "is_read": bool(n.is_read),
            "is_starred": bool(getattr(n, 'is_starred', False)),
            "created_at": n.created_at.isoformat() + "Z" if n.created_at else datetime.now(timezone.utc).replace(tzinfo=None).isoformat() + "Z",
            "link": n.link,
            "is_announcement": is_ann,
            "announcement_id": ann_id
        })

    return jsonify(result), 200

# ==============================================================================
# [DEAD CODE - UNUSED BY FRONTEND / REMOVED FEATURE]
# Function: toggle_star_notification (Lines 57-85)
# Reason: Star/favorite notification feature was removed from frontend bell dropdown.
# ==============================================================================
# @notification_bp.route('/notifications/<int:notif_id>/star', methods=['POST'])
# @jwt_required()
# def toggle_star_notification(notif_id):
#     user_id = int(get_jwt_identity())
#     user = db.session.get(User, user_id)
#     if not user:
#         return jsonify({"msg": "User not found"}), 404

#     # Ensure column exists
#     try:
#         db.session.execute(db.text("ALTER TABLE notifications ADD COLUMN is_starred BOOLEAN DEFAULT FALSE;"))
#         db.session.commit()
#     except Exception:
#         db.session.rollback()

#     notif = db.session.get(Notification, notif_id)
#     if not notif or (notif.user_id != user.id and notif.org_id != user.org_id):
#         return jsonify({"msg": "Notification not found"}), 404

#     current_starred = bool(getattr(notif, 'is_starred', False))
#     notif.is_starred = not current_starred
#     db.session.commit()

#     return jsonify({
#         "status": "success",
#         "id": notif.id,
#         "is_starred": notif.is_starred,
#         "msg": f"Notification {'starred' if notif.is_starred else 'unstarred'}"
#     }), 200
# [END DEAD CODE: toggle_star_notification]


# ==============================================================================
# [DEAD CODE - UNUSED BY FRONTEND / REMOVED FEATURE]
# Function: mark_single_read (Lines 87-100)
# Reason: Single notification mark read. Frontend marks all read via /read.
# ==============================================================================
# @notification_bp.route('/notifications/<int:notif_id>/read', methods=['POST'])
# @jwt_required()
# def mark_single_read(notif_id):
#     user_id = int(get_jwt_identity())
#     user = db.session.get(User, user_id)
#     if not user:
#         return jsonify({"msg": "User not found"}), 404

#     notif = db.session.get(Notification, notif_id)
#     if notif and (notif.user_id == user.id or notif.org_id == user.org_id):
#         notif.is_read = True
#         db.session.commit()

#     return jsonify({"msg": "Notification marked as read", "id": notif_id}), 200
# [END DEAD CODE: mark_single_read]


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

    # Keep starred notifications when clearing, only delete unstarred!
    db.session.query(Notification).filter_by(
        user_id=user.id,
        org_id=user.org_id,
        is_starred=False
    ).delete(synchronize_session=False)

    db.session.commit()
    return jsonify({"msg": "Unstarred notifications cleared"}), 200


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
