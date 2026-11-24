"""
Neon PostgreSQL Verification & Diagnostic Script for Sky Reader.
Usage:
    python backend/test_neon.py
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Ensure backend can be imported
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

# Load .env if present
load_dotenv(ROOT_DIR / ".env")
load_dotenv(ROOT_DIR / "backend" / ".env")

from backend.database import (
    get_neon_url,
    PSYCOPG2_AVAILABLE,
    get_db_connection,
    init_db,
    create_user,
    authenticate_user,
    create_session,
    get_user_by_session_token,
    delete_session,
    PostgresConnectionWrapper
)

def run_diagnostic():
    print("=" * 60)
    print(" SKY READER - DATABASE CONNECTION DIAGNOSTIC")
    print("=" * 60)
    
    neon_url = get_neon_url()
    print(f"psycopg2 installed: {PSYCOPG2_AVAILABLE}")
    
    if not PSYCOPG2_AVAILABLE:
        print("[!] Warning: psycopg2 is not installed in the active environment.")
        print("    Install it via: pip install psycopg2-binary")
    
    if neon_url:
        masked_url = neon_url
        if "@" in masked_url:
            prefix, host = masked_url.split("@", 1)
            masked_url = prefix[:prefix.find("://") + 3] + "****:****@" + host
        print(f"Neon PostgreSQL URL detected: {masked_url}")
    else:
        print("No NEON_DATABASE_URL or DATABASE_URL detected in environment.")
        print("--> System running in local SQLite fallback mode (skyreader.db)")

    print("\nTesting database connection...")
    try:
        conn = get_db_connection()
        is_pg = isinstance(conn, PostgresConnectionWrapper)
        engine_name = "Neon Serverless PostgreSQL" if is_pg else "SQLite"
        print(f"[OK] Successfully connected to: {engine_name}")
        
        print("\nInitializing database schemas...")
        init_db()
        print("[OK] Schemas verified (users, sessions, guest_sessions, conversation_threads).")
        
        # Test basic CRUD flow with temporary diagnostic user
        test_email = "diag_test_neon@skyreader.internal"
        test_pass = "TestNeonSecure!2026"
        test_name = "Neon Test Agent"
        
        print(f"\nTesting Auth Cycle on {engine_name}...")
        
        # 1. Clean up if leftover from previous test
        with conn:
            conn.execute("DELETE FROM users WHERE LOWER(email) = ?", (test_email,))
        
        # 2. Create user
        user = create_user(test_email, test_pass, test_name)
        print(f"[OK] User created with ID: {user['id']}")
        
        # 3. Authenticate
        auth_user = authenticate_user(test_email, test_pass)
        assert auth_user is not None, "Authentication failed!"
        print(f"[OK] User successfully authenticated: {auth_user['name']} ({auth_user['email']})")
        
        # 4. Create Session
        token = create_session(user["id"], duration_days=7)
        print(f"[OK] Session token issued: {token[:12]}...")
        
        # 5. Fetch User by Session Token
        session_user = get_user_by_session_token(token)
        assert session_user is not None, "Session verification failed!"
        print(f"[OK] Session validated for user: {session_user['email']}")
        
        # 6. Delete Session & Clean up
        delete_session(token)
        with conn:
            conn.execute("DELETE FROM users WHERE LOWER(email) = ?", (test_email,))
        print("[OK] Session deleted & diagnostic test user purged.")
        
        print("\n" + "=" * 60)
        print(f" RESULT: {engine_name} IS FULLY OPERATIONAL AND VERIFIED!")
        print("=" * 60)
        
    except Exception as exc:
        print(f"\n[X] Database diagnostic encountered an error: {exc}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    run_diagnostic()
