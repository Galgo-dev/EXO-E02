"""Outils mis à disposition de l'agent : lecture seule."""
from conseil import regles


def creer_outils_classe(charte):
    """Outils de la synthèse de classe : seulement la lecture de la charte."""

    def lire_charte() -> str:
        """Renvoie le texte complet de la charte de rédaction de l'établissement."""
        return charte

    return {"lire_charte": lire_charte}


def creer_outils(eleve, charte):
    """Crée les outils d'un élève. Sans argument, le modèle ne peut pas inventer de chiffres."""

    def absences_graves() -> bool:
        """Indique si le nombre de demi-journées d'absence de l'élève atteint le seuil de signalement de la charte."""
        return regles.absences_graves(eleve["absences"])

    def matieres_en_baisse() -> int:
        """Renvoie le nombre de matières dont la moyenne a baissé d'au moins 1,0 point depuis le trimestre précédent."""
        return regles.matieres_en_baisse(eleve["matieres"])

    def a_surveiller() -> dict:
        """Indique si l'élève doit être surveillé (absences nombreuses ou baisse généralisée) et pour quel motif."""
        surveiller, motif = regles.a_surveiller(
            eleve["absences"], regles.matieres_en_baisse(eleve["matieres"])
        )
        return {"a_surveiller": surveiller, "motif": motif}

    outils = (absences_graves, matieres_en_baisse, a_surveiller)
    return {**creer_outils_classe(charte), **{outil.__name__: outil for outil in outils}}


def definitions(outils):
    """Déclaration des outils pour l'API : nom, description (docstring), aucun argument."""
    return [
        {
            "name": nom,
            "description": outil.__doc__,
            "input_schema": {"type": "object", "properties": {}},
        }
        for nom, outil in outils.items()
    ]
