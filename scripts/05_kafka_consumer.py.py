"""
Consumer Kafka
==============
Lit les messages depuis les topics Kafka
et les stocke dans MinIO/bronze/
"""
import json
import io
import pandas as pd
from kafka import KafkaConsumer
from minio import Minio

# Connexion MinIO
client = Minio(
    "localhost:9000",
    access_key="admin",
    secret_key="password123",
    secure=False
)

def consommer_et_stocker(topic, filename, timeout_ms=60000):
    print(f"\n=== Topic '{topic}' → MinIO/bronze/{filename} ===")

    consumer = KafkaConsumer(
        topic,
        bootstrap_servers='localhost:9092',
        value_deserializer=lambda x: json.loads(x.decode('utf-8')),
        auto_offset_reset='earliest',
        consumer_timeout_ms=timeout_ms,
        group_id=f'consumer_{topic}'
    )

    messages = []
    for message in consumer:
        messages.append(message.value)
    consumer.close()

    if not messages:
        print(f"  Aucun message dans '{topic}'")
        return

    df = pd.DataFrame(messages)
    print(f"  {len(df)} lignes recues depuis Kafka")

    csv_bytes = df.to_csv(index=False).encode('utf-8')
    client.put_object(
        "bronze", filename,
        io.BytesIO(csv_bytes), len(csv_bytes),
        content_type="text/csv"
    )
    print(f"  OK - {filename} uploade dans MinIO/bronze/")

# Consommer les 2 topics
consommer_et_stocker('sncf.gares',     'gares_raw.csv')
consommer_et_stocker('sncf.festivals', 'festivals_raw.csv')

# Résumé final
print("\n=== Contenu MinIO/bronze/ ===")
for obj in client.list_objects("bronze"):
    taille = round((obj.size or 0) / 1024)
    print(f"  {obj.object_name:<40} {taille} Ko")

print("\nConsumer termine ! Bronze mis a jour via Kafka.")
