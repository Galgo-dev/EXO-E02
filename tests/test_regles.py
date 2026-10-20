import pytest

from conseil import regles


def matiere(precedente, actuelle):
    return {"moyenne_precedente": precedente, "moyenne": actuelle}


def test_moyenne_generale_arrondie_a_deux_decimales():
    assert regles.moyenne_generale([10, 11, 12]) == 11.0
    assert regles.moyenne_generale([10, 10, 11]) == 10.33


@pytest.mark.parametrize("absences, attendu", [(11, False), (12, True), (17, True), (0, False)])
def test_absences_graves_seuil_12(absences, attendu):
    assert regles.absences_graves(absences) is attendu


def test_matieres_en_baisse_seuil_exact_une_unite():
    matieres = [matiere(13.7, 12.7), matiere(12.0, 11.1), matiere(10.0, 12.0)]
    assert regles.matieres_en_baisse(matieres) == 1


def test_matieres_en_baisse_ignore_les_erreurs_de_virgule_flottante():
    # 14.7 - 13.7 vaut 0.99999... en flottant : doit compter comme une baisse de 1,0.
    assert regles.matieres_en_baisse([matiere(14.7, 13.7)]) == 1


@pytest.mark.parametrize("nb_baisses, attendu", [(4, False), (5, True), (9, True)])
def test_a_surveiller_baisse_generalisee_a_partir_de_cinq_matieres(nb_baisses, attendu):
    assert regles.a_surveiller(0, nb_baisses) == (attendu, "baisse des notes" if attendu else "")


def test_a_surveiller_absences_seules():
    assert regles.a_surveiller(12, 0) == (True, "absences")


def test_a_surveiller_les_deux_motifs():
    assert regles.a_surveiller(15, 6) == (True, "absences et baisse des notes")


def test_a_surveiller_eleve_sans_signal():
    assert regles.a_surveiller(11, 4) == (False, "")


@pytest.mark.parametrize(
    "precedente, actuelle, attendu",
    [(9.83, 13.32, True), (10.0, 11.99, False), (10.0, 12.0, True)],
)
def test_forte_progression_seuil_deux_points(precedente, actuelle, attendu):
    assert regles.forte_progression(precedente, actuelle) is attendu


@pytest.mark.parametrize(
    "moyennes, absences, attendu",
    [([12, 15], 2, True), ([12, 11.9], 0, False), ([14, 15], 3, False)],
)
def test_sans_difficulte(moyennes, absences, attendu):
    assert regles.sans_difficulte(moyennes, absences) is attendu


def test_verifier_charte_appreciation_conforme():
    assert regles.verifier_charte("Résultats en progrès. À poursuivre.", absences_signalees=False) == []


def test_verifier_charte_longueur_limite_300():
    assert regles.verifier_charte("a" * 300, False) == []
    assert len(regles.verifier_charte("a" * 301, False)) == 1


@pytest.mark.parametrize("texte", ["Un élève moyen.", "Il est évident que cela progresse.", "Peut mieux faire."])
def test_verifier_charte_formulations_interdites(texte):
    assert "formulation interdite" in regles.verifier_charte(texte, False)[0]


def test_verifier_charte_absences_seulement_si_seuil_atteint():
    texte = "Douze demi-journées d'absence."
    assert regles.verifier_charte(texte, absences_signalees=True) == []
    assert len(regles.verifier_charte(texte, absences_signalees=False)) == 1
