# simple_api_filter.py

import pandas as pd
import requests
import time
import json
import os
from collections import defaultdict


def simple_filter_grand_tunis(input_file, output_file, radius=5):
    """
    Optimized version that groups properties by coordinates to reduce API calls.
    Handles the actual API response structure.
    """

    print("Filtering properties in Grand Tunis...")

    # Load data
    df = pd.read_csv(input_file)

    # API configuration
    base_url = "https://tn-municipality-api.vercel.app/api/municipalities/near"
    headers = {'User-Agent': 'MubawabFilter/1.0'}

    # Target gouvernorats
    target_gouvernorats = ['Tunis', 'Ariana', 'Manouba', 'Ben Arous']

    # Group rows by coordinates
    print("Grouping properties by coordinates...")
    coord_groups = defaultdict(list)

    for idx, row in df.iterrows():
        lat = row['latitude']
        lon = row['longitude']

        if pd.isna(lat) or pd.isna(lon):
            continue

        # Round coordinates to avoid floating-point precision issues
        # Using 5 decimal places (~1 meter precision)
        coord_key = (round(float(lat), 5), round(float(lon), 5))
        coord_groups[coord_key].append((idx, row))

    print(f"Grouped {len(df)} properties into {len(coord_groups)} unique coordinate groups")

    # Cache for coordinate results
    coord_cache = {}

    # Results
    filtered_rows = []
    api_calls = 0
    processed_rows = 0

    # Process each unique coordinate
    for coord_idx, (coord_key, rows) in enumerate(coord_groups.items()):
        lat, lon = coord_key

        print(f"Processing coordinate group {coord_idx}/{len(coord_groups)} - {len(rows)} properties at this location")

        # Check cache first
        if coord_key in coord_cache:
            in_target = coord_cache[coord_key]['in_target']
            corrected_gov = coord_cache[coord_key]['corrected_gov']
        else:
            # Call API for this coordinate
            params = {'lat': lat, 'lng': lon, 'radius': radius}

            try:
                time.sleep(0.2)  # Rate limiting
                api_calls += 1

                response = requests.get(base_url, params=params, headers=headers, timeout=10)

                if response.status_code == 200:
                    data = response.json()
                    # Check if in target gouvernorat
                    in_target = False
                    corrected_gov = None

                    # Based on the example response, it's a list of municipalities
                    for municipality in data:
                        # Try different possible field names for governorate
                        gov_name = None

                        # Check if municipality has governorate info directly
                        if isinstance(municipality, dict):
                            # Option 1: 'Name' field might contain governorate name
                            if 'Name' in municipality:
                                gov_name = municipality['Name']

                            # Option 2: Check for governorate field
                            elif 'governorate' in municipality and isinstance(municipality['governorate'], dict):
                                if 'name' in municipality['governorate']:
                                    gov_name = municipality['governorate']['name']

                            # Option 3: Check for delegation governorate info
                            elif 'Delegations' in municipality and municipality['Delegations']:
                                # Take first delegation as representative
                                first_delegation = municipality['Delegations'][0]
                                if isinstance(first_delegation, dict) and 'governorate' in first_delegation:
                                    gov_name = first_delegation['governorate'].get('name', '')

                        if gov_name:
                            # Clean the governorate name
                            gov_name_clean = gov_name.strip().upper()

                            # Check if it's in target gouvernorats
                            for target in target_gouvernorats:
                                if target.upper() in gov_name_clean:
                                    in_target = True
                                    corrected_gov = target
                                    break

                            if in_target:
                                break

                    # Cache the result
                    coord_cache[coord_key] = {
                        'in_target': in_target,
                        'corrected_gov': corrected_gov,
                        'raw_response': data  # Store for debugging
                    }
                else:
                    coord_cache[coord_key] = {
                        'in_target': False,
                        'corrected_gov': None
                    }

            except Exception as e:
                print(f"Error calling API for ({lat}, {lon}): {str(e)}")
                # If API call fails, mark as not in target
                coord_cache[coord_key] = {
                    'in_target': False,
                    'corrected_gov': None
                }
                continue

        # Process all rows with this coordinate
        if in_target and corrected_gov:
            for idx, row in rows:
                row_copy = row.copy()
                if 'gouvernorat' in row_copy:
                    row_copy['gouvernorat'] = corrected_gov
                filtered_rows.append(row_copy)

        processed_rows += len(rows)

    print(f"Made {api_calls} API calls for {len(coord_groups)} unique coordinates")
    print(f"Processed {processed_rows} properties total")

    # Create new DataFrame
    if filtered_rows:
        filtered_df = pd.DataFrame(filtered_rows)

        # Save
        filtered_df.to_csv(output_file, index=False)
        print(f"✅ Saved {len(filtered_df)} properties to {output_file}")
        print(f"API calls reduced from ~{len(df)} to {api_calls}")

        # Print some statistics
        print("\n📊 Statistics:")
        print(f"   Total properties: {len(df)}")
        print(f"   Unique coordinates: {len(coord_groups)}")
        print(f"   Properties in Grand Tunis: {len(filtered_df)}")
        print(f"   API calls saved: {len(df) - api_calls}")

        return filtered_df
    else:
        print("❌ No properties found in Grand Tunis")
        return None



# Quick test
if __name__ == "__main__":
    # Try the main version first
    result = simple_filter_grand_tunis(
        input_file='mubawab_with_coordinates.csv',
        output_file='mubawab_grand_tunis.csv'
    )
