# 🚆 Tourisme durable en train – Analyse et recommandation pour Limoges

## 📌 Contexte du projet

Ce projet est réalisé dans le cadre du défi **Open Data University – Tourisme en train**.
L’objectif est d’encourager le tourisme durable en France en facilitant la découverte de destinations accessibles en train.

Nous avons choisi de nous concentrer sur la ville de **Limoges**, afin d’analyser son potentiel touristique et d’identifier des moyens d’encourager les voyageurs à s’y rendre en utilisant le train, un mode de transport à faible empreinte carbone.

Le projet combine **analyse de données, machine learning et visualisation** pour proposer des recommandations basées sur les données ouvertes.

---

# 🎯 Objectifs du projet

Les objectifs principaux sont :

* analyser l’accessibilité de Limoges en train
* identifier les points d’intérêt touristiques autour des gares
* comparer l’impact carbone du train avec d’autres modes de transport
* développer un modèle de recommandation de destinations touristiques
* construire un pipeline de données structuré pour traiter les données open data

---

# 👥 Équipe

Projet réalisé par :
-Ichrak Hassine
-Fokoue reine clean
-Hiba Brahim
---

# 🧱 Architecture du pipeline de données

Le projet suit une architecture classique de **Data Lake** avec trois couches :

* **Bronze** : données brutes
* **Silver** : données nettoyées et préparées
* **Gold** : données enrichies, indicateurs et résultats de modèles

Les données sont stockées dans **MinIO**, un système de stockage compatible S3 utilisé comme Data Lake.

---

# ⚙️ Étape 1 — Ingestion des données (Bronze)

## Objectif

Collecter et stocker les données brutes nécessaires au projet.

## Actions réalisées

* Compréhension de l’architecture globale du pipeline de données
* Choix du challenge : **Tourisme en train**
* Mise en place de l’infrastructure :

  * MinIO pour le stockage des données
  * Kafka (optionnel) pour le streaming de données
* Téléchargement des datasets à l’aide de scripts Python
* Stockage des données brutes dans la couche **Bronze** du Data Lake

## Sources de données

Les données proviennent principalement de sources open data :

* données sur les gares et lignes ferroviaires
* données sur les points d’intérêt touristiques
* données sur les transports et mobilités locales
* données sur l’empreinte carbone des transports

Ces datasets sont disponibles sur les plateformes d’open data publiques.

---

# 🧹 Étape 2 — Nettoyage et préparation des données (Silver)

## Objectif

Préparer les données pour l’analyse et le machine learning.

## Actions réalisées

* lecture des données depuis la couche **Bronze**
* exploration du dataset :

  * analyse des colonnes
  * vérification des types de données
  * détection des valeurs manquantes
* nettoyage des données :

  * suppression des doublons
  * gestion des valeurs manquantes
  * correction des types de données
* structuration des données pour faciliter l’analyse

Les données nettoyées sont ensuite stockées dans la couche **Silver** du Data Lake.

---

# 🤖 Étape 3 — Analyse et Machine Learning (Gold)

## Objectif

Extraire des informations utiles et construire un modèle pour répondre au défi.

## Actions réalisées

* lecture des données depuis la couche **Silver**

* création d’indicateurs simples :

  * accessibilité des gares
  * nombre de points d’intérêt touristiques
  * estimation du gain carbone en utilisant le train

* exploration des variables importantes

## Machine Learning

Un premier modèle de machine learning est développé afin de :

* identifier les destinations touristiques les plus attractives
* classer les villes selon leur potentiel touristique accessible en train

Les modèles utilisés peuvent inclure :

* Random Forest
* K-Means clustering
* Régression simple

Les modèles sont évalués à l’aide de métriques simples.

Les résultats et prédictions sont stockés dans la couche **Gold**.

---

# 📊 Étape 4 — Finalisation du pipeline et visualisation

## Objectif

Mettre en place un pipeline complet et produire des visualisations.

## Actions réalisées

* vérification du bon fonctionnement du pipeline complet
* orchestration du pipeline avec **Airflow**
* création de visualisations à partir des données de la couche **Gold**

Les visualisations permettent par exemple de :

* montrer l’accessibilité de Limoges en train
* comparer l’impact carbone des différents modes de transport
* visualiser les zones touristiques autour des gares

---

# 📈 Étape 5 — Finalisation du projet et préparation de la soutenance

Cette étape comprend :

* amélioration du modèle et des analyses
* validation des résultats
* finalisation de la documentation du projet
* préparation de la présentation finale

La soutenance présentera :

* la problématique
* les données utilisées
* la méthodologie
* les résultats obtenus
* les recommandations pour encourager le tourisme durable en train.

---

# 🛠️ Technologies utilisées

* Python
* Pandas
* Scikit-learn
* Apache Airflow
* MinIO
* Jupyter Notebook
* outils de visualisation de données

---

# 🌱 Impact du projet

Ce projet vise à :

* encourager les déplacements touristiques bas-carbone
* valoriser des destinations accessibles en train comme Limoges
* utiliser les données ouvertes pour soutenir un tourisme durable.

---
