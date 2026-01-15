"""
Seed script for the Nagar Alert Hub mock DB or Firestore.

Usage:
  - Dry run (default): python scripts/seed_db.py
  - Apply to configured DB: python scripts/seed_db.py --apply
  - Force mock DB even if FIREBASE configured: python scripts/seed_db.py --apply --force-mock

Behavior:
  - Loads `db_seed.json` from repo root.
  - Gets DB via `app.config.firebase.get_db()` which will return the mock DB or real Firestore depending on settings.
  - Writes each top-level collection/document to the DB.

NOTE: When applying to real Firestore, ensure `FIREBASE_CREDENTIALS_PATH` and `USE_MOCK_DB=false` are set in `.env` and you've restarted the app or set env before running.
"""

import argparse
import json
import os
from typing import Any

from app.config.firebase import get_db
from app.core import settings


def load_seed(path: str = "./db_seed.json") -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_to_db(db: Any, seed: dict, apply: bool = False):
    # db is either MockFirestore or a real firestore client
    for collection, docs in seed.items():
        for doc_id, data in docs.items():
            print(f"Preparing: {collection}/{doc_id}")
            if not apply:
                continue
            try:
                # Firestore client and MockFirestore share .collection(name).document(id).set(data)
                db.collection(collection).document(doc_id).set(data)
                print(f"Wrote: {collection}/{doc_id}")
            except Exception as e:
                print(f"Failed to write {collection}/{doc_id}: {e}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Write seed to the DB instead of dry-run")
    parser.add_argument("--force-mock", action="store_true", help="Force use of mock DB even if FIREBASE configured")
    args = parser.parse_args()

    seed_path = os.path.join(os.getcwd(), "db_seed.json")
    if not os.path.exists(seed_path):
        print(f"Seed file not found: {seed_path}")
        return

    seed = load_seed(seed_path)

    # If force mock, set environment var temporarily
    if args.force_mock:
        print("Forcing mock DB usage for this run.")
        # Temporarily monkeypatch settings (works because Settings reads .env only once at import)
        settings.USE_MOCK_DB = True

    db = get_db()

    write_to_db(db, seed, apply=args.apply)

    if args.apply:
        print("Seeding completed.")
    else:
        print("Dry run complete. Re-run with --apply to write to DB.")


if __name__ == "__main__":
    main()
