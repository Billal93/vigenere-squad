"""Générateur d'exercices du Pédagogue : un exercice n'est publié que si son corrigé est vérifié par les outils.

Le texte clair vient du corpus d'évaluation (data/corpus/base.jsonl), la clé est tirée avec la graine donnée.
Le corrigé est produit par l'orchestrateur (outils de cryptanalyse), puis contrôlé : le clair retrouvé doit
égaler le clair d'origine, et les valeurs d'indice de coïncidence citées sont recalculées. Un exercice dont le
corrigé échoue est rejeté et un autre est tiré (le nombre de rejets est renvoyé).
"""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

from . import corpus
from .orchestrateur import Orchestrateur
from .outils import chiffres as ch
from .outils import stats
from .outils.langue import ModeleQuadrigrammes

RACINE = Path(__file__).resolve().parents[2]

CONSIGNES = {
    "cesar": "Le texte a subi un décalage constant. Retrouvez le décalage.",
    "affine": "Le texte a été chiffré par c = a·p + b (mod 26). Retrouvez a et b.",
    "vigenere": "Le texte a été chiffré avec une clé répétée. Retrouvez la longueur de la clé, puis la clé.",
    "beaufort": "Le texte a été chiffré avec une clé répétée (variante). Retrouvez la longueur de la clé, puis la clé.",
    "autoclave": "La clé est une amorce suivie du texte clair lui-même. Retrouvez l'amorce.",
    "substitution": "Chaque lettre est remplacée par une autre, toujours la même. Retrouvez la table.",
}


def _clairs(longueur: int) -> list[str]:
    lignes = [json.loads(x) for x in (RACINE / "data" / "corpus" / "base.jsonl").read_text(encoding="utf-8").splitlines() if x]
    return [ch.normaliser(r["clair"]) for r in lignes if r["tranche"] >= longueur]


def _tirer(procede: str, longueur: int, graine: int) -> dict[str, Any]:
    rng = random.Random(graine)
    clair = rng.choice(_clairs(longueur))[:longueur]
    cle = corpus._clef(procede, rng)
    return {"procede": procede, "longueur": longueur, "graine": graine, "cle": cle, "clair": clair,
            "chiffre": corpus._chiffrer(procede, clair, cle)}


def generer_exercice(procede: str, modele: ModeleQuadrigrammes, longueur: int = 300, graine: int = 1,
                     essais_max: int = 8) -> dict[str, Any]:
    rejets = 0
    for k in range(essais_max):
        brut = _tirer(procede, longueur, graine + 1000 * k)
        etat = Orchestrateur(None, modele).resoudre(f"exo-{procede}-{graine}-{k}", brut["chiffre"], "fr")
        trouve = ch.normaliser(etat.clair or "")
        if etat.statut == "succes" and trouve == brut["clair"]:
            ex = {"procede": procede, "longueur": longueur, "enonce": {"consigne": CONSIGNES[procede], "chiffre": brut["chiffre"]},
                  "corrige": {"cle": brut["cle"], "clair": brut["clair"],
                              "etapes": {"ic_du_chiffre": round(stats.indice_coincidence(brut["chiffre"]), 4),
                                         "ic_du_clair": round(stats.indice_coincidence(brut["clair"]), 4),
                                         "tentatives": [(t.procede, t.plausible) for t in etat.tentatives]},
                              "explication": etat.explication},
                  "graine": brut["graine"], "rejets_avant_publication": rejets}
            return ex
        rejets += 1
    raise RuntimeError(f"aucun exercice vérifiable pour {procede} après {essais_max} essais")


def verifier_corrige(ex: dict[str, Any]) -> list[str]:
    """Contrôle indépendant d'un exercice déjà généré : liste des écarts (vide si le corrigé est cohérent)."""
    ecarts = []
    cle, clair, chiffre = ex["corrige"]["cle"], ex["corrige"]["clair"], ex["enonce"]["chiffre"]
    if corpus._chiffrer(ex["procede"], clair, cle) != chiffre:
        ecarts.append("le chiffrement du clair du corrigé avec la clé du corrigé ne redonne pas le chiffré de l'énoncé")
    if round(stats.indice_coincidence(chiffre), 4) != ex["corrige"]["etapes"]["ic_du_chiffre"]:
        ecarts.append("IC du chiffré recalculé différent")
    if round(stats.indice_coincidence(clair), 4) != ex["corrige"]["etapes"]["ic_du_clair"]:
        ecarts.append("IC du clair recalculé différent")
    return ecarts
