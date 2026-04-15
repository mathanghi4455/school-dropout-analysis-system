import os
import random
import numpy as np
from pymongo import MongoClient
import json
from datetime import datetime

def generate_and_load_data():
    print("Generating Award-Winning Mock Dataset...")
    
    np.random.seed(42)
    random.seed(42)
    
    states = ["Maharashtra", "Uttar Pradesh", "Bihar", "Tamil Nadu", "Karnataka", "Kerala", "Rajasthan", "Gujarat"]
    districts_per_state = 5
    
    data = []
    
    for state in states:
        for d in range(districts_per_state):
            district = f"{state}_Dist_{d+1}"
            
            socioeconomic_score = np.random.normal(loc=50, scale=15) if state not in ["Bihar", "Uttar Pradesh"] else np.random.normal(loc=35, scale=10)
            infrastructure_score = socioeconomic_score * 0.8 + np.random.normal(loc=10, scale=5)
            infrastructure_score = min(max(infrastructure_score, 0), 100)
            
            base_dropout = 45 - (socioeconomic_score * 0.3) - (infrastructure_score * 0.2)
            base_dropout += np.random.normal(loc=0, scale=3)
            base_dropout = min(max(base_dropout, 2), 40)
            
            primary_dropout = base_dropout * 0.4
            upper_primary_dropout = base_dropout * 0.8
            secondary_dropout = base_dropout * 1.5
            
            male_dropout = secondary_dropout * (1 - (50 - socioeconomic_score)/200)
            female_dropout = secondary_dropout * (1 + (50 - socioeconomic_score)/100)
            
            for year in range(2019, 2024):
                yoy_improvement_factor = 1 - ((year - 2019) * 0.05)
                
                doc = {
                    "year": year,
                    "state": state,
                    "district": district,
                    "socioeconomic_score": round(socioeconomic_score, 2),
                    "infrastructure_score": round(infrastructure_score, 2),
                    "dropout_rates": {
                        "primary": round(primary_dropout * yoy_improvement_factor, 2),
                        "upper_primary": round(upper_primary_dropout * yoy_improvement_factor, 2),
                        "secondary": round(secondary_dropout * yoy_improvement_factor, 2)
                    },
                    "gender_rates": {
                        "male_secondary": round(male_dropout * yoy_improvement_factor, 2),
                        "female_secondary": round(female_dropout * yoy_improvement_factor, 2)
                    }
                }
                data.append(doc)
                
    try:
        client = MongoClient('localhost', 27017, serverSelectionTimeoutMS=2000)
        client.drop_database('school_dropout_db') 
        db = client['school_dropout_db']
        collection = db['education_data']
        collection.insert_many(data)
        print(f"Successfully generated and inserted {len(data)} records into MongoDB.")
    except Exception as e:
        print("MongoDB connection failed! Saving offline fallback to 'offline_db.json' instead...")
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'offline_db.json'), 'w') as f:
            json.dump(data, f)
        print("Offline dataset created (`offline_db.json`).")

if __name__ == '__main__':
    generate_and_load_data()
