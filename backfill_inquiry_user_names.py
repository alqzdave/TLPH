"""Backfill inquiry user_name from users.firstName + users.lastName.

Usage:
  python backfill_inquiry_user_names.py --dry-run
  python backfill_inquiry_user_names.py --apply
"""

from __future__ import annotations

import argparse
from typing import Dict

from firebase_config import get_firestore_db


ADMIN_ROLES = {
    "superadmin",
    "super-admin",
    "municipal",
    "municipal_admin",
    "regional",
    "regional_admin",
    "national",
    "national_admin",
}


def looks_like_email(value: str) -> bool:
    text = str(value or "").strip()
    return "@" in text and "." in text


def extract_full_name(user: dict) -> str:
    first_name = str(user.get("firstName") or user.get("first_name") or "").strip()
    last_name = str(user.get("lastName") or user.get("last_name") or "").strip()
    full_name = f"{first_name} {last_name}".strip()
    if full_name:
        return full_name

    # Fallbacks keep the script useful for mixed legacy user docs.
    return str(user.get("name") or user.get("displayName") or user.get("username") or "").strip()


def build_user_indexes() -> tuple[Dict[str, str], Dict[str, str]]:
    db = get_firestore_db()
    by_doc_id: Dict[str, str] = {}
    by_email: Dict[str, str] = {}

    for doc in db.collection("users").stream():
        data = doc.to_dict() or {}
        full_name = extract_full_name(data)
        if not full_name:
            continue

        by_doc_id[str(doc.id).strip()] = full_name
        email = str(data.get("email") or "").strip().lower()
        if email:
            by_email[email] = full_name

    return by_doc_id, by_email


def resolve_name(inquiry: dict, by_doc_id: Dict[str, str], by_email: Dict[str, str]) -> str:
    user_id = str(inquiry.get("user_id") or "").strip()
    email = str(inquiry.get("email") or inquiry.get("user_email") or "").strip().lower()

    if user_id and "@" not in user_id and user_id in by_doc_id:
        return by_doc_id[user_id]

    if email and email in by_email:
        return by_email[email]

    if user_id and "@" in user_id and user_id.lower() in by_email:
        return by_email[user_id.lower()]

    return ""


def should_skip_as_admin(inquiry: dict) -> bool:
    sender_role = str(inquiry.get("sender_role") or "").strip().lower()
    return bool(inquiry.get("is_admin")) or sender_role in ADMIN_ROLES


def backfill(apply_updates: bool = False, limit: int = 0) -> None:
    db = get_firestore_db()
    by_doc_id, by_email = build_user_indexes()

    print(f"Loaded {len(by_doc_id)} named user docs and {len(by_email)} email mappings")

    processed = 0
    candidates = 0
    updated = 0

    for doc in db.collection("inquiries").stream():
        data = doc.to_dict() or {}
        processed += 1

        if should_skip_as_admin(data):
            continue

        current_name = str(data.get("user_name") or "").strip()
        if current_name and not looks_like_email(current_name):
            continue

        resolved = resolve_name(data, by_doc_id, by_email)
        if not resolved:
            continue

        candidates += 1
        print(f"[{doc.id}] {current_name or '<empty>'} -> {resolved}")

        if apply_updates:
            doc.reference.update({"user_name": resolved})
            updated += 1

        if limit > 0 and candidates >= limit:
            print(f"Reached limit={limit}, stopping early")
            break

    print("--- Summary ---")
    print(f"Processed inquiries: {processed}")
    print(f"Matched candidates: {candidates}")
    print(f"Updated documents: {updated}")
    print("Mode: APPLY" if apply_updates else "Mode: DRY-RUN")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backfill inquiry user_name using users collection")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--apply", action="store_true", help="Write updates to Firestore")
    mode.add_argument("--dry-run", action="store_true", help="Preview updates without writing")
    parser.add_argument("--limit", type=int, default=0, help="Max matched documents to process (0 = no limit)")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    apply_mode = bool(args.apply)
    backfill(apply_updates=apply_mode, limit=max(0, int(args.limit or 0)))
