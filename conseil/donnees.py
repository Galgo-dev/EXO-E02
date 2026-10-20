"""Lecture et validation des exports CSV et de la charte."""
import csv
from pathlib import Path

COLONNES_ELEVES = [
    "classe", "matricule", "nom", "prenom",
    "moyenne_generale_precedente", "moyenne_generale", "absences_demi_journees",
]
COLONNES_APPRECIATIONS = [
    "classe", "matricule", "matiere", "enseignant",
    "moyenne_trimestre_precedent", "moyenne_trimestre", "appreciation",
]


class DonneesInvalides(ValueError):
    """Les fichiers fournis sont vides ou n'ont pas le format attendu."""


def _lire_csv(chemin, colonnes):
    """Lit un CSV, vérifie ses colonnes et renvoie les lignes avec leur numéro."""
    with open(chemin, encoding="utf-8-sig", newline="") as f:
        lecteur = csv.DictReader(f)
        if lecteur.fieldnames != colonnes:
            raise DonneesInvalides(
                f"{chemin.name} : format invalide, colonnes attendues {colonnes}."
            )
        lignes = list(enumerate(lecteur, start=2))
    if not lignes:
        raise DonneesInvalides(f"{chemin.name} : la liste est vide.")
    return lignes


def _nombre(chemin, numero, ligne, colonne, type_=float):
    try:
        return type_(ligne[colonne])
    except (TypeError, ValueError):
        raise DonneesInvalides(
            f"{chemin.name}, ligne {numero} : format invalide, "
            f"« {ligne[colonne]} » n'est pas un nombre dans la colonne {colonne}."
        ) from None


def _fichier_unique(dossier, motif):
    trouves = sorted(dossier.glob(motif))
    if len(trouves) != 1:
        raise DonneesInvalides(
            f"{dossier} : un seul fichier {motif} attendu, {len(trouves)} trouvé(s)."
        )
    return trouves[0]


def charger_classe(dossier):
    """Charge une classe : liste d'élèves, chacun avec la liste de ses matières."""
    dossier = Path(dossier)
    chemin_eleves = _fichier_unique(dossier, "eleves*.csv")
    chemin_appreciations = _fichier_unique(dossier, "appreciations*.csv")

    eleves = {}
    for numero, ligne in _lire_csv(chemin_eleves, COLONNES_ELEVES):
        eleves[ligne["matricule"]] = {
            "classe": ligne["classe"],
            "matricule": ligne["matricule"],
            "nom": ligne["nom"],
            "prenom": ligne["prenom"],
            "moyenne_precedente": _nombre(chemin_eleves, numero, ligne, "moyenne_generale_precedente"),
            "moyenne": _nombre(chemin_eleves, numero, ligne, "moyenne_generale"),
            "absences": _nombre(chemin_eleves, numero, ligne, "absences_demi_journees", int),
            "matieres": [],
        }

    for numero, ligne in _lire_csv(chemin_appreciations, COLONNES_APPRECIATIONS):
        matricule = ligne["matricule"]
        if matricule not in eleves:
            raise DonneesInvalides(
                f"{chemin_appreciations.name}, ligne {numero} : "
                f"matricule {matricule} absent de {chemin_eleves.name}."
            )
        eleves[matricule]["matieres"].append({
            "matiere": ligne["matiere"],
            "enseignant": ligne["enseignant"],
            "moyenne_precedente": _nombre(chemin_appreciations, numero, ligne, "moyenne_trimestre_precedent"),
            "moyenne": _nombre(chemin_appreciations, numero, ligne, "moyenne_trimestre"),
            "appreciation": ligne["appreciation"],
        })

    sans_matiere = [e["matricule"] for e in eleves.values() if not e["matieres"]]
    if sans_matiere:
        raise DonneesInvalides(
            f"{chemin_appreciations.name} : aucune appréciation pour {sans_matiere}."
        )
    return list(eleves.values())


def charger_charte(chemin):
    """Lit la charte de rédaction ; refuse un fichier vide."""
    texte = Path(chemin).read_text(encoding="utf-8").strip()
    if not texte:
        raise DonneesInvalides("La charte est vide : fournissez une charte de rédaction correcte.")
    return texte
