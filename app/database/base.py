"""
Database base class and metadata.
Single source of truth for all model metadata.
"""
from sqlalchemy.orm import declarative_base

# Single declarative base for all models
Base = declarative_base()