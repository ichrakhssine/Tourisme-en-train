import io
import pandas as pd
from minio import Minio

client = Minio("localhost:9000", access_key="admin", secret_key="password123", secure=False)

print("=== Upload : datatourisme_raw.csv ===")
try:
    # Essai 1 : virgule avec guillemets
    df = pd.read_csv(r"data\raw\evenements.csv", sep=",", 
                     quotechar='"', on_bad_lines="skip", 
                     low_memory=False, encoding="utf-8")
    if len(df) < 10:
        # Essai 2 : point-virgule
        df = pd.read_csv(r"data\raw\evenements.csv", sep=";",
                         on_bad_lines="skip", low_memory=False)
    print(f"  {len(df)} lignes trouvees")
    print(f"  Colonnes : {list(df.columns[:6])}")
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    client.put_object("bronze", "datatourisme_raw.csv", 
                      io.BytesIO(csv_bytes), len(csv_bytes), 
                      content_type="text/csv")
    print("  OK - datatourisme_raw.csv uploade dans bronze")
except Exception as e:
    print(f"  Erreur : {e}")

# Résumé MinIO
print("\n=== Contenu MinIO/bronze/ ===")
for obj in client.list_objects("bronze"):
    taille = round((obj.size or 0) / 1024)
    print(f"  {obj.object_name:<40} {taille} Ko")
