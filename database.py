from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import DeclarativeBase, relationship
from datetime import datetime, timezone
import os
from dotenv import load_dotenv


load_dotenv()

DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT')
DB_NAME = os.getenv('DB_NAME')

DATABASE_URL = os.getenv('DATABASE_URL')

if not DATABASE_URL:
    DB_USER = os.getenv('DB_USER')
    DB_PASSWORD = os.getenv('DB_PASSWORD')
    DB_HOST = os.getenv('DB_HOST')
    DB_PORT = os.getenv('DB_PORT')
    DB_NAME = os.getenv('DB_NAME')
    DATABASE_URL = f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'

DATABASE_URL = f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'

engine = create_engine(DATABASE_URL)


class Base(DeclarativeBase):
    pass


class Link(Base):
    __tablename__ = 'links'
    id = Column(Integer, primary_key=True)
    long_url = Column(String, nullable=False)
    short_url = Column(String, unique=True, nullable=False)
    create_dttm = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    clicks_num = Column(Integer, default=0, nullable=False)
    last_click_dttm = Column(DateTime(timezone=True))
    expires_at = Column(DateTime(timezone=True))
    owner_id = Column(Integer, ForeignKey('users.id'))

    owner = relationship('User', back_populates='links')


class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    login = Column(String, unique=True, nullable=False)
    password = Column(String, unique=True, nullable=False)

    links = relationship('Link', back_populates='owner')
    expired_links = relationship('ExpiredLink', back_populates='owner2')


class ExpiredLink(Base):
    __tablename__ = 'expired_links'
    id = Column(Integer, primary_key=True)
    long_url = Column(String, nullable=False)
    short_url = Column(String, nullable=False)
    create_dttm = Column(DateTime(timezone=True), nullable=False)
    clicks_num = Column(Integer, nullable=False)
    last_click_dttm = Column(DateTime(timezone=True))
    expired_at = Column(DateTime(timezone=True), nullable=False)
    owner_id = Column(Integer, ForeignKey('users.id'))

    owner2 = relationship('User', back_populates='expired_links')


Base.metadata.create_all(engine)
