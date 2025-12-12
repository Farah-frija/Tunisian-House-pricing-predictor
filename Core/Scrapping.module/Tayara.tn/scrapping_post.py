import requests
from bs4 import BeautifulSoup
import pandas as pd
import time

# List of URLs to scrape


import pandas as pd
import requests
from bs4 import BeautifulSoup
import time

def scrape_property_data(url):
    """Scrape data from a single property URL"""
    try:
        # Fetch the page
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        data = {'URL': url}
        
        # 1. Extract Description
        desc_p = soup.find('p', {'dir': 'auto', 'class': lambda x: x and 'whitespace-pre-line' in x})
        if desc_p:
            # Remove phone number buttons
            for btn in desc_p.find_all('span', {'class': 'inline-block'}):
                btn.decompose()
            data['description'] = desc_p.get_text(strip=True)
        
        # 2. Extract Price
        price_elem = soup.find('data', {'class': 'text-red-600'})
        if price_elem:
            # Get all number spans (exclude the DT span)
            numbers = []
            for span in price_elem.find_all('span'):
                if 'DT' not in span.text:
                    numbers.append(span.text.strip())
            if numbers:
                data['Prix'] = int(''.join(numbers))
        
        return data
        
    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return None

def enrich_dataframe_simple(df, url_column='url', delay=1,output_file="posts.csv"):
    """
     sauvegarde toutes les 5 itérations
    """
    print(f"Scraping {len(df)} URLs...")
    
    for i, url in enumerate(df[url_column]):
        print(f"  [{i+1}/{len(df)}] Scraping {url}")
        
        scraped = scrape_property_data(url)
        
        if scraped:
            # Ajouter toutes les colonnes scrapées (sauf URL qui existe déjà)
            for key, value in scraped.items():
                if key != url_column:
                    df.at[i, key] = value
        
        # Sauvegarder toutes les 5 itérations
        if (i + 1) % 5 == 0 or i == len(df) - 1:
            df.to_csv(output_file, index=False, encoding='utf-8-sig')
            print(f"  💾 Sauvegarde dans: {output_file} ({i+1} URLs traitées)")
        
        time.sleep(delay)
    
    # Sauvegarde finale
    final_file = 'dataframe_final.csv'
    df.to_csv(final_file, index=False, encoding='utf-8-sig')
    print(f"Scraping terminé!")
    print(f"Fichier final sauvegardé: {final_file}")
    
    return df

def main():
    """Main scraping function"""
    all_properties = []
    
    print(f"Starting to scrape {len(urls)} properties...")
    
    for i, url in enumerate(urls, 1):
        print(f"Scraping {i}/{len(urls)}: {url}")
        
        data = scrape_property_data(url)
        if data:
            all_properties.append(data)
        
        # Small delay to be polite to server
        time.sleep(1)
    
    # Convert to DataFrame
    if all_properties:
        df = pd.DataFrame(all_properties)
        
     
        # Save to CSV
        filename = 'properties_data_test.csv'
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        print(f"\n✓ Successfully saved {len(all_properties)} properties to {filename}")
        
        # Display summary
        print(f"\nSummary:")
        print(f"- Total scraped: {len(all_properties)}/{len(urls)}")
        print(f"- Columns: {', '.join(df.columns.tolist())}")
    else:
        print("✗ No data was scraped successfully")

if __name__ == "__main__":
    # Install required packages first:
    # pip install requests beautifulsoup4 pandas
    
    # Update your URLs list
    urls = [
        "https://www.tayara.tn/item/appartements/monastir/monastir/a-vendre-appartement-s2-monastir-c1/693ab70e8914daae5199a65a/"
    ]
    
    main()