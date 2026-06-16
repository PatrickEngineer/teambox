import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.api import auth
from app.api import comments as comments_router
from app.api import files as files_router
from app.api import projects as projects_router
from app.api import tasks as tasks_router
from app.core.logging_config import logger
from app.database import Base, engine, SessionLocal
from app.models import users, projects, project_members, tasks, comments, files, refresh_token
from app.services.user_service import create_super_admin

os.makedirs("uploads", exist_ok=True)
os.makedirs("logs", exist_ok=True)

logger.info("Starting TeamBox application...")

Base.metadata.create_all(bind=engine)
logger.info("Database tables created/verified")

limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="TeamBox")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


def init_super_admin():
    db = SessionLocal()
    try:
        from app.models.users import User
        existing = db.query(User).filter(User.role == "super_admin").first()
        if not existing:
            logger.info("Creating default super_admin...")
            create_super_admin(
                db,
                username="admin",
                email="admin@teambox.com",
                password="Admin123!"
            )
            logger.info("Super_admin created: username=admin, password=Admin123!")
        else:
            logger.info(f"Super_admin already exists: {existing.username}")
    except Exception as e:
        logger.error(f"Error creating super_admin: {e}")
    finally:
        db.close()


init_super_admin()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(projects_router.router)
app.include_router(tasks_router.router)
app.include_router(comments_router.router)
app.include_router(files_router.router)

logger.info("All routers registered")


@app.get("/")
def root():
    logger.debug("Root endpoint called")
    return {"message": "TeamBox работает"}