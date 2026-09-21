from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import create_database_tables
from .routers import account_routes, checkin_routes


@asynccontextmanager
# Create the database tables when the backend starts
async def lifespan(_: FastAPI):
    create_database_tables()
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    lifespan=lifespan,
)


# Allow the React frontend on port 5173 to call the backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Add the account routes and the check-in routes
app.include_router(account_routes.router)
app.include_router(checkin_routes.router)
