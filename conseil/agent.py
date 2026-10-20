"""Agent Claude : boucle d'outils et proposition d'appréciation par élève."""
import json
import os

import anthropic

from conseil import regles
from conseil.outils import creer_outils, definitions

MODELE_DEFAUT = "claude-haiku-5-5"
EFFORT = "medium"      # profondeur de réflexion : low | medium | high
MAX_TOKENS = 4000
MAX_TOURS = 8
TENTATIVES = 2
PRIX_PAR_MILLION = {   # dollars par million de jetons : (entrée, sortie)
    "claude-opus-5-5": (4.0, 20.0),
    "claude-sonnet-5-5": (2.0, 10.0),
    "claude-haiku-5-5": (0.10, 0.50),
}

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


class AgentClaude:
    """Client Claude, boucle d'outils et suivi de la consommation de jetons."""

    def __init__(self, client=None):
        if client is None:
            cle = os.environ.get("CLAUDE_API_KEY")
            if not cle:
                raise RuntimeError("CLAUDE_API_KEY est absente : ajoutez-la dans le fichier .env.")
            client = anthropic.Anthropic(api_key=cle)
        self.client = client
        self.modele = os.environ.get("CLAUDE_MODEL", MODELE_DEFAUT)
        self.jetons_entree = 0
        self.jetons_sortie = 0

    @property
    def cout_estime(self):
        """Coût estimé en dollars, ou None si le prix du modèle n'est pas connu."""
        if self.modele not in PRIX_PAR_MILLION:
            return None
        prix_entree, prix_sortie = PRIX_PAR_MILLION[self.modele]
        return (self.jetons_entree * prix_entree + self.jetons_sortie * prix_sortie) / 1_000_000

    def boucle(self, prompt, outils):
        """Appelle le modèle jusqu'à ce qu'il réponde sans demander d'outil."""
        messages = [{"role": "user", "content": prompt}]
        for _ in range(MAX_TOURS):
            reponse = self.client.messages.create(
                model=self.modele,
                max_tokens=MAX_TOKENS,
                system=SYSTEM_PROMPT,
                tools=definitions(outils),
                output_config={"effort": EFFORT},
                messages=messages,
            )
            self.jetons_entree += reponse.usage.input_tokens
            self.jetons_sortie += reponse.usage.output_tokens
            if reponse.stop_reason == "refusal":
                raise RuntimeError("Claude a refusé de répondre à cette demande.")
            if reponse.stop_reason == "max_tokens":
                raise RuntimeError("La réponse de Claude a été coupée (max_tokens atteint).")
            if reponse.stop_reason != "tool_use":
                return "".join(b.text for b in reponse.content if b.type == "text")
            messages.append({"role": "assistant", "content": reponse.content})
            messages.append({"role": "user", "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": appel.id,
                    "content": json.dumps(executer_outil(outils, appel.name), ensure_ascii=False),
                }
                for appel in reponse.content if appel.type == "tool_use"
            ]})
        raise RuntimeError(f"Claude n'a pas conclu après {MAX_TOURS} appels d'outils.")


def executer_outil(outils, nom):
    """Exécute l'outil demandé par le modèle."""
    return outils[nom]() if nom in outils else "outil inconnu"


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


def proposer_appreciation(claude, eleve, charte):
    """Propose une appréciation vérifiée par la charte, avec une régénération en cas d'écart.

    Renvoie un dictionnaire : appreciation, commentaires_ecartes, alertes (écarts restants).
    """
    outils = creer_outils(eleve, charte)
    absences_signalees = regles.absences_graves(eleve["absences"])
    prompt = construire_prompt(eleve)
    proposition, alertes = {}, []
    for _ in range(TENTATIVES):
        try:
            proposition = lire_json(claude.boucle(prompt, outils))
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
