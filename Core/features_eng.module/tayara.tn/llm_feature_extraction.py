import json
import os
from typing import Dict, Any, List

import pandas as pd
from groq import Groq
FICHIER_RESULTATS=r"llm_extracted_features_raw_data.json"
# Initialisation du client Groq

attributs = [
    "prix",
    "categorie",
    "transaction_type",
    "latitude",
    "longitude",
    "surface",
    "nombre_des_chambres",
    "nombre_des_salles_de_bains",
    "haut_standing",
    "terrasse",
    "balcon",
    "etage",
    "parking",
    "ascenseur",
    "jardin",
    "vue_panoramique",
    "climatiseur",
    "chauffage_central",
    "piscine"
]


def extraire_attributs_immobiliers(annonce: str) -> Dict[str, Any]:
    """
    Extrait les attributs structurés d'une annonce immobilière en français
    """
    
    
    annonce = annonce.encode('utf-8', errors='ignore').decode('utf-8')
    
    prompt = f"""
    Tu es un assistant expert en extraction d'informations immobilières.
    
    À PARTIR DE CETTE ANNONCE :
    \"\"\"{annonce}\"\"\"
    
    EXTRAIS LES ATTRIBUTS SUIVANTS sous forme de JSON structuré :
    
    LA LISTE  DES ATTRIBUTS À EXTRAIRE :
    {', '.join(attributs)}
   
    
    RÈGLES IMPORTANTES :
    - Pour les nombres : mettre 0 si non mentionné
    - Pour les booléens : False si non mentionné, true seulement si explicitement mentionné
    - "S+2" = 2 chambres, "S+3" = 3 chambres, "F2" = 2 chambres, "F3" = 3 chambres
    - Interprète intelligemment les abréviations et expressions de la ou les langues du texte.
    -vue_panoramique: maison sur mer, sur montagne, pieds dans l'eau (maison avec vue)
    -transaction_type: vendre (à vendre) , location (à louer)
    
    FORMAT DE SORTIE EXACT :
    {{
    "prix": 0,
    "categorie": "maison | villa | appartement | autre",
    "transaction_type": "vendre | location",
    "latitude": 0,
    "longitude": 0,
    "surface": 0,
    "nombre_des_chambres": 0,
    "nombre_des_salles_de_bains": 0,
    "haut_standing": False,
    "terrasse": False,
    "balcon": False,
    "etage": 0,
    "parking": False,
    "ascenseur": False,
    "jardin": False,
    "vue_panoramique": False,
    "climatiseur": False,
    "chauffage_central": False,
    "piscine": False
}}
    
    Fournis UNIQUEMENT le JSON, sans texte supplémentaire.
    """
    prompt = prompt.encode('utf-8', errors='ignore').decode('utf-8')
            # Appel à l'API Groq avec GPT-OSS-120b
    completion = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0,  # Très bas pour des extractions consistantes
        stream=False
    )
    
    # Récupération de la réponse
    response_text = completion.choices[0].message.content
    
    # Nettoyage du JSON
    response_text = response_text.strip()
    if "```json" in response_text:
        json_start = response_text.find("```json") + 7
        json_end = response_text.find("```", json_start)
        json_text = response_text[json_start:json_end].strip()
    elif "```" in response_text:
        json_start = response_text.find("```") + 3
        json_end = response_text.find("```", json_start)
        json_text = response_text[json_start:json_end].strip()
    else:
        json_text = response_text
    
    # Parsing du JSON
    result = json.loads(json_text)
    
    # Vérification que tous les attributs sont présents
    for attribut in attributs:
        if attribut not in result:
            result[attribut] = 0 if attribut in ["surface", "nombre_des_chambres", "nombre_des_salles_de_bains", "etage"] else False
    
    return result
        


# Fonction utilitaire pour traiter plusieurs annonces
def traiter_annonces(df: pd.DataFrame, colonne_texte: str = "texte", batch_size: int =2) -> List[Dict[str, Any]]:
    """
    Traite les annonces d'un DataFrame par batch et retourne les attributs extraits.
    Les résultats sont sauvegardés dans FICHIER_RESULTATS.
    
    :param df: DataFrame contenant les annonces avec une colonne 'id' et une colonne texte
    :param colonne_texte: nom de la colonne contenant le texte de l'annonce
    :param batch_size: nombre d'annonces à traiter avant de sauvegarder
    :return: liste des dictionnaires d'attributs extraits
    """
    dossier_resultats = os.path.dirname(FICHIER_RESULTATS)
    if dossier_resultats and not os.path.exists(dossier_resultats):
        os.makedirs(dossier_resultats, exist_ok=True)

    # Charger les résultats existants
    if os.path.exists(FICHIER_RESULTATS):
        with open(FICHIER_RESULTATS, 'r', encoding='utf-8') as f:
            try:
                data_existant = json.load(f)
            except:
                data_existant = {}
    else:
        data_existant = {}

    resultats = []
    batch_count = 0

    for index, row in df.iterrows():
        annonce_id = str(row['id'])
        annonce_texte = str(row[colonne_texte]).encode('utf-8', errors='ignore').decode('utf-8')

        # Vérifier si déjà traité
        if annonce_id in data_existant:
            print(f"✓ Annonce {annonce_id} déjà traitée")
            continue

        print(f"🔍 Traitement de l'annonce {annonce_id}...")

        # Extraire les attributs
        try:
            attributs = extraire_attributs_immobiliers(annonce_texte)
        except Exception as e:
            msg = str(e)
            if '429' in msg:
                print(f"Erreur llm (429) : {msg}. Arrêt du traitement.")
                return  # exit the function
            else:
                print(f"Erreur lors de l'extraction : {msg}. On continue...")
                continue  # skip this annonce



        # Ajouter l'ID et le texte original (tronqué)
        attributs_complet = {
            "id": annonce_id,
            "texte": annonce_texte[:200] + "..." if len(annonce_texte) > 200 else annonce_texte,
            **attributs
        }

        # Ajouter au dictionnaire existant
        data_existant[annonce_id] = attributs_complet
        resultats.append(attributs_complet)
        batch_count += 1

        # Sauvegarder par batch
        if batch_count >= batch_size:
            with open(FICHIER_RESULTATS, 'w', encoding='utf-8') as f:
                json.dump(data_existant, f, indent=2, ensure_ascii=False)
            print(f"💾 Batch de {batch_count} annonces sauvegardé.")
            batch_count = 0  # reset pour le prochain batch

        print(f"✅ Annonce {annonce_id} traitée")

    # Sauvegarder les annonces restantes si batch incomplet
    if batch_count > 0:
        with open(FICHIER_RESULTATS, 'w', encoding='utf-8') as f:
            json.dump(data_existant, f, indent=2, ensure_ascii=False)
        print(f"💾 Dernier batch de {batch_count} annonces sauvegardé.")

    return resultats



# Exemple d'utilisation
if __name__ == "__main__":
    # Exemple d'annonce
    annonce_exemple = """
    avendre magnifique duplex haut standing de 85m², 
    situé au 3ème étage avec ascenseur dans résidence sécurisée.
    Composition : S+2 (2 chambres), 1 salle de bains, séjour avec terrasse.
    Appartement entièrement climatisé avec chauffage central.
    Belles prestations : parquet, double vitrage.
    Parking privé inclus. Vue dégagée sur la ville.
    Prix : 250 000€.
    """
    
    # Extraction des attributs
    resultat = extraire_attributs_immobiliers(annonce_exemple)
    
    # Affichage du résultat
    print("Attributs extraits :")
    print(json.dumps(resultat, indent=2, ensure_ascii=False))
    
    # Affichage formaté
    print("\n" + "="*50)
    print("RÉSUMÉ DE L'EXTRACTION :")
    print("="*50)
    print(f"Surface : {resultat['surface']} m²")
    print(f"Chambres : {resultat['nombre_des_chambres']}")
    print(f"Salles de bains : {resultat['nombre_des_salles_de_bains']}")
    print(f"Haut standing : {'OUI' if resultat['haut_standing'] else 'NON'}")
    print(f"Terrasse : {'OUI' if resultat['terrasse'] else 'NON'}")
    print(f"Balcon : {'OUI' if resultat['balcon'] else 'NON'}")
    print(f"Étage : {resultat['etage']}")
    print(f"Parking : {'OUI' if resultat['parking'] else 'NON'}")
    print(f"Ascenseur : {'OUI' if resultat['ascenseur'] else 'NON'}")
    print(f"Jardin : {'OUI' if resultat['jardin'] else 'NON'}")
    print(f"Vue panoramique : {'OUI' if resultat['vue_panoramique'] else 'NON'}")
    print(f"Climatisation : {'OUI' if resultat['climatiseur'] else 'NON'}")
    print(f"Chauffage central : {'OUI' if resultat['chauffage_central'] else 'NON'}")
    print(f"transaction : { resultat['transaction_type']}")
    print(f"categorie : { resultat['categorie']}")