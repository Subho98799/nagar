# Database Schema for Nagar Alert Hub

This document describes the Firestore-compatible schema used by the backend to serve the frontend. The app uses a JSON-backed mock DB for local development; the same logical collections/fields map directly to Firestore documents.

Design goals:
- Keep queries simple and index-friendly for Firestore.
- Store raw `reports` (per-user submissions) and derived `issues` (clustered/aggregated events shown on the map).
- Keep `timeline` events either as an array in an `issue` document or as a subcollection for larger histories.

Collections
-----------
1. `reports` (one document per user submission)
   - Document ID: auto-generated or assigned string (e.g., `r1`, `uuid`)
   - Fields:
     - `title`: string (short title provided by user, optional)
     - `description`: string
     - `issue_type`: string (e.g., "Traffic & Roads", "Electricity")
     - `severity`: string (e.g., "LOW", "MEDIUM", "HIGH")
     - `confidence`: string (e.g., "LOW", "MEDIUM", "HIGH") — optional, may be set by confidence engine
     - `latitude`: number (float)
     - `longitude`: number (float)
     - `city`: string
     - `locality`: string (optional)
     - `reporter_name`: string (optional)
     - `ip_address`: string (best-effort capture)
     - `ai_metadata`: object (optional extra metadata from AI/interpretation)
     - `status`: string (e.g., "UNDER_OBSERVATION", "CONFIRMED", "RESOLVED")
     - `created_at`: ISO 8601 timestamp string
     - `updated_at`: ISO 8601 timestamp string

2. `issues` (aggregated clusters shown on the map)
   - Document ID: stable cluster id (e.g., `issue-<type>-<num>`). You may generate as `<primaryReportId>-<count>` or use Firestore auto-id.
   - Fields:
     - `title`: string
     - `description`: string (summary or latest report text)
     - `issue_type`: string
     - `severity`: string (aggregate / highest severity)
     - `confidence`: string (aggregated confidence)
     - `latitude`: number (centroid latitude)
     - `longitude`: number (centroid longitude)
     - `city`: string
     - `report_count`: integer
     - `report_ids`: array of string references (report document IDs)
     - `created_at`: ISO 8601 timestamp (first report time)
     - `updated_at`: ISO 8601 timestamp (most recent report time or last operator update)
     - `status`: string
     - `operatorNotes`: array of objects or string (notes from operators)
     - `timeline`: array of timeline objects OR keep `timeline` as a subcollection (see below)

   - Example `timeline` entry (embedded array)
     - `id`: string
     - `timestamp`: ISO 8601
     - `time`: human-friendly time string
     - `confidence`: string
     - `description`: string

   - Alternative: `issues/{issueId}/timeline` subcollection with documents having the same fields. Use subcollection when timelines can grow large.

3. `cities` (optional)
   - Document per city that needs additional metadata (bounds, center, slug)
   - Fields: `name`, `slug`, `center_lat`, `center_lng`, `bounds` (optional)

4. `operators` (optional admin users)
   - `email`, `name`, `role`, `last_active` etc.

Indexes
-------
- Index `reports` by `city` and `created_at` for range queries.
- Index `issues` by `city`, `updated_at`, and `confidence` if you plan to sort/filter on them.

Data access patterns
--------------------
- Frontend `/map/issues?city=<City>` expects a list of aggregated issues with the following shape (see `db_seed.json` for an exact example):
  - `id`, `title`, `description`, `issue_type`, `severity`, `confidence`, `status`, `latitude`, `longitude`, `report_count`, `created_at`, `updated_at`, `timeline`, `operatorNotes`
- Backend clustering logic reads recent `reports` for the city, groups them (e.g., within 500m and 30 minutes), and writes/updates an `issue` document.
- Keep canonical raw reports in `reports`; `issues` is derived and contains references to reports for traceability.

Safety and privacy
------------------
- `ip_address` and `reporter_name` are optional and sensitive; ensure your deployment environment protects access to Firestore rules and that secrets are not committed.

Seeding and migration
---------------------
- Use the provided `scripts/seed_db.py` to load the `db_seed.json` into either the mock JSON DB or the configured Firestore (depending on `USE_MOCK_DB` and `FIREBASE_CREDENTIALS_PATH`).

