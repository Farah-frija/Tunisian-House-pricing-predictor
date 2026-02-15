import streamlit as st
import pandas as pd
import json
import os

# -----------------------------
# Page config
# -----------------------------
st.set_page_config(
    page_title="Tunisia House Price Predictor",
    page_icon="🏠",
    layout="centered"
)

st.title("🏠 Tunisia House Price Predictor")
st.write("Fill in the house attributes and get an estimated price (model will be linked later).")

st.divider()


# -----------------------------
# Load coords_map from JSON
# -----------------------------
DELEGATIONS_PATH = os.path.join(
    os.path.dirname(__file__),
    "delegations_tunis.json"
)


@st.cache_data
def load_delegations_coords():
    try:
        with open(DELEGATIONS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Keep only valid entries
        coords = {}
        for name, obj in data.items():
            if isinstance(obj, dict) and "lat" in obj and "lon" in obj:
                coords[name] = {"lat": float(obj["lat"]), "lon": float(obj["lon"])}

        return coords

    except FileNotFoundError:
        st.error("⚠️ delegations_tunis.json not found. Check the path in DELEGATIONS_PATH.")
        return {}
    except json.JSONDecodeError:
        st.error("⚠️ Invalid JSON format in delegations_tunis.json.")
        return {}
    except Exception as e:
        st.error(f"⚠️ Unexpected error while loading delegations: {e}")
        return {}

coords_map = load_delegations_coords()

if not coords_map:
    st.stop()


# -----------------------------
# Helper: bool input
# -----------------------------
def bool_input(label, default=False):
    return 1 if st.checkbox(label, value=default) else 0


# -----------------------------
# Location section
# -----------------------------
st.subheader("📍 Location")

location = st.selectbox(
    "Choose delegation / area",
    options=sorted(coords_map.keys())
)

latitude = coords_map[location]["lat"]
longitude = coords_map[location]["lon"]

st.info(f"Auto-filled coordinates:  Latitude = {latitude:.6f} | Longitude = {longitude:.6f}")

st.divider()


# -----------------------------
# Numeric inputs
# -----------------------------
st.subheader("🏗️ House Details")

col1, col2 = st.columns(2)

with col1:
    surface = st.number_input("Surface (m²)", min_value=0, value=120, step=5)
    bedrooms = st.number_input("Number of bedrooms", min_value=0, value=3, step=1)
    bathrooms = st.number_input("Number of bathrooms", min_value=0, value=1, step=1)

with col2:
    floor = st.number_input("Floor", min_value=0, value=1, step=1)

st.divider()


# -----------------------------
# Category
# -----------------------------
st.subheader("🏠 Property Type")

category_ui = st.selectbox(
    "Category",
    options=["apartment", "villa", "house"]  # English labels
)

# Convert UI category to your training labels (French)
ui_to_train_category = {
    "apartment": "appartement",
    "villa": "villa",
    "house": "maison"
}

category_train = ui_to_train_category[category_ui]

st.divider()


# -----------------------------
# Boolean features
# -----------------------------
st.subheader("✨ Features")

c1, c2, c3 = st.columns(3)

with c1:
    high_standing = bool_input("High standing")
    terrace = bool_input("Terrace")
    balcony = bool_input("Balcony")
    parking = bool_input("Parking")

with c2:
    elevator = bool_input("Elevator")
    garden = bool_input("Garden")
    panoramic_view = bool_input("Panoramic view")
    air_conditioning = bool_input("Air conditioning")

with c3:
    central_heating = bool_input("Central heating")
    pool = bool_input("Pool")

st.divider()


# -----------------------------
# One-hot encoding for category
# (VERY IMPORTANT for later model)
# -----------------------------
categorie_appartement = 1 if category_train == "appartement" else 0
categorie_maison = 1 if category_train == "maison" else 0
categorie_villa = 1 if category_train == "villa" else 0


# -----------------------------
# Build input row (ready for model)
# -----------------------------
input_data = {
    "surface": int(surface),
    "nombre_des_chambres": int(bedrooms),
    "nombre_des_salles_de_bains": int(bathrooms),
    "etage": int(floor),

    "haut_standing": int(high_standing),
    "terrasse": int(terrace),
    "balcon": int(balcony),
    "parking": int(parking),
    "ascenseur": int(elevator),
    "jardin": int(garden),
    "vue_panoramique": int(panoramic_view),
    "climatiseur": int(air_conditioning),
    "chauffage_central": int(central_heating),
    "piscine": int(pool),

    # Instead of "categorie": "villa"
    # We send one-hot encoding (recommended)
    "categorie_appartement": int(categorie_appartement),
    "categorie_maison": int(categorie_maison),
    "categorie_villa": int(categorie_villa),

    "latitude": float(latitude),
    "longitude": float(longitude),
}

input_df = pd.DataFrame([input_data])


# -----------------------------
# Prediction button (placeholder)
# -----------------------------
if st.button("🔮 Predict Price"):
    st.success("✅ Input prepared successfully (model not linked yet).")

    st.write("### Model Input Row")
    st.dataframe(input_df)

    st.warning("Model not connected yet. When ready, we will load it and predict here.")
