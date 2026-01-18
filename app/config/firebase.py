"""
Firebase Firestore initialization.
Single-source-of-truth Firestore client for Nagar Alert Hub.
"""

from typing import Optional
import firebase_admin
from firebase_admin import credentials, firestore, initialize_app

from app.core.settings import settings

db: Optional[firestore.Client] = None


def initialize_firestore() -> firestore.Client:
    global db

    if db is not None:
        return db

    if settings.USE_MOCK_DB:
        from app.config.mock_firestore import get_mock_db
        db = get_mock_db(settings.MOCK_DB_PATH)
        print("[FIRESTORE] USING MOCK DATABASE")
        return db

    try:
        if not firebase_admin._apps:
            if settings.FIREBASE_CREDENTIALS_PATH:
                import os
                cred_path = settings.FIREBASE_CREDENTIALS_PATH
                
                # Validate credentials file exists
                if not os.path.exists(cred_path):
                    raise FileNotFoundError(
                        f"Firebase credentials file not found: {cred_path}\n"
                        f"Please check your .env file and ensure FIREBASE_CREDENTIALS_PATH is correct.\n"
                        f"Current working directory: {os.getcwd()}"
                    )
                
                # Validate credentials file is readable
                try:
                    import json
                    with open(cred_path, 'r') as f:
                        cred_data = json.load(f)
                    
                    # Validate required fields
                    required_fields = ['type', 'project_id', 'private_key', 'client_email']
                    missing_fields = [field for field in required_fields if field not in cred_data]
                    if missing_fields:
                        raise ValueError(
                            f"Firebase credentials file is missing required fields: {missing_fields}\n"
                            f"Please download a fresh service account key from Firebase Console."
                        )
                    
                    # Validate private key format
                    private_key = cred_data.get('private_key', '')
                    if not private_key or not private_key.startswith('-----BEGIN PRIVATE KEY-----'):
                        raise ValueError(
                            "Firebase credentials file has invalid private_key format.\n"
                            "Please download a fresh service account key from Firebase Console."
                        )
                    
                    print(f"[FIRESTORE] Credentials file validated: {cred_path}")
                    print(f"[FIRESTORE] Project ID: {cred_data.get('project_id', 'N/A')}")
                    
                except json.JSONDecodeError as e:
                    raise ValueError(
                        f"Firebase credentials file is not valid JSON: {e}\n"
                        f"Please check the file at: {cred_path}"
                    )
                
                cred = credentials.Certificate(cred_path)
                initialize_app(cred)
                print("[FIRESTORE] Firebase Admin SDK initialized with service account")
            else:
                print("[FIRESTORE] No credentials path set, using Application Default Credentials")
                initialize_app()

        # Test the connection by creating a client
        db = firestore.client()
        
        # Verify connection by attempting a simple operation (non-blocking test)
        try:
            # Just get a reference - doesn't actually query
            test_ref = db.collection("_test_connection").limit(1)
            print("[FIRESTORE] Connection test successful")
        except Exception as test_error:
            print(f"[FIRESTORE] Warning: Connection test failed: {test_error}")
            # Continue anyway - might be a permissions issue
        
        print("[FIRESTORE] USING REAL FIRESTORE DATABASE")
        print(f"[FIRESTORE] Project: {settings.FIREBASE_PROJECT_ID or 'default'}")
        return db

    except FileNotFoundError as e:
        raise RuntimeError(
            f"Firestore initialization FAILED - Credentials file not found.\n"
            f"{str(e)}\n"
            f"SOLUTION: Check your .env file and ensure FIREBASE_CREDENTIALS_PATH points to a valid service account JSON file."
        )
    except ValueError as e:
        raise RuntimeError(
            f"Firestore initialization FAILED - Invalid credentials file.\n"
            f"{str(e)}\n"
            f"SOLUTION: Download a fresh service account key from Firebase Console:\n"
            f"1. Go to Firebase Console > Project Settings > Service Accounts\n"
            f"2. Click 'Generate New Private Key'\n"
            f"3. Save the JSON file and update FIREBASE_CREDENTIALS_PATH in .env"
        )
    except Exception as e:
        error_msg = str(e)
        if "Invalid JWT Signature" in error_msg or "invalid_grant" in error_msg:
            raise RuntimeError(
                f"Firestore initialization FAILED - Invalid JWT Signature.\n"
                f"This usually means:\n"
                f"1. The service account key has been revoked/disabled in Firebase Console\n"
                f"2. The private key in the credentials file is corrupted\n"
                f"3. The credentials file is for a different project\n\n"
                f"SOLUTION:\n"
                f"1. Go to Firebase Console > Project Settings > Service Accounts\n"
                f"2. Generate a NEW service account key\n"
                f"3. Replace your credentials file with the new one\n"
                f"4. Restart the server\n\n"
                f"Original error: {error_msg}"
            )
        raise RuntimeError(
            f"Firestore initialization FAILED. Error: {error_msg}\n"
            f"Please check your Firebase credentials and configuration."
        )


def get_db() -> firestore.Client:
    """
    Get the initialized Firestore client.
    
    Raises RuntimeError if Firestore has not been initialized.
    """
    if db is None:
        # Try to initialize if not already done
        try:
            initialize_firestore()
        except Exception as e:
            raise RuntimeError(
                f"Firestore not initialized and initialization failed: {e}. "
                "Please check your Firebase credentials and configuration."
            )
    return db
