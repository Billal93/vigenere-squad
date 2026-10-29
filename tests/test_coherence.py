"""Contrôle de cohérence : exact sur les six procédés, et un résultat falsifié mais plausible est écarté."""

import json
import random

import pytest

from vigenere_squad import corpus
from vigenere_squad.evaluation import RACINE, modeles_langue
from vigenere_squad.orchestrateur import Orchestrateur
from vigenere_squad.outils import chiffres as ch
from vigenere_squad.outils import registre
from vigenere_squad.outils.coherence import coherent

LIGNES = [json.loads(x) for x in (RACINE / "data" / "corpus" / "base.jsonl").read_text(encoding="utf-8").splitlines() if x]


@pytest.mark.parametrize("procede", ch.PROCEDES)
def test_rechiffrement_exact(procede):
    rng = random.Random(1)
    clair = ch.normaliser(next(r["clair"] for r in LIGNES if r["tranche"] == 300))
    cle = corpus._clef(procede, rng)
    chiffre = corpus._chiffrer(procede, clair, cle)
    annonce = {"cesar": str(cle.get("decalage")), "affine": f"{cle.get('a')},{cle.get('b')}"}.get(procede, cle.get("cle"))
    assert coherent(procede, annonce, clair, chiffre)
    assert not coherent(procede, annonce, clair[:-1] + ("A" if clair[-1] != "A" else "B"), chiffre)


def test_resultat_falsifie_mais_plausible_est_ecarte(monkeypatch):
    modele = modeles_langue()["fr"]
    r = next(r for r in LIGNES if r["procede"] == "cesar" and r["tranche"] == 300)
    faux = ch.normaliser(next(x["clair"] for x in LIGNES if x["tranche"] == 300 and x["id"] != r["id"]))[:300]
    monkeypatch.setitem(registre.OUTILS, "chi2_cesar", lambda ctx: {"cle": "3", "clair": faux, "score_moyen": -3.0, "plausible": True})
    avec = Orchestrateur(None, modele, avec_pedagogue=False).resoudre("p1", r["chiffre"], "fr")
    sans = Orchestrateur(None, modele, avec_pedagogue=False, verifier_coherence=False).resoudre("p2", r["chiffre"], "fr")
    assert sans.statut == "succes" and ch.normaliser(sans.clair) == faux      # faux succès accepté sans contrôle
    assert not (avec.statut == "succes" and ch.normaliser(avec.clair) == faux)
