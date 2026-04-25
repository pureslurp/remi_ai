from sqlalchemy import Column, String, Text, Float, Integer, ForeignKey
from sqlalchemy.orm import relationship
from uuid import uuid4
from database import Base


class Property(Base):
    __tablename__ = "properties"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    address = Column(String, nullable=False)
    city = Column(String)
    state = Column(String, default="MI")
    zip_code = Column(String)
    mls_number = Column(String)
    list_price = Column(Float)
    beds = Column(Integer)
    baths = Column(Float)
    sqft = Column(Integer)
    status = Column(String, default="active")  # active|pending|contingent|closed|dead
    notes = Column(Text)
    reapi_property_id = Column(String, nullable=True)  # RealEstateAPI / vendor property id

    project = relationship("Project", back_populates="properties", foreign_keys="[Property.project_id]")
    transactions = relationship("Transaction", back_populates="property", cascade="all, delete-orphan")
