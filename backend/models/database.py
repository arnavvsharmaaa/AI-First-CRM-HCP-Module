import os
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/hcp_crm")

# Hosts like Render hand out postgres:// or postgresql:// URLs — force the asyncpg driver
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = "postgresql+asyncpg://" + DATABASE_URL[len("postgres://"):]
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = "postgresql+asyncpg://" + DATABASE_URL[len("postgresql://"):]

# Neon/Supabase-style URLs carry libpq options (sslmode, channel_binding) that
# asyncpg rejects as unknown keywords. Strip them and pass SSL via connect_args.
_url = make_url(DATABASE_URL)
_sslmode = _url.query.get("sslmode")
_url = _url.difference_update_query(["sslmode", "channel_binding"])
connect_args = {"ssl": "require"} if _sslmode and _sslmode != "disable" else {}

DEBUG = os.getenv("DEBUG", "false").lower() == "true"

engine = create_async_engine(_url, echo=DEBUG, pool_pre_ping=True, connect_args=connect_args)

async_session = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

Base = declarative_base()
