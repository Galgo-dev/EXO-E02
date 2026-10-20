"""Tests de l'agent avec un faux client : aucun appel réel à l'API."""
import json
from types import SimpleNamespace

import pytest

from conseil import agent
from conseil.outils import creer_outils

ELEVE = {
    "prenom": "Léna", "nom": "Vincent", "classe": "1re 2",
    "moyenne_precedente": 9.83, "moyenne": 13.32, "absences": 5,
    "matieres": [{"matiere": "Français", "enseignant": "Mme Garnier",
                  "moyenne_precedente": 10.7, "moyenne": 13.8, "appreciation": "Nette progression."}],
}


def reponse(stop_reason, *blocs, entree=100, sortie=50):
    return SimpleNamespace(
        stop_reason=stop_reason, content=list(blocs),
        usage=SimpleNamespace(input_tokens=entree, output_tokens=sortie),
    )


def texte(contenu):
    return SimpleNamespace(type="text", text=contenu)


def appel_outil(nom, identifiant="outil_1"):
    return SimpleNamespace(type="tool_use", id=identifiant, name=nom, input={})


class FauxClient:
    """Rejoue des réponses dans l'ordre et garde les requêtes reçues."""

    def __init__(self, *reponses):
        self.reponses = iter(reponses)
        self.requetes = []
        self.messages = SimpleNamespace(create=self.create)

    def create(self, **requete):
        self.requetes.append(requete)
        return next(self.reponses)


def proposition_json(appreciation, ecartes=()):
    return texte(json.dumps({"appreciation": appreciation, "commentaires_ecartes": list(ecartes)}))


@pytest.fixture(autouse=True)
def modele_par_defaut(monkeypatch):
    monkeypatch.delenv("CLAUDE_MODEL", raising=False)


def test_boucle_execute_l_outil_puis_renvoie_le_texte():
    client = FauxClient(
        reponse("tool_use", appel_outil("absences_graves")),
        reponse("end_turn", texte("Réponse finale.")),
    )
    claude = agent.AgentClaude(client)
    outils = creer_outils(ELEVE, "charte")
    assert claude.boucle("Bonjour", outils) == "Réponse finale."
    retour = client.requetes[1]["messages"][-1]["content"][0]
    assert retour == {"type": "tool_result", "tool_use_id": "outil_1", "content": "false"}
    assert (claude.jetons_entree, claude.jetons_sortie) == (200, 100)


def test_boucle_refus_leve_une_erreur():
    claude = agent.AgentClaude(FauxClient(reponse("refusal")))
    with pytest.raises(RuntimeError, match="refusé"):
        claude.boucle("Bonjour", {})


def test_boucle_s_arrete_apres_le_nombre_maximal_de_tours():
    reponses = [reponse("tool_use", appel_outil("lire_charte")) for _ in range(agent.MAX_TOURS)]
    claude = agent.AgentClaude(FauxClient(*reponses))
    with pytest.raises(RuntimeError, match="n'a pas conclu"):
        claude.boucle("Bonjour", creer_outils(ELEVE, "charte"))


def test_cout_estime_selon_le_modele(monkeypatch):
    claude = agent.AgentClaude(FauxClient())
    claude.jetons_entree, claude.jetons_sortie = 1_000_000, 1_000_000
    assert claude.cout_estime == pytest.approx(0.60)  # haiku 5.5 : 0,10 $ + 0,50 $
    claude.modele = "modele-inconnu"
    assert claude.cout_estime is None


def test_cle_absente_leve_une_erreur_claire(monkeypatch):
    monkeypatch.delenv("CLAUDE_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="CLAUDE_API_KEY"):
        agent.AgentClaude()


def test_lire_json_ignore_le_texte_autour():
    assert agent.lire_json('Voici : {"appreciation": "ok"} fin') == {"appreciation": "ok"}


def test_proposer_appreciation_conforme_en_un_appel():
    client = FauxClient(reponse("end_turn", proposition_json("Belle progression, à poursuivre.")))
    resultat = agent.proposer_appreciation(agent.AgentClaude(client), ELEVE, "charte")
    assert resultat["appreciation"] == "Belle progression, à poursuivre."
    assert resultat["alertes"] == []
    assert len(client.requetes) == 1


def test_proposer_appreciation_regenere_quand_la_charte_n_est_pas_respectee():
    client = FauxClient(
        reponse("end_turn", proposition_json("a" * 301)),
        reponse("end_turn", proposition_json("Version courte.")),
    )
    resultat = agent.proposer_appreciation(agent.AgentClaude(client), ELEVE, "charte")
    assert resultat["appreciation"] == "Version courte."
    assert resultat["alertes"] == []
    assert "pas conforme" in client.requetes[1]["messages"][0]["content"]


def test_proposer_appreciation_signale_une_reponse_illisible():
    client = FauxClient(reponse("end_turn", texte("pas de json")), reponse("end_turn", texte("toujours pas")))
    resultat = agent.proposer_appreciation(agent.AgentClaude(client), ELEVE, "charte")
    assert resultat["appreciation"] == ""
    assert "illisible" in resultat["alertes"][0]


def test_proposer_appreciation_transmet_les_commentaires_ecartes():
    ecarte = {"enseignant": "Mme Delcourt", "matiere": "Anglais LV1", "raison": "situation sociale"}
    client = FauxClient(reponse("end_turn", proposition_json("Texte correct.", [ecarte])))
    resultat = agent.proposer_appreciation(agent.AgentClaude(client), ELEVE, "charte")
    assert resultat["commentaires_ecartes"] == [ecarte]
