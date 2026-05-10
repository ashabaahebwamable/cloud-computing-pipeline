import pandas as pd
import json
import os
import matplotlib.pyplot as plt
from sqlalchemy import create_engine

os.makedirs('reports', exist_ok=True)

db_user = 'root'
db_password = ''
db_host = 'localhost'
db_name = 'patent_db'
engine = create_engine(
    f'mysql+mysqlconnector://{db_user}@{db_host}/{db_name}' if not db_password
    else f'mysql+mysqlconnector://{db_user}:{db_password}@{db_host}/{db_name}'
)

def run_query(query):
    return pd.read_sql_query(query, engine)

# Q1: Top Inventors
q1 = run_query("""
SELECT i.name, COUNT(r.patent_id) as patent_count
FROM inventors i
JOIN relationships r ON i.inventor_id = r.inventor_id
GROUP BY i.inventor_id, i.name
ORDER BY patent_count DESC
LIMIT 10;
""")

# Q2: Top Companies
q2 = run_query("""
SELECT c.name, COUNT(r.patent_id) as patent_count
FROM companies c
JOIN relationships r ON c.company_id = r.company_id
GROUP BY c.company_id, c.name
ORDER BY patent_count DESC
LIMIT 10;
""")

# Q3: Countries
q3 = run_query("""
SELECT i.country, COUNT(DISTINCT r.patent_id) as patent_count
FROM inventors i
JOIN relationships r ON i.inventor_id = r.inventor_id
WHERE i.country IS NOT NULL
GROUP BY i.country
ORDER BY patent_count DESC
LIMIT 10;
""")

# Q4: Trends Over Time
q4 = run_query("""
SELECT year, COUNT(*) as patent_count
FROM patents
WHERE year IS NOT NULL
GROUP BY year
ORDER BY year;
""")

# Total patents
total_patents = run_query("SELECT COUNT(*) as total FROM patents;").iloc[0]['total']

# Console Report
print("================== PATENT REPORT ===================")
print(f"Total Patents: {total_patents}")
print("Top Inventors:")
for idx, row in q1.iterrows():
    print(f"{idx+1}. {row['name']} - {row['patent_count']}")
print("Top Companies:")
for idx, row in q2.iterrows():
    print(f"{idx+1}. {row['name']} - {row['patent_count']}")
print("Top Countries:")
for idx, row in q3.iterrows():
    print(f"{idx+1}. {row['country']} - {row['patent_count']}")

# Export CSVs
q1.to_csv('reports/top_inventors.csv', index=False)
q2.to_csv('reports/top_companies.csv', index=False)
q3.to_csv('reports/country_trends.csv', index=False)  # Top countries
q4.to_csv('reports/trends_over_time.csv', index=False)

# JSON Report
report = {
    "total_patents": int(total_patents),
    "top_inventors": [{"name": row['name'], "patents": int(row['patent_count'])} for _, row in q1.iterrows()],
    "top_companies": [{"name": row['name'], "patents": int(row['patent_count'])} for _, row in q2.iterrows()],
    "top_countries": [{"country": row['country'], "patents": int(row['patent_count'])} for _, row in q3.iterrows()]
}

with open('reports/patent_report.json', 'w') as f:
    json.dump(report, f, indent=4)

# Visualizations
plt.figure(figsize=(10, 6))
plt.bar(q4['year'], q4['patent_count'])
plt.title('Patents Over Time')
plt.xlabel('Year')
plt.ylabel('Number of Patents')
plt.savefig('reports/patents_over_time.png')
plt.close()

plt.figure(figsize=(10, 6))
q3_top = q3.head(10)
plt.bar(q3_top['country'], q3_top['patent_count'])
plt.title('Top Countries by Patents')
plt.xlabel('Country')
plt.ylabel('Number of Patents')
plt.xticks(rotation=45)
plt.savefig('reports/top_countries.png')
plt.close()

# Top companies chart
plt.figure(figsize=(10, 6))
q2_top = q2.head(10)
plt.barh(q2_top['name'], q2_top['patent_count'])
plt.title('Top Companies by Patents')
plt.xlabel('Number of Patents')
plt.gca().invert_yaxis()
plt.tight_layout()
plt.savefig('reports/top_companies.png')
plt.close()

print("Reports generated!")