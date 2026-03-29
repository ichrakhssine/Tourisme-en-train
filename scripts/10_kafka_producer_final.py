import json
import pandas as pd
from kafka import KafkaProducer

producer = KafkaProducer(
    bootstrap_servers='kafka:9092',
    value_serializer=lambda x: json.dumps(x, ensure_ascii=False).encode('utf-8'),
    max_request_size=10485760
)

def envoyer(filepath, topic, sep=","):
    print(f"\n=== Producer : {topic} ===")
    try:
        df = pd.read_csv(filepath, sep=sep, low_memory=False)
        if len(df.columns) < 3:
            df = pd.read_csv(filepath, sep=";", low_memory=False)
        print(f"  {len(df)} lignes a envoyer...")
        for _, row in df.iterrows():
            producer.send(topic, value=row.to_dict())
        producer.flush()
        print(f"  OK - {len(df)} messages envoyes dans '{topic}'")
    except Exception as e:
        print(f"  Erreur : {e}")

# Envoyer tous les fichiers
envoyer(r"/opt/airflow/data/raw/datatourisme-reg-naq.csv", "datatourisme.naq")
envoyer(r"/opt/airflow/data/raw/datatourisme-reg-idf.csv", "datatourisme.idf")
envoyer(r"/opt/airflow/data/raw/datatourisme-tour.csv",    "datatourisme.tour")
envoyer(r"/opt/airflow/data/raw/Limoges_cycle.csv",        "limoges.cycle",    sep=";")
envoyer(r"/opt/airflow/data/raw/Limoges_historic.csv",     "limoges.historic", sep=";")


print("\nProducer termine !")
print("Lance maintenant : python scripts\11_kafka_consumer_final.py")
