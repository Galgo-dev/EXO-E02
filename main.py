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


def analyser_eleve(eleve):
    """Calcule les indicateurs de la charte pour un élève."""
    nb_baisses = regles.matieres_en_baisse(eleve["matieres"])
    surveiller, motif = regles.a_surveiller(eleve["absences"], nb_baisses)
    moyennes = [m["moyenne"] for m in eleve["matieres"]]
    return {
        "nb_baisses": nb_baisses,
        "surveiller": surveiller,
        "motif": motif,
        "progression": regles.forte_progression(eleve["moyenne_precedente"], eleve["moyenne"]),
        "sans_difficulte": regles.sans_difficulte(moyennes, eleve["absences"]),
    }


def afficher_analyse(dossier):
    eleves = donnees.charger_classe(dossier)
    print(f"{'Matricule':<9} {'Nom':<10} {'Prénom':<8} {'Moy.':>5} {'Abs.':>4} {'Baisses':>7}  Indicateurs")
    for eleve in eleves:
        a = analyser_eleve(eleve)
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


def lancer_validation(eleves):
    """Propose, fait valider élève par élève, et enregistre les CSV après chaque validation."""
    charte = donnees.charger_charte(CHARTE)
    claude = agent.AgentClaude()
    dossier_classe = DOSSIER_SORTIES / eleves[0]["classe"]
    appreciations, a_surveiller, ecartes = [], [], []
    try:
        for eleve in eleves:
            motif = analyser_eleve(eleve)["motif"]
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
    except (KeyboardInterrupt, EOFError):
        print("\nInterrompu : les élèves déjà validés sont enregistrés.")
    print(f"\n{len(appreciations)} appréciation(s) validée(s), {len(a_surveiller)} élève(s) à surveiller.")
    print(f"Fichiers dans {dossier_classe}")
    afficher_consommation(claude)


def quitter_avec_erreur(message):
    print(f"Erreur : {message}", file=sys.stderr)
    sys.exit(1)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stdin.reconfigure(encoding="utf-8")
    load_dotenv()
    parser = argparse.ArgumentParser(description="Agent conseil de classe")
    parser.add_argument("dossier", nargs="?", help="dossier de la classe (eleves*.csv et appreciations*.csv)")
    parser.add_argument("--modeles", action="store_true", help="liste les modèles Claude disponibles")
    parser.add_argument("--analyse", action="store_true", help="affiche les indicateurs de la charte sans appeler le modèle")
    parser.add_argument("--apercu", action="store_true", help="affiche les propositions sans validation ni fichiers")
    parser.add_argument("--limite", type=int, help="se limite aux N premiers élèves")
    parser.add_argument("--eleve", help="se limite à un matricule")
    args = parser.parse_args()

    try:
        if args.modeles:
            afficher_modeles()
        elif args.dossier and args.analyse:
            afficher_analyse(args.dossier)
        elif args.dossier and args.apercu:
            afficher_apercu(choisir_eleves(args.dossier, args.limite, args.eleve))
        elif args.dossier:
            lancer_validation(choisir_eleves(args.dossier, args.limite, args.eleve))
        else:
            parser.print_help()
    except donnees.DonneesInvalides as erreur:
        quitter_avec_erreur(erreur)
    except anthropic.AuthenticationError:
        quitter_avec_erreur("CLAUDE_API_KEY est refusée par l'API : vérifiez la clé dans .env.")
    except anthropic.RateLimitError:
        quitter_avec_erreur("limite de débit atteinte. Les élèves déjà validés sont enregistrés, réessayez plus tard.")
    except (anthropic.APIError, RuntimeError) as erreur:
        quitter_avec_erreur(erreur)


if __name__ == "__main__":
    main()
