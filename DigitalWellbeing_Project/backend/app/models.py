from sqlalchemy import Column, Integer, String, DateTime, func
from .database import Base
# models/__init__.py or models/base.py
from .user import User
from .session import Session
from .app_usage import AppUsage
# Import all your other models here
# At the top of env.py, add:
import sys
import os
from pathlib import Path

# Add your project root to Python path
from backend.app.models import project_root
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# Import your models
from models import *  # This imports all your models
from database import Base  # Import your SQLAlchemy Base

# Set target_metadata (this line should already exist, just modify it)
target_metadata = Base.metadata
# This makes all models available when this module is imported

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
