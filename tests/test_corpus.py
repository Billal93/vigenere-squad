from pathlib import Path

import pytest

from vigenere_squad import corpus
from vigenere_squad.outils import chiffres as ch

DATA = Path(__file__).resolve().parents[1] / "data"


def test_remettre_en_forme_gere_les_ligatures():
    # « cœur » compte 5 lettres normalisées (C, O, E, U, R), « ok » en compte 2.
    assert ch.normaliser("cœur ok") == "COEURRK"[:5] + "OK"
    assert corpus.remettre_en_forme("ABCDEFG", "cœur ok") == "ABCDE FG"
    assert corpus.remettre_en_forme("ABCDEFG", "Cœur, ok") == "ABCDE, FG"


def test_fautes_remplacent_exactement_le_taux_demande():
    import random
    clair = "A" * 200
    fautif = corpus.appliquer_fautes(clair, 0.05, random.Random(1))
    assert sum(a != b for a, b in zip(clair, fautif)) == 10 and len(fautif) == 200


def test_corpus_complet_et_coherent():
    if not (DATA / "corpus" / "base.jsonl").exists():
        pytest.skip("exécuter make data d'abord")
    for variante in corpus.VARIANTES:
        lignes = corpus.lire(DATA / "corpus" / f"{variante}.jsonl")
        assert len(lignes) == 180
        assert {e["procede"] for e in lignes} == set(ch.PROCEDES)
        assert {e["tranche"] for e in lignes} == set(corpus.TRANCHES)
        for e in lignes:
            assert len(ch.normaliser(e["chiffre"])) == len(ch.normaliser(e["clair"])) == e["tranche"]
