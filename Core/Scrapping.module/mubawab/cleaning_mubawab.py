# simple_transform.py

import pandas as pd
import numpy as np
import os


def transform_data_simple():
    """
    Simple version of the data transformation.
    """
    input_file = 'mubawab_combined_properties.csv'
    output_file = 'mubawab_transformed_properties.csv'

    print("Transforming Mubawab data to new format...")

    if not os.path.exists(input_file):
        print(f"Error: File '{input_file}' not found!")
        return False

    try:
        # Lire les données
        df = pd.read_csv(input_file, encoding='utf-8-sig')

        # Mapping des colonnes
        transformations = {
            'id': lambda x: range(1, len(x) + 1),
            'surface': lambda x: pd.to_numeric(x.get('surface_totale', 0), errors='coerce').fillna(0).astype(int),
            'nombre_des_chambres': lambda x: pd.to_numeric(x.get('nombre_chambres', 0), errors='coerce').fillna(
                0).astype(int),
            'nombre_des_salles_de_bains': lambda x: pd.to_numeric(x.get('nombre_salle_bain', 1),
                                                                  errors='coerce').fillna(1).astype(int),
            'haut_standing': lambda x: x.get('haut_standing', False).astype(bool),
            'terrasse': lambda x: x.get('terrasse', False).astype(bool),
            'balcon': lambda x: x.get('balcon', False).astype(bool),
            'etage': lambda x: pd.to_numeric(x.get('etage', 0), errors='coerce').fillna(0).astype(int),
            'parking': lambda x: x.get('parking', False).astype(bool),
            'ascenseur': lambda x: x.get('ascenseur', False).astype(bool),
            'jardin': lambda x: x.get('jardin', False).astype(bool),
            'vue_panoramique': lambda x: x.get('vue_panoramique', False).astype(bool),
            'climatiseur': lambda x: x.get('climatisation', False).astype(bool),
            'chauffage_central': lambda x: x.get('chauffage', False).astype(bool),
            'piscine': lambda x: x.get('piscine', False).astype(bool),
            'prix': lambda x: pd.to_numeric(x.get('price', 0), errors='coerce').fillna(0).astype(int),
            'categorie': lambda x: x.get('type', 0).map({0: 'maison', 1: 'appartement'}).fillna('maison'),
            'latitude': lambda x: pd.Series([np.nan] * len(x)),
            'longitude': lambda x: pd.Series([np.nan] * len(x)),
            'gouvernorat': lambda x: x.get('gouvernorat', 'Non spécifié').fillna('Non spécifié'),
            'delegation': lambda x: x.get('delegation', 'Non spécifié').fillna('Non spécifié'),
        }

        # Appliquer les transformations
        new_df = pd.DataFrame()

        for new_col, transform_func in transformations.items():
            new_df[new_col] = transform_func(df)
            print(f"Created column: {new_col}")

        # Réorganiser les colonnes
        column_order = [
            'id', 'surface', 'nombre_des_chambres', 'nombre_des_salles_de_bains',
            'haut_standing', 'terrasse', 'balcon', 'etage', 'parking', 'ascenseur',
            'jardin', 'vue_panoramique', 'climatiseur', 'chauffage_central', 'piscine',
            'prix', 'categorie', 'latitude', 'longitude', 'gouvernorat', 'delegation'
        ]

        new_df = new_df[[col for col in column_order if col in new_df.columns]]

        # Sauvegarder
        new_df.to_csv(output_file, index=False, encoding='utf-8-sig')

        print(f"\n✅ Transformation complete!")
        print(f"   Original data: {df.shape}")
        print(f"   Transformed data: {new_df.shape}")
        print(f"   Saved to: {output_file}")

        # Afficher un aperçu
        print("\nPreview:")
        print(new_df.head().to_string(index=False))

        return True

    except Exception as e:
        print(f"Error: {e}")
        return False


if __name__ == "__main__":
    transform_data_simple()