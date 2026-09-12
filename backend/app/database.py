import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Hardcoded for local dev based on docker-compose.
# In production, this would be loaded from a .env file.
SQLALCHEMY_DATABASE_URL = "postgresql://desk_admin:cozy_password_123@localhost:5432/study_desk"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
