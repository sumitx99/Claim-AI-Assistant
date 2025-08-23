import pandas as pd
from faker import Faker
import random
import uuid

class ClaimsDataGenerator:
    def __init__(self):
        self.fake = Faker()
        self.claim_types = ['Auto Accident', 'Medical', 'Property Damage', 'Theft']
        self.claim_statuses = ['Pending', 'Approved', 'Denied', 'Settled']
    def generate_and_save(self, num_records, filename):
        print(f"Generating {num_records:,} records for {filename}...")
        records = []
        for _ in range(num_records):
            claim_date = self.fake.date_between(start_date='-2y', end_date='today')
            claim_amount = round(random.uniform(100, 50000), 2)
            claim_status = random.choice(self.claim_statuses)
            settlement_amount = 0.0
            if claim_status in ['Approved', 'Settled']:
                settlement_amount = round(random.uniform(claim_amount * 0.6, claim_amount), 2)
            records.append({
                'claim_id': f"CLM-{uuid.uuid4().hex[:8].upper()}",
                'policy_number': f"POL-{random.randint(100000, 999999)}",
                'claim_date': claim_date.strftime('%Y-%m-%d'),
                'claim_amount': claim_amount,
                'claim_status': claim_status,
                'claim_type': random.choice(self.claim_types),
                'settlement_amount': settlement_amount,
                'processing_days': random.randint(5, 120),
                'diagnosis_code': '', 'provider_id': f"PRV-{random.randint(1000, 9999)}"
            })
        pd.DataFrame(records).to_csv(filename, index=False)
        print(f"Successfully created {filename}")

def main():
    generator = ClaimsDataGenerator()
    print("Creating sample CSV files for upload...")
    generator.generate_and_save(10000, 'claims_data_part_3.csv')
    generator.generate_and_save(5000, 'claims_data_part_4.csv')
    print("\nSample files are ready.")

if __name__ == "__main__":
    main()