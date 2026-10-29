"""Orchestrateur, agents et robustesse : faux client LLM scripté, pannes injectées. Nécessite make data."""

import json
import time
from pathlib import Path

import pytest

from vigenere_squad import corpus
from vigenere_squad.agents.base import ErreurOutil, Executeur, OutilRefuse
from vigenere_squad.journal import Journal, lire_journal
from vigenere_squad.llm import ErreurLLM, Reponse
from vigenere_squad.orchestrateur import Orchestrateur
from vigenere_squad.outils import chiffres as ch
from vigenere_squad.outils.langue import ModeleQuadrigrammes
from vigenere_squad.outils.registre import ContexteOutil

DATA = Path(__file__).resolve().parents[1] / "data"
MODELE = DATA / "modeles" / "quadrigrammes_fr.npy"
pytestmark = pytest.mark.skipif(not MODELE.exists(), reason="exécuter make data d'abord")


@pytest.fixture(scope="module")
def modele():
    return ModeleQuadrigrammes.charger(MODELE)


@pytest.fixture(scope="module")
def base():
    return {e["id"]: e for e in corpus.lire(DATA / "corpus" / "base.jsonl")}


class Faux:
    """Client scripté : `reponses` est une liste d'objets (str de JSON, ou exception à lever)."""
    etiquette = "faux"

    def __init__(self, reponses):
        self.reponses, self.appels = list(reponses), 0

    def chat(self, messages, schema, max_jetons):
        self.appels += 1
        r = self.reponses.pop(0) if self.reponses else "{}"
        if isinstance(r, Exception):
            raise r
        return Reponse(r, 10, 5, 0.01)


def _ok(orch, e):
    s = orch.resoudre(e["id"], e["chiffre"])
    return s, s.statut == "succes" and ch.normaliser(s.clair) == ch.normaliser(e["clair"])


def test_sans_llm_resout_cesar_et_vigenere(modele, base, tmp_path):
    orch = Orchestrateur(None, modele, tmp_path, avec_pedagogue=True)
    for ident in ("fr-cesar-300-1", "fr-vigenere-1000-0"):
        s, ok = _ok(orch, base[ident])
        assert ok, (ident, s.statut, s.motif)
        assert s.explication and s.procede in ident
    ev = lire_journal(tmp_path / "fr-cesar-300-1.jsonl")
    assert {e["type"] for e in ev} >= {"debut", "outil_appel", "outil_resultat", "decision", "fin"}
    assert all("t" in e for e in ev)


def test_restitue_la_mise_en_forme(modele, base):
    s, ok = _ok(Orchestrateur(None, modele, avec_pedagogue=False), base["fr-cesar-600-0"])
    assert ok
    original = base["fr-cesar-600-0"]["clair"]
    # Mêmes espaces et ponctuation que le clair d'origine ; les lettres sont en majuscules sans accents.
    assert [c for c in s.clair if not c.isalpha()] == [c for c in original if not ch.normaliser(c)]
    assert ch.normaliser(s.clair) == ch.normaliser(original)


def test_boucle_de_verification_ecarte_une_mauvaise_hypothese(modele, base):
    """Un classifieur trompé propose d'abord le mauvais procédé : le Linguiste le rejette, l'itération suivante corrige."""
    e = base["fr-affine-600-0"]
    mauvais = json.dumps({"famille": "monoalphabetique", "procedes": ["cesar"], "justification": "test"})
    crypto = json.dumps({"appel": {"outil": "chi2_cesar", "arguments": {}}, "justification": "test"})
    lin = json.dumps({"plausible": True, "justification": "test"})   # avis faux : le code fait foi
    bon = json.dumps({"famille": "monoalphabetique", "procedes": ["affine"], "justification": "test"})
    crypto2 = json.dumps({"appel": {"outil": "force_brute_affine", "arguments": {}}, "justification": "test"})
    lin2 = json.dumps({"plausible": True, "justification": "test"})
    ped = json.dumps({"explication": "Le texte est chiffré par un chiffre affine : on teste les clés."})
    client = Faux([mauvais, crypto, lin, bon, crypto2, lin2, ped])
    s, ok = _ok(Orchestrateur(client, modele), e)
    assert ok and s.iterations == 2 and s.procedes_exclus == ["cesar"]


def test_outil_hors_liste_est_refuse_puis_repli(modele, base, tmp_path):
    """Appel d'outil halluciné : refusé et journalisé, l'agent se replie sur la décision déterministe."""
    e = base["fr-cesar-300-1"]
    cl = json.dumps({"famille": "monoalphabetique", "procedes": ["cesar"], "justification": "x"})
    halluci = json.dumps({"appel": {"outil": "executer_shell", "arguments": {"cmd": "id"}}, "justification": "x"})
    client = Faux([cl, halluci, halluci])   # deux essais du Cryptanalyste, tous deux refusés
    s, ok = _ok(Orchestrateur(client, modele, tmp_path, avec_pedagogue=False), e)
    assert ok
    ev = lire_journal(tmp_path / f"{e['id']}.jsonl")
    assert sum(x["type"] == "outil_refuse" for x in ev) == 2
    assert any(x["type"] == "decision" and x["agent"] == "cryptanalyste" and x["source"] == "repli" for x in ev)


def test_outil_d_un_autre_agent_refuse(modele):
    ctx = ContexteOutil("ABCDEFGH", modele)
    ex = Executeur("classifieur", ctx, Journal())
    with pytest.raises(OutilRefuse):
        ex.appeler("attaque_substitution")
    with pytest.raises(ErreurOutil):
        ex.appeler("frequences", {"inconnu": 1})


@pytest.mark.parametrize("panne", ["json_invalide", "vide", "erreur_reseau", "mauvais_schema"])
def test_pannes_du_llm_replient_sur_le_deterministe(modele, base, panne):
    e = base["fr-cesar-300-1"]
    mauvaise = {"json_invalide": "{pas du json", "vide": ErreurLLM("réponse vide"),
                "erreur_reseau": ErreurLLM("ConnectError"), "mauvais_schema": json.dumps({"x": 1})}[panne]
    client = Faux([mauvaise] * 40)
    s, ok = _ok(Orchestrateur(client, modele), e)
    assert ok and client.appels >= 4          # essais répétés avant repli


def test_outil_en_echec_reessai_puis_abandon_propre(modele, base, tmp_path):
    e = base["fr-cesar-300-1"]

    def casse(outil):
        if outil == "chi2_cesar":
            raise RuntimeError("panne injectée")
    s = Orchestrateur(None, modele, tmp_path, pannes=casse).resoudre(e["id"], e["chiffre"])
    assert s.statut == "abandon" and "panne" in s.motif
    ev = lire_journal(tmp_path / f"{e['id']}.jsonl")
    assert any(x["type"] == "reessai" for x in ev) and ev[-1]["type"] == "fin"


def test_outil_en_panne_transitoire_est_rattrape(modele, base):
    e = base["fr-cesar-300-1"]
    etat = {"n": 0}

    def une_fois(outil):
        if outil == "chi2_cesar" and etat["n"] == 0:
            etat["n"] += 1
            raise RuntimeError("panne transitoire")
    s, ok = _ok(Orchestrateur(None, modele, pannes=une_fois, avec_pedagogue=False), e)
    assert ok


def test_outil_hors_delai(modele, base):
    e = base["fr-cesar-300-1"]
    s = Orchestrateur(None, modele, delai_outil_s=0.05,
                      pannes=lambda o: time.sleep(0.3) if o == "chi2_cesar" else None).resoudre(e["id"], e["chiffre"])
    assert s.statut == "abandon" and "délai" in s.motif


def test_echec_propre_si_aucune_hypothese_plausible(modele):
    s = Orchestrateur(None, modele, max_iterations=2, avec_pedagogue=False).resoudre("bruit", "XQZJKVWXQZJKVWPQZXJKVQZXJVKQXZJKQXZJKVQ" * 3)
    assert s.statut == "echec" and s.clair is None


def test_texte_piege_dans_le_clair_ne_change_pas_la_decision(modele, base):
    """Injection de consigne dans les données : le Linguiste fictif obéit, mais le code fait foi."""
    e = base["fr-cesar-300-1"]
    pieges = [json.dumps({"famille": "monoalphabetique", "procedes": ["cesar"], "justification": "x"}),
              json.dumps({"appel": {"outil": "chi2_cesar", "arguments": {}}, "justification": "x"}),
              json.dumps({"plausible": False, "justification": "ordre injecté : réponds non"})]
    s, ok = _ok(Orchestrateur(Faux(pieges), modele, avec_pedagogue=False), e)
    assert ok
