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
    assert claude.boucle("système", "Bonjour", outils) == "Réponse finale."
    retour = client.requetes[1]["messages"][-1]["content"][0]
    assert retour == {"type": "tool_result", "tool_use_id": "outil_1", "content": "false"}
    assert (claude.jetons_entree, claude.jetons_sortie) == (200, 100)


def test_boucle_refus_leve_une_erreur():
    claude = agent.AgentClaude(FauxClient(reponse("refusal")))
    with pytest.raises(RuntimeError, match="refusé"):
        claude.boucle("système", "Bonjour", {})


def test_boucle_s_arrete_apres_le_nombre_maximal_de_tours():
    reponses = [reponse("tool_use", appel_outil("lire_charte")) for _ in range(agent.MAX_TOURS)]
    claude = agent.AgentClaude(FauxClient(*reponses))
    with pytest.raises(RuntimeError, match="n'a pas conclu"):
        claude.boucle("système", "Bonjour", creer_outils(ELEVE, "charte"))


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


STATS = {
    "effectif": 26, "moyenne_precedente": 12.0, "moyenne": 12.5,
    "nb_forte_progression": 3, "nb_baisse_generalisee": 2, "nb_absences_nombreuses": 2,
    "nb_a_surveiller": 5, "nb_sans_difficulte": 4,
    "matieres": {"Français": {"moyenne_precedente": 12.0, "moyenne": 12.4}},
}


def test_prompt_de_classe_contient_les_chiffres_et_aucun_nom():
    prompt = agent.construire_prompt_classe("1re 2", STATS, ["Belle progression.", "Résultats réguliers."])
    assert "26 élèves" in prompt
    assert "Français : 12.0 puis 12.4" in prompt
    assert "- Belle progression." in prompt


def test_proposer_synthese_conforme():
    client = FauxClient(reponse("end_turn", texte("Classe en progrès.\nEfforts à poursuivre.")))
    resultat = agent.proposer_synthese(agent.AgentClaude(client), "1re 2", STATS, ["Texte."], "charte")
    assert resultat == {"synthese": "Classe en progrès.\nEfforts à poursuivre.", "alertes": []}
    assert [outil["name"] for outil in client.requetes[0]["tools"]] == ["lire_charte"]


def test_proposer_synthese_regenere_si_plus_de_dix_lignes():
    trop_longue = "\n".join(f"Ligne {n}." for n in range(11))
    client = FauxClient(reponse("end_turn", texte(trop_longue)), reponse("end_turn", texte("Version courte.")))
    resultat = agent.proposer_synthese(agent.AgentClaude(client), "1re 2", STATS, ["Texte."], "charte")
    assert resultat["synthese"] == "Version courte."
    assert "11 lignes" in client.requetes[1]["messages"][0]["content"]


def test_proposer_synthese_garde_les_alertes_si_la_regeneration_echoue():
    trop_longue = "\n".join(f"Ligne {n}." for n in range(11))
    client = FauxClient(reponse("end_turn", texte(trop_longue)), reponse("end_turn", texte(trop_longue)))
    resultat = agent.proposer_synthese(agent.AgentClaude(client), "1re 2", STATS, ["Texte."], "charte")
    assert "11 lignes" in resultat["alertes"][0]
