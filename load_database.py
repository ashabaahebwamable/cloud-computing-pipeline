import pandas as pd
import os
from sqlalchemy import create_engine, text

# MySQL connection details 
db_user = 'root' 
db_password = ''  
db_host = 'localhost'  
db_name = 'patent_db'  

#  SQLAlchemy engine for MySQL
engine = create_engine(f'mysql+mysqlconnector://{db_user}@{db_host}/{db_name}' if not db_password else f'mysql+mysqlconnector://{db_user}:{db_password}@{db_host}/{db_name}')

#  tables from schema.sql
with open('schema.sql', 'r') as f:
    sql_script = f.read()


def strip_comments(stmt):
    lines = [l for l in stmt.splitlines() if not l.strip().startswith('--')]
    return '\n'.join(lines).strip()

statements = [strip_comments(s) for s in sql_script.split(';') if strip_comments(s)]
with engine.connect() as conn:
    for stmt in statements:
        if stmt:
            conn.execute(text(stmt))
    conn.commit()

# loading cleaned data
clean_dir = 'clean_data'

patents_df = pd.read_csv(os.path.join(clean_dir, 'clean_patents.csv'))
inventors_df = pd.read_csv(os.path.join(clean_dir, 'clean_inventors.csv'))
companies_df = pd.read_csv(os.path.join(clean_dir, 'clean_companies.csv'))
relationships_df = pd.read_csv(os.path.join(clean_dir, 'relationships.csv'))

# Truncating and reloading on a single connection so FK_CHECKS=0 stays in effect
with engine.connect() as conn:
    conn.execute(text("SET FOREIGN_KEY_CHECKS=0"))
    for table in ['relationships', 'patents', 'inventors', 'companies']:
        conn.execute(text(f"TRUNCATE TABLE {table}"))
    conn.commit()

    bulk = dict(if_exists='append', index=False, chunksize=2000, method='multi')
    print(f"Inserting {len(patents_df):,} patents...")
    patents_df.to_sql('patents', conn, **bulk)
    print(f"Inserting {len(inventors_df):,} inventors...")
    inventors_df.to_sql('inventors', conn, **bulk)
    print(f"Inserting {len(companies_df):,} companies...")
    companies_df.to_sql('companies', conn, **bulk)
    print(f"Inserting {len(relationships_df):,} relationships...")
    relationships_df.to_sql('relationships', conn, **bulk)

    conn.execute(text("SET FOREIGN_KEY_CHECKS=1"))
    conn.commit()

print("MySQL database created and populated!")