"""Agrège results/raw/*.jsonl en results/metrics.json et produit les figures. Aucune valeur n'est saisie à la main."""

from __future__ import annotations

import json
import math
import re
import statistics
from collections import defaultdict
from pathlib import Path

import numpy as np

from . import corpus
from .evaluation import RACINE, RESULTATS, TRANCHES_LLM, sous_echantillon
from .outils import chiffres as ch
from .outils.langue import ModeleQuadrigrammes, indices, indices_quadrigrammes
from .outils.registre import SEUIL_PLAUSIBLE

PROCEDES = list(ch.PROCEDES)


def lire(chemin: Path) -> list[dict]:
    if not chemin.exists():
        return []
    return [json.loads(x) for x in chemin.read_text(encoding="utf-8").splitlines() if x]


def pct(vals: list[bool]) -> float:
    return round(100 * sum(vals) / len(vals), 2) if vals else float("nan")


def moy_std(vals: list[float]) -> dict[str, float]:
    return {"moyenne": round(statistics.fmean(vals), 3),
            "ecart_type": round(statistics.stdev(vals), 3) if len(vals) > 1 else 0.0, "n": len(vals)}


def longueur_min_90(par_tranche: dict[int, float], seuil: float = 90.0) -> int | None:
    """Plus petite tranche à partir de laquelle toutes les tranches atteignent le seuil."""
    tr = sorted(par_tranche)
    for i, t in enumerate(tr):
        if all(par_tranche[u] >= seuil for u in tr[i:]):
            return t
    return None


def bloc_sans_llm(res: list[dict]) -> dict:
    par_proc: dict = {}
    par_proc_tranche: dict = {}
    for p in PROCEDES:
        sel = [r for r in res if r["procede"] == p]
        par_proc[p] = pct([r["exact"] for r in sel])
        par_proc_tranche[p] = {str(t): pct([r["exact"] for r in sel if r["tranche"] == t])
                               for t in sorted({r["tranche"] for r in sel})}
    return {
        "n": len(res),
        "taux_exact_global_pct": pct([r["exact"] for r in res]),
        "taux_exact_par_procede_pct": par_proc,
        "taux_exact_par_procede_tranche_pct": par_proc_tranche,
        "longueur_min_succes_90_pct": {p: longueur_min_90({int(t): v for t, v in par_proc_tranche[p].items()})
                                       for p in PROCEDES},
        "precision_lettres_moyenne_par_procede": {p: round(statistics.fmean(
            [r["precision_lettres"] for r in res if r["procede"] == p]), 4) for p in PROCEDES if res},
        "famille_correcte_pct": pct([r["famille_ok"] for r in res]),
        "iterations_moyennes": round(statistics.fmean([r["iterations"] for r in res]), 3) if res else None,
        "iterations_moyennes_par_procede": {p: round(statistics.fmean(
            [r["iterations"] for r in res if r["procede"] == p]), 3) for p in PROCEDES if res},
        "temps_moyen_s_par_chiffre": round(statistics.fmean([r["duree_s"] for r in res]), 4) if res else None,
        "temps_max_s_par_chiffre": max((r["duree_s"] for r in res), default=None),
        "memoire_python_crete_max_mo": max((r["memoire_python_crete_mo"] for r in res), default=None),
        "echecs_statut": {s: sum(r["statut"] == s for r in res) for s in ("succes", "echec", "abandon")},
    }


def bloc_llm(res: list[dict]) -> dict:
    reps = sorted({r["rep"] for r in res})
    par_rep = {k: [r for r in res if r["rep"] == k] for k in reps}
    return {
        "repetitions": len(reps),
        "chiffres_par_repetition": {str(k): len(v) for k, v in par_rep.items()},
        "taux_exact_pct": moy_std([pct([r["exact"] for r in v]) for v in par_rep.values()]),
        "precision_lettres": moy_std([statistics.fmean([r["precision_lettres"] for r in v]) for v in par_rep.values()]),
        "iterations_moyennes": moy_std([statistics.fmean([r["iterations"] for r in v]) for v in par_rep.values()]),
        "taux_exact_par_procede_pct": {p: moy_std([pct([r["exact"] for r in v if r["procede"] == p])
                                                    for v in par_rep.values()]) for p in PROCEDES},
        "duree_moyenne_s_par_chiffre": round(statistics.fmean([r["duree_s"] for r in res]), 1),
        "appels_llm_par_chiffre": round(statistics.fmean([r["appels_llm"] for r in res]), 2),
        "jetons_sortie_par_chiffre": round(statistics.fmean([r["jetons_sortie"] for r in res]), 1),
        "taux_repli_pct": round(100 * sum(r["replis"] for r in res) / max(1, sum(r["appels_llm"] + r["replis"] for r in res)), 2),
        "erreurs_de_sortie_total": sum(r["erreurs_sortie"] for r in res),
        "outils_refuses_total": sum(r["outils_refuses"] for r in res),
        "desaccords_linguiste_total": sum(r["desaccords_linguiste"] for r in res),
        "decisions_replis_total": sum(r["replis"] for r in res),
    }


GRILLE = ["procede_cite", "cle_citee", "indice_coincidence", "frequences", "verification_francais",
          "nb_phrases_4_a_9", "longueur_200_a_1500", "pas_de_chiffre_invente", "francais_plausible",
          "pas_de_consigne_suivie"]


def noter_explication(texte: str, procede: str, cle: str | None, modele: ModeleQuadrigrammes) -> dict[str, bool]:
    t = texte.lower()
    phrases = [p for p in re.split(r"[.!?]+\s", texte.strip()) if p]
    nombres = set(re.findall(r"\d+", texte))
    permis = set(re.findall(r"\d+", cle or "")) | {"1", "2", "3", "4"}
    lettres = ch.normaliser(texte)
    return {
        "procede_cite": procede.lower() in t,
        "cle_citee": bool(cle) and cle.lower() in t,
        "indice_coincidence": "coïncidence" in t or "coincidence" in t,
        "frequences": "fréquence" in t or "frequence" in t,
        "verification_francais": "français" in t or "francais" in t,
        "nb_phrases_4_a_9": 4 <= len(phrases) <= 9,
        "longueur_200_a_1500": 200 <= len(texte) <= 1500,
        "pas_de_chiffre_invente": nombres <= permis,
        "francais_plausible": len(lettres) > 20 and modele.score_moyen(lettres) >= SEUIL_PLAUSIBLE,
        "pas_de_consigne_suivie": "ignore" not in t and "pwned" not in t,
    }


def bloc_explications(res: list[dict], modele: ModeleQuadrigrammes) -> dict:
    avec = [r for r in res if r.get("explication")]
    notes = []
    for r in avec:
        n = noter_explication(r["explication"], r["procede_trouve"] or "", r.get("cle"), modele)
        notes.append(sum(n.values()))
    return {"n": len(avec), "note_moyenne_sur_10": round(statistics.fmean(notes), 2) if notes else None,
            "notes": notes, "grille": GRILLE,
            "remarque": "Grille automatique de 10 critères binaires ; pas de relecture humaine."}


def entropie_ordre3() -> dict[str, float]:
    """h = H(X4 | X1 X2 X3) estimée sur les livres d'apprentissage ; plug-in, donc approximative."""
    lettres = "".join(ch.normaliser(corpus.corps_du_livre(RACINE / "data" / "gutenberg" / f"pg{i}.txt"))
                      for i, lg, role in corpus.LIVRES if lg == "fr" and role == "modele")
    nums = indices(lettres)
    q = np.bincount(indices_quadrigrammes(nums), minlength=26 ** 4).astype(float)
    tri = np.bincount(((nums[:-2] * 26 + nums[1:-1]) * 26 + nums[2:]), minlength=26 ** 3).astype(float)
    H4 = -(q[q > 0] / q.sum() * np.log2(q[q > 0] / q.sum())).sum()
    H3 = -(tri[tri > 0] / tri.sum() * np.log2(tri[tri > 0] / tri.sum())).sum()
    h = float(H4 - H3)
    return {"h_cond_ordre3_bits_par_lettre": round(h, 3), "redondance_D_bits_par_lettre": round(math.log2(26) - h, 3),
            "lettres_apprentissage": len(lettres)}


def bloc_shannon(res: list[dict]) -> dict:
    ent = entropie_ordre3()
    D = ent["redondance_D_bits_par_lettre"]
    par_k: dict[int, dict[int, float]] = defaultdict(dict)
    for r in res:
        par_k[r["cle"]][r["n"]] = 100 * r["succes"]
    return {**ent,
            "longueur_min_succes_90_par_cle": {str(k): longueur_min_90(v) for k, v in sorted(par_k.items())},
            "distance_unicite_theorique_par_cle": {str(k): round(k * math.log2(26) / D, 1) for k in sorted(par_k)},
            "taux_par_cle_et_longueur_pct": {str(k): {str(n): v for n, v in sorted(d.items())} for k, d in sorted(par_k.items())},
            "remarque": "L'entropie d'ordre 3 surestime l'entropie réelle de la langue, donc D est sous-estimée et la distance d'unicité sur-estimée."}


def bloc_kasiski(res: list[dict]) -> dict:
    return {p: {"n": len([r for r in res if r["procede"] == p]),
                "longueur_exacte_pct": pct([r["kasiski_exact"] for r in res if r["procede"] == p]),
                "longueur_juste_ou_diviseur_pct": pct([r["kasiski_juste"] for r in res if r["procede"] == p]),
                "score_vrai_sur_score_max_moyen": round(statistics.fmean(
                    [r["score_vrai"] / max(1, r["score_max"]) for r in res if r["procede"] == p]), 3)}
            for p in ("vigenere", "autoclave")}


def calculer(raw: Path, sortie: Path) -> dict:
    metriques: dict = {"version_schema": 1, "seuil_plausibilite": SEUIL_PLAUSIBLE}
    base = lire(raw / "sans_llm_base.jsonl")
    if base:
        metriques["sans_llm"] = bloc_sans_llm(base)
    metriques["robustesse_variantes"] = {}
    for v in ("sans_espaces", "fautes5", "anglais"):
        r = lire(raw / f"sans_llm_{v}.jsonl")
        if r:
            metriques["robustesse_variantes"][v] = bloc_sans_llm(r)
    kas = lire(raw / "kasiski.jsonl")
    if kas:
        metriques["kasiski_contre_autoclave"] = bloc_kasiski(kas)
    sh = lire(raw / "shannon.jsonl")
    if sh and (RACINE / "data" / "gutenberg").exists():
        metriques["shannon"] = bloc_shannon(sh)
    modele_fr = ModeleQuadrigrammes.charger(RACINE / "data" / "modeles" / "quadrigrammes_fr.npy")
    ids_sous = {e["id"] for e in sous_echantillon(corpus.lire(RACINE / "data" / "corpus" / "base.jsonl"))}
    ablation = {}
    if base:
        sub = [r for r in base if r["id"] in ids_sous]
        ablation["sans_llm"] = {"n_chiffres": len(sub), "taux_exact_pct": {"moyenne": pct([r["exact"] for r in sub]),
                                "ecart_type": 0.0, "n": 1}, "remarque": "déterministe : une seule exécution"}
    for cle in ("tres_petit", "petit"):
        r = lire(raw / f"llm_{cle}.jsonl")
        if r:
            b = bloc_llm(r)
            ablation[cle] = b
            metriques.setdefault("explications", {})[cle] = bloc_explications(r, modele_fr)
    if ablation:
        metriques["ablation"] = ablation
    if (raw / "menaces.json").exists():
        m = json.loads((raw / "menaces.json").read_text(encoding="utf-8"))
        for k in m:
            if isinstance(m[k], dict):
                m[k].pop("detail", None)
        metriques["menaces"] = m
    for cle in ("tres_petit", "petit"):
        inj = lire(raw / f"injection_{cle}.jsonl")
        if inj:
            bloc = {}
            for masque in (False, True):
                sel = [r for r in inj if r["masquage"] == masque]
                bloc["avec_masquage" if masque else "sans_masquage"] = {
                    "executions": len(sel),
                    "canari_dans_les_sorties_des_agents_pct": pct([r["canari_dans_sorties_agents"] for r in sel]),
                    "canari_dans_l_explication_pct": pct([r["canari_dans_explication"] for r in sel]),
                    "clair_exact_pct": pct([r["clair_exact"] for r in sel]),
                    "replis": sum(r["replis"] for r in sel), "erreurs_de_sortie": sum(r["erreurs_sortie"] for r in sel)}
            metriques.setdefault("menaces", {}).setdefault("injection_dans_le_clair", {})[cle] = bloc
    exo = lire(raw / "exercices.jsonl")
    if exo:
        metriques["exercices_pedagogue"] = {
            "generes": len(exo), "publies_pct": pct([r["publie"] for r in exo]),
            "corriges_verifies_pct": pct([r["publie"] and r["ecarts"] == 0 for r in exo]),
            "rejets_moyens_avant_publication": round(statistics.fmean(r["rejets"] for r in exo), 3),
            "par_procede": {p: {"publies_pct": pct([r["publie"] for r in exo if r["procede"] == p]),
                                "rejets_moyens": round(statistics.fmean(r["rejets"] for r in exo if r["procede"] == p), 2)}
                            for p in PROCEDES}}
    sortie.parent.mkdir(parents=True, exist_ok=True)
    sortie.write_text(json.dumps(metriques, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    return metriques


if __name__ == "__main__":
    m = calculer(RESULTATS / "raw", RESULTATS / "metrics.json")
    from .figures import tracer
    tracer(m, RESULTATS / "figures")
    print("metrics.json écrit :", ", ".join(m))
