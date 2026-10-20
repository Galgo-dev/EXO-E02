"""Validation par le professeur principal d'une appréciation proposée."""
from conseil import regles

INVITE = "[Entrée] valider, [m] modifier, [r] régénérer : "


def _afficher(eleve, motif, proposition):
    texte = proposition["appreciation"]
    print(f"\n=== {eleve['prenom']} {eleve['nom']} ({eleve['matricule']}) - {len(texte)} caractères ===")
    if motif:
        print(f"À surveiller : {motif}")
    print(texte or "(aucune proposition)")
    for ecarte in proposition["commentaires_ecartes"]:
        print(f"Commentaire écarté : {ecarte['enseignant']} ({ecarte['matiere']}) - {ecarte['raison']}")
    for alerte in proposition["alertes"]:
        print(f"ALERTE charte : {alerte}")


def valider_appreciation(eleve, motif, proposition, regenerer, demander=input):
    """Boucle de validation. Renvoie (appréciation validée, commentaires écartés).

    Entrée valide, `m` remplace le texte, `r` demande une nouvelle proposition.
    """
    absences_signalees = regles.absences_graves(eleve["absences"])
    while True:
        _afficher(eleve, motif, proposition)
        choix = demander(INVITE).strip().lower()
        if choix == "m":
            nouveau = demander("Nouvelle appréciation : ").strip()
            if nouveau:
                proposition = {
                    **proposition,
                    "appreciation": nouveau,
                    "alertes": regles.verifier_charte(nouveau, absences_signalees),
                }
        elif choix == "r":
            proposition = regenerer()
        elif choix == "" and proposition["appreciation"]:
            return proposition["appreciation"], proposition["commentaires_ecartes"]
