import psycopg2
import psycopg2.extras
from thefuzz import fuzz, process
import pandas as pd
import time
from DatabaseConnector import DatabaseConnector

class PropertyAddressProcessor:
    def __init__(self):
        self.connect_to_postgres()
        self.load_ref_address()

    def connect_to_postgres(self):
        self.db_connector = DatabaseConnector()
        self.cursor = self.db_connector.cursor
        self.conn = self.cursor.connection

    def load_ref_address(self):
        # Load all data once into memory
        self.ref_df = pd.read_sql("SELECT DISTINCT provinsi, kabupatenkota, kecamatan FROM public.ref_address", self.conn)

    def fetch_property_address(self, limit=250):
        query = """
        SELECT t1.propertyid, t1.address
        FROM public.property_detil t1
        LEFT JOIN property_address t2 ON t1.propertyid = t2.propertyid
        WHERE t2.score IS NULL
        LIMIT %s;
        """
        self.cursor.execute(query, (limit,))
        return self.cursor.fetchall()

    def match_best(self, text, choices):
        if not choices:
            return None, 0
        match, score = process.extractOne(text, choices, scorer=fuzz.WRatio)
        if score < 90:
            match, score = process.extractOne(text, choices, scorer=fuzz.token_set_ratio)
        return match, score

    def calculate_score(self, *scores):
        return int(sum(scores) / len(scores))

    def bulk_insert_addresses(self, rows):
        query = """
        INSERT INTO public.property_address (
            propertyid, address_nonstandard, province, kabupatenkota, kecamatan, score
        ) VALUES %s
        ON CONFLICT (propertyid) DO NOTHING;
        """
        psycopg2.extras.execute_values(self.cursor, query, rows)
        self.conn.commit()

    def process_address(self, property_address):
        data_to_insert = []
        province_list = self.ref_df['provinsi'].dropna().unique().tolist()

        for idx, (propertyid, address) in enumerate(property_address, start=1):
            print(f"\n🔄 Processing {idx}/{len(property_address)} — PropertyID: {propertyid}")

            address_clean = address.replace("'", "")
            print(f"📍 Address: {address_clean}")

            province, province_score = self.match_best(address_clean, province_list)
            print(f"🏙️ Matched Province: {province} (Score: {province_score})")

            kabupaten_list = self.ref_df[self.ref_df['provinsi'] == province]['kabupatenkota'].dropna().unique().tolist()
            kabupaten, kabupaten_score = self.match_best(address_clean, kabupaten_list)
            print(f"🌆 Matched City/Kabupaten: {kabupaten} (Score: {kabupaten_score})")

            kecamatan_list = self.ref_df[
                (self.ref_df['provinsi'] == province) &
                (self.ref_df['kabupatenkota'] == kabupaten)
            ]['kecamatan'].dropna().unique().tolist()
            kecamatan, kecamatan_score = self.match_best(address_clean, kecamatan_list)
            print(f"🏘️ Matched Subdistrict/Kecamatan: {kecamatan} (Score: {kecamatan_score})")

            total_score = self.calculate_score(province_score, kabupaten_score, kecamatan_score)
            print(f"✅ Total Score: {total_score}")

            data_to_insert.append((propertyid, address_clean, province, kabupaten, kecamatan, total_score))

        if data_to_insert:
            self.bulk_insert_addresses(data_to_insert)
            print(f"\n📥 Bulk insert completed for {len(data_to_insert)} records.\n{'='*60}")


    def run(self):
        while True:
            try:
                property_address = self.fetch_property_address(limit=250)
                if not property_address:
                    print("🎉 All addresses processed!")
                    break
                self.process_address(property_address)
            except psycopg2.Error as e:
                print(f"⛔ Lost connection or error: {e}")
                time.sleep(60)
                self.connect_to_postgres()
                self.load_ref_address()

if __name__ == "__main__":
    processor = PropertyAddressProcessor()
    processor.run()
