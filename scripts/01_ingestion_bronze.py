import io
import requests
import pandas as pd
from minio import Minio

client = Minio("localhost:9000", access_key="admin", secret_key="password123", secure=False)

def upload(df, filename):
    print(f"  {len(df)} lignes trouvees")
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    client.put_object("bronze", filename, io.BytesIO(csv_bytes), len(csv_bytes), content_type="text/csv")
    print(f"  OK - {filename} uploade dans bronze")

# Dataset 1 - Gares SNCF
print("=== Gares SNCF ===")
url = "https://ressources.data.sncf.com/api/explore/v2.1/catalog/datasets/gares-de-voyageurs/exports/csv?use_labels=true"
response = requests.get(url, timeout=120)
df = pd.read_csv(io.StringIO(response.text), sep=";", low_memory=False)
if len(df) < 100:
    df = pd.read_csv(io.StringIO(response.text), sep=",", low_memory=False)
upload(df, "gares_raw.csv")

# Dataset 2 - Festivals
print("=== Festivals ===")
url = "https://data.culture.gouv.fr/api/explore/v2.1/catalog/datasets/panorama-des-festivals/exports/csv?limit=-1"
response = requests.get(url, timeout=120)
df = pd.read_csv(io.StringIO(response.text), sep=";", low_memory=False)
if len(df) < 100:
    df = pd.read_csv(io.StringIO(response.text), sep=",", low_memory=False)
upload(df, "festivals_raw.csv")

print("Termine ! Verifie MinIO/bronze/")