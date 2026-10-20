"""Agent Claude : boucle d'outils, appréciation par élève et synthèse de classe."""
import json
import os

import anthropic

from conseil import regles
from conseil.outils import creer_outils, creer_outils_classe, definitions

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

SYSTEME_ELEVE = """Tu aides le professeur principal à rédiger l'appréciation générale d'un élève.
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

SYSTEME_CLASSE = """Tu aides le professeur principal à rédiger la synthèse générale d'une classe.
Avant de rédiger, appelle l'outil lire_charte.

Règles, issues de la charte :
- 10 lignes au plus : une idée par ligne, une ligne par phrase, sans titre ni liste à puces.
- Ton factuel et bienveillant, à la troisième personne. Phrases courtes. Le constat précède le conseil.
- Ne reprends que des faits présents dans les statistiques et les appréciations fournies. N'ajoute rien.
- Ne cite aucun élève par son nom.
- Aucun jugement sur la personnalité, la situation familiale, sociale, économique ou la santé.

Réponds uniquement avec la synthèse, sans texte autour."""


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

    def boucle(self, systeme, prompt, outils):
        """Appelle le modèle jusqu'à ce qu'il réponde sans demander d'outil."""
        messages = [{"role": "user", "content": prompt}]
        for _ in range(MAX_TOURS):
            reponse = self.client.messages.create(
                model=self.modele,
                max_tokens=MAX_TOKENS,
                system=systeme,
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


def lire_json(texte):
    """Extrait l'objet JSON de la réponse du modèle."""
    debut, fin = texte.find("{"), texte.rfind("}")
    if debut == -1 or fin == -1:
        raise ValueError("réponse sans JSON")
    return json.loads(texte[debut:fin + 1])


def generer_conforme(claude, systeme, prompt, outils, extraire, verifier):
    """Demande une proposition, la vérifie, et redemande une fois en cas d'écart à la charte.

    Renvoie (résultat extrait ou None, alertes restantes).
    """
    resultat, alertes, invite = None, [], prompt
    for _ in range(TENTATIVES):
        try:
            resultat = extraire(claude.boucle(systeme, invite, outils))
            alertes = verifier(resultat)
        except (ValueError, KeyError) as erreur:
            resultat, alertes = None, [f"réponse du modèle illisible ({erreur})"]
        if not alertes:
            break
        invite = prompt + "\n\nTa proposition précédente n'était pas conforme : " + " ; ".join(alertes) + ". Corrige-la."
    return resultat, alertes


def construire_prompt_eleve(eleve):
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


def proposer_appreciation(claude, eleve, charte):
    """Propose une appréciation vérifiée par la charte.

    Renvoie un dictionnaire : appreciation, commentaires_ecartes, alertes (écarts restants).
    """
    absences_signalees = regles.absences_graves(eleve["absences"])
    proposition, alertes = generer_conforme(
        claude, SYSTEME_ELEVE, construire_prompt_eleve(eleve), creer_outils(eleve, charte),
        extraire=lire_json,
        verifier=lambda p: regles.verifier_charte(p["appreciation"], absences_signalees),
    )
    proposition = proposition or {}
    return {
        "appreciation": proposition.get("appreciation", ""),
        "commentaires_ecartes": proposition.get("commentaires_ecartes", []),
        "alertes": alertes,
    }


def construire_prompt_classe(classe, stats, appreciations):
    """Statistiques de la classe et appréciations validées, sans les noms des élèves."""
    lignes = [
        f"Classe : {classe}, {stats['effectif']} élèves.",
        f"Moyenne générale de la classe : {stats['moyenne_precedente']} puis {stats['moyenne']}.",
        f"Élèves en forte progression : {stats['nb_forte_progression']}.",
        f"Élèves en baisse généralisée : {stats['nb_baisse_generalisee']}.",
        f"Élèves avec des absences nombreuses : {stats['nb_absences_nombreuses']}.",
        f"Élèves à surveiller : {stats['nb_a_surveiller']}.",
        f"Élèves sans difficulté : {stats['nb_sans_difficulte']}.",
        "Moyennes par matière (trimestre précédent puis trimestre en cours) :",
    ]
    for matiere, m in stats["matieres"].items():
        lignes.append(f"- {matiere} : {m['moyenne_precedente']} puis {m['moyenne']}")
    lignes.append("Appréciations générales validées :")
    lignes += [f"- {a}" for a in appreciations]
    return "\n".join(lignes)


def proposer_synthese(claude, classe, stats, appreciations, charte):
    """Propose la synthèse de classe vérifiée par la charte.

    Renvoie un dictionnaire : synthese, alertes (écarts restants).
    """
    synthese, alertes = generer_conforme(
        claude, SYSTEME_CLASSE, construire_prompt_classe(classe, stats, appreciations),
        creer_outils_classe(charte),
        extraire=str.strip,
        verifier=regles.verifier_synthese,
    )
    return {"synthese": synthese or "", "alertes": alertes}
