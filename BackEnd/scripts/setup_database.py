import os
import sys
from sqlalchemy import text

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.database import Base, get_engine


def setup_database():
    """Creates all database tables.

    Run this script once during initial deployment, or re-run it after schema changes.
    """
    engine = get_engine()
    print("Connecting to database...")
    Base.metadata.create_all(bind=engine)
    print("Tables created successfully: image_metadata, cluster_results")


if __name__ == "__main__":
    setup_database()
