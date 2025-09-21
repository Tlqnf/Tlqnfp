from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

Base = declarative_base() # Moved to top

@event.listens_for(Engine, "connect")
def set_timezone(dbapi_connection, connection_record):
    """Force timezone to be 'Asia/Seoul' for every connection."""
    cursor = dbapi_connection.cursor()
    cursor.execute("SET TIME ZONE 'Asia/Seoul'")
    cursor.close()

# PostgreSQL 연결 예시
DB_USER = os.getenv("POSTGRES_USER", "postgres")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "password")
DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = os.getenv("POSTGRES_PORT", "5123")
DB_NAME = os.getenv("POSTGRES_DB", "fitness_db")

DATABASE_URL = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_engine(
    DATABASE_URL, 
    pool_pre_ping=True,
    pool_size=20,
    max_overflow=10
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Function to initialize the database (create tables)
def init_db():
    # Import all models here to ensure they are registered with Base.metadata
    import models.user
    import models.community
    import models.report
    import models.route
    import models.image
    Base.metadata.create_all(bind=engine)
