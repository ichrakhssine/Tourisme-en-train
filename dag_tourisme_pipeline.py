"""
DAG — Pipeline Tourisme en Train
==================================
Orchestration complète : Bronze → Silver → Gold
Planifié tous les lundis à 6h00
"""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator

# ── Arguments par défaut ───────────────────────────────
default_args = {
    'owner': 'ichrak',
    'depends_on_past': False,
    'email_on_failure': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

# ── DAG ───────────────────────────────────────────────
dag = DAG(
    'tourisme_en_train_pipeline',
    default_args=default_args,
    description='Pipeline Big Data Tourisme en Train',
    schedule_interval='0 6 * * 1',   # Chaque lundi à 6h00
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=['tourisme', 'bigdata', 'sncf'],
)

# ══════════════════════════════════════════════════════
# ÉTAPE 1 — BRONZE : Ingestion APIs publiques
# ══════════════════════════════════════════════════════
def ingestion_bronze():
    import io
    import requests
    import pandas as pd
    from minio import Minio
    import os

    endpoint = os.getenv('MINIO_ENDPOINT', 'minio:9000')
    client = Minio(endpoint,
                   access_key=os.getenv('MINIO_ACCESS_KEY', 'admin'),
                   secret_key=os.getenv('MINIO_SECRET_KEY', 'password123'),
                   secure=False)

    # Créer les buckets si besoin
    for bucket in ['bronze', 'silver', 'gold']:
        if not client.bucket_exists(bucket):
            client.make_bucket(bucket)
            print(f"Bucket '{bucket}' créé")

    def upload(df, filename):
        csv_bytes = df.to_csv(index=False).encode('utf-8')
        client.put_object('bronze', filename,
                          io.BytesIO(csv_bytes), len(csv_bytes),
                          content_type='text/csv')
        print(f"OK → bronze/{filename} ({len(df)} lignes)")

    # Gares SNCF
    print("=== Gares SNCF ===")
    url = "https://ressources.data.sncf.com/api/explore/v2.1/catalog/datasets/gares-de-voyageurs/exports/csv?use_labels=true"
    r = requests.get(url, timeout=120)
    df = pd.read_csv(io.StringIO(r.text), sep=';', low_memory=False)
    if len(df.columns) < 3:
        df = pd.read_csv(io.StringIO(r.text), sep=',', low_memory=False)
    upload(df, 'gares_raw.csv')

    # Festivals
    print("=== Festivals ===")
    url = "https://data.culture.gouv.fr/api/explore/v2.1/catalog/datasets/panorama-des-festivals/exports/csv?limit=-1"
    r = requests.get(url, timeout=120)
    df = pd.read_csv(io.StringIO(r.text), sep=';', low_memory=False)
    if len(df.columns) < 3:
        df = pd.read_csv(io.StringIO(r.text), sep=',', low_memory=False)
    upload(df, 'festivals_raw.csv')

    print("Bronze API termine !")

task_bronze = PythonOperator(
    task_id='ingestion_bronze',
    python_callable=ingestion_bronze,
    dag=dag,
)

# ══════════════════════════════════════════════════════
# ÉTAPE 2 — BRONZE : Kafka producer (fichiers locaux)
# ══════════════════════════════════════════════════════
task_kafka_producer = BashOperator(
    task_id='kafka_producer',
    bash_command='python /opt/airflow/scripts/10_kafka_producer_final.py',
    dag=dag,
)

# ══════════════════════════════════════════════════════
# ÉTAPE 3 — BRONZE : Kafka consumer → MinIO
# ══════════════════════════════════════════════════════
task_kafka_consumer = BashOperator(
    task_id='kafka_consumer',
    bash_command='python /opt/airflow/scripts/11_kafka_consumer_final.py',
    dag=dag,
)

# ══════════════════════════════════════════════════════
# ÉTAPE 4 — SILVER : Nettoyage Gares
# ══════════════════════════════════════════════════════
def silver_gares():
    import pandas as pd
    import io
    from minio import Minio
    import os

    endpoint = os.getenv('MINIO_ENDPOINT', 'minio:9000')
    client = Minio(endpoint,
                   access_key=os.getenv('MINIO_ACCESS_KEY', 'admin'),
                   secret_key=os.getenv('MINIO_SECRET_KEY', 'password123'),
                   secure=False)

    obj = client.get_object('bronze', 'gares_raw.csv')
    df = pd.read_csv(io.BytesIO(obj.read()), low_memory=False)
    print(f"Avant : {len(df)} lignes")

    df = df.drop_duplicates()

    # Extraire latitude/longitude
    if 'Position géographique' in df.columns:
        df['latitude']  = df['Position géographique'].str.split(',').str[0].astype(float, errors='ignore')
        df['longitude'] = df['Position géographique'].str.split(',').str[1].astype(float, errors='ignore')

    df = df.rename(columns={
        'Nom': 'nom_gare',
        'Code commune': 'code_commune',
        'Code(s) UIC': 'code_uic'
    })

    cols = [c for c in ['nom_gare', 'code_commune', 'code_uic', 'latitude', 'longitude'] if c in df.columns]
    df = df[cols].dropna(subset=['latitude', 'longitude'])
    print(f"Après : {len(df)} lignes")

    csv_bytes = df.to_csv(index=False).encode('utf-8')
    client.put_object('silver', 'gares_silver.csv',
                      io.BytesIO(csv_bytes), len(csv_bytes),
                      content_type='text/csv')
    print(f"OK → silver/gares_silver.csv")

task_silver_gares = PythonOperator(
    task_id='silver_gares',
    python_callable=silver_gares,
    dag=dag,
)

# ══════════════════════════════════════════════════════
# ÉTAPE 5 — SILVER : Nettoyage Datatourisme
# ══════════════════════════════════════════════════════
task_silver_datatourisme = BashOperator(
    task_id='silver_datatourisme',
    bash_command='python /opt/airflow/scripts/silver_clean_datatourisme.py',
    dag=dag,
)

# ══════════════════════════════════════════════════════
# ÉTAPE 6 — SILVER : Nettoyage Festivals
# ══════════════════════════════════════════════════════
task_silver_festivals = BashOperator(
    task_id='silver_festivals',
    bash_command='python /opt/airflow/scripts/silver_clean_festivale.py',
    dag=dag,
)

# ══════════════════════════════════════════════════════
# ÉTAPE 7 — SILVER : Limoges fréquentation
# ══════════════════════════════════════════════════════
task_silver_limoges = BashOperator(
    task_id='silver_limoges',
    bash_command='python /opt/airflow/scripts/silver_clean_limoges_freq.py',
    dag=dag,
)

# ══════════════════════════════════════════════════════
# ÉTAPE 8 — GOLD : ML + agrégation
# ══════════════════════════════════════════════════════
task_gold = BashOperator(
    task_id='gold_ml',
    bash_command='python /opt/airflow/scripts/gold_ml.py',
    dag=dag,
)

# ══════════════════════════════════════════════════════
# ÉTAPE 9 — Vérification finale
# ══════════════════════════════════════════════════════
def verification_finale():
    from minio import Minio
    import os

    endpoint = os.getenv('MINIO_ENDPOINT', 'minio:9000')
    client = Minio(endpoint,
                   access_key=os.getenv('MINIO_ACCESS_KEY', 'admin'),
                   secret_key=os.getenv('MINIO_SECRET_KEY', 'password123'),
                   secure=False)

    print("\n=== VÉRIFICATION FINALE ===")
    total = 0
    for bucket in ['bronze', 'silver', 'gold']:
        objets = list(client.list_objects(bucket))
        print(f"\nBucket '{bucket}' : {len(objets)} fichiers")
        for obj in objets:
            taille = round((obj.size or 0) / 1024)
            total += taille
            print(f"  ✅ {obj.object_name:<45} {taille:>6} Ko")
    print(f"\nTOTAL : {round(total/1024)} Mo")
    print("\nPipeline 100% terminée !")

task_verification = PythonOperator(
    task_id='verification_finale',
    python_callable=verification_finale,
    dag=dag,
)

# ══════════════════════════════════════════════════════
# ORDRE D'EXÉCUTION
# ══════════════════════════════════════════════════════
task_bronze >> task_kafka_producer >> task_kafka_consumer

task_kafka_consumer >> task_silver_gares
task_kafka_consumer >> task_silver_datatourisme
task_kafka_consumer >> task_silver_festivals
task_kafka_consumer >> task_silver_limoges

[task_silver_gares,
 task_silver_datatourisme,
 task_silver_festivals,
 task_silver_limoges] >> task_gold >> task_verification
