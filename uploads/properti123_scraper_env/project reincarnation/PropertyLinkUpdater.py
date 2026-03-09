from DatabaseConnector import DatabaseConnector
from bs4 import BeautifulSoup
import time
import requests

class PropertyLinkUpdater:
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
                    continue
                else:
                    print(f"Failed to retrieve {url} after {retries} attempts.")
                    return None

    def fetch_new_links(self, starting_page, page_length):
        new_links = []
        current_page = starting_page
        batch_size = 250  # Changed batch size to 250
        total_processed = 0
        
        while current_page < page_length:
            batch_links = []
            pages_in_batch = min(batch_size, page_length - current_page)
            
            for _ in range(pages_in_batch):
                url = f'https://properti123.com/properti-jual?post_date=DESC&listing_type=SALE&page={current_page}'
                soup = self.get_page(url)
                
                if not soup:
                    print(f"Website failed to respond. Waiting for 1 minute before retrying page {current_page}...")
                    time.sleep(60)
                    continue
                
                links = [link.get('href') for link in soup.find_all('a') if link.get('href') and 'https://properti123.com/properti-jual/' in link.get('href')]
                if links:
                    batch_links.extend([(link, 'JUAL', 0) for link in links])
                    print(f'Collected {len(links)} links from page {current_page}')
                else:
                    print(f'No links found on page {current_page}')
                
                current_page += 1
                total_processed += 1
            
            if batch_links:
                # Convert to tuple for SQL query
                formatted_links = tuple(link[0] for link in batch_links)
                # Check which links already exist
                existing_links = self.db_connector.fetch_data("SELECT url FROM public.property_link WHERE status = 'JUAL' AND url IN %s", (formatted_links,))
                # Filter out existing links
                new_batch_links = [link for link in batch_links if (link[0],) not in existing_links]
                
                if new_batch_links:
                    self.db_connector.executemany_query(
                        "INSERT INTO public.property_link (url, status, available_data) VALUES (%s, %s, %s) ON CONFLICT (url) DO NOTHING;", 
                        new_batch_links
                    )
                    print(f'Batch inserted {len(new_batch_links)} new links from {pages_in_batch} pages')
                else:
                    print(f'No new links to insert from {pages_in_batch} pages')
            
            print(f'Progress: {total_processed} pages processed, current page: {current_page}')
            
        return new_links

if __name__ == "__main__":
    updater = PropertyLinkUpdater()
    updater.fetch_new_links(29, 35)

