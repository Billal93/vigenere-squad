"""Pédagogue : un exercice publié a un corrigé vérifié ; un corrigé truqué est détecté."""

import pytest

from vigenere_squad.evaluation import modeles_langue
from vigenere_squad.exercices import generer_exercice, verifier_corrige


@pytest.fixture(scope="module")
def modele():
    try:
        return modeles_langue()["fr"]
    except FileNotFoundError:
        pytest.skip("modèle de langue absent (make data)")


@pytest.mark.parametrize("procede", ["cesar", "affine", "vigenere"])
def test_exercice_verifie(modele, procede):
    ex = generer_exercice(procede, modele, longueur=300, graine=7)
    assert verifier_corrige(ex) == []
    assert ex["corrige"]["clair"] != ex["enonce"]["chiffre"]


def test_corrige_truque_detecte(modele):
    ex = generer_exercice("cesar", modele, longueur=300, graine=3)
    ex["corrige"]["cle"] = {"decalage": (ex["corrige"]["cle"]["decalage"] % 25) + 1}
    assert verifier_corrige(ex)
