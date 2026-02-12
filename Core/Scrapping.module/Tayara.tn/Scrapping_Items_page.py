import requests
import pandas as pd
import time
import random
from typing import List, Dict, Optional

BASE_URLS = {
    "appartements": "https://www.tayara.tn/_next/data/GtgveimIGnQSSDzbYtC9S/en/listing/c/immobilier/appartements.json",
    "maisons": "https://www.tayara.tn/_next/data/GtgveimIGnQSSDzbYtC9S/en/listing/c/immobilier/maisons-et-villas.json",
    "immoneuf": "https://www.tayara.tn/_next/data/GtgveimIGnQSSDzbYtC9S/en/listing/c/immoneuf.json"
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 (contact: farah.131.frija@gmail.com)",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Referer": "https://www.tayara.tn/",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "sec-ch-ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "DNT": "1",
    "Upgrade-Insecure-Requests": "1"
}
# Add cookies like your browser does
session = requests.Session()

# Copy cookies from your browser (F12 > Network > Request Headers > Cookie)
session.headers.update(HEADERS)

def scrape_page(url: str, page: int, property_type: str) -> Optional[List[Dict]]:
    """Scrape a single page of listings"""
    try:
        params = {"page": page}
        
        # Add subCategory parameter for specific property types
        """if property_type == "appartements":
            params["subCategory"] = "appartements"
        elif property_type == "maisons":
            params["subCategory"] = "maisons-et-villas"
        elif property_type == "immoneuf":
            params = {"page": page, "category": "immoneuf"}  # Different parameter structure"""
        
        response = session.get(url,
                                params=params,
                                 timeout=60)
        response.raise_for_status()
        
        data = response.json()
        
        # Navigate to the listings data
        listings = data.get("pageProps", {}).get("searchedListingsAction", {}).get("newHits", [])
        
        if not listings:
            print(f"No listings found on page {page} for {property_type}")
            return None
        
        processed_listings = []
        for listing in listings:
            obj={
                "id": listing.get("id", ""),
                "titre": listing.get("title", ""),
                "description": listing.get("description", ""),
                "prix": listing.get("price", 0),
                "gouvernorat": listing.get("location", {}).get("governorate", ""),
                "delegation": listing.get("location", {}).get("delegation", ""),
                "date": listing.get("metadata", {}).get("publishedOn", ""),
                "categorie": property_type,
               
            }
            if obj['prix']>20000:
                processed_listings.append(obj)
        
        print(f"Successfully scraped {len(processed_listings)} listings from page {page} ({property_type})")
        return processed_listings
        
    except requests.exceptions.RequestException as e:
        print(f"Error scraping page {page} for {property_type}: {e}")
        return None
    except (KeyError, ValueError) as e:
        print(f"Error parsing data from page {page} for {property_type}: {e}")
        return None

def scrape_property_type(property_type: str, max_pages: int = 100, delay: float = 2.0) -> List[Dict]:
    """Scrape all pages for a specific property type"""
    if property_type not in BASE_URLS:
        print(f"Invalid property type. Choose from: {list(BASE_URLS.keys())}")
        return []
    
    url = BASE_URLS[property_type]
    all_listings = []
    
    for page in range(1, max_pages + 1):
        print(f"Scraping {property_type} - Page {page}/{max_pages}")
        
        listings = scrape_page(url, page, property_type)
        
        if listings is None:
            # If we get None, it might mean we've reached the last page
            break
        
        all_listings.extend(listings)
        
        # Add delay between requests to be respectful to the server
        if page < max_pages:
            time.sleep(delay + random.uniform(0.5, 1.5))  # Add some randomness
    
    print(f"Total scraped for {property_type}: {len(all_listings)} listings")
    return all_listings

def scrape_all_properties(max_pages_per_type: int = 100, delay: float = 2.0) -> pd.DataFrame:
    """Scrape all property types and return a combined DataFrame"""
    all_data = []
    
    for property_type in BASE_URLS.keys():
        print(f"\n{'='*50}")
        print(f"Starting scrape for: {property_type}")
        print(f"{'='*50}")
        
        property_listings = scrape_property_type(property_type, max_pages_per_type, delay)
        all_data.extend(property_listings)
        
        # Longer delay between different property types
        if property_type != list(BASE_URLS.keys())[-1]:  # If not the last property type
            time.sleep(5)
    
    # Create DataFrame
    df = pd.DataFrame(all_data)
    
    # Convert date column to datetime
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
    
    # Reorder columns as requested
    desired_columns = ['id', 'categorie','date', 'gouvernorat','delegation' ,'prix','titre', 'description'
                        ]
    
    # Add any additional columns we have
    for col in df.columns:
        if col not in desired_columns:
            desired_columns.append(col)
    
    df = df[desired_columns]
    
    print(f"\n{'='*50}")
    print(f"Total listings scraped from all categories: {len(df)}")
    print(f"{'='*50}")
    
    return df

def save_to_csv(df: pd.DataFrame, filename: str = "tayara_listings.csv"):
    """Save DataFrame to CSV with proper encoding"""
    df.to_csv(filename, index=False, encoding='utf-8')
    print(f"Data saved to {filename}")
    print(f"File contains {len(df)} rows and {len(df.columns)} columns")

def get_sample_data(property_type: str = "appartements", pages: int = 1) -> pd.DataFrame:
    """Get a small sample of data for testing"""
    print(f"Getting sample data for {property_type} ({pages} page(s))")
    listings = scrape_property_type(property_type, max_pages=pages, delay=1.0)
    df = pd.DataFrame(listings)
    return df

# Main execution
if __name__ == "__main__":
    try:
        # Option 1: Scrape all property types (100 pages each)
        print("Starting comprehensive Tayara.tn scraper...")
        df = scrape_all_properties(max_pages_per_type=100, delay=2.0)
        
        # Display summary
        print("\nSummary by property type:")
        print(df['categorie'].value_counts())
        
        print("\nSummary by governorat:")
        print(df['gouvernorat'].value_counts().head(10))
        
        print("\nPrice statistics:")
        print(df['prix'].describe())
        
        # Save to CSV
        save_to_csv(df, "tayara_listings_complete_1.csv")
        
        # Option 2: For testing with fewer pages
        # df_sample = get_sample_data("appartements", pages=2)
        # print(f"Sample data shape: {df_sample.shape}")
        # save_to_csv(df_sample, "tayara_sample.csv")
        
        # Option 3: Scrape specific property type only
        # maison_listings = scrape_property_type("maisons", max_pages=10, delay=2.0)
        # df_maisons = pd.DataFrame(maison_listings)
        # save_to_csv(df_maisons, "tayara_maisons.csv")
        
    except KeyboardInterrupt:
        print("\nScraping interrupted by user")
    except Exception as e:
        print(f"An error occurred: {e}")