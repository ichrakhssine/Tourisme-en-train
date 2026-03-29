import io
import pandas as pd
from minio import Minio

client = Minio("localhost:9000", access_key="admin", secret_key="password123", secure=False)

def upload(filepath, filename):
    print(f"=== Upload : {filename} ===")
    try:
        df = pd.read_csv(filepath, sep=";", low_memory=False)
        if len(df) < 10:
            df = pd.read_csv(filepath, sep=",", low_memory=False)
    except Exception as e:
        print(f"  Erreur lecture : {e}")
        return
    print(f"  {len(df)} lignes trouvees")
    print(f"  Colonnes : {list(df.columns[:5])}")
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    client.put_object("bronze", filename, io.BytesIO(csv_bytes), len(csv_bytes), content_type="text/csv")
    print(f"  OK - {filename} uploade dans bronze")

# Dataset 3 - DATAtourisme evenements
upload(r"data\raw\evenements.csv", "datatourisme_raw.csv")

# Dataset 4 - INSEE frequentation
upload(r"data\raw\DS_TOUR_CAP_2026_data.csv", "frequentation_raw.csv")

# Résumé MinIO
print("\n=== Contenu MinIO/bronze/ ===")
for obj in client.list_objects("bronze"):
    taille = round((obj.size or 0) / 1024)
    print(f"  {obj.object_name:<40} {taille} Ko")
