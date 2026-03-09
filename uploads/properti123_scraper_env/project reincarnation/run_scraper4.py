from PropertyDetailsUpdater2 import PropertyDetailsUpdater
from psycopg2.extras import execute_values

def bulk_insert_properties(db_connector, property_data_list):
    if not property_data_list:
        print("No property details to insert.")
        return

    sql = '''
        INSERT INTO property_detil (
            propertyid, propertylistingid, propertytipe, title, currency, 
            price_real, price_short, price_monthly, price_psm, address, 
            contact_person, phone_number, agency, kondisi_bangunan, luas_bangunan, 
            luas_tanah, jumlah_lantai, floor_loc, certificate, interior, main_bedroom, 
            bathroom, secondary_bedroom, saluran_telepon, listrik, air_pam, air_tanah, 
            jalur_mobil, garasi, carport, direction, about, domain, url, page_created_at, 
            created_at
        ) VALUES %s
    '''
    values = [tuple(item.values()) for item in property_data_list]
    with db_connector.conn.cursor() as cursor:
        execute_values(cursor, sql, values)
        db_connector.conn.commit()
        print(f"Inserted {len(values)} records into property_detil.")

def bulk_update_statuses(db_connector, updates):
    if not updates:
        return
    with db_connector.conn.cursor() as cur:
        cur.executemany("UPDATE property_link SET available_data = %s WHERE url = %s", updates)
        db_connector.conn.commit()
        print(f"Updated {len(updates)} property_link statuses.")

def run_batch_processing(batch_size=1000):
    updater = PropertyDetailsUpdater()
    offset = 500

    while True:
        links = updater.db_connector.fetch_data(
            "SELECT url, status, available_data FROM property_link WHERE available_data = 0 order by url desc LIMIT %s OFFSET %s",
            (batch_size, offset)
        )

        if not links:
            print("No more URLs to process.")
            break

        print(f"Scraping batch at offset {offset} with size {len(links)}...")
        results = updater.update_property_details(links)

        successful_data = [r[3] for r in results if r[0] == 'success']
        status_updates = [(r[2], r[1]) for r in results]

        bulk_insert_properties(updater.db_connector, successful_data)
        bulk_update_statuses(updater.db_connector, status_updates)

        offset += batch_size

if __name__ == "__main__":
    run_batch_processing(batch_size=100)
