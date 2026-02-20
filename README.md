# 🏠 Tunisian Real Estate Price Prediction

## Overview

This project predicts **house selling prices in Greater Tunis** using a **machine learning regression pipeline** enhanced by **LLM-assisted preprocessing** to handle incomplete and unstructured real estate listings.

---

## Team

- Farah Frija  
- Emna Gharbi  
- Rima Zarrouki  
- Wala Ali  

---

## Objectives

- Unify real estate data from multiple platforms  
- Clean and enrich incomplete listings  
- Engineer spatial features  
- Compare regression models  
- Build an interactive price prediction system  

---

## Dataset

- ~400 properties  
- Sources: Tecnocasa, Mubawab, Tayara  
- Structured attributes + free-text descriptions  

### Target
- `prix` (selling price in TND)

---

## Data Preprocessing

### Classical Steps
- Duplicate removal  
- Type normalization  
- Outlier handling  
- Basic missing value treatment  

### LLM-Assisted Enrichment

We used the **Groq API (`chatgpt-oss-120`)** to:

- Complete missing attributes (rooms, amenities, standing)
- Extract structured information from text descriptions
- Reduce data loss due to incomplete listings

> The LLM was used **only during preprocessing**, not for prediction.

---

## Geolocation Processing

- Latitude and longitude were obtained using the **OpenStreetMap API**
- Exact coordinates were available only for some sources
- For others, geocoding was performed at the administrative (delegation) level

---

## Feature Engineering

- Distance to Tunis center (`distance_center`)
- Distance to the coast (`distance_coast`)
- Spatial features from latitude / longitude
- Price per square meter (`price_m2`) for data validation

---

## Modeling

- **Type:** Supervised learning  
- **Task:** Regression  

Models evaluated:
- Linear Regression  
- KNN  
- Tree-based models  
- **CatBoost Regressor**

### Best Model: CatBoost

- **R²:** 0.83  
- **MSE:** 0.088  

---

## Pipeline Overview

![ML + LLM Pipeline](images/pipeline.png)

*End-to-end pipeline from data collection to Streamlit deployment.*

---

## Interface & Visualization

An interactive interface was built using **Streamlit**, allowing users to:

- Input property characteristics
- Get instant price predictions
- Explore feature influence on prices

---

## Deployment

- Trained model integrated into the Streamlit app  
- Ready for extension as a REST API or production service  

---

## Limitations

- Limited dataset size  
- Approximate geolocation for some listings  
- Possible semantic noise from LLM-based extraction  

---

## Future Improvements

- Add transport and socio-economic features  
- Extend to all Tunisian regions  
- Integrate temporal price trends  
- Strengthen LLM validation  

---

## Conclusion

Combining **machine learning**, **LLM-assisted preprocessing**, and **geospatial enrichment** leads to robust real estate price prediction in a data-scarce environment.

The Streamlit interface makes the model directly usable, while CatBoost explains **83% of price variance**.
