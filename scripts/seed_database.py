#!/usr/bin/env python3
"""
IndusPilot — Standalone Database Seeder
Seeds reproducible synthetic demonstration data for Tech4Bharat 2026 Problem 4.1.

Usage:
    python scripts/seed_database.py
    python scripts/seed_database.py --reset
"""

import sys
import os
import argparse

# Configure UTF-8 stdout encoding for Windows
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

# Add backend directory to sys.path
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.database.session import SessionLocal, engine
from app.models.entities import Base
from app.services.seed_data import seed_induspilot_demonstration_data


def main():
    parser = argparse.ArgumentParser(description="IndusPilot Synthetic Demonstration Data Seeder")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Force reset existing records and re-seed clean demonstration state"
    )
    args = parser.parse_args()

    print("=" * 70)
    print("  INDUSPILOT — SYNTHETIC DEMONSTRATION TESTBED SEEDER")
    print("  Theme: Industrial Manufacturing | Problem Statement 4.1")
    print("=" * 70)

    # Ensure tables exist
    print("[*] Verifying database schema...")
    Base.metadata.create_all(bind=engine)

    # Seed
    db = SessionLocal()
    try:
        action_desc = "Force resetting and seeding" if args.reset else "Seeding (preserving if existing)"
        print(f"[*] {action_desc}...")
        result = seed_induspilot_demonstration_data(db, force_reset=args.reset)
        
        print("\n[+] Database Seed Results:")
        print(f"    - Status:             {result.get('status')}")
        print(f"    - Organization ID:    {result.get('organization_id')}")
        if result.get("status") == "SUCCESS":
            print(f"    - Suppliers Seeded:   {result.get('suppliers_count')}")
            print(f"    - Materials Seeded:   {result.get('materials_count')}")
            print(f"    - Product Part ID:    {result.get('product_id')}")
            print(f"    - Quotations Seeded:  {result.get('quotations_seeded')}")
            print(f"    - Negotiation Session:{result.get('negotiation_session_id')}")
            print(f"    - Customer Quote ID:  {result.get('customer_quote_id')}")
            print("\n[✓] Canonical 500 Industrial Brackets demonstration testbed is LIVE!")
        else:
            print("    - Demo dataset already present. Use --reset to re-seed from scratch.")
    except Exception as e:
        print(f"\n[!] Error during database seed: {e}")
        db.rollback()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()

