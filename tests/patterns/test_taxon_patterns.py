import unittest

from tests.setup import test


class TestTaxon(unittest.TestCase):
    def test_taxon_01(self):
        self.assertEqual(
            test("""M. sensitiva"""),
            [
                {
                    "rank": "species",
                    "taxon": "M. sensitiva",
                    "trait": "taxon",
                    "start": 0,
                    "end": 12,
                }
            ],
        )

    def test_taxon_02(self):
        self.assertEqual(
            test("""Mimosa sensitiva"""),
            [
                {
                    "rank": "species",
                    "taxon": "Mimosa sensitiva",
                    "trait": "taxon",
                    "start": 0,
                    "end": 16,
                }
            ],
        )

    def test_taxon_03(self):
        self.assertEqual(
            test("""M. polycarpa var. spegazzinii"""),
            [
                {
                    "rank": "variety",
                    "taxon": "M. polycarpa var. spegazzinii",
                    "trait": "taxon",
                    "start": 0,
                    "end": 29,
                }
            ],
        )

    def test_taxon_04(self):
        self.assertEqual(
            test("""A. pachyphloia subsp. brevipinnula."""),
            [
                {
                    "rank": "subspecies",
                    "taxon": "A. pachyphloia subsp. brevipinnula",
                    "trait": "taxon",
                    "start": 0,
                    "end": 34,
                }
            ],
        )

    def test_taxon_05(self):
        self.assertEqual(
            test("""M. pachyphloia Bamehy 184."""),
            [
                {
                    "authority": "Bamehy",
                    "rank": "species",
                    "taxon": "M. pachyphloia",
                    "trait": "taxon",
                    "start": 0,
                    "end": 21,
                }
            ],
        )

    def test_taxon_06(self):
        self.assertEqual(
            test("""A. pachyphloia Britton & Rose"""),
            [
                {
                    "authority": "Britton & Rose",
                    "rank": "species",
                    "taxon": "A. pachyphloia",
                    "trait": "taxon",
                    "start": 0,
                    "end": 29,
                }
            ],
        )

    def test_taxon_07(self):
        self.assertEqual(
            test("""Af. pachyphloia"""),
            [
                {
                    "rank": "species",
                    "taxon": "Af. pachyphloia",
                    "trait": "taxon",
                    "start": 0,
                    "end": 15,
                }
            ],
        )

    def test_taxon_08(self):
        self.assertEqual(
            test("""Sect. Vulpinae is characterized"""),
            [
                {
                    "rank": "section",
                    "taxon": "sect. Vulpinae",
                    "trait": "taxon",
                    "start": 0,
                    "end": 14,
                }
            ],
        )

    def test_taxon_09(self):
        self.assertEqual(
            test("""All species are trees"""),
            [{"end": 21, "part": "tree", "start": 16, "trait": "part"}],
        )

    def test_taxon_10(self):
        self.assertEqual(
            test("""Alajuela, between La Palma and Rio Platanillo"""),
            [],
        )

    def test_taxon_11(self):
        self.assertEqual(
            test("""ruiziana and I. silanchensis."""),
            [
                {
                    "rank": "species",
                    "taxon": ["ruiziana", "I. silanchensis"],
                    "trait": "multi_taxon",
                    "start": 0,
                    "end": 28,
                }
            ],
        )
