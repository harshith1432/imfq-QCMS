@dashboard_bp.route('/activity', methods=['GET'])
@jwt_required()
def get_dashboard_activity():
    user = User.query.get(get_jwt_identity())
    from app.infrastructure.database.models.models import AuditLog, Project
    
    query = AuditLog.query.join(Project, AuditLog.project_id == Project.id).filter(AuditLog.org_id == user.org_id)
    
    if user.role.name == 'Team Leader':
        query = query.filter(Project.department_id == user.department_id)
    elif user.role.name == 'Team Member':
        query = query.filter(Project.members.any(id=user.id))
    elif user.role.name == 'Facilitator':
        # Facilitators only see activity for projects they are assigned to
        query = query.filter(Project.facilitator_id == user.id)
    elif user.role.name == 'Reviewer':
        # Reviewers only see activity for projects they are assigned to review
        query = query.filter(Project.reviewer_id == user.id)
            
    recent_logs = query.order_by(AuditLog.created_at.desc()).limit(10).all()
    
    return jsonify([{
        "id": log.id,
        "project_id": log.project_id,
        "project_title": log.project.title if log.project else "Unknown",
        "action": log.action,
        "user_name": log.user.full_name if log.user else "System",
        "created_at": log.created_at.isoformat() + "Z",
        "details": log.details
    } for log in recent_logs]), 200
