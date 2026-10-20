"""Seuils de la charte de rédaction (section 5) sous forme de fonctions pures."""

ABSENCES_NOMBREUSES = 12          # demi-journées sur le trimestre
BAISSE_PAR_MATIERE = 1.0          # points perdus pour compter une matière en baisse
MATIERES_EN_BAISSE_MIN = 5        # nombre de matières pour une baisse généralisée
FORTE_PROGRESSION = 2.0           # hausse de la moyenne générale
SANS_DIFFICULTE_MOYENNE_MIN = 12  # moyenne minimale dans chaque matière
SANS_DIFFICULTE_ABSENCES_MAX = 2  # demi-journées d'absence au plus


LONGUEUR_MAX_APPRECIATION = 300   # caractères, espaces compris
FORMULATIONS_INTERDITES = (       # section 4 de la charte
    "élève moyen", "élève faible", "fainéant", "ne fait aucun effort",
    "peut mieux faire", "il est évident que", "sans doute",
)


def moyenne_generale(moyennes):
    """Moyenne arithmétique des moyennes par matière, arrondie à 2 décimales."""
    return round(sum(moyennes) / len(moyennes), 2)


def absences_graves(demi_journees):
    """Indique si le nombre de demi-journées d'absence atteint le seuil de signalement."""
    return demi_journees >= ABSENCES_NOMBREUSES


def matieres_en_baisse(matieres):
    """Compte les matières dont la moyenne baisse d'au moins 1,0 point.

    Chaque matière est un dictionnaire avec `moyenne_precedente` et `moyenne`.
    La différence est arrondie pour éviter les erreurs de virgule flottante.
    """
    return sum(
        1
        for m in matieres
        if round(m["moyenne_precedente"] - m["moyenne"], 2) >= BAISSE_PAR_MATIERE
    )


def a_surveiller(absences, nb_baisses):
    """Renvoie (à surveiller, motif) selon les absences et le nombre de matières en baisse."""
    motifs = []
    if absences_graves(absences):
        motifs.append("absences")
    if nb_baisses >= MATIERES_EN_BAISSE_MIN:
        motifs.append("baisse des notes")
    return bool(motifs), " et ".join(motifs)


def forte_progression(moyenne_precedente, moyenne):
    """Indique si la moyenne générale progresse d'au moins 2,0 points."""
    return round(moyenne - moyenne_precedente, 2) >= FORTE_PROGRESSION


def sans_difficulte(moyennes, absences):
    """Indique si toutes les moyennes sont au moins 12 et les absences au plus 2 demi-journées."""
    return (
        all(m >= SANS_DIFFICULTE_MOYENNE_MIN for m in moyennes)
        and absences <= SANS_DIFFICULTE_ABSENCES_MAX
    )


def verifier_charte(texte, absences_signalees):
    """Renvoie la liste des règles de la charte non respectées par une appréciation."""
    problemes = []
    if len(texte) > LONGUEUR_MAX_APPRECIATION:
        problemes.append(f"{len(texte)} caractères au lieu de {LONGUEUR_MAX_APPRECIATION} au plus")
    minuscules = texte.lower()
    for formule in FORMULATIONS_INTERDITES:
        if formule in minuscules:
            problemes.append(f"formulation interdite : « {formule} »")
    if "absence" in minuscules and not absences_signalees:
        problemes.append("absences mentionnées alors que le seuil de signalement n'est pas atteint")
    return problemes
