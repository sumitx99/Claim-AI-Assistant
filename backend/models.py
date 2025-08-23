from sqlalchemy import Column, Integer, String, Float, Date
# Use absolute import from the 'backend' package
from backend.database import Base

class Claim(Base):
    __tablename__ = "claims"

    claim_id = Column(String, primary_key=True, index=True)
    policy_number = Column(String, index=True)
    claim_date = Column(Date)
    claim_amount = Column(Float)
    claim_status = Column(String, index=True)
    claim_type = Column(String, index=True)
    settlement_amount = Column(Float)
    processing_days = Column(Integer)
    diagnosis_code = Column(String)
    provider_id = Column(String)