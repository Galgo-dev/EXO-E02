"""Point d'entrée de l'agent conseil de classe."""
import argparse
import sys
from pathlib import Path

import anthropic
from dotenv import load_dotenv

from conseil import agent, donnees, regles, sorties, validation

CHARTE = Path(__file__).parent / "ressource" / "charte-redaction.md"
DOSSIER_SORTIES = Path(__file__).parent / "sorties"


def afficher_modeles():
    claude = agent.AgentClaude()
    print("Modèles Claude disponibles :")
    for modele in claude.client.models.list():
        print(f"  {modele.id}")
    print(f"Modèle utilisé : {claude.modele} (CLAUDE_MODEL pour le changer)")


def afficher_consommation(claude):
    texte = f"Consommation : {claude.jetons_entree} jetons en entrée, {claude.jetons_sortie} en sortie"
    if claude.cout_estime is not None:
        texte += f", environ {claude.cout_estime:.3f} $"
    print(texte)


def afficher_analyse(dossier):
    eleves = donnees.charger_classe(dossier)
    print(f"{'Matricule':<9} {'Nom':<10} {'Prénom':<8} {'Moy.':>5} {'Abs.':>4} {'Baisses':>7}  Indicateurs")
    for eleve in eleves:
        a = regles.analyser_eleve(eleve)
        indicateurs = []
        if a["surveiller"]:
            indicateurs.append(f"À SURVEILLER ({a['motif']})")
        if a["progression"]:
            indicateurs.append("forte progression")
        if a["sans_difficulte"]:
            indicateurs.append("sans difficulté")
        print(
            f"{eleve['matricule']:<9} {eleve['nom']:<10} {eleve['prenom']:<8} "
            f"{eleve['moyenne']:>5.2f} {eleve['absences']:>4} {a['nb_baisses']:>7}  {', '.join(indicateurs)}"
        )


def choisir_eleves(dossier, limite, matricule):
    eleves = donnees.charger_classe(dossier)
    if matricule:
        eleves = [e for e in eleves if e["matricule"] == matricule]
    return eleves[:limite]


def afficher_apercu(eleves):
    """Affiche les propositions de l'agent sans validation."""
    charte = donnees.charger_charte(CHARTE)
    claude = agent.AgentClaude()
    for eleve in eleves:
        proposition = agent.proposer_appreciation(claude, eleve, charte)
        texte = proposition["appreciation"]
        print(f"\n{eleve['prenom']} {eleve['nom']} ({eleve['matricule']}) - {len(texte)} caractères")
        print(texte)
        for ecarte in proposition["commentaires_ecartes"]:
            print(f"  Commentaire écarté : {ecarte['enseignant']} ({ecarte['matiere']}) - {ecarte['raison']}")
        for alerte in proposition["alertes"]:
            print(f"  ALERTE charte : {alerte}")
    print()
    afficher_consommation(claude)


def valider_synthese_classe(claude, eleves, appreciations, charte, dossier_classe):
    """Propose la synthèse de la classe, la fait valider et l'enregistre."""
    classe = eleves[0]["classe"]
    stats = regles.statistiques_classe(eleves)
    textes = [a["appreciation_generale"] for a in appreciations]

    def proposer():
        return agent.proposer_synthese(claude, classe, stats, textes, charte)

    synthese = validation.valider_synthese(classe, proposer(), regenerer=proposer)
    sorties.ecrire_synthese(dossier_classe, classe, synthese)


def lancer_validation(eleves, avec_synthese):
    """Propose, fait valider élève par élève, et enregistre les CSV après chaque validation.

    La synthèse de classe est proposée à la fin, seulement si la classe entière est traitée.
    """
    charte = donnees.charger_charte(CHARTE)
    claude = agent.AgentClaude()
    dossier_classe = DOSSIER_SORTIES / eleves[0]["classe"]
    appreciations, a_surveiller, ecartes = [], [], []
    try:
        for eleve in eleves:
            motif = regles.analyser_eleve(eleve)["motif"]
            proposition = agent.proposer_appreciation(claude, eleve, charte)
            texte, commentaires = validation.valider_appreciation(
                eleve, motif, proposition,
                regenerer=lambda e=eleve: agent.proposer_appreciation(claude, e, charte),
            )
            identite = {k: eleve[k] for k in ("matricule", "nom", "prenom", "classe")}
            appreciations.append({**identite, "appreciation_generale": texte})
            if motif:
                a_surveiller.append({**identite, "motif": motif})
            ecartes += [
                {"matricule": eleve["matricule"], **{k: c[k] for k in ("matiere", "enseignant", "raison")}}
                for c in commentaires
            ]
            sorties.ecrire_sorties(dossier_classe, appreciations, a_surveiller, ecartes)
        if avec_synthese:
            valider_synthese_classe(claude, eleves, appreciations, charte, dossier_classe)
    except (KeyboardInterrupt, EOFError):
        print("\nInterrompu : ce qui est déjà validé est enregistré.")
    print(f"\n{len(appreciations)} appréciation(s) validée(s), {len(a_surveiller)} élève(s) à surveiller.")
    print(f"Fichiers dans {dossier_classe}")
    afficher_consommation(claude)


def lancer_synthese(dossier):
    """Refait seulement la synthèse, à partir des appréciations déjà validées."""
    eleves = donnees.charger_classe(dossier)
    charte = donnees.charger_charte(CHARTE)
    dossier_classe = DOSSIER_SORTIES / eleves[0]["classe"]
    appreciations = sorties.lire_appreciations(dossier_classe)
    if len(appreciations) != len(eleves):
        raise RuntimeError(
            f"synthèse impossible : {len(appreciations)} appréciation(s) validée(s) sur {len(eleves)}. "
            "Terminez d'abord la validation de la classe."
        )
    claude = agent.AgentClaude()
    try:
        valider_synthese_classe(claude, eleves, appreciations, charte, dossier_classe)
    except (KeyboardInterrupt, EOFError):
        print("\nInterrompu : la synthèse n'est pas enregistrée.")
    print(f"Fichiers dans {dossier_classe}")
    afficher_consommation(claude)


def quitter_avec_erreur(message):
    print(f"Erreur : {message}", file=sys.stderr)
    sys.exit(1)


def main():
    for flux in (sys.stdout, sys.stderr, sys.stdin):
        flux.reconfigure(encoding="utf-8")
    load_dotenv()
    parser = argparse.ArgumentParser(description="Agent conseil de classe")
    parser.add_argument("dossier", nargs="?", help="dossier de la classe (eleves*.csv et appreciations*.csv)")
    parser.add_argument("--modeles", action="store_true", help="liste les modèles Claude disponibles")
    parser.add_argument("--analyse", action="store_true", help="affiche les indicateurs de la charte sans appeler le modèle")
    parser.add_argument("--apercu", action="store_true", help="affiche les propositions sans validation ni fichiers")
    parser.add_argument("--synthese", action="store_true", help="refait seulement la synthèse de classe")
    parser.add_argument("--limite", type=int, help="se limite aux N premiers élèves (sans synthèse de classe)")
    parser.add_argument("--eleve", help="se limite à un matricule (sans synthèse de classe)")
    args = parser.parse_args()

    try:
        if args.modeles:
            afficher_modeles()
        elif args.dossier and args.analyse:
            afficher_analyse(args.dossier)
        elif args.dossier and args.apercu:
            afficher_apercu(choisir_eleves(args.dossier, args.limite, args.eleve))
        elif args.dossier and args.synthese:
            lancer_synthese(args.dossier)
        elif args.dossier:
            eleves = choisir_eleves(args.dossier, args.limite, args.eleve)
            lancer_validation(eleves, avec_synthese=not (args.limite or args.eleve))
        else:
            parser.print_help()
    except donnees.DonneesInvalides as erreur:
        quitter_avec_erreur(erreur)
    except anthropic.AuthenticationError:
        quitter_avec_erreur("CLAUDE_API_KEY est refusée par l'API : vérifiez la clé dans .env.")
    except anthropic.RateLimitError:
        quitter_avec_erreur("limite de débit atteinte. Ce qui est validé est enregistré, réessayez plus tard.")
    except (anthropic.APIError, RuntimeError) as erreur:
        quitter_avec_erreur(erreur)


if __name__ == "__main__":
    main()
