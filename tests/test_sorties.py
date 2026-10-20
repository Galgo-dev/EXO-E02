import csv

from conseil import sorties

IDENTITE = {"matricule": "1R2-001", "nom": "Vincent", "prenom": "Léna", "classe": "1re 2"}


def lire(chemin):
    with open(chemin, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def test_ecrire_sorties_cree_les_trois_fichiers(tmp_path):
    dossier = tmp_path / "1re 2"
    sorties.ecrire_sorties(
        dossier,
        appreciations=[{**IDENTITE, "appreciation_generale": "Élève en progrès, à poursuivre."}],
        a_surveiller=[{**IDENTITE, "motif": "absences"}],
        commentaires_ecartes=[{"matricule": "1R2-001", "matiere": "Anglais LV1",
                               "enseignant": "Mme Delcourt", "raison": "situation sociale"}],
    )
    assert lire(dossier / "appreciations.csv")[0]["appreciation_generale"] == "Élève en progrès, à poursuivre."
    assert lire(dossier / "a_surveiller.csv")[0]["motif"] == "absences"
    assert lire(dossier / "commentaires_ecartes.csv")[0]["enseignant"] == "Mme Delcourt"


def test_ecrire_sorties_listes_vides_gardent_les_en_tetes(tmp_path):
    sorties.ecrire_sorties(tmp_path, [], [], [])
    assert lire(tmp_path / "a_surveiller.csv") == []
    assert (tmp_path / "a_surveiller.csv").read_text(encoding="utf-8-sig").startswith("matricule,nom,prenom,classe,motif")


def test_ecrire_sorties_protege_les_virgules(tmp_path):
    texte = "Résultats corrects, à consolider."
    sorties.ecrire_sorties(tmp_path, [{**IDENTITE, "appreciation_generale": texte}], [], [])
    assert lire(tmp_path / "appreciations.csv")[0]["appreciation_generale"] == texte
