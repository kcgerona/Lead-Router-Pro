#!/usr/bin/env python3
"""
Test assigned_to_history with mock data.

Run from project root:
  ./run_test_assigned_to_history.sh   # uses .venv if present
  # or with venv:
  .venv/bin/python test_assigned_to_history.py
  # or system (requires: pip install sqlalchemy):
  python3 test_assigned_to_history.py
"""

import sys
import logging
import json

# Ensure project root is on path
sys.path.insert(0, ".")

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# Mock data
MOCK_CONTACT_ID = "mock_contact_test_001"
MOCK_USER_1 = "mock_ghl_user_aaa"
MOCK_USER_2 = "mock_ghl_user_bbb"
MOCK_LEAD_ID = "mock_lead_001"
MOCK_OPP_ID = "mock_opp_001"


def query_history(ghl_contact_id: str):
    """Read rows from assigned_to_histories for a contact."""
    from database.simple_connection import db as simple_db_instance

    conn = simple_db_instance._get_raw_conn()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, ghl_contact_id, ghl_user_id, assigned_at, status, service_details
            FROM assigned_to_histories
            WHERE ghl_contact_id = ?
            ORDER BY assigned_at
            """,
            (ghl_contact_id,),
        )
        rows = cursor.fetchall()
        return [
            {
                "id": r[0],
                "ghl_contact_id": r[1],
                "ghl_user_id": r[2],
                "assigned_at": r[3],
                "status": r[4],
                "service_details": json.loads(r[5]) if r[5] else None,
            }
            for r in rows
        ]
    finally:
        conn.close()


def delete_test_history(ghl_contact_id: str):
    """Remove test rows for a contact."""
    from database.simple_connection import db as simple_db_instance

    conn = simple_db_instance._get_raw_conn()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM assigned_to_histories WHERE ghl_contact_id = ?", (ghl_contact_id,))
        conn.commit()
        return cursor.rowcount
    finally:
        conn.close()


def run_tests():
    from api.services.assigned_to_history import record_assigned_to_change
    from database.simple_connection import db as simple_db_instance

    print("\n" + "=" * 60)
    print("Testing assigned_to_history with mock data")
    print("=" * 60)

    # Clean any previous test data
    deleted = delete_test_history(MOCK_CONTACT_ID)
    if deleted:
        print(f"Cleaned {deleted} existing test row(s) for {MOCK_CONTACT_ID}")

    # --- Test 1: record_assigned_to_change — first assignment (no previous) ---
    print("\n--- Test 1: First assignment (previous=None) ---")
    rid1 = record_assigned_to_change(
        ghl_contact_id=MOCK_CONTACT_ID,
        new_ghl_user_id=MOCK_USER_1,
        previous_ghl_user_id=None,
        service_details={"source": "test", "scenario": "first_assignment"},
    )
    assert rid1 is not None, "First assignment should return history id"
    print(f"  record_assigned_to_change returned id: {rid1}")

    # --- Test 2: record_assigned_to_change — no change (same user) ---
    print("\n--- Test 2: No change (same user) ---")
    rid2 = record_assigned_to_change(
        ghl_contact_id=MOCK_CONTACT_ID,
        new_ghl_user_id=MOCK_USER_1,
        previous_ghl_user_id=MOCK_USER_1,
        service_details={"source": "test"},
    )
    assert rid2 is None, "Same user should skip and return None"
    print("  record_assigned_to_change returned None (correct)")

    # --- Test 3: record_assigned_to_change — reassignment ---
    print("\n--- Test 3: Reassignment (user1 -> user2) ---")
    rid3 = record_assigned_to_change(
        ghl_contact_id=MOCK_CONTACT_ID,
        new_ghl_user_id=MOCK_USER_2,
        previous_ghl_user_id=MOCK_USER_1,
        service_details={"source": "test", "scenario": "reassignment"},
    )
    assert rid3 is not None, "Reassignment should return history id"
    print(f"  record_assigned_to_change returned id: {rid3}")

    # --- Test 4: record_assigned_to_history direct (with lead_id, opportunity_id) ---
    print("\n--- Test 4: record_assigned_to_history with lead_id & opportunity_id ---")
    rid4 = simple_db_instance.record_assigned_to_history(
        ghl_contact_id=MOCK_CONTACT_ID,
        ghl_user_id=MOCK_USER_1,
        status="approved",
        service_details={"source": "test", "scenario": "direct_call"},
        lead_id=MOCK_LEAD_ID,
        opportunity_id=MOCK_OPP_ID,
    )
    assert rid4 is not None, "Direct record should return history id"
    print(f"  record_assigned_to_history returned id: {rid4}")

    # --- Test 5: record_assigned_to_history — empty ghl_user_id (should return None) ---
    print("\n--- Test 5: Validation — empty ghl_user_id ---")
    rid5 = simple_db_instance.record_assigned_to_history(
        ghl_contact_id=MOCK_CONTACT_ID,
        ghl_user_id="",
        status="approved",
    )
    assert rid5 is None, "Empty ghl_user_id should return None"
    print("  record_assigned_to_history returned None (correct)")

    # --- Verify table contents ---
    print("\n--- Table contents for mock contact ---")
    rows = query_history(MOCK_CONTACT_ID)
    for i, row in enumerate(rows, 1):
        print(f"  Row {i}: {row['ghl_user_id']} @ {row['assigned_at']} status={row['status']}")
        if row.get("service_details"):
            print(f"         service_details: {row['service_details']}")

    assert len(rows) >= 3, f"Expected at least 3 rows, got {len(rows)}"

    # Cleanup
    delete_test_history(MOCK_CONTACT_ID)
    print("\n--- Cleanup: test rows removed ---")
    print("All tests passed.\n")
    return True


if __name__ == "__main__":
    try:
        ok = run_tests()
        sys.exit(0 if ok else 1)
    except Exception as e:
        logger.exception("Test failed: %s", e)
        sys.exit(1)
