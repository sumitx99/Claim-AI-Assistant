import os
import pandas as pd
from faker import Faker
import random
import uuid
from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, Integer, String, Float, Date
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

print("=== DATABASE SEEDING SCRIPT STARTED ===")

# --- 1. DATABASE CONNECTION SETUP ---
# Load environment variables from .env file in the backend folder
dotenv_path = os.path.join(os.path.dirname(__file__), 'backend', '.env')
load_dotenv(dotenv_path=dotenv_path)

SQLALCHEMY_DATABASE_URL = r"postgresql://postgres:sumit12$@localhost/claims_db"
if not SQLALCHEMY_DATABASE_URL:
    raise ValueError("DATABASE_URL not found in .env file. Please check the path and content.")

print("Connecting to the database...")
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- 2. DEFINE THE TABLE SCHEMA (must match models.py) ---
# We define it here so the script is self-contained
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

# --- 3. DATA GENERATION LOGIC (Same as before) ---
class ClaimsDataGenerator:
    def __init__(self):
        self.fake = Faker()
        self.claim_types = [
            'Auto Accident', 'Medical', 'Property Damage', 'Theft', 'Fire Damage',
            'Water Damage', 'Vandalism', 'Natural Disaster', 'Personal Injury'
        ]
        self.claim_statuses = ['Pending', 'Approved', 'Denied', 'Settled', 'Closed']
        self.diagnosis_codes = ['M79.3', 'S72.001A', 'G93.1', 'M25.511', 'S06.0X0A']

    def generate_claim_record(self):
        claim_date = self.fake.date_between(start_date='-2y', end_date='today')
        claim_amount = round(random.uniform(100, 50000), 2)
        claim_status = random.choice(self.claim_statuses)
        settlement_amount = 0.0
        if claim_status in ['Approved', 'Settled', 'Closed']:
            settlement_amount = round(random.uniform(claim_amount * 0.6, claim_amount), 2)
        
        return {
            'claim_id': f"CLM-{uuid.uuid4().hex[:8].upper()}",
            'policy_number': f"POL-{random.randint(100000, 999999)}",
            'claim_date': claim_date, # Keep as datetime object for direct insertion
            'claim_amount': claim_amount,
            'claim_status': claim_status,
            'claim_type': random.choice(self.claim_types),
            'settlement_amount': settlement_amount,
            'processing_days': random.randint(5, 120),
            'diagnosis_code': random.choice(self.diagnosis_codes) if random.random() < 0.3 else None,
            'provider_id': f"PRV-{random.randint(1000, 9999)}"
        }

    def generate_claims_data(self, num_records=100000): # Reduced for faster testing
        print(f"Generating {num_records:,} claim records in memory...")
        return [self.generate_claim_record() for _ in range(num_records)]

# --- 4. DATA INSERTION FUNCTION ---
def insert_data_to_db(db_session, claims_data):
    """Inserts a list of claim dictionaries into the database using bulk_insert_mappings."""
    total_records = len(claims_data)
    print(f"Preparing to insert {total_records:,} records into the database...")
    
    try:
        # Use bulk_insert_mappings for efficiency
        db_session.bulk_insert_mappings(Claim, claims_data)
        db_session.commit()
        print(f"Successfully inserted {total_records:,} records.")
    except Exception as e:
        print(f"An error occurred during insertion: {e}")
        db_session.rollback()
    finally:
        db_session.close()

def main():
    """Main function to generate and directly insert insurance claims data."""
    
    # Create the table if it doesn't exist
    print("Ensuring 'claims' table exists...")
    Base.metadata.create_all(bind=engine)
    
    # Get a database session
    db = SessionLocal()

    # Clear existing data to avoid duplicates on re-run (optional)
    print("Clearing any existing data from the 'claims' table...")
    db.query(Claim).delete()
    db.commit()

    # Generate the data
    generator = ClaimsDataGenerator()
    # Let's start with 100,000 records for a faster seed. You can change this to 1,000,000.
    claims_to_insert = generator.generate_claims_data(num_records=100000) 
    
    # Insert the data
    insert_data_to_db(db, claims_to_insert)
    
    print("\n=== DATABASE SEEDING SCRIPT FINISHED SUCCESSFULLY! ===")
    print("Your database is now ready with test data.")

if __name__ == "__main__":
    main()