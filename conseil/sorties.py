"""Écriture et relecture des fichiers de sortie (CSV, séparateur virgule, point décimal)."""
import csv

COLONNES_APPRECIATIONS = ["matricule", "nom", "prenom", "classe", "appreciation_generale"]
COLONNES_A_SURVEILLER = ["matricule", "nom", "prenom", "classe", "motif"]
COLONNES_ECARTES = ["matricule", "matiere", "enseignant", "raison"]


def _ecrire_csv(chemin, colonnes, lignes):
    # utf-8-sig : Excel reconnaît les accents.
    with open(chemin, "w", encoding="utf-8-sig", newline="") as f:
        ecrivain = csv.DictWriter(f, fieldnames=colonnes)
        ecrivain.writeheader()
        ecrivain.writerows(lignes)


def ecrire_sorties(dossier, appreciations, a_surveiller, commentaires_ecartes):
    """Écrit les trois CSV de la classe dans `dossier` (créé si besoin)."""
    dossier.mkdir(parents=True, exist_ok=True)
    _ecrire_csv(dossier / "appreciations.csv", COLONNES_APPRECIATIONS, appreciations)
    _ecrire_csv(dossier / "a_surveiller.csv", COLONNES_A_SURVEILLER, a_surveiller)
    _ecrire_csv(dossier / "commentaires_ecartes.csv", COLONNES_ECARTES, commentaires_ecartes)


def lire_appreciations(dossier):
    """Relit les appréciations validées d'une classe ; liste vide si le fichier n'existe pas."""
    chemin = dossier / "appreciations.csv"
    if not chemin.exists():
        return []
    with open(chemin, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def ecrire_synthese(dossier, classe, texte):
    """Écrit la synthèse de classe validée dans synthese.md."""
    dossier.mkdir(parents=True, exist_ok=True)
    (dossier / "synthese.md").write_text(
        f"# Synthèse de la classe {classe}\n\n{texte.strip()}\n", encoding="utf-8"
    )
