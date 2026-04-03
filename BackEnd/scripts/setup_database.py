import os
import sys
from sqlalchemy import text

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.database import Base, get_engine


def setup_database():
    """Creates all database tables and configures Row Level Security (RLS).

    Run this script once during initial deployment, or re-run it after schema changes.
    Note: CREATE POLICY is idempotent in PostgreSQL 9.5+ when using IF NOT EXISTS.
    """
    engine = get_engine()
    print("Connecting to database...")
    Base.metadata.create_all(bind=engine)
    print("Tables created successfully: image_metadata, cluster_results")

    # ── Row Level Security ───────────────────────────────────────────────────
    # RLS ensures users can only read/write their own rows at the database level,
    # independent of application logic. The application must set the
    # app.current_user_id session variable before issuing any query
    # (see services/database.py set_rls_user), otherwise RLS will block all access.
    print("Enabling Row Level Security...")
    with engine.connect() as conn:
        conn.execute(text("ALTER TABLE image_metadata ENABLE ROW LEVEL SECURITY;"))
        conn.execute(text("ALTER TABLE cluster_results ENABLE ROW LEVEL SECURITY;"))

        # current_setting('app.current_user_id', true) is set per-connection by the
        # set_rls_user() context manager. The 'true' (missing_ok) flag prevents an
        # error if the variable is not set — the policy will simply evaluate to NULL
        # and block access, which is the safe/secure default behaviour.
        conn.execute(text("""
            CREATE POLICY IF NOT EXISTS user_isolation ON image_metadata
                USING (user_id = current_setting('app.current_user_id', true));
        """))
        conn.execute(text("""
            CREATE POLICY IF NOT EXISTS user_isolation ON cluster_results
                USING (user_id = current_setting('app.current_user_id', true));
        """))
        conn.commit()

    print("Row Level Security enabled on image_metadata and cluster_results.")


if __name__ == "__main__":
    setup_database()
