"""
Module for initializing the Firebase Admin SDK.
"""
import json
import logging
import firebase_admin
from firebase_admin import credentials
from app.core.config import settings


def initialize_firebase():
    """
    Initializes the Firebase Admin SDK using credentials from environment variables.
    This function should be called once when the application starts.
    """
    try:
        # Check if the app is already initialized to prevent errors during reloads
        if not firebase_admin._apps:
            logging.info("Initializing Firebase Admin SDK...")
            firebase_creds_json = settings.FIREBASE_CREDENTIALS_JSON
            if not firebase_creds_json:
                raise ValueError("FIREBASE_CREDENTIALS_JSON environment variable is not set or is empty.")

            cred_dict = json.loads(firebase_creds_json)
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred)
            logging.info("Firebase Admin SDK initialized successfully.")
    except Exception as e:
        logging.error(f"Fatal error: Failed to initialize Firebase Admin SDK: {e}")
        raise
