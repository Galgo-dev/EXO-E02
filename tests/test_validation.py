from conseil.validation import valider_appreciation, valider_synthese

ELEVE = {"prenom": "Léna", "nom": "Vincent", "matricule": "1R2-001", "absences": 5}
ECARTE = {"enseignant": "Mme Delcourt", "matiere": "Anglais LV1", "raison": "situation sociale"}


def proposition(texte="Bonne progression.", alertes=()):
    return {"appreciation": texte, "commentaires_ecartes": [ECARTE], "alertes": list(alertes)}


def saisies(*reponses):
    suite = iter(reponses)
    return lambda invite: next(suite)


def test_entree_valide_la_proposition():
    texte, ecartes = valider_appreciation(
        ELEVE, "", proposition(), regenerer=None, demander=saisies("")
    )
    assert texte == "Bonne progression."
    assert ecartes == [ECARTE]


def test_modifier_remplace_le_texte():
    texte, _ = valider_appreciation(
        ELEVE, "", proposition(), regenerer=None, demander=saisies("m", "Texte du principal.", "")
    )
    assert texte == "Texte du principal."


def test_modification_vide_conserve_la_proposition():
    texte, _ = valider_appreciation(
        ELEVE, "", proposition(), regenerer=None, demander=saisies("m", "  ", "")
    )
    assert texte == "Bonne progression."


def test_regenerer_demande_une_nouvelle_proposition():
    texte, _ = valider_appreciation(
        ELEVE, "", proposition(), regenerer=lambda: proposition("Nouvelle version."),
        demander=saisies("r", ""),
    )
    assert texte == "Nouvelle version."


def test_appreciation_vide_ne_peut_pas_etre_validee():
    texte, _ = valider_appreciation(
        ELEVE, "", proposition(""), regenerer=None, demander=saisies("", "m", "Texte saisi.", "")
    )
    assert texte == "Texte saisi."


def test_modification_trop_longue_declenche_une_alerte(capsys):
    valider_appreciation(
        ELEVE, "", proposition(), regenerer=None, demander=saisies("m", "a" * 301, "")
    )
    assert "ALERTE charte" in capsys.readouterr().out


def synthese(texte="Classe en progrès.", alertes=()):
    return {"synthese": texte, "alertes": list(alertes)}


def test_synthese_validee_avec_entree():
    assert valider_synthese("1re 2", synthese(), regenerer=None, demander=saisies("")) == "Classe en progrès."


def test_synthese_modifiee_puis_validee():
    texte = valider_synthese(
        "1re 2", synthese(), regenerer=None, demander=saisies("m", "Texte du principal.", "")
    )
    assert texte == "Texte du principal."


def test_synthese_regeneree():
    texte = valider_synthese(
        "1re 2", synthese(), regenerer=lambda: synthese("Nouvelle version."), demander=saisies("r", "")
    )
    assert texte == "Nouvelle version."


def test_synthese_modifiee_de_plus_de_dix_lignes_declenche_une_alerte(capsys):
    onze_lignes = "\n".join(f"Ligne {n}." for n in range(11))
    valider_synthese("1re 2", synthese(), regenerer=None, demander=saisies("m", onze_lignes, ""))
    assert "ALERTE charte" in capsys.readouterr().out
