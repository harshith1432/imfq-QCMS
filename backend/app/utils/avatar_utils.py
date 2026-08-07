import os
from flask import current_app

def get_profile_picture_url(user):
    if not user or not user.profile_picture:
        username = user.username if user else 'User'
        return f"/api/auth/avatar/{username}"
    
    # Strip any prepended /uploads/ or uploads/ to get clean filename
    path = user.profile_picture
    if path.startswith('/uploads/'):
        filename = path[len('/uploads/'):]
    elif path.startswith('uploads/'):
        filename = path[len('uploads/'):]
    else:
        filename = path
        
    file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
    if os.path.exists(file_path):
        return f"/uploads/{filename}"
    else:
        username = user.username if user else 'User'
        return f"/api/auth/avatar/{username}"
