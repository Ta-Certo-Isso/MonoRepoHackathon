from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from src.core.database import Base

class DBProposition(Base):
    __tablename__ = "propositions"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(Text, nullable=True)
    content = Column(Text, nullable=True)
    link = Column(String, nullable=True)
    date = Column(String, nullable=True)
    source = Column(String)
    level = Column(String)
    collection_type = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

    scripts = relationship("DBScript", back_populates="proposition")

class DBScript(Base):
    __tablename__ = "scripts"

    id = Column(Integer, primary_key=True, index=True)
    proposition_id = Column(Integer, ForeignKey("propositions.id"))
    content = Column(Text)
    style = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

    proposition = relationship("DBProposition", back_populates="scripts")
    videos = relationship("DBVideo", back_populates="script")

class DBVideo(Base):
    __tablename__ = "videos"

    id = Column(Integer, primary_key=True, index=True)
    script_id = Column(Integer, ForeignKey("scripts.id"))
    url = Column(String)
    local_path = Column(String, nullable=True)
    status = Column(String) # 'pending', 'completed', 'failed'
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    script = relationship("DBScript", back_populates="videos")
