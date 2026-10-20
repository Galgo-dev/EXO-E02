# Agent conseil de classe

Agent local qui propose des appréciations générales à partir des exports CSV et de la charte de rédaction.
Le principal valide chaque proposition. Voir `ressource/` pour les données et la charte.

## Installation

```
.venv\Scripts\python -m pip install -r requirements.txt
```

Créer un fichier `.env` à la racine :

```
GEMINI_API_KEY=...
GEMINI_MODEL=...   # optionnel
```

## Vérifier la clé et les modèles

```
.venv\Scripts\python main.py --modeles
```

## Commandes

```
.venv\Scripts\python main.py ressource\classe_1 --analyse           # indicateurs de la charte, sans modèle
.venv\Scripts\python main.py ressource\classe_1 --limite 2          # propositions pour les 2 premiers élèves
.venv\Scripts\python main.py ressource\classe_1 --limite 1 --eleve 1R2-010
```

Le modèle par défaut est `gemini-3.6-flash` ; `GEMINI_MODEL` dans `.env` le remplace.
