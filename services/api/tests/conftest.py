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

from app.db import engine  # noqa: E402
from app.documents.service import init_db  # noqa: E402

init_db()  # the app's own startup: creates tables, then adds any newer columns


@pytest.fixture(autouse=True)
def empty_tables():
    yield
    with engine.begin() as connection:
        connection.execute(
            text("TRUNCATE documents, sections, segments, personas, render_jobs, chapter_audio RESTART IDENTITY CASCADE")
        )
