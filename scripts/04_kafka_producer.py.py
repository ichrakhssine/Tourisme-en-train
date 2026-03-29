"""
Producer Kafka
==============
Lit les datasets depuis les APIs
et envoie les donnees dans les topics Kafka
"""
import json
import requests
import io
import pandas as pd
from kafka import KafkaProducer

# Connexion Kafka
producer = KafkaProducer(
    bootstrap_servers='localhost:9092',
    value_serializer=lambda x: json.dumps(
        x, ensure_ascii=False).encode('utf-8')
)

def envoyer_dans_kafka(df, topic):
    print(f"  Envoi de {len(df)} lignes dans '{topic}'...")
    for _, row in df.iterrows():
        producer.send(topic, value=row.to_dict())
    producer.flush()
    print(f"  OK - {len(df)} messages envoyes dans '{topic}'")

# Dataset 1 - Gares SNCF
print("=== Gares SNCF → topic : sncf.gares ===")
url = "https://ressources.data.sncf.com/api/explore/v2.1/catalog/datasets/gares-de-voyageurs/exports/csv?use_labels=true"
response = requests.get(url, timeout=120)
df = pd.read_csv(io.StringIO(response.text), sep=";", low_memory=False)
if len(df) < 100:
    df = pd.read_csv(io.StringIO(response.text), sep=",", low_memory=False)
envoyer_dans_kafka(df, 'sncf.gares')

# Dataset 2 - Festivals
print("=== Festivals → topic : sncf.festivals ===")
url = "https://data.culture.gouv.fr/api/explore/v2.1/catalog/datasets/panorama-des-festivals/exports/csv?limit=-1"
response = requests.get(url, timeout=120)
df = pd.read_csv(io.StringIO(response.text), sep=";", low_memory=False)
if len(df) < 100:
    df = pd.read_csv(io.StringIO(response.text), sep=",", low_memory=False)
envoyer_dans_kafka(df, 'sncf.festivals')

print("\nProducer termine !")
print("Lance maintenant : python scripts/05_kafka_consumer.py")
