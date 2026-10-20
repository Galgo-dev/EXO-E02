"""Validation par le professeur principal d'une proposition de l'agent."""
from conseil import regles

INVITE = "[Entrée] valider, [m] modifier, [r] régénérer : "


def saisir(invite):
    """Lit la réponse du principal au clavier."""
    return input(invite)


def _afficher_alertes(proposition):
    for alerte in proposition["alertes"]:
        print(f"ALERTE charte : {alerte}")


def _afficher_appreciation(eleve, motif, proposition):
    texte = proposition["appreciation"]
    print(f"\n=== {eleve['prenom']} {eleve['nom']} ({eleve['matricule']}) - {len(texte)} caractères ===")
    if motif:
        print(f"À surveiller : {motif}")
    print(texte or "(aucune proposition)")
    for ecarte in proposition["commentaires_ecartes"]:
        print(f"Commentaire écarté : {ecarte['enseignant']} ({ecarte['matiere']}) - {ecarte['raison']}")
    _afficher_alertes(proposition)


def _afficher_synthese(classe, proposition):
    print(f"\n=== Synthèse de la classe {classe} ===")
    print(proposition["synthese"] or "(aucune proposition)")
    _afficher_alertes(proposition)


def _valider(proposition, cle, afficher, regenerer, verifier, demander):
    """Boucle commune : Entrée valide, `m` remplace le texte, `r` demande une nouvelle proposition.

    `cle` désigne le texte dans la proposition ; `verifier(texte)` renvoie les alertes de la charte.
    """
    demander = demander or saisir
    while True:
        afficher(proposition)
        choix = demander(INVITE).strip().lower()
        if choix == "m":
            nouveau = demander("Nouveau texte : ").strip()
            if nouveau:
                proposition = {**proposition, cle: nouveau, "alertes": verifier(nouveau)}
        elif choix == "r":
            proposition = regenerer()
        elif choix == "" and proposition[cle]:
            return proposition


def valider_appreciation(eleve, motif, proposition, regenerer, demander=None):
    """Renvoie (appréciation validée, commentaires écartés)."""
    absences_signalees = regles.absences_graves(eleve["absences"])
    validee = _valider(
        proposition, "appreciation",
        afficher=lambda p: _afficher_appreciation(eleve, motif, p),
        regenerer=regenerer,
        verifier=lambda texte: regles.verifier_charte(texte, absences_signalees),
        demander=demander,
    )
    return validee["appreciation"], validee["commentaires_ecartes"]


def valider_synthese(classe, proposition, regenerer, demander=None):
    """Renvoie la synthèse de classe validée."""
    validee = _valider(
        proposition, "synthese",
        afficher=lambda p: _afficher_synthese(classe, p),
        regenerer=regenerer,
        verifier=regles.verifier_synthese,
        demander=demander,
    )
    return validee["synthese"]
