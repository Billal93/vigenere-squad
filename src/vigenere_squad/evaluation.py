"""Évaluation : exécute l'orchestrateur sur le corpus et écrit des enregistrements bruts (results/raw/*.jsonl)."""

from __future__ import annotations

import json
import os
import random
import time
import tracemalloc
from pathlib import Path
from typing import Any

import yaml

from . import corpus
from .llm import ClientOllama
from .orchestrateur import Orchestrateur
from .outils import chiffres as ch
from .outils import stats
from .outils import attaques as at
from .outils.langue import ModeleQuadrigrammes
from .outils.registre import SEUIL_PLAUSIBLE

RACINE = Path(__file__).resolve().parents[2]
TRANCHES_LLM = [150, 300, 600, 1000]


def charger_config(chemin: Path | None = None) -> dict[str, Any]:
    return yaml.safe_load((chemin or RACINE / "config" / "experiment.yaml").read_text(encoding="utf-8"))


def modeles_langue() -> dict[str, ModeleQuadrigrammes]:
    return {lg: ModeleQuadrigrammes.charger(RACINE / "data" / "modeles" / f"quadrigrammes_{lg}.npy")
            for lg in ("fr", "en")}


def precision_lettres(trouve: str | None, attendu: str) -> float:
    if not trouve:
        return 0.0
    a, b = ch.normaliser(trouve), ch.normaliser(attendu)
    return sum(x == y for x, y in zip(a, b)) / len(b) if b else 0.0


def sous_echantillon(lignes: list[dict]) -> list[dict]:
    """Une seule graine par cellule (procédé × tranche) : 6 procédés × 4 tranches = 24 chiffrés."""
    return [e for e in lignes if e["tranche"] in TRANCHES_LLM and e["id"].endswith("-0")]


def memoire_crete_mo() -> float:
    try:
        import psutil
        info = psutil.Process().memory_info()
        return round(getattr(info, "peak_wset", info.rss) / 2**20, 1)
    except Exception:  # noqa: BLE001
        return -1.0


def evenements_resume(evs: list[dict]) -> dict[str, int]:
    msgs = [e for e in evs if e["type"] == "message" and e.get("role") == "assistant"]
    return {
        "appels_llm": len(msgs),
        "jetons_entree": sum(e.get("jetons_entree", 0) for e in msgs),
        "jetons_sortie": sum(e.get("jetons_sortie", 0) for e in msgs),
        "erreurs_sortie": sum(e["type"] == "erreur_sortie" for e in evs),
        "outils_refuses": sum(e["type"] == "outil_refuse" for e in evs),
        "replis": sum(e["type"] == "decision" and e.get("source") == "repli" for e in evs),
        "desaccords_linguiste": sum(e["type"] == "desaccord_linguiste" for e in evs),
    }


def executer_un(orch: Orchestrateur, e: dict, config: str, rep: int | None, langue: str) -> dict[str, Any]:
    tracemalloc.start()
    t0 = time.perf_counter()
    etat = orch.resoudre(e["id"] if rep is None else f"{e['id']}#r{rep}", e["chiffre"], langue)
    duree = time.perf_counter() - t0
    _, crete = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    attendu = e["clair"]
    exact = etat.statut == "succes" and ch.normaliser(etat.clair or "") == ch.normaliser(attendu)
    meilleur = max(etat.tentatives, key=lambda t: t.score_moyen, default=None)
    return {
        "id": e["id"], "variante": e["variante"], "procede": e["procede"], "tranche": e["tranche"],
        "langue": langue, "config": config, "rep": rep, "statut": etat.statut, "procede_trouve": etat.procede,
        "famille_ok": (etat.famille == ("monoalphabetique" if e["procede"] in ("cesar", "affine", "substitution")
                                         else "polyalphabetique")),
        "exact": exact, "precision_lettres": round(precision_lettres(etat.clair, attendu), 4),
        "iterations": etat.iterations, "duree_s": round(duree, 3), "memoire_python_crete_mo": round(crete / 2**20, 2),
        "tentatives": [t.procede for t in etat.tentatives], "meilleur_score": meilleur.score_moyen if meilleur else None,
        **evenements_resume(orch.dernier_journal.evenements), "explication": etat.explication,
    }


def ecrire_jsonl(chemin: Path, lignes: list[dict]) -> None:
    chemin.parent.mkdir(parents=True, exist_ok=True)
    with chemin.open("w", encoding="utf-8", newline="\n") as f:
        for ligne in lignes:
            f.write(json.dumps(ligne, ensure_ascii=False, sort_keys=True) + "\n")


def evaluer_sans_llm(variante: str, sortie: Path, limite: int | None = None) -> list[dict]:
    mods = modeles_langue()
    lignes = corpus.lire(RACINE / "data" / "corpus" / f"{variante}.jsonl")[:limite]
    langue = "en" if variante == "anglais" else "fr"
    orch = Orchestrateur(None, mods[langue], avec_pedagogue=False)
    res = [executer_un(orch, e, "sans_llm", None, langue) for e in lignes]
    ecrire_jsonl(sortie, res)
    return res


def evaluer_llm(modele_cle: str, repetitions: int, sortie: Path, dossier_traces: Path,
                limite: int | None = None, pedagogue_sur: int = 10) -> list[dict]:
    cfg = charger_config()
    mods = modeles_langue()
    etiquette = cfg["modeles"][modele_cle]["etiquette"]
    lignes = sous_echantillon(corpus.lire(RACINE / "data" / "corpus" / "base.jsonl"))[:limite]
    pedago = {e["id"] for e in random.Random(cfg["graine"]).sample(lignes, min(pedagogue_sur, len(lignes)))}
    res: list[dict] = []
    for rep in range(1, repetitions + 1):
        client = ClientOllama(etiquette, cfg["ollama"]["hote"], cfg["temperature"], cfg["graine"] + rep, cfg["contexte"])
        for e in lignes:
            orch = Orchestrateur(client, mods["fr"], dossier_traces / modele_cle / f"rep{rep}",
                                 avec_pedagogue=(rep == 1 and e["id"] in pedago))
            res.append(executer_un(orch, e, modele_cle, rep, "fr"))
            ecrire_jsonl(sortie, res)       # sauvegarde incrémentale : une coupure ne perd rien
            print(f"[{modele_cle} rep{rep}] {e['id']} {res[-1]['statut']} exact={res[-1]['exact']} {res[-1]['duree_s']}s", flush=True)
    return res


def experience_kasiski(sortie: Path) -> list[dict]:
    """Kasiski sur Vigenère contre autoclave, mêmes longueurs de clé : la longueur proposée est-elle la bonne ?"""
    res = []
    for e in corpus.lire(RACINE / "data" / "corpus" / "base.jsonl"):
        if e["procede"] not in ("vigenere", "autoclave") or e["tranche"] < 600:
            continue
        c = ch.normaliser(e["chiffre"])
        vraie = len(e["cle"]["cle"])
        prop = stats.longueur_kasiski(c, 20)
        sc = stats.kasiski(c, 20)
        res.append({"id": e["id"], "procede": e["procede"], "tranche": e["tranche"], "longueur_vraie": vraie,
                    "kasiski_propose": prop, "kasiski_juste": prop is not None and vraie % prop == 0 and prop <= vraie,
                    "kasiski_exact": prop == vraie, "score_max": sc[0][1], "score_vrai": dict(sc).get(vraie, 0)})
    ecrire_jsonl(sortie, res)
    return res


def experience_shannon(sortie: Path, essais: int = 20, graine: int = 42) -> list[dict]:
    """Taux de succès de l'attaque Vigenère selon (longueur de clé, longueur de texte), clairs Gutenberg."""
    chemins = {i: RACINE / "data" / "gutenberg" / f"pg{i}.txt" for i, lg, role in corpus.LIVRES if lg == "fr" and role == "clair"}
    corps = {i: corpus.corps_du_livre(p) for i, p in chemins.items()}
    longueurs = [30, 50, 80, 120, 160, 200, 300, 400, 600, 800, 1200, 2000]
    res = []
    for k in range(3, 13):
        for n in longueurs:
            ok = 0
            for t in range(essais):
                rng = random.Random(f"{graine}|{k}|{n}|{t}")
                livre = rng.choice(list(corps))
                lettres = ch.normaliser(corpus._fenetre(corps[livre], n, rng))
                cle = ch.cle_aleatoire(rng, k)
                c = ch.vigenere_chiffrer(lettres, cle)
                _, out = at.attaque_vigenere(c, stats.longueur_par_ic(c, 20))
                ok += out == lettres
            res.append({"cle": k, "n": n, "succes": ok / essais, "essais": essais})
    ecrire_jsonl(sortie, res)
    return res
