from sqlalchemy import create_engine, Column, String, Float, Integer, Text, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session
from contextlib import contextmanager
from config import get_settings

class Base(DeclarativeBase):
    pass

class ImageMetadata(Base):
    __tablename__ = "image_metadata"

    image_id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False, index=True)
    uploaded_at = Column(String, nullable=False)
    date_taken = Column(String, nullable=True)
    gps_lat = Column(Float, nullable=True)
    gps_lon = Column(Float, nullable=True)
    thumbnail_key = Column(String, nullable=True)
    # Tracks processing state: 'pending' (set at upload time) → 'processed' (set by image_processor Lambda)
    status = Column(String, nullable=False, default='pending')


class ClusterResult(Base):
    __tablename__ = "cluster_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, nullable=False, index=True)
    computed_at = Column(String, nullable=False)
    mode = Column(String, nullable=False)
    result = Column(Text, nullable=False)  # JSON stored as text

_engine = None

def get_engine():
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_engine(settings.DATABASE_URL)
    return _engine

@contextmanager
def get_db() -> Session:
    factory = sessionmaker(bind=get_engine())
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@contextmanager
def set_rls_user(session: Session, user_id: str):
    """Context manager that scopes Row Level Security to the given user for the duration
    of the current transaction.

    Usage:
        with get_db() as session:
            with set_rls_user(session, current_user):
                results = session.query(ImageMetadata).all()

    Mechanism:
        Executes SET LOCAL app.current_user_id = :user_id before yielding.
        SET LOCAL scopes this to the current transaction only — it resets automatically
        on commit/rollback, making it safe in a connection pool environment.

    The PostgreSQL RLS policies on image_metadata and cluster_results check
    current_setting('app.current_user_id', true) to enforce row-level isolation.
    If this context manager is not used, RLS will evaluate the setting as NULL
    and block all access — the safe/secure default.
    """
    session.execute(text("SET LOCAL app.current_user_id = :uid"), {"uid": user_id})
    yield session

