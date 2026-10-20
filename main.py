"""Point d'entrée de l'agent conseil de classe."""
import argparse
import os
import sys

from dotenv import load_dotenv

from conseil import donnees, regles


def afficher_modeles():
    from google import genai

    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    noms = sorted(m.name.removeprefix("models/") for m in client.models.list())
    print(f"{len(noms)} modèles disponibles. Modèles Flash :")
    for nom in noms:
        if "flash" in nom:
            print(f"  {nom}")
    print(f"GEMINI_MODEL actuel : {os.environ.get('GEMINI_MODEL', '(non défini)')}")


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


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    load_dotenv()
    parser = argparse.ArgumentParser(description="Agent conseil de classe")
    parser.add_argument("dossier", nargs="?", help="dossier de la classe (eleves*.csv et appreciations*.csv)")
    parser.add_argument("--modeles", action="store_true", help="liste les modèles Gemini disponibles")
    parser.add_argument("--analyse", action="store_true", help="affiche les indicateurs de la charte sans appeler le modèle")
    args = parser.parse_args()

    try:
        if args.modeles:
            afficher_modeles()
        elif args.analyse and args.dossier:
            afficher_analyse(args.dossier)
        else:
            parser.print_help()
    except donnees.DonneesInvalides as erreur:
        print(f"Erreur : {erreur}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
