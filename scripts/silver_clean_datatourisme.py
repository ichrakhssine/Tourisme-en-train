from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import DoubleType
from minio import Minio
import pandas as pd
from io import BytesIO

spark = SparkSession.builder \
    .appName("Silver_DATAtourisme") \
    .config("spark.driver.memory", "4g") \
    .getOrCreate()
spark.sparkContext.setLogLevel("ERROR")
print("Spark demarre !")

client = Minio("host.docker.internal:9000",
               access_key="admin",
               secret_key="password123",
               secure=False)

def extraire_categorie(texte):
    if not texte:
        return "Autre"
    ignorer = {"PointOfInterest", "PlaceOfInterest",
               "EntertainmentAndEvent", "Product", "Visit", "Event"}
    for partie in str(texte).split("|"):
        if "datatourisme.fr/ontology/core#" in partie:
            nom = partie.split("#")[-1]
            if nom not in ignorer:
                return nom
    return "Autre"

udf_categorie = F.udf(extraire_categorie)

def nettoyer(filename_in, filename_out, label):
    print(f"\n=== {label} ===")
    response = client.get_object("bronze", filename_in)
    pdf = pd.read_csv(BytesIO(response.read()), low_memory=False)
    sdf = spark.createDataFrame(pdf)
    print(f"Avant : {sdf.count()} lignes")

    sdf = sdf.dropDuplicates()
    sdf = sdf.withColumn("categorie", udf_categorie(F.col("Categories_de_POI")))
    sdf = sdf.select(
        F.col("Nom_du_POI").alias("nom_poi"),
        F.col("categorie"),
        F.col("Latitude").cast(DoubleType()).alias("latitude"),
        F.col("Longitude").cast(DoubleType()).alias("longitude"),
        F.col("Code_postal_et_commune").alias("commune"),
        F.col("Description").alias("description")
    ).dropna(subset=["latitude", "longitude"])

    sdf = sdf.filter(
        F.col("latitude").between(41, 52) &
        F.col("longitude").between(-5, 10)
    )

    print(f"Final : {sdf.count()} lignes")
    sdf.show(3, truncate=True)

    pdf_clean = sdf.toPandas()
    pdf_clean.to_csv(f"/tmp/{filename_out}", index=False)
    client.fput_object("silver", filename_out,
                       f"/tmp/{filename_out}")
    print(f"OK → silver/{filename_out}")

nettoyer("datatourisme_naq_raw.csv", "datatourisme_naq_silver.csv", "NAQ Nouvelle-Aquitaine")
nettoyer("datatourisme_idf_raw.csv", "datatourisme_idf_silver.csv", "IDF Île-de-France")
nettoyer("datatourisme_tour_raw.csv", "datatourisme_tour_silver.csv", "TOUR Itinéraires France")

spark.stop()
print("\nDATAtourisme Silver termine !")