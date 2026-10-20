"""Cas de test de la fiche de cadrage, rejoués sans appel à l'API.

Les cas 2 et 7 dépendent de la rédaction du modèle : leur partie déterministe est testée ici,
leur partie rédactionnelle est vérifiée à la main (voir le README).
"""
from pathlib import Path

import pytest

import main
from conseil import agent, donnees, regles
from tests.test_agent import FauxClient, proposition_json, reponse
from tests.test_donnees import ENTETE_APPRECIATIONS, ENTETE_ELEVES, ecrire_classe

FIXTURES = Path(__file__).parent / "fixtures"
VRAI_AGENT = agent.AgentClaude


def charger(cas):
    return donnees.charger_classe(FIXTURES / cas)


def surveilles(eleves):
    return [e for e in eleves if regles.analyser_eleve(e)["surveiller"]]


@pytest.fixture
def sans_dotenv(monkeypatch):
    """Les tests ne chargent jamais le vrai fichier .env."""
    monkeypatch.setattr(main, "load_dotenv", lambda: None)


def test_cas_1_dix_eleves_au_dessus_du_seuil_d_absences():
    eleves = charger("cas1_absences")
    assert len(eleves) == 10
    assert surveilles(eleves) == eleves
    assert {regles.analyser_eleve(e)["motif"] for e in eleves} == {"absences"}


def test_cas_2_classe_partagee_entre_progression_et_baisse():
    eleves = charger("cas2_mixte")
    stats = regles.statistiques_classe(eleves)
    assert (stats["nb_forte_progression"], stats["nb_baisse_generalisee"]) == (5, 5)
    prompt = agent.construire_prompt_classe("1re 2", stats, [])
    assert "Élèves en forte progression : 5." in prompt
    assert "Élèves en baisse généralisée : 5." in prompt


def test_cas_3_cinq_eleves_avec_cinq_matieres_en_baisse():
    eleves = charger("cas3_baisses")
    assert len(eleves) == 5
    assert all(regles.analyser_eleve(e)["nb_baisses"] == 5 for e in eleves)
    assert surveilles(eleves) == eleves
    assert {regles.analyser_eleve(e)["motif"] for e in eleves} == {"baisse des notes"}


def test_cas_4_liste_vide_signalee_a_l_utilisateur(tmp_path, capsys, sans_dotenv):
    ecrire_classe(tmp_path, ENTETE_ELEVES, ENTETE_APPRECIATIONS)
    with pytest.raises(SystemExit):
        main.main([str(tmp_path), "--analyse"])
    assert "la liste est vide" in capsys.readouterr().err


def test_cas_5_valeurs_dans_les_mauvaises_colonnes_signalees(tmp_path, capsys, sans_dotenv):
    eleve_invalide = "1re 2,1R2-001,Vincent,Léna,Léna,Vincent,5\n"
    appreciation = "1re 2,1R2-001,Français,Mme Garnier,10.7,13.8,Texte.\n"
    ecrire_classe(tmp_path, ENTETE_ELEVES + eleve_invalide, ENTETE_APPRECIATIONS + appreciation)
    with pytest.raises(SystemExit):
        main.main([str(tmp_path), "--analyse"])
    assert "format invalide" in capsys.readouterr().err


def test_cas_6_charte_vide_signalee_a_l_utilisateur(tmp_path, monkeypatch, capsys, sans_dotenv):
    charte = tmp_path / "charte.md"
    charte.write_text("", encoding="utf-8")
    monkeypatch.setattr(main, "CHARTE", charte)
    with pytest.raises(SystemExit):
        main.main([str(FIXTURES / "cas3_baisses")])
    assert "charte est vide" in capsys.readouterr().err


def test_cas_7_commentaire_ecarte_avec_le_nom_du_professeur(tmp_path, monkeypatch):
    charte = tmp_path / "charte.md"
    charte.write_text("# Charte", encoding="utf-8")
    monkeypatch.setattr(main, "CHARTE", charte)
    monkeypatch.setattr(main, "DOSSIER_SORTIES", tmp_path / "sorties")
    monkeypatch.setattr(main.validation, "saisir", lambda invite: "")
    ecarte = {"enseignant": "Mme Delcourt", "matiere": "Anglais LV1", "raison": "jugement sur la situation sociale"}
    client = FauxClient(reponse("end_turn", proposition_json("Bon trimestre.", [ecarte])))
    monkeypatch.setattr(main.agent, "AgentClaude", lambda: VRAI_AGENT(client))
    main.lancer_validation(donnees.charger_classe("ressource/classe_1")[:1], avec_synthese=False)
    contenu = (tmp_path / "sorties" / "1re 2" / "commentaires_ecartes.csv").read_text(encoding="utf-8-sig")
    assert "1R2-001" in contenu and "Mme Delcourt" in contenu
