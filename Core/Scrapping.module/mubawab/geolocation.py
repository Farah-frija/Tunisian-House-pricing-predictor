# simple_osm_geocoder.py

import pandas as pd
import requests
import time
import pickle
import os


class SimpleOSMGeocoder:
    def __init__(self, cache_file='osm_cache.pkl'):
        self.url = "https://nominatim.openstreetmap.org/search"
        self.headers = {'User-Agent': 'MubawabGeocoder/1.0'}
        self.cache_file = cache_file
        self.cache = self.load_cache()

    def load_cache(self):
        if os.path.exists(self.cache_file):
            with open(self.cache_file, 'rb') as f:
                return pickle.load(f)
        return {}

    def save_cache(self):
        with open(self.cache_file, 'wb') as f:
            pickle.dump(self.cache, f)

    def get_coordinates(self, gouvernorat, delegation):
        """Get coordinates with caching and fallback"""
        # Create cache key
        cache_key = f"{gouvernorat}_{delegation}"

        # Check cache
        if cache_key in self.cache:
            return self.cache[cache_key]

        # Wait to respect rate limit
        time.sleep(1)

        # Try with delegation + gouvernorat first
        if delegation and delegation != 'Non spécifié':
            query = f"{delegation}, {gouvernorat}, Tunisie"
            coords = self.search_osm(query)
            if coords:
                self.cache[cache_key] = coords
                return coords

        # Fallback to gouvernorat only
        query = f"{gouvernorat}, Tunisie"
        coords = self.search_osm(query)

        if coords:
            self.cache[cache_key] = coords

        return coords or {'latitude': None, 'longitude': None}

    def search_osm(self, query):
        """Search OpenStreetMap for coordinates"""
        params = {
            'q': query,
            'format': 'json',
            'limit': 1,
            'countrycodes': 'tn'
        }

        try:
            response = requests.get(self.url, params=params,
                                    headers=self.headers, timeout=10)

            if response.status_code == 200:
                data = response.json()
                if data:
                    print(data)
                    return {
                        'latitude': float(data[0]['lat']),
                        'longitude': float(data[0]['lon'])
                    }
        except:
            pass

        return None


def add_coordinates_to_data(input_file, output_file):
    """Add coordinates to Mubawab data"""
    # Load data
    df = pd.read_csv(input_file)

    # Initialize geocoder
    geocoder = SimpleOSMGeocoder()

    # Add coordinates
    coords_list = []
    for i, row in df.iterrows():
        print(f"Processing {i + 1}/{len(df)}")
        coords = geocoder.get_coordinates(
            row['gouvernorat'],
            row['delegation']
        )
        coords_list.append(coords)

        # Save cache every 50 rows
        if (i + 1) % 50 == 0:
            geocoder.save_cache()

    # Add to DataFrame
    df['latitude'] = [c['latitude'] for c in coords_list]
    df['longitude'] = [c['longitude'] for c in coords_list]

    # Save
    df.to_csv(output_file, index=False)
    geocoder.save_cache()

    print(f"✅ Saved {len(df)} properties with coordinates")
    print(f"✅ Cache saved with {len(geocoder.cache)} locations")


# Usage
if __name__ == "__main__":
    add_coordinates_to_data(
        'mubawab_transformed_properties.csv',
        'mubawab_with_coordinates.csv'
    )