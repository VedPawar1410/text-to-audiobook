"""Tests use their own database, created on first run and emptied after every test."""

import os

TEST_DATABASE = "text_to_audiobook_test"
os.environ["DATABASE_URL"] = f"postgresql+psycopg://localhost/{TEST_DATABASE}"  # before app imports

import psycopg  # noqa: E402
import pytest  # noqa: E402
from sqlalchemy import text  # noqa: E402

with psycopg.connect(dbname="postgres", autocommit=True) as connection:
    if not connection.execute("SELECT 1 FROM pg_database WHERE datname = %s", (TEST_DATABASE,)).fetchone():
        connection.execute(f'CREATE DATABASE "{TEST_DATABASE}"')

import app.models  # noqa: E402,F401  (registers the tables)
from app.db import Base, engine  # noqa: E402

Base.metadata.create_all(engine)


@pytest.fixture(autouse=True)
def empty_tables():
    yield
    with engine.begin() as connection:
        connection.execute(
            text("TRUNCATE documents, sections, segments, personas, render_jobs, chapter_audio RESTART IDENTITY CASCADE")
        )
