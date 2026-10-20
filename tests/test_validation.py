from conseil.validation import valider_appreciation

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
