import pandas as pd
import psycopg2
from psycopg2.extras import execute_values

# === CONFIGURATION ===
csv_path = r'C:\Users\Adham\Work\4_VPS\01_Property_Data\property_detil_20240608.csv'
table_name = 'property_detil'

# PostgreSQL connection config
db_config = {
    'host': '203.194.112.169',
    'port': 5432,
    'database': 'property',
    'user': 'admin',
    'password': 'delapane8E#'
}

# Expected columns in order
expected_columns = [
    'propertyid', 'propertylistingid', 'propertytipe', 'title', 'currency',
    'price_real', 'price_short', 'price_monthly', 'price_psm', 'address',
    'contact_person', 'phone_number', 'agency', 'kondisi_bangunan', 'luas_bangunan',
    'luas_tanah', 'jumlah_lantai', 'floor_loc', 'certificate', 'interior', 'main_bedroom',
    'bathroom', 'secondary_bedroom', 'saluran_telepon', 'listrik', 'air_pam', 'air_tanah',
    'jalur_mobil', 'garasi', 'carport', 'direction', 'about', 'domain', 'url',
    'page_created_at', 'created_at'
]

# === READ CSV ===
df = pd.read_csv(csv_path, dtype=str, low_memory=False)
for col in expected_columns:
    if col not in df.columns:
        df[col] = None
df = df[expected_columns]

# === INSERT TO POSTGRES WITH ON CONFLICT ===
insert_query = f"""
    INSERT INTO {table_name} ({', '.join(expected_columns)})
    VALUES %s
    ON CONFLICT (url) DO NOTHING;
"""

# Convert DataFrame to list of tuples
data = [tuple(x) for x in df.to_numpy()]

# Execute
try:
    with psycopg2.connect(**db_config) as conn:
        with conn.cursor() as cur:
            execute_values(cur, insert_query, data, page_size=1000)
    print(f"✅ Successfully inserted with ON CONFLICT SKIP for duplicates (total rows: {len(df)})")
except Exception as e:
    print(f"❌ Error inserting data: {e}")
