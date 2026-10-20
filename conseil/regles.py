"""Seuils de la charte de rédaction (section 5) sous forme de fonctions pures."""

ABSENCES_NOMBREUSES = 12          # demi-journées sur le trimestre
BAISSE_PAR_MATIERE = 1.0          # points perdus pour compter une matière en baisse
MATIERES_EN_BAISSE_MIN = 5        # nombre de matières pour une baisse généralisée
FORTE_PROGRESSION = 2.0           # hausse de la moyenne générale
SANS_DIFFICULTE_MOYENNE_MIN = 12  # moyenne minimale dans chaque matière
SANS_DIFFICULTE_ABSENCES_MAX = 2  # demi-journées d'absence au plus

LONGUEUR_MAX_APPRECIATION = 300   # caractères, espaces compris
LIGNES_MAX_SYNTHESE = 10          # lignes de la synthèse de classe
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


def analyser_eleve(eleve):
    """Calcule les indicateurs de la charte pour un élève."""
    nb_baisses = matieres_en_baisse(eleve["matieres"])
    surveiller, motif = a_surveiller(eleve["absences"], nb_baisses)
    moyennes = [m["moyenne"] for m in eleve["matieres"]]
    return {
        "nb_baisses": nb_baisses,
        "baisse_generalisee": nb_baisses >= MATIERES_EN_BAISSE_MIN,
        "absences_nombreuses": absences_graves(eleve["absences"]),
        "surveiller": surveiller,
        "motif": motif,
        "progression": forte_progression(eleve["moyenne_precedente"], eleve["moyenne"]),
        "sans_difficulte": sans_difficulte(moyennes, eleve["absences"]),
    }


def statistiques_classe(eleves):
    """Chiffres de la classe, calculés sans le modèle : effectifs par indicateur et moyennes."""
    analyses = [analyser_eleve(e) for e in eleves]
    par_matiere = {}
    for eleve in eleves:
        for m in eleve["matieres"]:
            par_matiere.setdefault(m["matiere"], []).append(m)
    return {
        "effectif": len(eleves),
        "moyenne_precedente": moyenne_generale([e["moyenne_precedente"] for e in eleves]),
        "moyenne": moyenne_generale([e["moyenne"] for e in eleves]),
        "nb_forte_progression": sum(a["progression"] for a in analyses),
        "nb_baisse_generalisee": sum(a["baisse_generalisee"] for a in analyses),
        "nb_absences_nombreuses": sum(a["absences_nombreuses"] for a in analyses),
        "nb_a_surveiller": sum(a["surveiller"] for a in analyses),
        "nb_sans_difficulte": sum(a["sans_difficulte"] for a in analyses),
        "matieres": {
            nom: {
                "moyenne_precedente": moyenne_generale([m["moyenne_precedente"] for m in lignes]),
                "moyenne": moyenne_generale([m["moyenne"] for m in lignes]),
            }
            for nom, lignes in par_matiere.items()
        },
    }


def _formulations_interdites(texte):
    minuscules = texte.lower()
    return [
        f"formulation interdite : « {formule} »"
        for formule in FORMULATIONS_INTERDITES
        if formule in minuscules
    ]


def verifier_charte(texte, absences_signalees):
    """Renvoie la liste des règles de la charte non respectées par une appréciation."""
    problemes = []
    if len(texte) > LONGUEUR_MAX_APPRECIATION:
        problemes.append(f"{len(texte)} caractères au lieu de {LONGUEUR_MAX_APPRECIATION} au plus")
    problemes += _formulations_interdites(texte)
    if "absence" in texte.lower() and not absences_signalees:
        problemes.append("absences mentionnées alors que le seuil de signalement n'est pas atteint")
    return problemes


def verifier_synthese(texte):
    """Renvoie la liste des règles de la charte non respectées par une synthèse de classe."""
    lignes = [ligne for ligne in texte.splitlines() if ligne.strip()]
    problemes = []
    if not lignes:
        problemes.append("synthèse vide")
    if len(lignes) > LIGNES_MAX_SYNTHESE:
        problemes.append(f"{len(lignes)} lignes au lieu de {LIGNES_MAX_SYNTHESE} au plus")
    return problemes + _formulations_interdites(texte)
