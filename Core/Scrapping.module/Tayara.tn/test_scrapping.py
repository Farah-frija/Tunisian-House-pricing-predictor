import requests
from bs4 import BeautifulSoup
import json
import csv
import re
import time
from datetime import datetime

class TayaraScraper:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        }
    
    def extract_phone_numbers(self, text):
        """Extrait les numéros de téléphone du texte"""
        phone_patterns = [
            r'\+\d{2,3}\s?\d{2}\s?\d{3}\s?\d{3}',  # Format international
            r'\d{2}\s?\d{3}\s?\d{3}',  # Format local
            r'0\d\s?\d{3}\s?\d{3}',  # Format avec 0
        ]
        
        phones = []
        for pattern in phone_patterns:
            matches = re.findall(pattern, text)
            phones.extend(matches)
        
        return list(set(phones))  # Supprimer les doublons
    
    def scrape_ad(self, url, page_number=None, category=None):
        """Scrape une annonce individuelle"""
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            next_data_script = soup.find('script', {'id': '__NEXT_DATA__'})
            
            if not next_data_script:
                return None
            
            data = json.loads(next_data_script.string)
            props = data.get('props', {}).get('pageProps', {})
            
            ad_details = props.get('adDetails', {})
            ad_user_data = props.get('adUserData', {})
            
            # Extraire les téléphones supplémentaires de la description
            description = ad_details.get('description', '')
            additional_phones = self.extract_phone_numbers(description)
            
            result = {
                'url': url,
                'id': ad_details.get('id'),
                'title': ad_details.get('title'),
                'description': description,
                'price': ad_details.get('price'),
                'currency': 'TND',
                'category': category if category else ad_details.get('category'),
                'page_number': page_number,
                'published_date': ad_details.get('publishedOn'),
                'phone': ad_details.get('phone'),
                'additional_phones': additional_phones,
                'image_count': len(ad_details.get('images', [])),
                'images': ad_details.get('images', []),
                'location': ad_details.get('location', {}),
                'seller_name': ad_user_data.get('fullname'),
                'seller_email': ad_user_data.get('email'),
                'seller_phone': ad_user_data.get('phonenumber'),
                'seller_is_shop': ad_user_data.get('isShop'),
                'ad_params': ad_details.get('adParams', []),
                'sold': ad_details.get('sold'),
                'views': ad_details.get('views', 0),
                'favorites': ad_details.get('favorites', 0),
                'scraped_at': datetime.now().isoformat()
            }
            print(result['id'])
            if not result['id']:
                return None
            else:
                return result
            
        except Exception as e:
            print(f"Erreur lors du scraping de {url}: {str(e)}")
            return None
    
    def load_urls_from_json(self, json_file):
        """Charge les URLs depuis le fichier JSON de pages"""
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        urls_to_scrape = []
        
        # Extraire toutes les URLs d'annonces avec leurs pages et catégories
        for category, pages in data['data'].items():
            for page in pages:
                page_num = page['page_number']
                for ad_url in page['post_urls']:
                    urls_to_scrape.append({
                        'url': ad_url,
                        'page_number': page_num,
                        'category': category
                    })
        
        print(f"Chargé {len(urls_to_scrape)} URLs depuis {json_file}")
        return urls_to_scrape
    
    def scrape_ads_from_json(self, json_file, max_ads=None, delay=1.0):
        """Scrape les annonces depuis le fichier JSON de pages"""
        urls_data = self.load_urls_from_json(json_file)
        
        if max_ads:
            urls_data = urls_data[:max_ads]
        
        all_data = []
        
        for i, url_info in enumerate(urls_data, 1):
            url = url_info['url']
            page_num = url_info['page_number']
            category = url_info['category']
            
            print(f"[{i}/{len(urls_data)}] Scraping: {category} - Page {page_num}")
            
            data = self.scrape_ad(url, page_num, category)
            
            if data:
                all_data.append(data)
                print(f"✓ {data['title'][:50]}...")
            else:
                print(f"✗ Échec pour {url}")
            
            # Pause entre les requêtes
            if i < len(urls_data):
                time.sleep(delay)
        
        return all_data
    
    def save_to_csv(self, data_list, filename='tayara_ads.csv'):
        """Sauvegarde les données en CSV"""
        if not data_list:
            print("Aucune donnée à sauvegarder")
            return
        
        # Déterminer tous les champs possibles
        fieldnames = set()
        for data in data_list:
            fieldnames.update(data.keys())
        
        # Réorganiser les champs
        preferred_order = [
            'url', 'id', 'title', 'price', 'currency', 'category',
            'page_number', 'published_date', 'phone', 'seller_name', 
            'seller_phone', 'seller_is_shop', 'location', 'description'
        ]
        
        ordered_fields = [f for f in preferred_order if f in fieldnames]
        other_fields = sorted(f for f in fieldnames if f not in preferred_order)
        all_fields = ordered_fields + other_fields
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=all_fields)
            writer.writeheader()
            for data in data_list:
                writer.writerow(data)
        
        print(f"Données sauvegardées dans {filename} ({len(data_list)} annonces)")
    
    def save_to_json(self, data_list, filename='tayara_ads.json'):
        """Sauvegarde les données en JSON"""
        output = {
            'metadata': {
                'total_ads': len(data_list),
                'categories': list(set(ad['category'] for ad in data_list if ad.get('category'))),
                'pages': list(set(ad['page_number'] for ad in data_list if ad.get('page_number'))),
                'scraped_at': datetime.now().isoformat()
            },
            'ads': data_list
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        print(f"Données sauvegardées dans {filename}")

# Exécution principale
if __name__ == "__main__":
    scraper = TayaraScraper()
    
    print("=" * 60)
    print("TAYARA ADS SCRAPER FROM PAGES JSON")
    print("=" * 60)
    
    # Charger et scraper depuis le fichier JSON
    input_file = "tayara_pages_range.json"
    
    try:
        # Demander combien scraper
        print(f"\nFichier d'entrée: {input_file}")
        choice = input("Combien d'annonces scraper? (Entrez 'all' pour tout ou un nombre): ").strip()
        
        if choice.lower() == 'all':
            max_ads = None
        else:
            try:
                max_ads = int(choice)
            except:
                max_ads = 10
        
        # Scraper les annonces
        print(f"\nDébut du scraping...")
        all_data = scraper.scrape_ads_from_json(
            input_file, 
            max_ads=max_ads, 
            delay=1.5
        )
        
        # Sauvegarder les résultats
        if all_data:
            scraper.save_to_csv(all_data, 'tayara_ads_complete.csv')
            scraper.save_to_json(all_data, 'tayara_ads_complete.json')
            
            # Afficher un résumé
            print(f"\n=== RÉSUMÉ ===")
            print(f"Annonces scrapées: {len(all_data)}")
            print(f"Total d'images: {sum(ad['image_count'] for ad in all_data if ad.get('image_count'))}")
            
            # Statistiques par catégorie
            categories = {}
            for ad in all_data:
                cat = ad.get('category', 'Inconnu')
                categories[cat] = categories.get(cat, 0) + 1
            
            print(f"\nPar catégorie:")
            for cat, count in categories.items():
                print(f"  {cat}: {count} annonces")
            
            # Statistiques sur les prix
            prices = [ad['price'] for ad in all_data if ad.get('price')]
            if prices:
                print(f"\nPrix moyen: {sum(prices)/len(prices):.2f} TND")
                print(f"Prix max: {max(prices)} TND")
                print(f"Prix min: {min(prices)} TND")
            
            # Afficher un échantillon
            print(f"\nÉchantillon (3 premières annonces):")
            for i, ad in enumerate(all_data[:3], 1):
                print(f"\n{i}. {ad.get('title', 'Sans titre')}")
                print(f"   Prix: {ad.get('price', 'N/A')} TND")
                print(f"   Catégorie: {ad.get('category', 'N/A')}")
                print(f"   Page: {ad.get('page_number', 'N/A')}")
                print(f"   URL: {ad['url']}")
        else:
            print("Aucune annonce n'a été scrapée avec succès!")
            
    except FileNotFoundError:
        print(f"Erreur: Fichier {input_file} non trouvé!")
        print("Assurez-vous que le fichier tayara_pages_range.json existe dans le même dossier.")
    except Exception as e:
        print(f"Erreur: {e}")
