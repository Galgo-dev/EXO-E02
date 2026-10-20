import pytest

from conseil import donnees, regles

ENTETE_ELEVES = (
    "classe,matricule,nom,prenom,moyenne_generale_precedente,moyenne_generale,absences_demi_journees\n"
)
ENTETE_APPRECIATIONS = (
    "classe,matricule,matiere,enseignant,moyenne_trimestre_precedent,moyenne_trimestre,appreciation\n"
)
ELEVE = "1re 2,1R2-001,Vincent,Léna,9.83,13.32,5\n"
APPRECIATION = "1re 2,1R2-001,Français,Mme Garnier,10.7,13.8,Nette progression.\n"


def ecrire_classe(dossier, eleves, appreciations):
    (dossier / "eleves.csv").write_text(eleves, encoding="utf-8")
    (dossier / "appreciations.csv").write_text(appreciations, encoding="utf-8")
    return dossier


def test_charger_classe_minimale(tmp_path):
    ecrire_classe(tmp_path, ENTETE_ELEVES + ELEVE, ENTETE_APPRECIATIONS + APPRECIATION)
    [eleve] = donnees.charger_classe(tmp_path)
    assert eleve["prenom"] == "Léna"
    assert eleve["absences"] == 5
    assert eleve["matieres"][0]["moyenne"] == 13.8


def test_liste_vide_est_signalee(tmp_path):
    ecrire_classe(tmp_path, ENTETE_ELEVES, ENTETE_APPRECIATIONS)
    with pytest.raises(donnees.DonneesInvalides, match="vide"):
        donnees.charger_classe(tmp_path)


def test_valeurs_dans_les_mauvaises_colonnes(tmp_path):
    eleve_invalide = "1re 2,1R2-001,Vincent,Léna,Léna,Vincent,5\n"
    ecrire_classe(tmp_path, ENTETE_ELEVES + eleve_invalide, ENTETE_APPRECIATIONS + APPRECIATION)
    with pytest.raises(donnees.DonneesInvalides, match="format invalide"):
        donnees.charger_classe(tmp_path)


def test_colonnes_manquantes(tmp_path):
    ecrire_classe(tmp_path, "classe,matricule\n1re 2,1R2-001\n", ENTETE_APPRECIATIONS + APPRECIATION)
    with pytest.raises(donnees.DonneesInvalides, match="format invalide"):
        donnees.charger_classe(tmp_path)


def test_matricule_inconnu(tmp_path):
    inconnu = "1re 2,1R2-999,Français,Mme Garnier,10.7,13.8,Texte.\n"
    ecrire_classe(tmp_path, ENTETE_ELEVES + ELEVE, ENTETE_APPRECIATIONS + inconnu)
    with pytest.raises(donnees.DonneesInvalides, match="1R2-999"):
        donnees.charger_classe(tmp_path)


def test_charte_vide(tmp_path):
    charte = tmp_path / "charte.md"
    charte.write_text("  \n", encoding="utf-8")
    with pytest.raises(donnees.DonneesInvalides, match="charte est vide"):
        donnees.charger_charte(charte)


def test_charte_lue(tmp_path):
    charte = tmp_path / "charte.md"
    charte.write_text("# Charte\n", encoding="utf-8")
    assert donnees.charger_charte(charte) == "# Charte"


@pytest.mark.parametrize(
    "dossier, nb_eleves", [("ressource/classe_1", 26), ("ressource/classe_2", 28)]
)
def test_classes_reelles_coherentes(dossier, nb_eleves):
    eleves = donnees.charger_classe(dossier)
    assert len(eleves) == nb_eleves
    for eleve in eleves:
        assert len(eleve["matieres"]) == 9
        moyennes = [m["moyenne"] for m in eleve["matieres"]]
        assert regles.moyenne_generale(moyennes) == pytest.approx(eleve["moyenne"], abs=0.01)
