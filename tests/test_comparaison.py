import unittest

from modules.comparaison import (
    classer_changement, completer_champs_absents, detecter_changements,
)
from modules.modele import Societe


class TestComparaison(unittest.TestCase):

    def test_premiere_collecte_ne_declenche_pas_d_alerte(self):
        nouvelle = Societe(siren="542051180", statut="Active")

        self.assertEqual(detecter_changements(None, nouvelle), [])

    def test_detecter_changements_retourne_les_champs_modifies(self):
        ancienne = Societe(
            siren="542051180",
            capital="100 000 €",
            statut="Active",
        )
        nouvelle = Societe(
            siren="542051180",
            capital="120 000 €",
            statut="Radiée",
        )

        changements = detecter_changements(ancienne, nouvelle)

        self.assertEqual(
            [changement.champ for changement in changements],
            ["statut", "capital"],
        )
        changement_capital = next(
            changement for changement in changements
            if changement.champ == "capital"
        )
        self.assertEqual(changement_capital.ancienne_valeur, "100 000 €")
        self.assertEqual(changement_capital.nouvelle_valeur, "120 000 €")

    def test_deux_etats_identiques_ne_declenchent_pas_d_alerte(self):
        ancienne = Societe(siren="542051180", statut="Active")
        nouvelle = Societe(siren="542051180", statut="Active")

        self.assertEqual(detecter_changements(ancienne, nouvelle), [])

    def test_preserve_un_champ_non_recollecte_sans_creer_de_fausse_alerte(self):
        ancienne = Societe(
            siren="542051180", capital="100 000 €", source="Pappers",
            provenance={"capital": "Pappers"},
            dates_provenance={"capital": "2026-07-01T07:00:00"},
        )
        nouvelle = Societe(
            siren="542051180", source="INSEE + INPI + BODACC",
            provenance={"statut": "INSEE"},
        )

        completer_champs_absents(ancienne, nouvelle)

        self.assertEqual(nouvelle.capital, "100 000 €")
        self.assertEqual(nouvelle.provenance["capital"], "Historique (Pappers)")
        self.assertEqual(
            nouvelle.dates_provenance["capital"], "2026-07-01T07:00:00"
        )
        self.assertEqual(detecter_changements(ancienne, nouvelle), [])

    def test_classe_radiation_et_procedure_collective_comme_critiques(self):
        self.assertEqual(
            classer_changement("statut", "Active", "Radiée")[:2],
            ("critique", "cessation_radiation"),
        )
        self.assertEqual(
            classer_changement(
                "dernier_changement", "", "Ouverture d'une liquidation judiciaire"
            )[:2],
            ("critique", "procedure_collective"),
        )

    def test_classe_les_evenements_juridiques_importants(self):
        cas = {
            "dirigeant": "dirigeant",
            "adresse": "siege",
            "capital": "capital",
            "forme_juridique": "forme_juridique",
        }
        for champ, categorie in cas.items():
            with self.subTest(champ=champ):
                self.assertEqual(classer_changement(champ)[0:2], ("important", categorie))
        self.assertEqual(
            classer_changement("dernier_changement", "", "Dépôt des comptes")[:2],
            ("important", "comptes"),
        )

    def test_trie_les_changements_par_criticite(self):
        ancienne = Societe(
            "542051180", raison_sociale="Ancien nom", capital="100 €", statut="Active"
        )
        nouvelle = Societe(
            "542051180", raison_sociale="Nouveau nom", capital="200 €", statut="Radiée"
        )

        changements = detecter_changements(ancienne, nouvelle)

        self.assertEqual(
            [changement.niveau for changement in changements],
            ["critique", "important", "informatif"],
        )


if __name__ == "__main__":
    unittest.main()
