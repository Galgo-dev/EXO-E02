"""Point d'entrée de l'agent conseil de classe."""
import argparse
import os
import sys

from dotenv import load_dotenv
from google import genai


def afficher_modeles():
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    noms = sorted(m.name.removeprefix("models/") for m in client.models.list())
    flash = [n for n in noms if "flash" in n]
    print(f"{len(noms)} modèles disponibles. Modèles Flash :")
    for nom in flash:
        print(f"  {nom}")
    print(f"GEMINI_MODEL actuel : {os.environ.get('GEMINI_MODEL', '(non défini)')}")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    load_dotenv()
    parser = argparse.ArgumentParser(description="Agent conseil de classe")
    parser.add_argument("--modeles", action="store_true", help="liste les modèles Gemini disponibles")
    args = parser.parse_args()
    if args.modeles:
        afficher_modeles()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
