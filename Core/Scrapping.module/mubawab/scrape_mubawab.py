import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import time
from urllib.parse import urljoin

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}


def extract_governorat_delegation(area_text):
    """
    Extrait le gouvernorat et la délégation du texte de localisation.
    Format typique: "Les Jardins d'El Menzah 2 à Ariana Ville" ou "Tunis, El Omrane"
    """
    if not area_text or area_text == 'Non spécifié':
        return 'Non spécifié', 'Non spécifié'

    # Nettoyer le texte
    area_text = area_text.strip().lower()

    # Vérifier si c'est le format "à"
    if ' à ' in area_text:
        parts = area_text.split(' à ')
        if len(parts) >= 2:
            # Le gouvernorat est généralement la dernière partie
            gouvernorat = parts[-1].strip()
            # La délégation pourrait être dans la première partie
            delegation = parts[0].strip()
            return gouvernorat, delegation

    # Chercher le pattern commune, délégation avec virgule
    if ',' in area_text:
        parts = area_text.split(',')
        if len(parts) >= 2:
            gouvernorat = parts[0].strip()
            delegation = parts[1].strip()
            return gouvernorat, delegation

    # Si un seul élément, le considérer comme gouvernorat
    return area_text, 'Non spécifié'


def get_property_links(search_url, max_pages=3):
    """
    Extract property links from Mubawab search pages.
    Links are found in the 'linkref' attribute of div elements with class 'listingBox'.
    """
    all_links = []

    for page in range(1, max_pages + 1):
        if page == 1:
            page_url = search_url
        else:
            page_url = f"{search_url}:p:{page}"

        print(f"Fetching page {page}: {page_url}")

        try:
            response = requests.get(page_url, headers=HEADERS, timeout=10)
            response.raise_for_status()
        except requests.RequestException as e:
            print(f"  Failed to fetch page {page}: {e}")
            continue

        soup = BeautifulSoup(response.text, 'html.parser')
        listing_boxes = soup.find_all('div', class_='listingBox')

        for box in listing_boxes:
            linkref = box.get('linkref')
            if linkref:
                if not linkref.startswith('http'):
                    full_url = urljoin('https://www.mubawab.tn', linkref)
                else:
                    full_url = linkref
                all_links.append(full_url)

        print(f"  Found {len(listing_boxes)} listings on page {page}")

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
    all_text = soup.get_text().lower()

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

    price_elements = soup.find_all(['h3', 'span', 'div'], class_=re.compile(r'price|Price|PRIX', re.I))
    for element in price_elements:
        element_text = element.get_text().lower()
        if any(phrase in element_text for phrase in ['non spécifié', 'sur demande', 'négociation']):
            return True

    return False


def extract_etage(soup, description, property_type):
    """
    Extract floor information from property page.
    Returns numeric floor or None if not found.
    """
    # Si c'est une maison (type=0), retourner 0
    if property_type == 0:
        return 0

    # Method 1: Look for floor information in main features
    main_features_container = soup.find('div', class_='adFeatures')
    if main_features_container:
        # Chercher les DIV avec classe 'adMainFeature' (c'est le conteneur parent)
        main_features = main_features_container.find_all('div', class_='adMainFeature')

        for feat in main_features:
            # À l'intérieur de chaque 'adMainFeature', chercher 'adMainFeatureContent'
            content_div = feat.find('div', class_='adMainFeatureContent')
            if content_div:
                label_tag = content_div.find('p', class_='adMainFeatureContentLabel')
                value_tag = content_div.find('p', class_='adMainFeatureContentValue')

                if label_tag and value_tag:
                    label = label_tag.get_text(strip=True)
                    value = value_tag.get_text(strip=True)

                    # Chercher "Étage du bien" ou variantes
                    if label.lower() in ['étage du bien', 'étage', 'etage', 'niveau']:
                        # Extraire le numéro - gérer "1er", "2ème", etc.
                        numbers = re.findall(r'\d+', value)
                        if numbers:
                            return int(numbers[0])
                        # Si pas de nombre, vérifier si c'est "rez-de-chaussée" ou "rdc"
                        elif 'rez' in value.lower() or 'rdc' in value.lower():
                            return 0

    # Method 2: Look in description text
    if description:
        description_lower = description.lower()

        # Patterns améliorés pour détecter l'étage
        floor_patterns = [
            r'(\d+)(?:ᵉʳ|er|ème|ème étage|er étage|étage|e étage)',
            r'étage\s*(\d+)',
            r'niveau\s*(\d+)',
            r'au\s*(\d+)(?:ᵉʳ|er|ème)\s*étage',
            r'rez-de-chaussée',
            r'rdc',
            r'rez de chaussée',
            r'1er étage',
            r'2ème étage',
            r'3ème étage'
        ]

        for pattern in floor_patterns:
            matches = re.search(pattern, description_lower)
            if matches:
                if pattern in ['rez-de-chaussée', 'rdc', 'rez de chaussée']:
                    return 0
                elif matches.group(1):
                    return int(matches.group(1))

        # Recherche spécifique pour "1er", "2ème", etc.
        ordinal_pattern = r'(\d+)(?:ᵉʳ|er|ème|e)'
        ordinal_match = re.search(ordinal_pattern, description_lower)
        if ordinal_match:
            # Vérifier si c'est bien un étage (pas une chambre, etc.)
            context = description_lower[
                max(0, ordinal_match.start() - 10):min(len(description_lower), ordinal_match.end() + 10)]
            if any(keyword in context for keyword in ['étage', 'niveau', 'e étage', 'er étage', 'ème étage']):
                return int(ordinal_match.group(1))

    return None


def extract_description(soup):
    """
    Extract property description from the <p> tag inside <div class="blockProp">
    Returns the description text or empty string if not found.
    """
    # Method 1: Look for description in <div class="blockProp"> -> <p>
    block_prop_div = soup.find('div', class_='blockProp')
    if block_prop_div:
        # Find the <p> tag inside blockProp
        p_tags = block_prop_div.find_all('p')

        # Usually the description is in a <p> tag after the title
        # Skip the first p if it contains searchTitle or similar
        for p_tag in p_tags:
            # Get parent to check context
            parent = p_tag.parent
            if parent and 'blockProp' in parent.get('class', []):
                text = p_tag.get_text(strip=True)
                return text
    return ''


def scrape_property_page(url, property_type):
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

    if should_exclude_property(soup):
        print(f"  ⚠️  EXCLUDED: Property under construction or price not specified")
        return None

    data = {'url': url, 'type': property_type}

    # --- 1. EXTRACT PRICE ---
    price_tag = soup.find('h3', class_='orangeTit')
    if price_tag:
        price_text = price_tag.get_text(strip=True).replace(u'\xa0', ' ')
        if any(phrase in price_text.lower() for phrase in ['non spécifié', 'sur demande', 'négociation']):
            print(f"  ⚠️  EXCLUDED: Invalid price format: {price_text}")
            return None

        price_numeric = re.sub(r'[^\d]', '', price_text)
        data['price'] = int(price_numeric) if price_numeric else 0
    else:
        print(f"  ⚠️  EXCLUDED: No price found")
        return None

    # --- 2. EXTRACT LOCATION FROM greyTit ---
    location_tag = soup.find('h3', class_='greyTit')
    if location_tag:
        area_text = location_tag.get_text(strip=True)
        # Nettoyer le texte - enlever les espaces excessifs et nouvelles lignes
        area_text = ' '.join(area_text.split())

        # Extraire gouvernorat et délégation
        gouvernorat, delegation = extract_governorat_delegation(area_text)
        data['gouvernorat'] = gouvernorat
        data['delegation'] = delegation
    else:
        # Fallback: chercher dans d'autres endroits
        location_block = soup.find('div', class_='blockProp mapBlockProp')
        if location_block:
            area_tag = location_block.find('h4', class_='titBlockProp')
            if area_tag:
                area_text = area_tag.get_text(strip=True)
                data['area'] = area_text
                gouvernorat, delegation = extract_governorat_delegation(area_text)
                data['gouvernorat'] = gouvernorat
                data['delegation'] = delegation
            else:
                data['area'] = 'Non spécifié'
                data['gouvernorat'] = 'Non spécifié'
                data['delegation'] = 'Non spécifié'
        else:
            data['area'] = 'Non spécifié'
            data['gouvernorat'] = 'Non spécifié'
            data['delegation'] = 'Non spécifié'

    # --- 3. EXTRACT CORE DETAILS ---
    details_container = soup.find('div', class_='disFlex adDetails')
    if details_container:
        for detail in details_container.find_all('div', class_='adDetailFeature'):
            text = detail.get_text(" ", strip=True)
            icon = detail.find('i')
            icon_class = icon['class'] if icon else []

            if 'icon-triangle' in str(icon_class) or 'm²' in text:
                numbers = re.findall(r'\d+', text)
                data['surface_totale'] = int(numbers[0]) if numbers else 0
            elif 'icon-bed' in str(icon_class) or 'Chambres' in text:
                numbers = re.findall(r'\d+', text)
                data['nombre_chambres'] = int(numbers[0]) if numbers else 0
            elif 'icon-bath' in str(icon_class) or 'Salle de bain' in text:
                numbers = re.findall(r'\d+', text)
                data['nombre_salle_bain'] = int(numbers[0]) if numbers else 1

    # --- 4. EXTRACT DESCRIPTION ---
    data['description'] = extract_description(soup)


    # --- 5. EXTRACT ETAGE ---
    data['etage'] = extract_etage(soup, data['description'], data['type'])


    # --- 6. EXTRACT PROPERTY TYPE, CONDITION, STANDING ---
    data['neuf'] = 0
    data['haut_standing'] = 0

    main_features_container = soup.find('div', class_='adFeatures')
    if main_features_container:
        main_features = main_features_container.find_all('div', class_='adMainFeature')
        for feat in main_features:
            label_tag = feat.find('p', class_='adMainFeatureContentLabel')
            value_tag = feat.find('p', class_='adMainFeatureContentValue')

            if label_tag and value_tag:
                label = label_tag.get_text(strip=True)
                value = value_tag.get_text(strip=True)

                if label == 'Etat':
                    if 'construction' in value.lower():
                        print(f"   EXCLUDED: Under construction (Etat: {value})")
                        return None
                    if value.lower() in ['nouveau', 'neuf', 'rénové', 'renove',"Project neuf"]:
                        data['neuf'] = 1
                elif label == 'Standing':
                    if 'haut' in value.lower() or 'standing' in value.lower():
                        data['haut_standing'] = 1


    # --- 7. EXTRACT AMENITIES ---
    # Initialiser toutes les aménités à 0
    requested_amenities = ['parking', 'piscine', 'vue_panoramique', 'jardin',
                           'climatisation', 'chauffage', 'ascenseur', 'balcon', 'terrasse']

    for amenity in requested_amenities:
        data[amenity] = 0

    # Chercher dans les conteneurs adFeatures
    amenities_containers = soup.find_all('div', class_='adFeatures')

    for container in amenities_containers:
        # Chercher les adFeature
        ad_features = container.find_all('div', class_='adFeature')
        for feature in ad_features:
            # Extraire TOUT le texte de ce feature
            feature_text = feature.get_text(strip=True).lower()
            # Vérifier chaque aménité dans le texte
            if 'jardin' in feature_text:
                data['jardin'] = 1
            if 'parking' in feature_text:
                data['parking'] = 1
            if 'piscine' in feature_text:
                data['piscine'] = 1
            if 'climatisation' in feature_text:
                data['climatisation'] = 1
            if 'chauffage' in feature_text:
                data['chauffage'] = 1
            if 'ascenseur' in feature_text:
                data['ascenseur'] = 1
            if 'balcon' in feature_text:
                data['balcon'] = 1
            if 'terrasse' in feature_text:
                data['terrasse'] = 1

    # Vérifier aussi dans les éléments individuels avec la classe fSize11
    all_amenity_texts = soup.find_all('p', class_='fSize11')
    for text_elem in all_amenity_texts:
        text = text_elem.get_text(strip=True).lower()
        if 'jardin' in text:
            data['jardin'] = 1
        if 'parking' in text:
            data['parking'] = 1
        if 'piscine' in text:
            data['piscine'] = 1
        if 'climatisation' in text:
            data['climatisation'] = 1
        if 'chauffage' in text:
            data['chauffage'] = 1
        if 'ascenseur' in text:
            data['ascenseur'] = 1
        if 'balcon' in text:
            data['balcon'] = 1
        if 'terrasse' in text:
            data['terrasse'] = 1

    # Vérifier aussi dans la description
    description_text = data.get('description', '').lower()
    if description_text:
        if 'jardin' in description_text:
            data['jardin'] = 1
        if 'parking' in description_text:
            data['parking'] = 1
        if 'piscine' in description_text:
            data['piscine'] = 1
        if 'climatisation' in description_text:
            data['climatisation'] = 1
        if 'chauffage' in description_text:
            data['chauffage'] = 1
        if 'ascenseur' in description_text:
            data['ascenseur'] = 1
        if 'balcon' in description_text:
            data['balcon'] = 1
        if 'terrasse' in description_text:
            data['terrasse'] = 1

    # DÉTECTION AMÉLIORÉE POUR VUE PANORAMIQUE
    vue_keywords = [
        'vue panoramique',
        'vue magnifique',
        'vue exceptionnelle',
        'vue splendide',
        'vue imprenable',
        'vue dégagée',
        'vue mer',
        'vue sur mer',
        'vue plage',
        'vue sur la plage',
        'vue montagne',
        'vue sur les montagnes',
        'vue campagne',
        'vue sur la campagne',
        'vue lac',
        'vue sur le lac',
        'vue jardin',
        'vue sur le jardin',
        'vue piscine',
        'vue sur la piscine',
        'panoramique',
        'panorama',
        'vue 360',
        'vue à 360°'
    ]

    all_page_text = soup.get_text().lower()
    # Vérifier chaque mot-clé
    for keyword in vue_keywords:
        if keyword in all_page_text:
            data['vue_panoramique'] = 1
            break  # Stop au premier match

    # Vérification spéciale pour mots séparés
    if data['vue_panoramique'] == 0:
        if ('vue' in all_page_text and any(word in all_page_text for word in
                                           ['magnifique', 'exceptionnelle', 'splendide', 'imprenable', 'dégagée'])):
            data['vue_panoramique'] = 1
        elif ('vue' in all_page_text and any(
                word in all_page_text for word in ['mer', 'plage', 'montagne', 'campagne', 'lac', 'jardin'])):
            data['vue_panoramique'] = 1

    # --- 8. FILL MISSING VALUES ---
    requested_fields = {
        'surface_totale': 0,
        'nombre_chambres': 0,
        'nombre_salle_bain': 1,
        'parking': 0,
        'piscine': 0,
        'jardin': 0,
        'balcon': 0,
        'terrasse': 0,
        'ascenseur': 0,
        'climatisation': 0,
        'chauffage': 0,
        'vue_panoramique': 0,
        'neuf': 0,
        'haut_standing': 0,
        'price': 0,
        'etage': None,
        'gouvernorat': 'Non spécifié',
        'delegation': 'Non spécifié',
        'description': '',
        'area': 'Non spécifié'
    }

    for field, default_value in requested_fields.items():
        if field not in data:
            data[field] = default_value

    print(
        f"   INCLUDED: {data.get('surface_totale', 0)}m², "
        f"{data.get('nombre_chambres', 0)} chambres, "
        f"{data.get('price', 0):,} TND"
        )
    return data


def scrape_mubawab(search_urls, filenames, max_pages):
    """
    Main function to scrape Mubawab properties with exclusion filters.
    Supports multiple search URLs.
    """
    all_results = []

    for search_url, filename, property_type in zip(search_urls, filenames, [0, 1]):
        print(f"\n{'=' * 80}")
        print(f"SCRAPING: {search_url}")
        property_type_name = 'Maison' if property_type == 0 else 'Appartement'
        print(f"PROPERTY TYPE: {property_type_name}")
        print(f"{'=' * 80}")

        property_urls = get_property_links(search_url, max_pages=max_pages[property_type_name])

        if not property_urls:
            print("No property links found!")
            continue

        all_properties_data = []
        excluded_count = 0
        included_count = 0

        for i, url in enumerate(property_urls):
            print(f"[{i + 1}/{len(property_urls)}] ", end="")
            property_data = scrape_property_page(url, property_type)

            if property_data is None:
                excluded_count += 1
            else:
                all_properties_data.append(property_data)
                included_count += 1

        print(f"\n{'=' * 60}")
        print(f"SCRAPING SUMMARY FOR {'MAISONS' if property_type == 0 else 'APPARTEMENTS'}:")
        print(f"{'=' * 60}")
        print(f"Total URLs processed: {len(property_urls)}")
        print(f"Included properties: {included_count}")
        print(f"Excluded properties: {excluded_count}")
        if (included_count + excluded_count) > 0:
            print(f"Inclusion rate: {(included_count / (included_count + excluded_count)) * 100:.1f}%")

        if all_properties_data:
            df = pd.DataFrame(all_properties_data)
            all_results.append(df)

            df.to_csv(filename, index=False, encoding='utf-8-sig')
            print(f"\nData saved to: {filename}")

    if all_results:
        combined_df = pd.concat(all_results, ignore_index=True)

        print(f"\n{'=' * 80}")
        print("FINAL COMBINED STATISTICS:")
        print(f"{'=' * 80}")

        if 'type' in combined_df.columns:
            maison_count = combined_df[combined_df['type'] == 0].shape[0]
            appart_count = combined_df[combined_df['type'] == 1].shape[0]
            print(f"\nBY PROPERTY TYPE:")
            print(f"• Maisons: {maison_count}")
            print(f"• Appartements: {appart_count}")

        if 'gouvernorat' in combined_df.columns:
            print(f"\nTOP 10 GOUVERNORATS:")
            top_gouvernorats = combined_df['gouvernorat'].value_counts().head(10)
            for gouvernorat, count in top_gouvernorats.items():
                print(f"  {gouvernorat}: {count}")

        if 'haut_standing' in combined_df.columns and 'neuf' in combined_df.columns:
            luxury_count = combined_df['haut_standing'].sum()
            neuf_count = combined_df['neuf'].sum()
            total_count = len(combined_df)

            print(f"\nQUALITY INDICATORS:")
            print(f"• Haut standing properties: {luxury_count} ({luxury_count / total_count * 100:.1f}%)")
            print(f"• New properties (neuf): {neuf_count} ({neuf_count / total_count * 100:.1f}%)")

        combined_filename = 'mubawab_combined_properties.csv'

        # Réorganiser les colonnes dans l'ordre demandé
        column_order = [
            'type', 'price', 'surface_totale', 'nombre_chambres',
            'nombre_salle_bain', 'etage', 'parking', 'piscine', 'jardin',
            'balcon', 'terrasse', 'ascenseur', 'climatisation', 'chauffage',
            'vue_panoramique', 'neuf', 'haut_standing', 'gouvernorat',
            'delegation', 'url', 'description', 'area'
        ]

        # Garder seulement les colonnes qui existent
        existing_columns = [col for col in column_order if col in combined_df.columns]
        combined_df = combined_df[existing_columns]

        combined_df.to_csv(combined_filename, index=False, encoding='utf-8-sig')
        print(f"\nCombined data saved to: {combined_filename}")

        print(f"\nSAMPLE OF COMBINED DATA (first 3 rows):")
        print(combined_df.head(3).to_string(index=False))

        return combined_df
    else:
        print("\nNo data collected from any search URLs.")
        return None


# --- CONFIGURATION ET EXÉCUTION ---
if __name__ == '__main__':
    SEARCH_URLS = [
        "https://www.mubawab.tn/fr/sc/maisons-a-vendre",
        "https://www.mubawab.tn/fr/sc/appartements-a-vendre"
    ]

    FILENAMES = [
        'maisons_mubawab.csv',
        'appartements_mubawab.csv'
    ]

    MAX_PAGES = {'Maison': 43, 'Appartement':153}  # Nombre de pages pour chaque type


    results = scrape_mubawab(
        search_urls=SEARCH_URLS,
        filenames=FILENAMES,
        max_pages=MAX_PAGES
    )

    if results is not None and len(results) > 0:
        print("\n" + "=" * 80)
        print("SCRAPING COMPLETED SUCCESSFULLY!")
        print("=" * 80)
        print(f"• Total valid properties collected: {len(results)}")
