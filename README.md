# Agent conseil de classe

Agent local qui propose des appréciations générales à partir des exports CSV et de la charte de rédaction.
Le principal valide chaque proposition. Voir `ressource/` pour les données et la charte.
L'agent utilise l'API Claude (Anthropic).

## Installation

```
.venv\Scripts\python -m pip install -r requirements.txt
```

Créer un fichier `.env` à la racine :

```
CLAUDE_API_KEY=...
CLAUDE_MODEL=...   # optionnel, claude-haiku-5-5 par défaut
```

Modèles connus pour l'estimation du coût : `claude-opus-5-5`, `claude-sonnet-5-5`, `claude-haiku-5-5`.

## Commandes

```
.venv\Scripts\python main.py --modeles                                   # liste les modèles (sans coût)
.venv\Scripts\python main.py ressource\classe_1 --analyse                 # indicateurs de la charte, sans modèle
.venv\Scripts\python main.py ressource\classe_1 --apercu --limite 1       # une proposition, sans validation
.venv\Scripts\python main.py ressource\classe_1                           # validation élève par élève, puis synthèse de classe
.venv\Scripts\python main.py ressource\classe_1 --synthese                 # refait seulement la synthèse de classe
```

Pendant la validation : Entrée valide, `m` remplace le texte, `r` régénère la proposition.
Les fichiers sont écrits dans `sorties\<classe>\` après chaque élève validé :
`appreciations.csv`, `a_surveiller.csv`, `commentaires_ecartes.csv`.
La synthèse de classe (10 lignes au plus, `synthese.md`) est proposée une fois la classe entière validée,
sauf avec `--limite` ou `--eleve`. Elle utilise les statistiques calculées par le code et les appréciations validées,
sans les noms des élèves. `--synthese` la refait sans repasser par les élèves.
La consommation de jetons et le coût estimé sont affichés en fin de session.

## Tests

```
.venv\Scripts\python -m pytest -q
```

Les tests n'appellent jamais l'API : l'agent est testé avec un faux client.
