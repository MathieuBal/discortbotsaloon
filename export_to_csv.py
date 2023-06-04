import psycopg2
import csv

# Connexion à la base de données
conn = psycopg2.connect(
    host="localhost",
    database="saloon_db",
    user="postgres",
    password="21052105"
)

# Liste des tables à exporter
tables = ["accounting", "drinks", "finished_products", "fournisseurs", "fournitures", "ingredients", "meals", "recipe_ingredients", "salaries"]

# Exportation des tables vers un fichier CSV
with open("export.csv", "w", newline="") as csvfile:
    writer = csv.writer(csvfile)

    # Parcourir les tables
    for table in tables:
        # Exécution de la requête SELECT pour chaque table
        cur = conn.cursor()
        cur.execute(f"SELECT * FROM {table}")

        # Enregistrement des en-têtes de colonnes
        writer.writerow([desc[0] for desc in cur.description])

        # Enregistrement des données de la table
        for row in cur:
            writer.writerow(row)

        cur.close()

# Fermeture de la connexion à la base de données
conn.close()
