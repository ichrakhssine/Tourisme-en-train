from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import DoubleType
from minio import Minio
import pandas as pd
from io import BytesIO

spark = SparkSession.builder \
    .appName("Silver_Festivals") \
    .config("spark.driver.memory", "2g") \
    .getOrCreate()
spark.sparkContext.setLogLevel("ERROR")
print("Spark demarre !")

client = Minio("host.docker.internal:9000",
               access_key="admin",
               secret_key="password123",
               secure=False)

print("\n=== Lecture bronze/festivals_raw.csv ===")
response = client.get_object("bronze", "festivals_raw.csv")
pdf = pd.read_csv(BytesIO(response.read()), low_memory=False)
sdf = spark.createDataFrame(pdf)
print(f"Avant nettoyage : {sdf.count()} lignes")

# Supprimer doublons
sdf = sdf.dropDuplicates()
print(f"Apres doublons  : {sdf.count()} lignes")

# Séparer GPS
sdf = sdf.withColumn("latitude",
        F.split(F.col("coordonnees_insee"), ",")[0].cast(DoubleType())) \
         .withColumn("longitude",
        F.split(F.col("coordonnees_insee"), ",")[1].cast(DoubleType()))

# Garder colonnes utiles
sdf = sdf.select(
    F.col("nom_de_la_manifestation").alias("nom_festival"),
    F.col("region"),
    F.col("domaine"),
    F.col("commune_principale").alias("commune"),
    F.col("departement"),
    F.col("mois_habituel_de_debut").alias("mois_debut"),
    F.col("latitude"),
    F.col("longitude")
).dropna(subset=["latitude", "longitude"])

print(f"Final           : {sdf.count()} lignes")
sdf.show(5, truncate=False)

print("\n=== Upload silver/festivals_silver.csv ===")
pdf_clean = sdf.toPandas()
pdf_clean.to_csv("/tmp/festivals_silver.csv", index=False)
client.fput_object("silver", "festivals_silver.csv", "/tmp/festivals_silver.csv")
print(f"OK ! {len(pdf_clean)} festivals dans MinIO/silver/")

spark.stop()
print("Spark arrete. Festivals Silver termine !")