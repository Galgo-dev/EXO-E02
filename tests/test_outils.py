from conseil.outils import creer_outils

ELEVE = {
    "absences": 12,
    "matieres": [
        {"moyenne_precedente": 14.0, "moyenne": 12.0},
        {"moyenne_precedente": 10.0, "moyenne": 10.5},
    ],
}


def test_outils_exposes_a_l_agent():
    outils = creer_outils(ELEVE, "charte")
    assert set(outils) == {"lire_charte", "absences_graves", "matieres_en_baisse", "a_surveiller"}


def test_outils_renvoient_les_donnees_de_l_eleve():
    outils = creer_outils(ELEVE, "texte de la charte")
    assert outils["lire_charte"]() == "texte de la charte"
    assert outils["absences_graves"]() is True
    assert outils["matieres_en_baisse"]() == 1
    assert outils["a_surveiller"]() == {"a_surveiller": True, "motif": "absences"}
