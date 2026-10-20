"""Parcours complet de main avec un faux client : aucun appel réel à l'API."""
import pytest

import main
from conseil import agent, donnees
from tests.test_agent import FauxClient, proposition_json, reponse, texte
from tests.test_donnees import ELEVE, ENTETE_APPRECIATIONS, ENTETE_ELEVES, APPRECIATION, ecrire_classe


@pytest.fixture
def environnement(tmp_path, monkeypatch):
    """Charte et dossier de sorties temporaires ; la validation répond toujours Entrée."""
    charte = tmp_path / "charte.md"
    charte.write_text("# Charte", encoding="utf-8")
    monkeypatch.setattr(main, "CHARTE", charte)
    monkeypatch.setattr(main, "DOSSIER_SORTIES", tmp_path / "sorties")
    monkeypatch.setattr(main.validation, "saisir", lambda invite: "")
    monkeypatch.delenv("CLAUDE_MODEL", raising=False)
    return tmp_path / "sorties" / "1re 2"


VRAI_AGENT = agent.AgentClaude


def brancher(monkeypatch, client):
    """Fait créer par main un agent branché sur le faux client."""
    monkeypatch.setattr(main.agent, "AgentClaude", lambda: VRAI_AGENT(client))


def classe_reelle(nombre):
    return donnees.charger_classe("ressource/classe_1")[:nombre]


def test_session_complete_ecrit_les_csv_et_la_synthese(environnement, monkeypatch, capsys):
    client = FauxClient(
        reponse("end_turn", proposition_json("Bon trimestre.")),
        reponse("end_turn", proposition_json("Trimestre correct.")),
        reponse("end_turn", texte("Classe en progrès.\nEfforts à poursuivre.")),
    )
    brancher(monkeypatch, client)
    main.lancer_validation(classe_reelle(2), avec_synthese=True)
    assert "Bon trimestre." in (environnement / "appreciations.csv").read_text(encoding="utf-8-sig")
    assert (environnement / "synthese.md").read_text(encoding="utf-8").endswith("Efforts à poursuivre.\n")
    assert "Consommation" in capsys.readouterr().out


def test_session_partielle_ne_produit_pas_de_synthese(environnement, monkeypatch):
    client = FauxClient(reponse("end_turn", proposition_json("Bon trimestre.")))
    brancher(monkeypatch, client)
    main.lancer_validation(classe_reelle(1), avec_synthese=False)
    assert (environnement / "appreciations.csv").exists()
    assert not (environnement / "synthese.md").exists()


def test_synthese_seule_apres_validation(environnement, monkeypatch, tmp_path):
    (tmp_path / "classe").mkdir()
    dossier = ecrire_classe(tmp_path / "classe", ENTETE_ELEVES + ELEVE, ENTETE_APPRECIATIONS + APPRECIATION)
    brancher(monkeypatch, FauxClient(reponse("end_turn", proposition_json("Bon trimestre."))))
    main.lancer_validation(donnees.charger_classe(dossier), avec_synthese=False)
    brancher(monkeypatch, FauxClient(reponse("end_turn", texte("Classe en progrès."))))
    main.lancer_synthese(dossier)
    assert "Classe en progrès." in (environnement / "synthese.md").read_text(encoding="utf-8")


def test_synthese_seule_refusee_si_la_classe_n_est_pas_validee(environnement):
    with pytest.raises(RuntimeError, match="0 appréciation"):
        main.lancer_synthese("ressource/classe_1")
