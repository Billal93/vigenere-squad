import random

import pytest

from vigenere_squad.outils import chiffres as ch


def test_normaliser_retire_accents_et_ponctuation():
    assert ch.normaliser("Été, où l'œuf ?") == "ETEOULOEUF"


def test_cesar_vecteur_connu():
    assert ch.cesar_chiffrer("HELLO", 3) == "KHOOR"
    assert ch.cesar_dechiffrer("KHOOR", 3) == "HELLO"


def test_affine_vecteur_connu():
    # Exemple classique : a=5, b=8
    assert ch.affine_chiffrer("AFFINECIPHER", 5, 8) == "IHHWVCSWFRCP"
    assert ch.affine_dechiffrer("IHHWVCSWFRCP", 5, 8) == "AFFINECIPHER"


def test_affine_refuse_a_non_inversible():
    with pytest.raises(ValueError):
        ch.affine_chiffrer("ABC", 2, 1)
    with pytest.raises(ValueError):
        ch.affine_dechiffrer("ABC", 13, 1)


def test_vigenere_vecteur_connu():
    assert ch.vigenere_chiffrer("ATTACKATDAWN", "LEMON") == "LXFOPVEFRNHR"
    assert ch.vigenere_dechiffrer("LXFOPVEFRNHR", "LEMON") == "ATTACKATDAWN"


def test_autoclave_vecteur_connu():
    assert ch.autoclave_chiffrer("ATTACKATDAWN", "QUEENLY") == "QNXEPVYTWTWP"
    assert ch.autoclave_dechiffrer("QNXEPVYTWTWP", "QUEENLY") == "ATTACKATDAWN"


def test_beaufort_est_involutif():
    c = ch.beaufort("ATTACKATDAWN", "LEMON")
    assert ch.beaufort(c, "LEMON") == "ATTACKATDAWN"


def test_substitution_aller_retour_et_validation():
    rng = random.Random(1)
    cle = ch.cle_substitution_aleatoire(rng)
    assert ch.substitution_valide(cle)
    assert ch.substitution_dechiffrer(ch.substitution_chiffrer("BONJOUR", cle), cle) == "BONJOUR"
    with pytest.raises(ValueError):
        ch.substitution_chiffrer("A", "ABC")
    with pytest.raises(ValueError):
        ch.substitution_dechiffrer("A", "ABC")


def test_cle_vide_refusee():
    with pytest.raises(ValueError):
        ch.vigenere_chiffrer("ABC", "")


@pytest.mark.parametrize("procede", ["cesar", "affine", "vigenere", "autoclave", "substitution", "beaufort"])
def test_aller_retour_aleatoire(procede):
    from vigenere_squad import corpus
    rng = random.Random(7)
    clair = ch.normaliser("Le renard brun saute par dessus le chien paresseux" * 3)
    cle = corpus._clef(procede, rng)
    chiffre = corpus._chiffrer(procede, clair, cle)
    assert chiffre != clair
    if procede == "cesar":
        assert ch.cesar_dechiffrer(chiffre, cle["decalage"]) == clair
    elif procede == "affine":
        assert ch.affine_dechiffrer(chiffre, cle["a"], cle["b"]) == clair
    elif procede == "vigenere":
        assert ch.vigenere_dechiffrer(chiffre, cle["cle"]) == clair
    elif procede == "beaufort":
        assert ch.beaufort(chiffre, cle["cle"]) == clair
    elif procede == "autoclave":
        assert ch.autoclave_dechiffrer(chiffre, cle["cle"]) == clair
    else:
        assert ch.substitution_dechiffrer(chiffre, cle["cle"]) == clair
