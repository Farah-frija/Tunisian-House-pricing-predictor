import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, parse_qs, urlencode, urlunparse
import json
import time

def scrape_page_range(base_url, category_name, start_page=1, end_page=10):
    """Scrape a specific range of pages"""
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    all_results = []
    
    print(f"Scraping {category_name}: pages {start_page} to {end_page}")
    
    for page_num in range(start_page, end_page + 1):
        # Construct URL for this page
        parsed = urlparse(base_url)
        params = parse_qs(parsed.query)
        params['page'] = [str(page_num)]
        
        # Reconstruct URL
        new_query = urlencode(params, doseq=True)
        url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}?{new_query}"
        
        print(f"  Page {page_num}: {url}")
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract post URLs
            post_urls = []
            seen_urls = set()
            
            # Find all post links
            for link in soup.find_all('a', href=True):
                href = link['href']
                if '/item/' in href and '?' not in href:
                    full_url = urljoin(url, href)
                    if full_url not in seen_urls:
                        seen_urls.add(full_url)
                        post_urls.append(full_url)
            
            # Remove duplicates
            post_urls = list(set(post_urls))
            
            result = {
                'url': url,
                'page_number': page_num,
                'category': category_name,
                'post_urls': post_urls,
                'total_posts': len(post_urls),
                'scraped_at': time.strftime('%Y-%m-%d %H:%M:%S')
            }
            
            print(f"    Found {len(post_urls)} posts")
            
            all_results.append(result)
            
        except Exception as e:
            print(f"    Error: {e}")
            all_results.append({
                'url': url,
                'page_number': page_num,
                'category': category_name,
                'post_urls': [],
                'total_posts': 0,
                'error': str(e),
                'scraped_at': time.strftime('%Y-%m-%d %H:%M:%S')
            })
        
        # Delay between requests
        time.sleep(1)
    
    return all_results

def main_simple_range():
    """Main function with specified page ranges"""
    
    # Define what to scrape
    scraping_tasks = [
        {
            'base_url': "https://www.tayara.tn/listing/c/immobilier/maisons-et-villas/?Type+de+transaction=%C3%80+Vendre&minChambres=1&minSalles+de+bains=1",
            'category': 'maison_villas',
            'start_page': 1,
            'end_page': 100  # Scrape first 5 pages
        },
        {
            'base_url': "https://www.tayara.tn/listing/c/immoneuf/",
            'category': 'immobilier_neuf',
            'start_page': 1,
            'end_page': 100 # Scrape first 3 pages
        }
    ]
    
    all_data = {}
    
    for task in scraping_tasks:
        print(f"\n{'='*50}")
        print(f"Starting: {task['category']}")
        
        results = scrape_page_range(
            task['base_url'],
            task['category'],
            task['start_page'],
            task['end_page']
        )
        
        all_data[task['category']] = results
        
        print(f"Completed: {task['category']}")
        print(f"{'='*50}")
        
        # Pause between categories
        time.sleep(2)
    
    # Save to JSON
    output = {
        'metadata': {
            'total_categories': len(all_data),
            'scraping_date': time.strftime('%Y-%m-%d'),
            'scraping_time': time.strftime('%H:%M:%S')
        },
        'data': all_data
    }
    
    with open('tayara_pages_range.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ Data saved to 'tayara_pages_range.json'")
    
    # Print summary
    total_posts = 0
    for category, pages in all_data.items():
        category_posts = sum(page['total_posts'] for page in pages)
        total_posts += category_posts
        print(f"{category}: {len(pages)} pages, {category_posts} posts")
    
    print(f"\n📊 TOTAL: {sum(len(pages) for pages in all_data.values())} pages, {total_posts} posts")

if __name__ == "__main__":
    # Run the simple range version
    main_simple_range()