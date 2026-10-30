from pathlib import Path

import firebase_admin
from firebase_admin import credentials

from app.core.config import get_settings


def get_firebase_app() -> firebase_admin.App:
    try:
        return firebase_admin.get_app("orbit")
    except ValueError:
        settings = get_settings()
        options = {"projectId": settings.firebase_project_id} if settings.firebase_project_id else {}
        credential_file = settings.firebase_service_account_file
        if credential_file and Path(credential_file).is_file():
            credential = credentials.Certificate(credential_file)
        else:
            credential = credentials.ApplicationDefault()
        return firebase_admin.initialize_app(credential, options=options, name="orbit")
