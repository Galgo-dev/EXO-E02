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
