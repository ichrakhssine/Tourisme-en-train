"""
Dashboard Tourisme en Train
============================
Interface Streamlit interactive
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from minio import Minio
from io import BytesIO
from geopy.distance import geodesic

# ══════════════════════════════════════════
# CONFIGURATION
# ══════════════════════════════════════════
st.set_page_config(
    page_title="Tourisme en Train 🚂",
    page_icon="🚂",
    layout="wide"
)

def apply_custom_design():
    st.markdown(
        """
        <style>
        /* Image de fond fixe */
        .stApp {
            background: url("https://images.unsplash.com/photo-1541427468627-a89a96e5ca1d?q=80&w=2070&auto=format&fit=crop");
            background-size: cover;
            background-attachment: fixed;
        }

        /* Forcer la couleur du texte en noir pour contrer le mode sombre éventuel */
        h1, h2, h3, p, span, .stMarkdown {
            color: #1E1E1E !important;
        }


        </style>
        """,
        unsafe_allow_html=True
    )

apply_custom_design()

# ══════════════════════════════════════════
# CHARGEMENT DES DONNÉES
# ══════════════════════════════════════════
@st.cache_resource
def get_client():
    return Minio("localhost:9000",
                 access_key="admin",
                 secret_key="password123",
                 secure=False)

@st.cache_data
def lire(bucket, filename):
    client = get_client()
    obj = client.get_object(bucket, filename)
    return pd.read_csv(BytesIO(obj.read()), low_memory=False)

@st.cache_data
def charger_donnees():
    gares     = lire("silver", "gares_silver.csv")
    pois_naq  = lire("silver", "datatourisme_naq_silver.csv")
    pois_idf  = lire("silver", "datatourisme_idf_silver.csv")
    festivals = lire("silver", "festivals_silver.csv")
    scores    = lire("gold",   "score_touristique.csv")
    co2       = lire("gold",   "comparaison_co2.csv")
    monuments = lire("gold",   "monuments_limoges.csv")
    cyclable  = lire("gold",   "cyclable_limoges.csv")
    return gares, pois_naq, pois_idf, festivals, scores, co2, monuments, cyclable

gares, pois_naq, pois_idf, festivals, scores, co2, monuments, cyclable = charger_donnees()
pois_all = pd.concat([pois_naq, pois_idf], ignore_index=True)

# Grouper les gares par ville
gares['ville'] = gares['nom_gare'].str.extract(r'^([A-Za-zÀ-ÿ\-]+)')
villes_uniques = sorted(gares['ville'].dropna().unique().tolist())

# ══════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════

st.sidebar.title("🚂 Tourisme en Train")
st.sidebar.markdown("**Challenge SNCF × Open Data**")
st.sidebar.markdown("---")

# CORRECTION : Noms simplifiés pour assurer la correspondance avec les 'if'
page = st.sidebar.radio(
    "Navigation",
    ["Accueil", "Explorer une destination", "Focus Limoges"]
)

# ══════════════════════════════════════════
# PAGE 1 — ACCUEIL
# ══════════════════════════════════════════
if page == "Accueil":

    st.title("🚂 Tourisme en Train en France")
    st.markdown("### *Comment faciliter et encourager le tourisme en train ?*")
    st.markdown("---")

    # Métriques
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("🚉 Gares analysées", f"{len(gares):,}")
    col2.metric("📍 POIs touristiques", f"{len(pois_all):,}")
    col3.metric("🎭 Festivals", f"{len(festivals):,}")
    col4.metric("🌿 CO₂ Train vs Voiture", "32× moins")

    st.markdown("---")

    # Carte France — toutes les gares
    st.subheader("🗺️ Toutes les Gares de France")

    fig_carte = px.scatter_mapbox(
        gares.dropna(subset=['latitude', 'longitude']),
        lat="latitude", lon="longitude",
        hover_name="nom_gare",
        zoom=5, height=500,
        mapbox_style="open-street-map",
        color_discrete_sequence=["#003189"]
    )
    fig_carte.update_traces(marker=dict(size=5))
    fig_carte.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
    st.plotly_chart(fig_carte, use_container_width=True)

    st.markdown("---")

    # Top 10 villes
    st.subheader("🏆 Top 10 Destinations Touristiques")
    st.caption("Score calculé sur la base des POIs (lieux touristiques) et festivals dans un rayon de 20-50km autour de la gare")

    if 'score_rf' in scores.columns:
        top10 = scores.nlargest(10, 'score_rf')[['nom_gare', 'nb_pois', 'score_rf']].copy()
        top10.columns = ['Gare', 'Nb POIs (20km)', 'Score /100']
        top10['Score /100'] = top10['Score /100'].round(1)
        st.dataframe(top10, use_container_width=True, hide_index=True)

# ══════════════════════════════════════════
# PAGE 2 — EXPLORER UNE DESTINATION
# ══════════════════════════════════════════
elif page == "Explorer une destination":

    st.title("🔍 Explorer une Destination")
    st.markdown("Choisissez une ville pour découvrir son potentiel touristique en train")
    st.markdown("---")

    # Sélection ville puis gare
    col_sel1, col_sel2 = st.columns(2)

    with col_sel1:
        ville_choisie = st.selectbox("🏙️ Choisissez une ville :", villes_uniques)

    with col_sel2:
        gares_ville = gares[gares['ville'] == ville_choisie]['nom_gare'].tolist()
        gare_choisie = st.selectbox("🚉 Choisissez une gare :", gares_ville)

    if gare_choisie:
        gare_info = gares[gares['nom_gare'] == gare_choisie]

        if len(gare_info) == 0:
            st.warning("Coordonnées GPS non disponibles.")
        else:
            gare_lat = float(gare_info.iloc[0]['latitude'])
            gare_lon = float(gare_info.iloc[0]['longitude'])

            # ── Métriques ──────────────────────────────
            score_info = scores[scores['nom_gare'] == gare_choisie]
            co2_ville  = co2[co2['ville'].str.contains(
                ville_choisie.split()[0], case=False, na=False)]

            col1, col2, col3, col4 = st.columns(4)

            if len(score_info) > 0:
                score   = round(float(score_info.iloc[0]['score_rf']), 1)
                nb_pois = int(score_info.iloc[0]['nb_pois'])
                col1.metric("⭐ Score Touristique", f"{score}/100")
                col2.metric("📍 POIs à 20km", f"{nb_pois:,}")

            if len(co2_ville) > 0:
                co2_train = co2_ville.iloc[0]['co2_train_kg']
                co2_voit  = co2_ville.iloc[0]['co2_voiture_kg']
                dist_km   = co2_ville.iloc[0]['distance_km']
                col3.metric("📏 Distance depuis Paris", f"{dist_km} km")
                col4.metric("🌿 CO₂ Train",
                            f"{co2_train} kg",
                            delta=f"-{round(co2_voit - co2_train, 1)} kg vs voiture",
                            delta_color="normal")

            st.markdown("---")

            # ── Carte POIs ─────────────────────────────
            st.subheader(f"🗺️ Carte touristique autour de {gare_choisie}")

            # Filtrer POIs à 20km
            pois_proches = []
            for _, poi in pois_all.iterrows():
                try:
                    d = geodesic((gare_lat, gare_lon),
                                 (float(poi['latitude']), float(poi['longitude']))).km
                    if d <= 20:
                        pois_proches.append({
                            'nom': poi['nom_poi'],
                            'categorie': poi.get('categorie', 'Autre'),
                            'latitude': poi['latitude'],
                            'longitude': poi['longitude'],
                            'type': 'POI'
                        })
                        if len(pois_proches) >= 300:
                            break
                except:
                    pass

            # Filtrer Festivals à 50km
            fests_proches = []
            for _, fest in festivals.iterrows():
                try:
                    d = geodesic((gare_lat, gare_lon),
                                 (float(fest['latitude']), float(fest['longitude']))).km
                    if d <= 50:
                        fests_proches.append({
                            'nom': fest['nom_festival'],
                            'categorie': 'Festival',
                            'latitude': fest['latitude'],
                            'longitude': fest['longitude'],
                            'type': 'Festival'
                        })
                except:
                    pass

            df_carte = pd.DataFrame(pois_proches + fests_proches)

            if len(df_carte) > 0:
                fig_map = px.scatter_mapbox(
                    df_carte,
                    lat="latitude", lon="longitude",
                    hover_name="nom",
                    color="categorie",
                    zoom=11, height=500,
                    mapbox_style="open-street-map"
                )

                # Ajouter la gare
                fig_map.add_trace(go.Scattermapbox(
                    lat=[gare_lat], lon=[gare_lon],
                    mode='markers',
                    marker=dict(size=15, color='red'),
                    name=f"🚉 {gare_choisie}",
                    hovertext=f"🚉 {gare_choisie}"
                ))

                fig_map.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
                st.plotly_chart(fig_map, use_container_width=True)
                st.caption(f"📍 {len(pois_proches)} POIs à 20km · 🎭 {len(fests_proches)} festivals à 50km")

            st.markdown("---")

            # ── Exemples de POIs ───────────────────────
            st.subheader(f"📍 Exemples de lieux à visiter autour de {gare_choisie}")

            if len(pois_proches) > 0:
                df_exemples = pd.DataFrame(pois_proches[:10])[['nom', 'categorie']]
                df_exemples.columns = ['Lieu', 'Catégorie']
                df_exemples['Catégorie'] = df_exemples['Catégorie'].replace({
                    'Accommodation': '🏨 Hébergement',
                    'FoodEstablishment': '🍽️ Restaurant',
                    'CulturalSite': '🏛️ Site culturel',
                    'CulturalEvent': '🎭 Événement',
                    'SportsAndLeisurePlace': '⚽ Sport & Loisir',
                    'Tour': '🚶 Itinéraire',
                    'CyclingTour': '🚲 Balade vélo',
                    'Autre': '📌 Autre'
                })
                st.dataframe(df_exemples, use_container_width=True, hide_index=True)

            # ── CO₂ ────────────────────────────────────
            if len(co2_ville) > 0:
                st.markdown("---")
                st.subheader(f"🌿 Comparateur CO₂ — Paris → {gare_choisie}")
                st.caption(f"Distance : {dist_km} km | Valeurs ADEME : Train=6g/km · Voiture=195g/km · Avion=285g/km")

                co2_avion = co2_ville.iloc[0]['co2_avion_kg']
                fig_co2 = go.Figure(data=[go.Bar(
                    x=['🚂 Train', '🚗 Voiture', '✈️ Avion'],
                    y=[co2_train, co2_voit, co2_avion],
                    marker_color=['#27AE60', '#E67E22', '#E74C3C'],
                    text=[f'{co2_train} kg', f'{co2_voit} kg', f'{co2_avion} kg'],
                    textposition='auto'
                )])
                fig_co2.update_layout(
                    title=f"Émissions CO₂ selon le mode de transport",
                    yaxis_title="kg CO₂ par passager",
                    height=400, showlegend=False
                )
                st.plotly_chart(fig_co2, use_container_width=True)

                economie = round(co2_voit - co2_train, 1)
                st.success(f"🌿 En prenant le train, vous économisez **{economie} kg de CO₂** par rapport à la voiture !")

# ══════════════════════════════════════════
# PAGE 3 — FOCUS LIMOGES
# ══════════════════════════════════════════
elif page == "Focus Limoges":

    st.title("🏛️ Focus Limoges — Ville à Découvrir en Train")
    st.markdown("*Une destination riche, accessible et écologique depuis Paris*")
    st.markdown("---")

    # Métriques
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("⭐ Score Touristique", "28.8/100", "Ville sous-estimée !")
    col2.metric("📍 POIs à 20km", "2 179", "hôtels, restos, musées...")
    col3.metric("🎭 Festivals à 50km", "21", "dont 6 à Limoges même")
    col4.metric("🚂 Temps de trajet", "2h15", "depuis Paris")

    st.markdown("---")

    # ── CO₂ + Catégories ──────────────────────────
    col_l, col_r = st.columns(2)

    with col_l:
        st.subheader("🌿 CO₂ — Paris → Limoges (346 km)")
        fig_co2 = go.Figure(data=[go.Bar(
            x=['🚂 Train', '🚗 Voiture', '✈️ Avion'],
            y=[2.07, 67.40, 98.61],
            marker_color=['#27AE60', '#E67E22', '#E74C3C'],
            text=['2.07 kg', '67.40 kg', '98.61 kg'],
            textposition='auto'
        )])
        fig_co2.update_layout(
            title="Le train pollue 32× moins que la voiture !",
            yaxis_title="kg CO₂",
            height=350, showlegend=False
        )
        st.plotly_chart(fig_co2, use_container_width=True)

    with col_r:
        st.subheader("📍 Que faire à Limoges ?")
        categories_limoges = {
            '🎭 Événements culturels': 458,
            '🏨 Hébergements': 407,
            '🍽️ Restaurants': 352,
            '🏛️ Sites culturels': 193,
            '⚽ Sports & Loisirs': 143,
            '🚲 Balades vélo': 119,
        }
        fig_cat = go.Figure(go.Bar(
            x=list(categories_limoges.values()),
            y=list(categories_limoges.keys()),
            orientation='h',
            marker_color='#E74C3C',
            text=list(categories_limoges.values()),
            textposition='auto'
        ))
        fig_cat.update_layout(
            title="POIs autour de la gare de Limoges (20km)",
            height=350, showlegend=False
        )
        st.plotly_chart(fig_cat, use_container_width=True)

    st.markdown("---")

    # ── Carte Limoges ─────────────────────────────
    st.subheader("🗺️ Carte Touristique de Limoges")

    df_carte_limoges = []
    for _, mon in monuments.iterrows():
        try:
            nom = mon.get('name', '')
            if pd.isna(nom) or nom == '':
                nom = f"Monument ({mon.get('type', 'historique')})"
            df_carte_limoges.append({
                'nom': nom,
                'latitude': float(mon['latitude']),
                'longitude': float(mon['longitude']),
                'type': '🏛️ Monument'
            })
        except:
            pass

    for _, piste in cyclable.iterrows():
        try:
            type_am = piste.get('type_amenagement', 'Piste cyclable')
            df_carte_limoges.append({
                'nom': str(type_am),
                'latitude': float(piste['latitude']),
                'longitude': float(piste['longitude']),
                'type': '🚲 Piste cyclable'
            })
        except:
            pass

    df_carte_limoges.append({
        'nom': '🚉 Gare de Limoges Bénédictins',
        'latitude': 45.836089,
        'longitude': 1.267356,
        'type': '🚉 Gare'
    })

    df_lim = pd.DataFrame(df_carte_limoges)

    if len(df_lim) > 0:
        fig_lim = px.scatter_mapbox(
            df_lim,
            lat="latitude", lon="longitude",
            hover_name="nom",
            color="type",
            zoom=12, height=500,
            mapbox_style="open-street-map",
            color_discrete_map={
                '🏛️ Monument': '#9B59B6',
                '🚲 Piste cyclable': '#27AE60',
                '🚉 Gare': '#E74C3C'
            }
        )
        fig_lim.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
        st.plotly_chart(fig_lim, use_container_width=True)

    st.markdown("---")

    # ── Exemples réels de POIs ────────────────────
    st.subheader("📍 Exemples de lieux à visiter à Limoges")

    exemples_limoges = pd.DataFrame({
        'Lieu': [
            'Cathédrale Saint-Étienne de Limoges', 'Musée national Adrien Dubouché',
            'Jardins de l\'Évêché', 'Musée des Beaux-Arts', 'Cité de la Porcelaine',
            'Château de Limoges', 'Festival des Francophonies', 'Festival 1001 Notes',
            'Éclats d\'Email', 'Lire à Limoges'
        ],
        'Catégorie': [
            '🏛️ Monument historique', '🏛️ Musée', '🌿 Jardin', '🏛️ Musée',
            '🏛️ Site culturel', '🏛️ Château', '🎭 Festival', '🎶 Festival musique classique',
            '🎨 Festival arts', '📚 Festival littérature'
        ],
        'Distance gare': [
            '10 min à pied', '12 min à pied', '15 min à pied', '10 min à pied',
            '5 min à pied', '8 min à pied', 'Centre-ville', 'Centre-ville',
            'Centre-ville', 'Centre-ville'
        ]
    })
    st.dataframe(exemples_limoges, use_container_width=True, hide_index=True)

    st.markdown("---")

    # ── Message final ──────────────────────────────
    st.subheader("💡 Pourquoi choisir Limoges en Train ?")
    col1, col2, col3 = st.columns(3)
    col1.success("✅ **Accessible** — 2h15 depuis Paris")
    col2.success("✅ **Écologique** — 32× moins de CO₂")
    col3.success("✅ **Riche** — 2179 POIs · 21 festivals")

    st.info("""
    🏛️ **Limoges** est la capitale mondiale de la porcelaine. 
    Avec sa magnifique gare des Bénédictins, c'est une destination idéale pour un week-end !
    """)