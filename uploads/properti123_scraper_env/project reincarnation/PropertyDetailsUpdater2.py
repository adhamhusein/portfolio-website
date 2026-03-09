from DatabaseConnector import DatabaseConnector
from bs4 import BeautifulSoup
import json
from urllib.parse import urlparse
from datetime import datetime
from psycopg2.extras import execute_values
import time
import requests

class PropertyDetailsUpdater:
    def __init__(self):
        self.db_connector = DatabaseConnector()

    def get_page(self, url, retries=3, backoff_factor=0.5):
        for attempt in range(retries):
            try:
                response = requests.get(url, timeout=15)
                response.raise_for_status()
                return BeautifulSoup(response.text, 'html.parser')
            except requests.exceptions.RequestException:
                if attempt < retries - 1:
                    time.sleep(backoff_factor * (2 ** attempt))
                else:
                    print(f"Failed to retrieve {url} after {retries} attempts.")
        return None

    def extract_property_details(self, soup, url):
        if len(soup.find_all('div', 'category')) == 0:
            return ('fail', url, 8, None)

        try:
            script_content = soup.find_all('script')[5].contents[0]
            price_data = json.loads(script_content)
            property_info_divs = soup.find_all('div', 'property-info')

            data = {
                "propertyid": soup.find_all('div', 'category')[0].text.strip(),
                "propertylistingid": int(property_info_divs[0].select_one('div.type:-soup-contains("ID Listing") + div.value').get_text(strip=True)),
                "propertytipe": property_info_divs[0].select_one('div.type:-soup-contains("Tipe") + div.value').get_text(strip=True),
                "title": price_data['name'],
                "currency": price_data['offers']['priceCurrency'],
                "price_real": float(price_data['offers']['price']),
                "price_short": soup.find_all('div', 'price')[0].contents[1].text.strip(),
                "price_monthly": soup.find_all('div', 'price')[0].contents[3].text.strip(),
                "price_psm": property_info_divs[0].select_one('div.type:-soup-contains("PSM") + div.value').get_text(strip=True),
                "address": soup.find_all('div', 'address')[0].text.strip(),
                "contact_person": soup.find_all('div', 'name')[0].text.strip(),
                "phone_number": soup.find_all('div', 'owner')[0].contents[5].text.strip(),
                "agency": soup.find_all('div', 'name')[1].text.strip() if len(soup.find_all('div', 'name')) > 1 else "Not Found!"
            }

            fields = ["Kondisi Bangunan", "Luas Bangunan", "Luas Tanah", "Jumlah Lantai", "Floor Location", "Sertifikat",
                      "Interior", "Kamar Tidur", "Kamar Mandi", "Kamar Pembantu", "Saluran Telepon", "Listrik", "Air Pam",
                      "Air Tanah", "Jalur Mobil", "Garasi", "Carport", "Menghadap"]
            for field in fields:
                try:
                    value = property_info_divs[0].select_one(f'div.type:-soup-contains("{field}") + div.value').get_text(strip=True)
                except:
                    value = "Not Found!"
                data[field.lower().replace(" ", "_")] = value

            data.update({
                "about": soup.find_all('div', 'about no-border')[0].contents[3].text.strip(),
                "domain": urlparse(url).netloc,
                "url": url,
                "page_created_at": property_info_divs[0].select_one('div.type:-soup-contains("Terdaftar pada") + div.value').get_text(strip=True),
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
            return ('success', url, 1, data)
        except Exception as e:
            return ('fail', url, 7, None)

    def update_property_details(self, links):
        results = []
        for index, (url, _, _) in enumerate(links):
            soup = self.get_page(url)
            if not soup:
                results.append(('fail', url, 9, None))
                continue

            result = self.extract_property_details(soup, url)
            results.append(result)

            print(f"Processed {index + 1}/{len(links)}: {url}")
            if (index + 1) % 50 == 0:
                print("Cooldown for 60 seconds...")
                time.sleep(5)
        return results
