"""
database.py
===========
Configuración de la base de datos SQLite con SQLAlchemy.
Para migrar a PostgreSQL en producción, solo cambia DATABASE_URL:
  DATABASE_URL = "postgresql://usuario:password@localhost/horarios_db"
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# URL de la base de datos — SQLite local para el MVP
DATABASE_URL = "sqlite:///./horarios.db"

# connect_args es necesario solo para SQLite (permite uso en múltiples threads)
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

# Fábrica de sesiones: cada request obtiene su propia sesión
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base para los modelos ORM
Base = declarative_base()


def get_db():
    """
    Dependencia de FastAPI que provee una sesión de BD por request.
    Se cierra automáticamente al terminar el request (patrón context manager).
    
    Ampliación futura: con PostgreSQL y múltiples workers, 
    considerar connection pooling con PgBouncer.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
