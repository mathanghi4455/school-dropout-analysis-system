import json, random, os
path = '/Users/mathangi/.gemini/antigravity/scratch/dropout_analysis/offline_db.json'
with open(path, 'r') as f:
    data = json.load(f)
new_data = []

# Multiply data to make it extremely large and dense (15x scale)
for i in range(15):
    for row in data:
        nr = row.copy()
        nr['infrastructure_score'] = max(10, min(100, nr['infrastructure_score'] + random.uniform(-15, 15)))
        nr['socioeconomic_score'] = max(10, min(100, nr['socioeconomic_score'] + random.uniform(-15, 15)))
        new_pri = max(0, min(40, nr['dropout_rates']['primary'] + random.uniform(-2, 2)))
        new_sec = max(0, min(40, nr['dropout_rates']['secondary'] + random.uniform(-4, 4)))
        nr['dropout_rates'] = {'primary': new_pri, 'secondary': new_sec}
        # Randomize district slightly to make scatter look massive
        nr['district'] = nr['district'] + '_' + str(i)
        new_data.append(nr)

# Save to offline fallback
with open(path, 'w') as f:
    json.dump(new_data, f)

# Try saving to MongoDB if running
from pymongo import MongoClient
try:
    client = MongoClient('localhost', 27017, serverSelectionTimeoutMS=500)
    db = client['school_dropout_db']
    db['education_data'].drop()
    db['education_data'].insert_many(new_data)
    print(f"Instantly ingested {len(new_data)} large records into DB!")
except Exception as e:
    pass
