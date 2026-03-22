import json
import io
import pandas as pd
from kafka import KafkaConsumer
from minio import Minio

client = Minio("localhost:9000", access_key="admin", secret_key="password123", secure=False)

def consommer(topic, filename, timeout_ms=60000):
    print(f"\n=== Consumer : {topic} → bronze/{filename} ===")
    consumer = KafkaConsumer(
        topic,
        bootstrap_servers='localhost:9092',
        value_deserializer=lambda x: json.loads(x.decode('utf-8')),
        auto_offset_reset='earliest',
        consumer_timeout_ms=timeout_ms,
        group_id=f'consumer_final_{topic}'
    )
    messages = []
    for msg in consumer:
        messages.append(msg.value)
    consumer.close()

    if not messages:
        print(f"  Aucun message dans '{topic}'")
        return

    df = pd.DataFrame(messages)
    print(f"  {len(df)} lignes recues")
    csv_bytes = df.to_csv(index=False).encode('utf-8')
    client.put_object("bronze", filename, io.BytesIO(csv_bytes), len(csv_bytes), content_type="text/csv")
    print(f"  OK - bronze/{filename} uploade")

# Consommer tous les topics
consommer("datatourisme.naq",  "datatourisme_naq_raw.csv")
consommer("datatourisme.idf",  "datatourisme_idf_raw.csv")
consommer("datatourisme.tour", "datatourisme_tour_raw.csv")
consommer("limoges.cycle",     "limoges_cycle_raw.csv")
consommer("limoges.historic",  "limoges_historic_raw.csv")

# Résumé final
print("\n=== BRONZE COMPLET ===")
total_ko = 0
for obj in client.list_objects("bronze"):
    taille = round((obj.size or 0) / 1024)
    total_ko += taille
    print(f"  ✅ {obj.object_name:<45} {taille:>8} Ko")
print(f"\n  TOTAL : {round(total_ko/1024)} Mo")
print("\nBronze 100% complet ! Prochaine etape : Silver")
