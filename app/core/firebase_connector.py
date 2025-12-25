"""
Module for initializing the Firebase Admin SDK with robust handling of credentials.

Behavior:
- If Firebase app already initialized, do nothing.
- Read credentials from `settings.FIREBASE_CREDENTIALS_JSON` (preferred).
  * If value looks like JSON (starts with '{'), parse it and use Certificate(dict).
  * Otherwise treat it as a path to a JSON file and load it.
- If `settings.FIREBASE_CREDENTIALS_JSON` is empty, fall back to the
  GOOGLE_APPLICATION_CREDENTIALS environment variable (path to file).
- Validate that the credential dict contains 'type' == 'service_account' and
  raise a clear ValueError otherwise.
"""
import os
import json
import logging
import firebase_admin
from firebase_admin import credentials
from app.core.config import settings


def _load_cred_from_json_string(val: str):
    try:
        cred_dict = json.loads(val)
    except Exception as e:
        raise ValueError(f"FIREBASE_CREDENTIALS_JSON does not contain valid JSON: {e}")
    if cred_dict.get("type") != "service_account":
        raise ValueError("Invalid service account certificate: 'type' field must be 'service_account'.")
    return credentials.Certificate(cred_dict)


def initialize_firebase():
    """Initializes the Firebase Admin SDK using credentials from environment variables.

    Raises a clear exception when credentials are missing or invalid so the deploy logs
    show an actionable message.
    """
    try:
        if firebase_admin._apps:
            logging.debug("Firebase already initialized")
            return

        logging.info("Initializing Firebase Admin SDK...")

        firebase_creds = getattr(settings, "FIREBASE_CREDENTIALS_JSON", None)

        # 1) If the settings value is provided
        if firebase_creds:
            # If it looks like JSON, parse it
            if isinstance(firebase_creds, str) and firebase_creds.strip().startswith("{"):
                cred = _load_cred_from_json_string(firebase_creds)
            else:
                # Treat as a path to a file
                path = os.path.expanduser(str(firebase_creds))
                if os.path.isfile(path):
                    cred = credentials.Certificate(path)
                else:
                    # Fall back: maybe it's JSON without braces
                    try:
                        cred = _load_cred_from_json_string(firebase_creds)
                    except ValueError:
                        raise ValueError(f"FIREBASE_CREDENTIALS_JSON value is neither a valid JSON nor a path to a file: {path}")

            firebase_admin.initialize_app(cred)
            logging.info("Firebase Admin SDK initialized successfully from FIREBASE_CREDENTIALS_JSON.")
            return

        # 2) Fallback to GOOGLE_APPLICATION_CREDENTIALS env var (path to file)
        gac = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        if gac:
            path = os.path.expanduser(gac)
            if os.path.isfile(path):
                cred = credentials.Certificate(path)
                firebase_admin.initialize_app(cred)
                logging.info("Firebase Admin SDK initialized successfully from GOOGLE_APPLICATION_CREDENTIALS.")
                return
            else:
                raise ValueError(f"GOOGLE_APPLICATION_CREDENTIALS is set but the file was not found: {path}")

        # 3) Nothing provided
        raise ValueError("Firebase credentials not provided. Set FIREBASE_CREDENTIALS_JSON (content or path) or GOOGLE_APPLICATION_CREDENTIALS (path).")

    except Exception as e:
        logging.error(f"Fatal error: Failed to initialize Firebase Admin SDK: {e}")
        raise
