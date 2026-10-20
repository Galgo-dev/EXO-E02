"""Agent Gemini : boucle d'outils et proposition d'appréciation par élève."""
import json
import os

from google import genai
from google.genai import types

from conseil import regles
from conseil.outils import creer_outils

MODELE_DEFAUT = "gemini-3.6-flash"
TEMPERATURE = 0.2
MAX_TOURS = 8
TENTATIVES = 2

SYSTEM_PROMPT = """Tu aides le professeur principal à rédiger l'appréciation générale d'un élève.
Avant de rédiger, appelle les outils lire_charte, absences_graves, matieres_en_baisse et a_surveiller.

Règles, issues de la charte :
- 300 caractères au plus, espaces compris. Ton factuel et bienveillant, à la troisième personne.
- Phrases courtes. Le constat précède le conseil.
- Ne reprends que des faits présents dans les données fournies. N'ajoute rien.
- Aucun jugement sur la personnalité, la situation familiale, sociale, économique ou la santé.
- Les absences sont indiquées en demi-journées, sans motif, seulement si l'outil absences_graves renvoie vrai.
- Une progression n'est mentionnée que si les données indiquent une forte progression.

Si un commentaire d'enseignant ne respecte pas la charte (ironie, jugement de personnalité,
situation familiale, sociale ou de santé, mention du motif d'une absence), ignore-le
et signale-le dans commentaires_ecartes.

Réponds uniquement avec un objet JSON, sans texte autour :
{"appreciation": "...", "commentaires_ecartes": [{"enseignant": "...", "matiere": "...", "raison": "..."}]}"""


def creer_client():
    """Client Gemini ; les erreurs de surcharge (503) sont relancées automatiquement."""
    relances = types.HttpRetryOptions(attempts=5, http_status_codes=[429, 500, 503])
    return genai.Client(
        api_key=os.environ["GEMINI_API_KEY"],
        http_options=types.HttpOptions(retry_options=relances),
    )


def boucle_agent(client, prompt, outils):
    """Appelle le modèle jusqu'à ce qu'il réponde sans demander d'outil."""
    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        temperature=TEMPERATURE,
        tools=list(outils.values()),
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    )
    contenus = [types.Content(role="user", parts=[types.Part(text=prompt)])]
    for _ in range(MAX_TOURS):
        reponse = client.models.generate_content(
            model=os.environ.get("GEMINI_MODEL", MODELE_DEFAUT), contents=contenus, config=config
        )
        appels = reponse.function_calls
        if not appels:
            return reponse.text
        contenus.append(reponse.candidates[0].content)
        resultats = [
            types.Part(function_response=types.FunctionResponse(
                id=appel.id,
                name=appel.name,
                response={"result": outils[appel.name]() if appel.name in outils else "outil inconnu"},
            ))
            for appel in appels
        ]
        contenus.append(types.Content(role="user", parts=resultats))
    raise RuntimeError(f"Le modèle n'a pas conclu après {MAX_TOURS} appels d'outils.")


def construire_prompt(eleve):
    """Résume les données de l'élève : identité, moyennes, absences et appréciations."""
    evolution = round(eleve["moyenne"] - eleve["moyenne_precedente"], 2)
    forte = "oui" if regles.forte_progression(eleve["moyenne_precedente"], eleve["moyenne"]) else "non"
    lignes = [
        f"Élève : {eleve['prenom']} {eleve['nom']} ({eleve['classe']}).",
        f"Moyenne générale : {eleve['moyenne_precedente']} puis {eleve['moyenne']} "
        f"(évolution {evolution:+}, forte progression : {forte}).",
        f"Absences : {eleve['absences']} demi-journées.",
        "Matières :",
    ]
    for m in eleve["matieres"]:
        lignes.append(
            f"- {m['matiere']} ({m['enseignant']}) : {m['moyenne_precedente']} puis {m['moyenne']}. "
            f"Appréciation : « {m['appreciation']} »"
        )
    return "\n".join(lignes)


def lire_json(texte):
    """Extrait l'objet JSON de la réponse du modèle."""
    debut, fin = texte.find("{"), texte.rfind("}")
    if debut == -1 or fin == -1:
        raise ValueError("réponse sans JSON")
    return json.loads(texte[debut:fin + 1])


def proposer_appreciation(client, eleve, charte):
    """Propose une appréciation vérifiée par la charte, avec une régénération en cas d'écart.

    Renvoie un dictionnaire : appreciation, commentaires_ecartes, alertes (écarts restants).
    """
    outils = creer_outils(eleve, charte)
    absences_signalees = regles.absences_graves(eleve["absences"])
    prompt = construire_prompt(eleve)
    proposition, alertes = {}, []
    for _ in range(TENTATIVES):
        try:
            proposition = lire_json(boucle_agent(client, prompt, outils))
            alertes = regles.verifier_charte(proposition["appreciation"], absences_signalees)
        except (ValueError, KeyError) as erreur:
            proposition, alertes = {}, [f"réponse du modèle illisible ({erreur})"]
        if not alertes:
            break
        prompt = (
            construire_prompt(eleve)
            + "\n\nTa proposition précédente n'était pas conforme : " + " ; ".join(alertes) + ". Corrige-la."
        )
    return {
        "appreciation": proposition.get("appreciation", ""),
        "commentaires_ecartes": proposition.get("commentaires_ecartes", []),
        "alertes": alertes,
    }
