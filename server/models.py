"""数据模型"""
from sqlalchemy import create_engine, Column, Integer, String, Boolean, Text, DateTime
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from datetime import datetime, timezone, timedelta

DB_URL = "sqlite:///data.db"
engine = create_engine(DB_URL, connect_args={"check_same_thread": False}, echo=False)
SessionLocal = sessionmaker(bind=engine, autoflush=False)

class Base(DeclarativeBase):
    pass

def tz_now():
    return datetime.now(timezone(timedelta(hours=8)))

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(32), unique=True, nullable=False, index=True)
    password_hash = Column(String(128), nullable=False)
    nickname = Column(String(32), default="")
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=tz_now)

class Bill(Base):
    __tablename__ = "bills"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    type = Column(String(10), nullable=False)           # expense / income
    amount = Column(Integer, nullable=False)             # 单位：分
    category = Column(String(20), nullable=False)
    note = Column(Text, default="")
    date = Column(String(10), nullable=False)            # YYYY-MM-DD
    created_at = Column(DateTime, default=tz_now)

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
