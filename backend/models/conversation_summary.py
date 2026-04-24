from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


class ProjectConversationSummary(Base):
    """Rolling summary of chat messages not in the live N-message window sent to the model."""

    __tablename__ = "project_conversation_summaries"

    project_id = Column(String, ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True)
    summary_text = Column(Text, nullable=False, default="")
    # When set, matches id of the last message that is fully represented by summary_text (oldest in live window - 1)
    covered_message_id = Column(String, ForeignKey("chat_messages.id", ondelete="SET NULL"), nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = relationship("Project", back_populates="conversation_summary_row", uselist=False)
