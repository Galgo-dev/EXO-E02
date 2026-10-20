# Agent conseil de classe

Agent IA local, niveau « agent simple » : une boucle d'agent sur le poste, avec des outils limités
aux fichiers locaux et au code. À partir de deux exports CSV par classe et de la charte de rédaction,
il propose :

- une appréciation générale par élève (300 caractères au plus) ;
- la liste des élèves à surveiller, avec le motif (absences ou baisse des notes) ;
- une synthèse de classe (10 lignes au plus).

Le professeur principal valide, modifie ou fait régénérer chaque proposition.
L'agent utilise l'API Claude (Anthropic). Les données de test sont dans `ressource/`.

## Principe

Le code décide, le modèle rédige.

- Les seuils de la charte (12 demi-journées d'absence, 5 matières en baisse d'au moins 1,0 point,
  forte progression de 2,0 points) sont calculés en Python, dans `conseil/regles.py`.
- Le modèle rédige et repère les commentaires d'enseignants contraires à la charte
  (jugement de personnalité, situation familiale ou sociale, motif d'absence).
- Le modèle n'a aucun accès au disque. Ses seuls outils sont en lecture seule : `lire_charte`,
  `absences_graves`, `matieres_en_baisse`, `a_surveiller`. Ils n'ont pas d'argument, donc il ne peut
  pas inventer de chiffres.
- Chaque proposition est vérifiée par le code (longueur, formulations interdites, absences citées
  sans seuil atteint, 10 lignes) et régénérée une fois en cas d'écart.
- Le principal valide tout avant l'écriture des fichiers.

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

## Utilisation

```
.venv\Scripts\python main.py --modeles                                   # liste les modèles (sans coût)
.venv\Scripts\python main.py ressource\classe_1 --analyse                 # indicateurs de la charte, sans modèle
.venv\Scripts\python main.py ressource\classe_1 --apercu --limite 1       # une proposition, sans validation
.venv\Scripts\python main.py ressource\classe_1                           # validation élève par élève, puis synthèse de classe
.venv\Scripts\python main.py ressource\classe_1 --synthese                 # refait seulement la synthèse de classe
```

Le dossier de classe contient un fichier `eleves*.csv` et un fichier `appreciations*.csv`.

Pendant la validation : Entrée valide, `m` remplace le texte, `r` régénère la proposition.
`--limite N` et `--eleve MATRICULE` restreignent la session ; la synthèse de classe n'est alors pas proposée.
La consommation de jetons et le coût estimé sont affichés en fin de session.

## Fichiers produits

Écrits dans `sorties\<classe>\` (le dossier est ignoré par git), après chaque élève validé :

| Fichier | Contenu |
|---|---|
| `appreciations.csv` | matricule, nom, prénom, classe, appréciation générale |
| `a_surveiller.csv` | matricule, nom, prénom, classe, motif |
| `commentaires_ecartes.csv` | matricule, matière, enseignant, raison |
| `synthese.md` | synthèse de la classe, 10 lignes au plus |

La synthèse utilise les statistiques calculées par le code et les appréciations validées,
sans les noms des élèves.

## Organisation du code

| Fichier | Rôle |
|---|---|
| `main.py` | ligne de commande, session de validation |
| `conseil/regles.py` | seuils de la charte, indicateurs, statistiques, vérifications |
| `conseil/donnees.py` | lecture et contrôle des CSV et de la charte |
| `conseil/outils.py` | outils en lecture seule exposés au modèle |
| `conseil/agent.py` | client Claude, boucle d'outils, appréciation et synthèse |
| `conseil/validation.py` | validation par le principal (Entrée, m, r) |
| `conseil/sorties.py` | écriture et relecture des fichiers de sortie |

## Tests

```
.venv\Scripts\python -m pytest -q
```

Les tests n'appellent jamais l'API : l'agent est testé avec un faux client.
Les fixtures de `tests/fixtures/` sont dérivées des données réelles de la classe 1.

### Cas de test de la fiche de cadrage

| Cas | Entrée | Résultat attendu | Vérification |
|---|---|---|---|
| 1 | 10 élèves au-dessus du seuil d'absences | les 10 élèves sont à surveiller | automatique (`test_cas_1`) |
| 2 | moitié en progression, moitié en baisse | synthèse de classe nuancée | statistiques automatiques (`test_cas_2`), rédaction à la main |
| 3 | 5 élèves avec 5 matières en baisse | les 5 élèves sont à surveiller | automatique (`test_cas_3`) |
| 4 | liste vide | l'agent signale que la liste est vide | automatique (`test_cas_4`) |
| 5 | valeurs dans les mauvaises colonnes | l'agent signale un format invalide | automatique (`test_cas_5`) |
| 6 | charte vide | l'agent signale que la charte est vide | automatique (`test_cas_6`) |
| 7 | commentaire d'enseignant non conforme | commentaire ignoré, professeur signalé | transmission automatique (`test_cas_7`), détection à la main |

### Vérifications à la main (20 octobre 2026, modèle `claude-haiku-5-5`)

- **Cas 7.** Sur Léna Vincent (1R2-001), le commentaire de Mme Delcourt sur un « milieu favorisé »
  est écarté et le professeur est nommé. L'appréciation ne le reprend pas.
- **Cas 2.** Sur la fixture `cas2_mixte` (5 élèves en forte progression, 5 en baisse généralisée),
  la synthèse de 7 lignes cite les deux groupes avec leurs effectifs. Elle ne qualifie pas la classe
  par un mot global comme « moyenne » : elle reste factuelle, ce qui est conforme à la charte.

## Limites connues

- Les seuils sont des constantes dans `regles.py`, à mettre à jour si la charte change.
- Les modèles Claude 5 n'acceptent pas le réglage de la température demandé par la fiche.
  Les garde-fous sont le prompt strict, les vérifications du code et la relecture du principal.
- La vérification automatique ne contrôle pas chaque fait cité : la relecture reste indispensable.
- Un refus de Claude est signalé comme une erreur ; aucun modèle de repli n'est configuré.
- Selon la charte, « sans difficulté » ne tient pas compte des baisses de notes : un élève peut
  être à la fois à surveiller et sans difficulté.
