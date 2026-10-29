"""Attaques évaluées sur des extraits du corpus : nécessitent data/ (make data)."""

from pathlib import Path

import pytest

from vigenere_squad import corpus
from vigenere_squad.outils import attaques as at
from vigenere_squad.outils import chiffres as ch
from vigenere_squad.outils import stats
from vigenere_squad.outils.langue import ModeleQuadrigrammes

DATA = Path(__file__).resolve().parents[1] / "data"
MODELE = DATA / "modeles" / "quadrigrammes_fr.npy"
pytestmark = pytest.mark.skipif(not MODELE.exists(), reason="exécuter make data d'abord")


@pytest.fixture(scope="module")
def modele():
    return ModeleQuadrigrammes.charger(MODELE)


@pytest.fixture(scope="module")
def base():
    return corpus.lire(DATA / "corpus" / "base.jsonl")


def _cas(base, procede, tranche, k=0):
    e = next(e for e in base if e["procede"] == procede and e["tranche"] == tranche and e["id"].endswith(f"-{k}"))
    return ch.normaliser(e["chiffre"]), ch.normaliser(e["clair"]), e["cle"]


def test_modele_prefere_le_francais_au_hasard(modele, base):
    _, clair, _ = _cas(base, "cesar", 600)
    assert modele.score_moyen(clair) > modele.score_moyen(ch.cesar_chiffrer(clair, 3)) + 1
    assert modele.score("AB") == float("-inf")


def test_chi2_cesar(base):
    c, clair, cle = _cas(base, "cesar", 150)
    decalage, _ = at.chi2_cesar(c)
    assert decalage == cle["decalage"]
    assert ch.cesar_dechiffrer(c, decalage) == clair


def test_force_brute_affine(modele, base):
    c, clair, cle = _cas(base, "affine", 300)
    a, b, _ = at.force_brute_affine(c, modele)
    assert (a, b) == (cle["a"], cle["b"])


def test_vigenere_longue(base):
    c, clair, cle = _cas(base, "vigenere", 1000)
    longueur = stats.longueur_par_ic(c)
    assert longueur == len(cle["cle"])
    _, out = at.attaque_vigenere(c, len(cle["cle"]))
    assert out == clair


def test_beaufort(base):
    c, clair, cle = _cas(base, "beaufort", 1000)
    k, out = at.attaque_beaufort(c, len(cle["cle"]))
    assert out == clair
    assert k == cle["cle"]


def test_autoclave(modele, base):
    c, clair, cle = _cas(base, "autoclave", 600)
    _, out, _ = at.attaque_autoclave(c, modele)
    assert out == clair


def test_kasiski_echoue_sur_autoclave_mais_pas_sur_vigenere(base):
    """L'autoclave n'a pas de période : les distances entre répétitions ne désignent aucune longueur."""
    cv, _, kv = _cas(base, "vigenere", 2000)
    ca, _, _ = _cas(base, "autoclave", 2000)
    sv = dict(stats.kasiski(cv, 20))
    sa = dict(stats.kasiski(ca, 20))
    assert sv[len(kv["cle"])] / max(sv.values()) > 0.7
    assert max(sa.values()) < max(sv.values()) / 3


def test_substitution_longue(modele, base):
    c, clair, cle = _cas(base, "substitution", 2000, k=0)
    _, out, _ = at.attaque_substitution(c, modele, graine=1)
    acc = sum(a == b for a, b in zip(out, clair)) / len(clair)
    assert acc > 0.97


def test_attaque_substitution_est_deterministe(modele, base):
    c, _, _ = _cas(base, "substitution", 300)
    r1 = at.attaque_substitution(c, modele, graine=3, iterations=800, redemarrages=1)
    r2 = at.attaque_substitution(c, modele, graine=3, iterations=800, redemarrages=1)
    assert r1 == r2
