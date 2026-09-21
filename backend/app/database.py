from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import settings


# SQLite needs this setting so more than one request can use the database
connection_options = {}

if settings.database_url.startswith("sqlite"):
    connection_options["check_same_thread"] = False


# Connect to the SQLite database file
database_engine = create_engine(
    settings.database_url,
    connect_args=connection_options,
)

DatabaseSession = sessionmaker(
    bind=database_engine,
    autoflush=False,
    autocommit=False,
)


class Base(DeclarativeBase):
    pass


# Open a database session for one request and always close it afterwards
def get_database_session():
    database = DatabaseSession()

    try:
        yield database
    finally:
        database.close()


# Create the accounts and check-ins tables if they do not exist yet
def create_database_tables():
    # The tables are only known once the database models are imported
    from . import db_models

    Base.metadata.create_all(bind=database_engine)
