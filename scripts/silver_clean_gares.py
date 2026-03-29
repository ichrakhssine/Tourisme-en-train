import os
import sys
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import DoubleType
from minio import Minio
import pandas as pd
from io import BytesIO

# Démarrer Spark
spark = SparkSession.builder \
    .appName("Silver_Gares") \
    .config("spark.driver.memory", "2g") \
    .getOrCreate()

spark.sparkContext.setLogLevel("ERROR")
print("Spark demarre !")

# Connexion MinIO
client = Minio("host.docker.internal:9000",
               access_key="admin",
               secret_key="password123",
               secure=False)

# Lire Bronze
print("\n=== Lecture bronze/gares_raw.csv ===")
response = client.get_object("bronze", "gares_raw.csv")
pdf = pd.read_csv(BytesIO(response.read()), low_memory=False)
sdf = spark.createDataFrame(pdf)
print(f"Avant nettoyage : {sdf.count()} lignes")

# Supprimer doublons
sdf = sdf.dropDuplicates()
print(f"Apres doublons  : {sdf.count()} lignes")

# Séparer GPS
sdf = sdf.withColumn("latitude",
        F.split(F.col("Position géographique"), ",")[0].cast(DoubleType())) \
         .withColumn("longitude",
        F.split(F.col("Position géographique"), ",")[1].cast(DoubleType()))

# Garder colonnes utiles
sdf = sdf.select(
    F.col("Nom").alias("nom_gare"),
    F.col("Code commune").alias("code_commune"),
    F.col("Code(s) UIC").alias("code_uic"),
    F.col("latitude"),
    F.col("longitude")
).dropna(subset=["latitude", "longitude"])

print(f"Final           : {sdf.count()} lignes")
sdf.show(5, truncate=False)

# Sauver dans Silver
print("\n=== Upload silver/gares_silver.csv ===")
pdf_clean = sdf.toPandas()
pdf_clean.to_csv("/tmp/gares_silver.csv", index=False)
client.fput_object("silver", "gares_silver.csv", "/tmp/gares_silver.csv")
print(f"OK ! {len(pdf_clean)} gares dans MinIO/silver/")

spark.stop()
print("Spark arrete. Gares Silver termine !")