"""Figures régénérées par script à partir de metrics.json."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

COULEURS = {"cesar": "#1b6ca8", "affine": "#2a9d8f", "vigenere": "#e9a23b", "autoclave": "#c8553d",
            "substitution": "#6a4c93", "beaufort": "#6c757d"}


def _style() -> None:
    plt.rcParams.update({"font.family": "serif", "font.serif": ["Times New Roman", "DejaVu Serif"],
                         "axes.spines.top": False, "axes.spines.right": False, "figure.dpi": 130,
                         "axes.grid": True, "grid.alpha": 0.25})


def tracer(m: dict, dossier: Path) -> None:
    dossier.mkdir(parents=True, exist_ok=True)
    _style()
    if "sans_llm" in m:
        fig, ax = plt.subplots(figsize=(6.4, 3.8))
        for p, d in m["sans_llm"]["taux_exact_par_procede_tranche_pct"].items():
            ax.plot([int(t) for t in d], list(d.values()), marker="o", label=p, color=COULEURS[p])
        ax.set_xscale("log"); ax.set_xlabel("longueur du texte (lettres)"); ax.set_ylabel("clair exact (%)")
        ax.axhline(90, ls="--", color="grey", lw=0.8); ax.legend(ncol=2, fontsize=8)
        fig.tight_layout(); fig.savefig(dossier / "succes_par_procede_et_longueur.png"); plt.close(fig)
    if "shannon" in m:
        s = m["shannon"]
        ks = sorted(int(k) for k in s["longueur_min_succes_90_par_cle"])
        emp = [s["longueur_min_succes_90_par_cle"][str(k)] for k in ks]
        th = [s["distance_unicite_theorique_par_cle"][str(k)] for k in ks]
        fig, ax = plt.subplots(figsize=(6.4, 3.8))
        ax.plot([k for k, e in zip(ks, emp) if e], [e for e in emp if e], "o-", color="#c8553d", label="longueur minimale mesurée (≥ 90 % de succès)")
        ax.plot(ks, th, "s--", color="#1b6ca8", label="distance d'unicité théorique U = k·log₂26 / D")
        ax.set_xlabel("longueur de la clé k"); ax.set_ylabel("lettres"); ax.legend(fontsize=8)
        fig.tight_layout(); fig.savefig(dossier / "shannon_longueur_minimale.png"); plt.close(fig)
    if "ablation" in m:
        a = m["ablation"]
        noms = list(a)
        moy = [a[n]["taux_exact_pct"]["moyenne"] for n in noms]
        err = [a[n]["taux_exact_pct"]["ecart_type"] for n in noms]
        fig, ax = plt.subplots(figsize=(5.4, 3.6))
        ax.bar(noms, moy, yerr=err, capsize=4, color=["#6c757d", "#2a9d8f", "#e9a23b"][: len(noms)])
        ax.set_ylabel("clair exact (%) sur les 24 chiffrés"); ax.set_ylim(0, 105)
        fig.tight_layout(); fig.savefig(dossier / "ablation.png"); plt.close(fig)
    if "kasiski_contre_autoclave" in m:
        k = m["kasiski_contre_autoclave"]
        fig, ax = plt.subplots(figsize=(4.8, 3.4))
        x = range(2)
        ax.bar([i - 0.2 for i in x], [k[p]["longueur_exacte_pct"] for p in ("vigenere", "autoclave")], 0.4, label="longueur exacte", color="#2a9d8f")
        ax.bar([i + 0.2 for i in x], [k[p]["longueur_juste_ou_diviseur_pct"] for p in ("vigenere", "autoclave")], 0.4, label="exacte ou diviseur", color="#e9a23b")
        ax.set_xticks(list(x), ["Vigenère", "autoclave"]); ax.set_ylabel("% des chiffrés ≥ 600 lettres"); ax.legend(fontsize=8)
        fig.tight_layout(); fig.savefig(dossier / "kasiski_vs_autoclave.png"); plt.close(fig)
