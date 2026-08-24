import os
from flask import current_app

def get_profile_picture_url(user_or_path):
    if not user_or_path:
        return "/api/auth/avatar/User"
    
    if isinstance(user_or_path, str):
        path = user_or_path
        username = 'User'
    else:
        path = getattr(user_or_path, 'profile_picture', None)
        username = getattr(user_or_path, 'username', 'User') or 'User'

    if not path:
        return f"/api/auth/avatar/{username}"
        
    if path.startswith('http://') or path.startswith('https://') or path.startswith('data:'):
        return path

    # Strip any prepended /uploads/ or uploads/ to get clean filename
    if path.startswith('/uploads/'):
        filename = path[len('/uploads/'):]
    elif path.startswith('uploads/'):
        filename = path[len('uploads/'):]
    else:
        filename = path

    upload_folder = current_app.config.get('UPLOAD_FOLDER') if current_app else None
    if upload_folder and filename:
        file_path = os.path.join(upload_folder, filename)
        if os.path.exists(file_path):
            return f"/uploads/{filename}"

    return f"/api/auth/avatar/{username}"
