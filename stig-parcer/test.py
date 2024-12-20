import json
import sqlite3

# Step 1: Load the JSON data
with open('red_hat_enterprise_linux_8_stig.json') as f:
    data = json.load(f)

# Step 2: Navigate to the findings section
findings = data['stig']['findings']

# Step 3: Extract relevant information
stig_entries = []
for finding_id, details in findings.items():
    title = details.get('title')
    severity = details.get('severity')
    description = details.get('description')
    version = details.get('version')
    
    stig_entries.append((title, version, severity, description))

# Step 4: Store the data in an SQLite database
db_file = 'stig_data.db'

# Connect to SQLite (or create the database if it doesn't exist)
conn = sqlite3.connect(db_file)
cursor = conn.cursor()

# Create the table if it doesn't exist
cursor.execute('''
CREATE TABLE IF NOT EXISTS stig_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    Title TEXT,
    Version TEXT,
    Severity TEXT,
    Description TEXT
)
''')

# Insert data into the table
cursor.executemany('''
INSERT INTO stig_data (Title, Version, Severity, Description)
VALUES (?, ?, ?, ?)
''', stig_entries)

# Commit the changes and close the connection
conn.commit()
conn.close()

print(f"STIG data successfully extracted and stored in {db_file}")
