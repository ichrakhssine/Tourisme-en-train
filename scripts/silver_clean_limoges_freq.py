from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import DoubleType
from minio import Minio
import pandas as pd
from io import BytesIO

spark = SparkSession.builder \
    .appName("Silver_Limoges_Freq") \
    .config("spark.driver.memory", "4g") \
    .getOrCreate()
spark.sparkContext.setLogLevel("ERROR")
print("Spark demarre !")

client = Minio("host.docker.internal:9000",
               access_key="admin",
               secret_key="password123",
               secure=False)

# ══════════════════════════════════════
# 1. LIMOGES CYCLABLE
# ══════════════════════════════════════
print("\n=== Limoges Cyclable ===")
response = client.get_object("bronze", "limoges_cycle_raw.csv")
pdf = pd.read_csv(BytesIO(response.read()), low_memory=False)

# Convertir tout en string pour éviter les conflits de types
pdf = pdf.astype(str)

sdf = spark.createDataFrame(pdf)
print(f"Avant : {sdf.count()} lignes")

sdf = sdf.dropDuplicates()
sdf = sdf.select(
    F.col("X").cast(DoubleType()).alias("longitude"),
    F.col("Y").cast(DoubleType()).alias("latitude"),
    F.col("ame_d").alias("type_amenagement"),
    F.col("regime_d").alias("regime"),
    F.col("statut_d").alias("statut")
).dropna(subset=["latitude", "longitude"])

print(f"Final : {sdf.count()} lignes")
sdf.show(3, truncate=False)
pdf_clean = sdf.toPandas()
pdf_clean.to_csv("/tmp/limoges_cycle_silver.csv", index=False)
client.fput_object("silver", "limoges_cycle_silver.csv",
                   "/tmp/limoges_cycle_silver.csv")
print("OK → silver/limoges_cycle_silver.csv")

# ══════════════════════════════════════
# 2. LIMOGES PATRIMOINE
# ══════════════════════════════════════
print("\n=== Limoges Patrimoine ===")
response = client.get_object("bronze", "limoges_historic_raw.csv")
pdf = pd.read_csv(BytesIO(response.read()), low_memory=False)
sdf = spark.createDataFrame(pdf)
print(f"Avant : {sdf.count()} lignes")

sdf = sdf.dropDuplicates()
sdf = sdf.select(
    F.col("X").cast(DoubleType()).alias("longitude"),
    F.col("Y").cast(DoubleType()).alias("latitude"),
    F.col("name"),
    F.col("type"),
    F.col("heritage"),
    F.col("com_nom")
).dropna(subset=["latitude", "longitude"])

print(f"Final : {sdf.count()} lignes")
sdf.show(3, truncate=False)
pdf_clean = sdf.toPandas()
pdf_clean.to_csv("/tmp/limoges_historic_silver.csv", index=False)
client.fput_object("silver", "limoges_historic_silver.csv",
                   "/tmp/limoges_historic_silver.csv")
print("OK → silver/limoges_historic_silver.csv")

# ══════════════════════════════════════
# 3. FREQUENTATION INSEE
# ══════════════════════════════════════
print("\n=== Frequentation INSEE ===")
response = client.get_object("bronze", "frequentation_raw.csv")
pdf = pd.read_csv(BytesIO(response.read()), low_memory=False)
sdf = spark.createDataFrame(pdf)
print(f"Avant : {sdf.count()} lignes")

annee_max = sdf.agg(F.max("TIME_PERIOD")).collect()[0][0]
print(f"Année max : {annee_max}")

sdf = sdf.filter(
    (F.col("TIME_PERIOD") == annee_max) &
    (F.col("TOUR_MEASURE") == "UNIT_LOC")
).dropDuplicates(["GEO", "ACTIVITY"])

sdf = sdf.select(
    F.col("GEO").alias("code_geo"),
    F.col("GEO_OBJECT").alias("nom_geo"),
    F.col("ACTIVITY").alias("activite"),
    F.col("OBS_VALUE").alias("nb_etablissements"),
    F.col("TIME_PERIOD").alias("annee")
)

print(f"Final : {sdf.count()} lignes")
sdf.show(3, truncate=False)
pdf_clean = sdf.toPandas()
pdf_clean.to_csv("/tmp/frequentation_silver.csv", index=False)
client.fput_object("silver", "frequentation_silver.csv",
                   "/tmp/frequentation_silver.csv")
print("OK → silver/frequentation_silver.csv")

spark.stop()
print("\nLimoges + Frequentation Silver termine !")