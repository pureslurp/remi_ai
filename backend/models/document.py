from sqlalchemy import Column, String, Text, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from uuid import uuid4
from database import Base


class Document(Base):
    __tablename__ = "documents"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    filename = Column(String, nullable=False)
    source = Column(String, nullable=False)  # "upload" | "drive" | "gmail"
    drive_file_id = Column(String)
    gmail_message_id = Column(String)
    mime_type = Column(String)
    size_bytes = Column(Integer)
    file_hash = Column(String)  # SHA256 for dedup
    storage_object_key = Column(String)  # Supabase Storage path when using cloud files
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="documents")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan",
                          order_by="DocumentChunk.chunk_index")


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    document_id = Column(String, ForeignKey("documents.id"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    text = Column(Text, nullable=False)
    token_count = Column(Integer)

    document = relationship("Document", back_populates="chunks")
