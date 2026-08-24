import json
import os
from flask import request, current_app
from app import db
from app.infrastructure.database.models.models import User

class BackendI18n:
    _translations = {}
    _base_path = None

    @classmethod
    def _load_translations(cls, lang):
        if not cls._base_path:
            # Assuming the backend is in /backend and frontend in /frontend
            # We might need to point to the shared translation files or have a copy
            # For now, let's look for assets/i18n relative to the app root or a configured path
            cls._base_path = os.path.join(os.getcwd(), '..', 'frontend', 'assets', 'i18n')
            
        if lang not in cls._translations:
            try:
                path = os.path.join(cls._base_path, f'{lang}.json')
                if os.path.exists(path):
                    with open(path, 'r', encoding='utf-8') as f:
                        cls._translations[lang] = json.load(f)
                else:
                    return None
            except Exception:
                return None
        return cls._translations.get(lang)

    @classmethod
    def get_user_locale(cls, user_id=None):
        # 1. User preference from DB
        if user_id:
            user = db.session.get(User, user_id)
            if user and user.language:
                return user.language
        
        # 2. Accept-Language header
        header = request.headers.get('Accept-Language', 'en')
        lang = header.split(',')[0].split('-')[0]
        if lang in ['en', 'hi', 'kn', 'te', 'ta', 'ml']:
            return lang
            
        return 'en'

    @classmethod
    def translate(cls, key, user_id=None, **kwargs):
        lang = cls.get_user_locale(user_id)
        translations = cls._load_translations(lang)
        
        if not translations and lang != 'en':
            translations = cls._load_translations('en')
            
        if not translations:
            return key

        keys = key.split('.')
        result = translations
        for k in keys:
            if isinstance(result, dict) and k in result:
                result = result[k]
            else:
                result = key
                break
        
        if isinstance(result, str):
            return result.format(**kwargs)
        return key

def _(key, **kwargs):
    """Shorthand for translate"""
    return BackendI18n.translate(key, **kwargs)
