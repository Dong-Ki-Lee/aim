import logging
import os

from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from aim.web.configs import AIM_LOG_LEVEL_KEY
from aim.web.utils import get_db_url

engine = create_engine(
    get_db_url()
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@contextmanager
def get_contexted_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
