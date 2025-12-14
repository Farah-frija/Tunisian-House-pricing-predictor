import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import time
from urllib.parse import urljoin

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}


def get_property_links(search_url, max_pages=3):
    """
    Extract property links from Mubawab search pages.
    Links are found in the 'linkref' attribute of div elements with class 'listingBox'.
    """
    all_links = []

    for page in range(1, max_pages + 1):
        # Handle pagination - adjust URL pattern as needed
        if page == 1:
            page_url = search_url
        else:
            # Check the actual pagination pattern on the website
            page_url = f"{search_url}:p:{page}"  # Common pattern

        print(f"Fetching page {page}: {page_url}")

        try:
            response = requests.get(page_url, headers=HEADERS, timeout=10)
            response.raise_for_status()
        except requests.RequestException as e:
            print(f"  Failed to fetch page {page}: {e}")
            continue

        soup = BeautifulSoup(response.text, 'html.parser')

        # Find all listing boxes
        listing_boxes = soup.find_all('div', class_='listingBox')

        for box in listing_boxes:
            # Get the link from the linkref attribute
            linkref = box.get('linkref')

            if linkref:
                # Make sure the URL is complete
                if not linkref.startswith('http'):
                    full_url = urljoin('https://www.mubawab.tn', linkref)
                else:
                    full_url = linkref

                all_links.append(full_url)

        print(f"  Found {len(listing_boxes)} listings on page {page}")

        # Check if there are more pages
        next_page_link = soup.find('a', class_='nextPage')
        if not next_page_link and page >= max_pages:
            break

        # delay
        time.sleep(0.1)

    print(f"\nTotal property links found: {len(all_links)}")
    return all_links


def should_exclude_property(soup):
    """
    Check if a property should be excluded based on criteria:
    1. "En cours de construction" (Under construction)
    2. "prix non spécifié" (Price not specified)
    3. "Prix sur demande" (Price on request)
    Returns True if property should be excluded, False otherwise.
    """
    # Get all text content in lowercase for easy searching
    all_text = soup.get_text().lower()

    # Check for exclusion criteria
    exclusion_phrases = [
        'en cours de construction',
        'construction en cours',
        'prix non spécifié',
        'prix non specifie',
        'prix sur demande',
        'sur demande',
        'négociation',
        'à débattre',
        'a débattre',
        'contactez-nous pour le prix',
        'Prix à consulter',
        'prix à consulter'
    ]

    for phrase in exclusion_phrases:
        if phrase in all_text:
            return True

    # Additional check: look for price not specified in specific elements
    price_elements = soup.find_all(['h3', 'span', 'div'], class_=re.compile(r'price|Price|PRIX', re.I))
    for element in price_elements:
        element_text = element.get_text().lower()
        if any(phrase in element_text for phrase in ['non spécifié', 'sur demande', 'négociation']):
            return True

    return False


def scrape_property_page(url):
    """
    Scrapes detailed property data from a single Mubawab listing page.
    Returns None if property should be excluded.
    """
    print(f"Scraping: {url}")

    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"  Failed to fetch page: {e}")
        return None

    soup = BeautifulSoup(response.text, 'html.parser')

    # Check if property should be excluded
    if should_exclude_property(soup):
        print(f"  ⚠️  EXCLUDED: Property under construction or price not specified")
        return None

    data = {'url': url}

    # --- 1. EXTRACT PRICE (check again specifically) ---
    price_tag = soup.find('h3', class_='orangeTit')
    if price_tag:
        price_text = price_tag.get_text(strip=True).replace(u'\xa0', ' ')
        # Additional check for price validity
        if any(phrase in price_text.lower() for phrase in ['non spécifié', 'sur demande', 'négociation']):
            print(f"  ⚠️  EXCLUDED: Invalid price format: {price_text}")
            return None
        data['price'] = price_text
    else:
        print(f"  ⚠️  EXCLUDED: No price found")
        return None

    # --- 2. EXTRACT AREA/LOCATION ---
    location_block = soup.find('div', class_='blockProp mapBlockProp')
    if location_block:
        area_tag = location_block.find('h4', class_='titBlockProp')
        if area_tag:
            data['area'] = area_tag.get_text(strip=True).replace(' ', '')
        else:
            data['area'] = 'Non spécifié'
    else:
        # Alternative location extraction
        loc_span = soup.find('span', class_='listingH3')
        if loc_span and 'icon-location' in str(loc_span):
            data['area'] = loc_span.get_text(strip=True).replace('icon-location', '').strip()
        else:
            data['area'] = 'Non spécifié'

    # --- 3. EXTRACT CORE DETAILS ---
    details_container = soup.find('div', class_='disFlex adDetails')
    if details_container:
        for detail in details_container.find_all('div', class_='adDetailFeature'):
            text = detail.get_text(" ", strip=True)
            icon = detail.find('i')
            icon_class = icon['class'] if icon else []

            if 'icon-triangle' in str(icon_class) or 'm²' in text:
                numbers = re.findall(r'\d+', text)
                data['surface'] = numbers[0] if numbers else 'Non spécifié'
            elif 'icon-house-boxes' in str(icon_class) or 'Pièces' in text:
                numbers = re.findall(r'\d+', text)
                data['nombre_pieces'] = numbers[0] if numbers else 'Non spécifié'
            elif 'icon-bed' in str(icon_class) or 'Chambres' in text:
                numbers = re.findall(r'\d+', text)
                data['nombre_chambres'] = numbers[0] if numbers else 'Non spécifié'
            elif 'icon-bath' in str(icon_class) or 'Salle de bain' in text:
                numbers = re.findall(r'\d+', text)
                data['nombre_salle_bain'] = numbers[0] if numbers else 'Non spécifié'

    # --- 4. EXTRACT PROPERTY TYPE, CONDITION, STANDING ---
    # Initialize all values first
    data['etat'] = 'Non spécifié'
    data['neuf'] = False
    data['haut_standing'] = False

    main_features_container = soup.find('div', class_='adFeatures')
    if main_features_container:
        main_features = main_features_container.find_all('div', class_='adMainFeature')
        for feat in main_features:
            label_tag = feat.find('p', class_='adMainFeatureContentLabel')
            value_tag = feat.find('p', class_='adMainFeatureContentValue')

            if label_tag and value_tag:
                label = label_tag.get_text(strip=True)
                value = value_tag.get_text(strip=True)

                if label == 'Type de bien':
                    data['type_bien'] = value
                elif label == 'Etat':
                    data['etat'] = value
                    # Check if under construction
                    if 'construction' in value.lower():
                        print(f"   EXCLUDED: Under construction (Etat: {value})")
                        return None
                    # Set 'neuf' based on 'Etat'
                    if value.lower() in ['nouveau', 'neuf', 'rénové', 'renove']:
                        data['neuf'] = True
                elif label == 'Standing':
                    # This is where 'haut_standing' should be detected
                    if 'haut' in value.lower() or 'standing' in value.lower():
                        data['haut_standing'] = True
                elif label == 'Années':
                    data['annees'] = value
                elif label == 'Type du sol':
                    data['type_sol'] = value

    # --- 5. EXTRACT AMENITIES ---
    amenities = []
    amenities_containers = soup.find_all('div', class_='adFeatures')

    for container in amenities_containers:
        ad_features = container.find_all('div', class_='adFeature')
        for feature in ad_features:
            feature_text = feature.get_text(strip=True)
            if feature_text:
                amenities.append(feature_text)

    # Create boolean fields for requested amenities
    requested_amenities = ['Terrasse', 'Parking', 'Piscine', 'Vue panoramique',
                           'Jardin', 'Climatisation', 'Chauffage', 'Ascenseur', 'Balcon']

    for req_amenity in requested_amenities:
        found = False
        for amenity in amenities:
            if req_amenity.lower() in amenity.lower():
                found = True
                break
        data[req_amenity.lower().replace(' ', '_')] = found

    data['amenities_raw'] = ', '.join(amenities) if amenities else ''

    if not data['haut_standing']:
        detection_sources = []
        all_text = soup.get_text().lower()

        # Check for 'haut standing' in full text
        if 'haut standing' in all_text or 'haut-standing' in all_text:
            data['haut_standing'] = True
            detection_sources.append('Keyword in text')



    # --- 7. FILL MISSING VALUES ---
    requested_fields = ['surface', 'nombre_chambres', 'nombre_salle_bain',
                        'parking', 'piscine', 'vue_panoramique', 'jardin',
                        'climatisation', 'chauffage', 'ascenseur', 'etat', 'neuf',
                        'balcon', 'terrasse', 'haut_standing', 'price', 'area']

    for field in requested_fields:
        if field not in data:
            if field in ['parking', 'piscine', 'vue_panoramique', 'jardin',
                         'climatisation', 'chauffage', 'ascenseur', 'balcon',
                         'terrasse', 'haut_standing', 'neuf']:
                data[field] = False
            else:
                data[field] = 'Non spécifié'

    print(
        f"   INCLUDED: {data.get('surface', 'N/A')}m², {data.get('nombre_chambres', 'N/A')} chambres, "
        f"{data.get('price', 'N/A')}, Neuf: {data.get('neuf', 'N/A')}, "
        f"Haut standing: {data.get('haut_standing', 'N/A')}")
    return data


def scrape_mubawab(search_url, filename, max_pages=3):
    """
    Main function to scrape Mubawab properties with exclusion filters.
    """

    # Step 1: Get property links
    print("\n1. COLLECTING PROPERTY LINKS...")
    property_urls = get_property_links(search_url, max_pages=max_pages)

    if not property_urls:
        print("No property links found!")
        return None

    # Step 2: Scrape each property with filtering
    print(f"\n2. SCRAPING ET FILTRAGE DES PROPRIÉTÉS...")
    all_properties_data = []
    excluded_count = 0
    included_count = 0

    for i, url in enumerate(property_urls):
        print(f"[{i + 1}/{len(property_urls)}] ", end="")
        property_data = scrape_property_page(url)

        if property_data is None:
            excluded_count += 1
        else:
            all_properties_data.append(property_data)
            included_count += 1
        time.sleep(0.1)

    # Print summary
    print(f"\n{'=' * 60}")
    print("SCRAPING SUMMARY:")
    print(f"{'=' * 60}")
    print(f"Total URLs processed: {len(property_urls)}")
    print(f"Included properties: {included_count}")
    print(f"Excluded properties: {excluded_count}")
    print(f"Inclusion rate: {(included_count / (included_count + excluded_count)) * 100:.1f}%")

    if all_properties_data:
        df = pd.DataFrame(all_properties_data)

        # Select and order columns
        desired_columns = ['surface', 'nombre_chambres', 'nombre_salle_bain',
                           'parking', 'piscine', 'vue_panoramique', 'jardin',
                           'climatisation', 'chauffage', 'ascenseur', 'etat', 'neuf',
                           'balcon', 'terrasse', 'haut_standing', 'price', 'area', 'url']

        existing_columns = [col for col in desired_columns if col in df.columns]
        df = df[existing_columns]

        # Display sample
        print(f"\n=== SAMPLE OF INCLUDED PROPERTIES ===")
        if len(df) > 0:
            sample_size = min(5, len(df))
            print(df.head(sample_size).to_string(index=False))
        else:
            print("No properties included after filtering.")

        df.to_csv(filename, index=False, encoding='utf-8-sig')
        print(f"\nData saved to: {filename}")

        # Display final statistics
        if 'haut_standing' in df.columns and 'neuf' in df.columns:
            luxury_count = df['haut_standing'].sum()
            neuf_count = df['neuf'].sum()
            if included_count > 0:
                print(f"\nAMONG INCLUDED PROPERTIES:")
                print(f"• Haut standing properties: {luxury_count} ({luxury_count / included_count * 100:.1f}%)")
                print(f"• New properties (neuf): {neuf_count} ({neuf_count / included_count * 100:.1f}%)")

                # Cross analysis
                haut_standing_neuf = df[(df['haut_standing'] == True) & (df['neuf'] == True)].shape[0]
                if luxury_count > 0:
                    print(
                        f"• New among haut standing: {haut_standing_neuf} ({haut_standing_neuf / luxury_count * 100:.1f}%)")

        return df
    else:
        print("\nNo data collected after filtering.")
        return None


# --- CONFIGURATION ET EXÉCUTION ---
if __name__ == '__main__':
    # Configuration
    SEARCH_URL = "https://www.mubawab.tn/fr/sc/maisons-a-vendre"
    MAX_PAGES = 43  # Nombre de pages de recherche à analyser

    # Lancer le scraping
    results = scrape_mubawab(
        search_url=SEARCH_URL,
        max_pages=MAX_PAGES,
        filename=f'maison_mubawab_properties.csv'
    )

    if results is not None and len(results) > 0:
        print("\n" + "=" * 70)
        print("SCRAPING COMPLETED SUCCESSFULLY!")
        print("=" * 70)

        print(f"• Valid properties collected: {len(results)}")

