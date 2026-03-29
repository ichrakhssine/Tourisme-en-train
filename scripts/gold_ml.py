"""
Script Gold — Machine Learning
================================
1. Score touristique (Random Forest)
2. Comparateur CO2
3. Clustering gares (K-Means)
4. Focus Limoges (POIs + Festivals + Monuments + Cyclable)
Tout basé sur les données — rien d'écrit à la main !
"""
from pyspark.sql import SparkSession
from minio import Minio
import pandas as pd
from io import BytesIO
from sklearn.ensemble import RandomForestRegressor
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from geopy.distance import geodesic

spark = SparkSession.builder \
    .appName("Gold_ML") \
    .config("spark.driver.memory", "4g") \
    .getOrCreate()
spark.sparkContext.setLogLevel("ERROR")
print("Spark demarre !")

import os
from minio import Minio

client = Minio(
    os.getenv("MINIO_ENDPOINT", "minio:9000"),
    access_key=os.getenv("MINIO_ACCESS_KEY", "admin"),
    secret_key=os.getenv("MINIO_SECRET_KEY", "password123"),
    secure=False
)
def lire_silver(filename):
    obj = client.get_object("silver", filename)
    return pd.read_csv(BytesIO(obj.read()), low_memory=False)

def sauver_gold(df, filename):
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    client.put_object("gold", filename,
                      BytesIO(csv_bytes), len(csv_bytes),
                      content_type="text/csv")
    print(f"OK → gold/{filename} ({len(df)} lignes)")

# ══════════════════════════════════════════
# ÉTAPE 1 — Charger les données Silver
# ══════════════════════════════════════════
print("\n=== Chargement des données Silver ===")

gares    = lire_silver("gares_silver.csv")
pois_naq = lire_silver("datatourisme_naq_silver.csv")
pois_idf = lire_silver("datatourisme_idf_silver.csv")
festivals= lire_silver("festivals_silver.csv")
historic = lire_silver("limoges_historic_silver.csv")
cycle    = lire_silver("limoges_cycle_silver.csv")

print(f"Gares    : {len(gares)}")
print(f"POIs NAQ : {len(pois_naq)}")
print(f"POIs IDF : {len(pois_idf)}")
print(f"Festivals: {len(festivals)}")
print(f"Monuments: {len(historic)}")
print(f"Cyclable : {len(cycle)}")

pois_all = pd.concat([pois_naq, pois_idf], ignore_index=True)

# ══════════════════════════════════════════
# FONCTIONS UTILITAIRES
# ══════════════════════════════════════════
def compter_pois_autour(gare_lat, gare_lon, pois_df, rayon_km=20):
    count = 0
    for _, poi in pois_df.iterrows():
        try:
            dist = geodesic(
                (gare_lat, gare_lon),
                (poi['latitude'], poi['longitude'])
            ).km
            if dist <= rayon_km:
                count += 1
        except:
            pass
    return count

def compter_festivals_autour(gare_lat, gare_lon, festivals_df, rayon_km=50):
    count = 0
    for _, fest in festivals_df.iterrows():
        try:
            dist = geodesic(
                (gare_lat, gare_lon),
                (fest['latitude'], fest['longitude'])
            ).km
            if dist <= rayon_km:
                count += 1
        except:
            pass
    return count

def filtrer_pois_autour(gare_lat, gare_lon, pois_df, rayon_km=20):
    pois_proches = []
    for _, poi in pois_df.iterrows():
        try:
            dist = geodesic(
                (gare_lat, gare_lon),
                (poi['latitude'], poi['longitude'])
            ).km
            if dist <= rayon_km:
                poi_dict = poi.to_dict()
                poi_dict['distance_km'] = round(dist, 2)
                pois_proches.append(poi_dict)
        except:
            pass
    return pd.DataFrame(pois_proches)

def filtrer_festivals_autour(gare_lat, gare_lon, festivals_df, rayon_km=50):
    fests_proches = []
    for _, fest in festivals_df.iterrows():
        try:
            dist = geodesic(
                (gare_lat, gare_lon),
                (fest['latitude'], fest['longitude'])
            ).km
            if dist <= rayon_km:
                fest_dict = fest.to_dict()
                fest_dict['distance_km'] = round(dist, 2)
                fests_proches.append(fest_dict)
        except:
            pass
    return pd.DataFrame(fests_proches)

# ══════════════════════════════════════════
# ÉTAPE 2 — Sélection des gares à analyser
# Basé 100% sur les données — rien à la main !
# ══════════════════════════════════════════
print("\n=== Sélection des gares depuis les données ===")

# Extraire les codes communes couverts par nos POIs
communes_naq = set(
    pois_naq['commune'].dropna()
    .str.split('#').str[0]
    .str.strip()
)
communes_idf = set(
    pois_idf['commune'].dropna()
    .str.split('#').str[0]
    .str.strip()
)
communes_couvertes = communes_naq | communes_idf
print(f"Communes couvertes par nos POIs : {len(communes_couvertes)}")

# Gares dans nos zones de données
gares_couvertes = gares[
    gares['code_commune'].astype(str).isin(communes_couvertes)
].copy()
print(f"Gares dans zones couvertes : {len(gares_couvertes)}")

# Compléter avec un échantillon aléatoire
gares_echantillon = gares.sample(
    min(50, len(gares)), random_state=42
)

# Combiner sans doublons
gares_sample = pd.concat([
    gares_couvertes,
    gares_echantillon
]).drop_duplicates(subset=['nom_gare'])
print(f"Gares analysées total : {len(gares_sample)}")

# Trouver Limoges depuis le dataset (pour Focus)
gare_limoges_df = gares[
    gares['nom_gare'].str.contains('Limoges', case=False, na=False)
]
if len(gare_limoges_df) > 0:
    gare_limoges = gare_limoges_df.iloc[0]
    LIMOGES_LAT = gare_limoges['latitude']
    LIMOGES_LON = gare_limoges['longitude']
    print(f"Gare Limoges trouvée : lat={LIMOGES_LAT}, lon={LIMOGES_LON}")
else:
    print("Gare Limoges non trouvée dans le dataset !")
    LIMOGES_LAT = None
    LIMOGES_LON = None

# Trouver Paris depuis le dataset (pour CO₂)
gare_paris_df = gares[
    gares['nom_gare'].str.contains('Paris', case=False, na=False)
]
if len(gare_paris_df) > 0:
    gare_paris = gare_paris_df.iloc[0]
    PARIS_LAT = gare_paris['latitude']
    PARIS_LON = gare_paris['longitude']
    print(f"Gare Paris trouvée : lat={PARIS_LAT}, lon={PARIS_LON}")
else:
    PARIS_LAT = 48.8566
    PARIS_LON = 2.3522
    print("Paris non trouvé, utilisation coordonnées fixes")

# ══════════════════════════════════════════
# ÉTAPE 3 — Calcul features par gare
# ══════════════════════════════════════════
print("\n=== Calcul features par gare (patience...) ===")

features = []
total = len(gares_sample)
for i, (idx, gare) in enumerate(gares_sample.iterrows()):
    try:
        nb_pois = compter_pois_autour(
            gare['latitude'], gare['longitude'],
            pois_all, rayon_km=20
        )
        nb_festivals = compter_festivals_autour(
            gare['latitude'], gare['longitude'],
            festivals, rayon_km=50
        )
        features.append({
            'nom_gare'    : gare['nom_gare'],
            'latitude'    : gare['latitude'],
            'longitude'   : gare['longitude'],
            'code_commune': gare['code_commune'],
            'nb_pois'     : nb_pois,
            'nb_festivals': nb_festivals,
        })
        if i % 10 == 0:
            print(f"  {i}/{total} gares traitées...")
    except Exception as e:
        pass

df_features = pd.DataFrame(features)
print(f"\nFeatures calculées pour {len(df_features)} gares")
print(df_features[['nom_gare', 'nb_pois', 'nb_festivals']].head(10))

# ══════════════════════════════════════════
# ÉTAPE 4 — Score touristique (Random Forest)
# ══════════════════════════════════════════
print("\n=== Score touristique — Random Forest ===")

df_features['score_brut'] = (
    df_features['nb_pois'] * 0.7 +
    df_features['nb_festivals'] * 2
)

score_max = df_features['score_brut'].max()
if score_max > 0:
    df_features['score_touristique'] = (
        df_features['score_brut'] / score_max * 100
    ).round(1)
else:
    df_features['score_touristique'] = 0

X = df_features[['nb_pois', 'nb_festivals']].fillna(0)
y = df_features['score_touristique']

rf = RandomForestRegressor(n_estimators=100, random_state=42)
rf.fit(X, y)
df_features['score_rf'] = rf.predict(X).round(1)

print("\nTop 10 villes par score touristique :")
print(df_features.nlargest(10, 'score_rf')[
    ['nom_gare', 'nb_pois', 'nb_festivals', 'score_rf']
].to_string())

sauver_gold(df_features[[
    'nom_gare', 'latitude', 'longitude',
    'nb_pois', 'nb_festivals',
    'score_touristique', 'score_rf'
]], "score_touristique.csv")

# ══════════════════════════════════════════
# ÉTAPE 5 — Clustering K-Means
# ══════════════════════════════════════════
print("\n=== Clustering gares — K-Means ===")

X_cluster = df_features[['nb_pois', 'nb_festivals']].fillna(0)
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X_cluster)

kmeans = KMeans(n_clusters=4, random_state=42, n_init=10)
df_features['cluster'] = kmeans.fit_predict(X_scaled)

centres = pd.DataFrame(
    scaler.inverse_transform(kmeans.cluster_centers_),
    columns=['nb_pois', 'nb_festivals']
)
labels = {}
ordre = centres['nb_pois'].argsort().values
for i, label in enumerate(["Petite gare rurale",
                            "Ville patrimoine",
                            "Ville touristique moyenne",
                            "Grande destination"]):
    labels[ordre[i]] = label

df_features['type_destination'] = df_features['cluster'].map(labels)

print("\nRépartition par type :")
print(df_features['type_destination'].value_counts())

sauver_gold(df_features[[
    'nom_gare', 'latitude', 'longitude',
    'cluster', 'type_destination', 'score_rf'
]], "clustering_gares.csv")

# ══════════════════════════════════════════
# ÉTAPE 6 — Comparateur CO₂
# ══════════════════════════════════════════
print("\n=== Comparateur CO₂ ===")

CO2_TRAIN   =   6
CO2_VOITURE = 195
CO2_AVION   = 285

trajets = []
for _, gare in gares_sample.iterrows():
    try:
        distance_km = geodesic(
            (PARIS_LAT, PARIS_LON),
            (gare['latitude'], gare['longitude'])
        ).km
        trajets.append({
            'ville'          : gare['nom_gare'],
            'distance_km'    : round(distance_km),
            'co2_train_kg'   : round(distance_km * CO2_TRAIN / 1000, 2),
            'co2_voiture_kg' : round(distance_km * CO2_VOITURE / 1000, 2),
            'co2_avion_kg'   : round(distance_km * CO2_AVION / 1000, 2),
            'economie_co2_kg': round(
                distance_km * (CO2_VOITURE - CO2_TRAIN) / 1000, 2
            ),
            'latitude'       : gare['latitude'],
            'longitude'      : gare['longitude']
        })
    except:
        pass

df_co2 = pd.DataFrame(trajets)
print(df_co2[['ville', 'distance_km', 'co2_train_kg',
              'co2_voiture_kg', 'economie_co2_kg']].head(10).to_string())
sauver_gold(df_co2, "comparaison_co2.csv")

# ══════════════════════════════════════════
# ÉTAPE 7 — Focus Limoges
# ══════════════════════════════════════════
if LIMOGES_LAT is not None:
    print("\n=== Focus Limoges ===")

    # POIs autour de Limoges (20km)
    print("Calcul POIs autour de Limoges...")
    df_pois_limoges = filtrer_pois_autour(
        LIMOGES_LAT, LIMOGES_LON, pois_naq, rayon_km=20
    )
    print(f"POIs trouvés : {len(df_pois_limoges)}")
    if len(df_pois_limoges) > 0:
        print("Top catégories :")
        print(df_pois_limoges['categorie'].value_counts().head(5))
        sauver_gold(df_pois_limoges, "pois_limoges.csv")

    # Festivals autour de Limoges (50km)
    print("\nCalcul festivals autour de Limoges...")
    df_fest_limoges = filtrer_festivals_autour(
        LIMOGES_LAT, LIMOGES_LON, festivals, rayon_km=50
    )
    print(f"Festivals trouvés : {len(df_fest_limoges)}")
    if len(df_fest_limoges) > 0:
        sauver_gold(df_fest_limoges, "festivals_limoges.csv")

    # Monuments historiques Limoges
    print("\nChargement monuments Limoges...")
    sauver_gold(historic, "monuments_limoges.csv")

    # Pistes cyclables Limoges
    print("Chargement pistes cyclables Limoges...")
    sauver_gold(cycle, "cyclable_limoges.csv")

    print(f"\nBilan Focus Limoges :")
    print(f"  POIs         : {len(df_pois_limoges)}")
    print(f"  Festivals    : {len(df_fest_limoges)}")
    print(f"  Monuments    : {len(historic)}")
    print(f"  Cyclable     : {len(cycle)}")

# ══════════════════════════════════════════
# RÉSUMÉ FINAL
# ══════════════════════════════════════════
print("\n" + "="*50)
print("GOLD 100% COMPLET !")
print("="*50)
for obj in client.list_objects("gold"):
    taille = round((obj.size or 0) / 1024)
    print(f"  ✅ {obj.object_name:<45} {taille:>6} Ko")

spark.stop()
print("\nSpark arrete. Gold termine !")