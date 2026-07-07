# Pipeline ETL local — Python / SQLite

Pipeline ETL local en Python : ingestion d’un fichier CSV, validation du schéma, typage des données, chargement idempotent dans SQLite et vérification SQL.

---

## Objectif

Ce projet démontre la construction d’un pipeline d’ingestion de données simple, local et reproductible.

Le script lit un fichier CSV de commandes, contrôle sa structure, nettoie et convertit certains champs, puis charge les données dans une base SQLite.

L’objectif est de montrer une logique d’ingestion claire :

```text
Source CSV → Validation → Transformation → Stockage SQLite → Vérification
```

---

## Structure du projet

```text
pipeline-etl-local-python-sqlite/
├── README.md
├── .gitignore
├── LICENSE
├── data/
│   └── orders_raw.csv        # Fichier CSV source d'exemple
└── src/
    └── ingest_orders.py      # Script principal d'ingestion
```

La base SQLite `warehouse.db` est générée localement lors de l’exécution du script.  
Elle n’est pas versionnée dans le dépôt GitHub.

---

## Entrée

Le script attend un fichier CSV contenant les colonnes suivantes :

```text
order_id, order_date, customer_id, product_id, product_category, quantity, unit_price
```

Exemple de ligne :

```csv
1001,2026-02-01,501,2001,Books,2,12.50
```

---

## Sortie

Le script crée ou réinitialise une base SQLite, puis alimente la table suivante :

```text
orders_raw
```

Schéma de la table :

| Colonne | Type SQLite | Description |
|---|---:|---|
| `order_id` | TEXT | Identifiant de commande |
| `order_date` | TEXT | Date de commande |
| `customer_id` | TEXT | Identifiant client |
| `product_id` | TEXT | Identifiant produit |
| `product_category` | TEXT | Catégorie produit |
| `quantity` | INTEGER | Quantité commandée |
| `unit_price` | REAL | Prix unitaire |

---

## Pipeline

À chaque exécution, le script suit les étapes suivantes :

```text
Arguments CLI (--csv, --db)
   ↓
Vérification de l’existence du fichier CSV
   ↓
Connexion à SQLite
   ↓
Initialisation de la table cible
   ↓
Lecture du CSV
   ↓
Validation du schéma
   ↓
Nettoyage et typage des données
   ↓
Insertion en base
   ↓
Vérification du nombre de lignes chargées
   ↓
Fermeture de la connexion
```

---

## Fonctionnement détaillé

Le script :

1. lit les chemins passés en ligne de commande avec `--csv` et `--db` ;
2. vérifie que le fichier CSV existe ;
3. ouvre une connexion vers la base SQLite cible ;
4. supprime la table `orders_raw` si elle existe déjà ;
5. recrée la table `orders_raw` ;
6. lit le fichier CSV avec `csv.DictReader` ;
7. vérifie que les colonnes du CSV correspondent exactement au schéma attendu ;
8. nettoie les espaces autour des valeurs texte ;
9. convertit `quantity` en entier ;
10. convertit `unit_price` en nombre décimal ;
11. insère les lignes dans SQLite avec une requête SQL paramétrée ;
12. valide les insertions avec `commit()` ;
13. vérifie le nombre de lignes réellement présentes en base avec `COUNT(*)` ;
14. ferme proprement la connexion à la base.

---

## Idempotence

Le pipeline est idempotent de manière simple.

À chaque exécution, la table cible est supprimée puis recréée :

```sql
DROP TABLE IF EXISTS orders_raw;
CREATE TABLE orders_raw (...);
```

Cela signifie que relancer le script avec le même fichier CSV ne duplique pas les lignes.  
La table repart d’un état propre avant chaque chargement.

---

## Exécution locale

### 1. Cloner le dépôt

```bash
git clone https://github.com/louis-mora/pipeline-etl-local-python-sqlite.git
cd pipeline-etl-local-python-sqlite
```

### 2. Créer un environnement virtuel

Le projet utilise uniquement des modules de la bibliothèque standard Python.  
L’environnement virtuel est donc recommandé, mais aucun package externe n’est nécessaire.

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Lancer le pipeline

Depuis la racine du projet :

```bash
python3 src/ingest_orders.py --csv data/orders_raw.csv --db warehouse.db
```

Sortie attendue avec le fichier d’exemple :

```text
[START] Ingestion CSV -> SQLite
[INFO] CSV: data/orders_raw.csv
[INFO] DB : warehouse.db
[STEP] init_db (DROP/CREATE) ...
[OK] DB initialized.
[STEP] load_csv_to_db ...
[OK] Inserted rows: 5
[CHECK] DB row count: 5
[DONE] Ingestion completed successfully.
```

---

## Vérification manuelle

Après exécution, la base `warehouse.db` est générée localement.

Compter les lignes chargées :

```bash
sqlite3 warehouse.db "SELECT COUNT(*) FROM orders_raw;"
```

Résultat attendu avec le fichier d’exemple :

```text
5
```

Afficher les premières lignes :

```bash
sqlite3 warehouse.db "SELECT * FROM orders_raw LIMIT 5;"
```

---

## Gestion des erreurs

Le script lève une erreur lisible dans les cas suivants :

- fichier CSV introuvable ;
- CSV sans ligne d’en-tête ;
- colonnes manquantes ;
- colonnes inattendues ;
- valeur non convertible en entier pour `quantity` ;
- valeur non convertible en nombre décimal pour `unit_price`.

En cas d’erreur, le script affiche un message `[ERROR]` et retourne un code de sortie `1`.

---

## Points techniques démontrés

- Lecture d’un fichier CSV avec `csv.DictReader`
- Validation stricte du schéma d’entrée
- Nettoyage simple des valeurs texte
- Conversion contrôlée de types avec `int` et `float`
- Création et alimentation d’une table SQLite
- Utilisation de requêtes SQL paramétrées
- Découpage du code en fonctions lisibles
- Orchestration via une fonction `main(argv)`
- Passage de chemins en ligne de commande avec `--csv` et `--db`
- Vérification du chargement avec `COUNT(*)`
- Fermeture propre de la connexion avec `try/finally`
- Idempotence simple par `DROP TABLE` / `CREATE TABLE`
- Code de sortie explicite : `0` en cas de succès, `1` en cas d’erreur

---

## Fichiers ignorés

Le dépôt ne versionne pas les fichiers générés localement.

Exemples recommandés dans `.gitignore` :

```gitignore
.DS_Store
.venv/
__pycache__/
*.pyc
warehouse.db
```

---

## Limites connues

Ce projet est volontairement minimal.

Il ne couvre pas encore :

- la gestion avancée des transactions ;
- les logs applicatifs structurés avec le module `logging` ;
- les tests automatisés ;
- l’ingestion depuis une API ;
- l’orchestration avec un outil externe ;
- l’utilisation de `argparse` pour une CLI plus complète.

Ces éléments pourront être ajoutés dans des itérations futures.
