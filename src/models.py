from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base
import datetime

class ActionLog(Base):
    __tablename__ = "action_logs"

    id = Column(Integer, primary_key=True, index=True)
    action_type = Column(String, index=True)
    details = Column(String)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    result_url = Column(String, nullable=True) # To store the URL for verification

class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(String)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    summary_comment = Column(String, nullable=True)

class Comment(Base):
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True, index=True)
    post_url = Column(String)
    content = Column(String)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

class Invitation(Base):
    __tablename__ = "invitations"

    id = Column(Integer, primary_key=True, index=True)
    profile_url = Column(String)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

class Token(Base):
    __tablename__ = "tokens"

    id = Column(Integer, primary_key=True, index=True)
    access_token = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class TranslatedPost(Base):
    __tablename__ = "translated_posts"

    id = Column(Integer, primary_key=True, index=True)
    original_post_url = Column(String, unique=True, index=True, nullable=False)
    original_content = Column(String)
    translated_content = Column(String)
    original_author = Column(String)
    image_url = Column(String, nullable=True)
    status = Column(String, default="pending")  # pending, approved, posted, rejected
    posted_at = Column(DateTime, default=datetime.datetime.utcnow)
    our_post_url = Column(String, nullable=True)
