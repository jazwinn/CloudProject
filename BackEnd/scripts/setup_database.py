import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.database import Base, get_engine

def setup_database():
    """Creates all database tables defined in the SQLAlchemy models."""
    engine = get_engine()
    print(f"Connecting to database...")
    Base.metadata.create_all(bind=engine)
    print("Tables created successfully: image_metadata, cluster_results")

if __name__ == "__main__":
    setup_database()
