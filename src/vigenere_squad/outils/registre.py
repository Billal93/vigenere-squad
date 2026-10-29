"""Registre des outils appelables par les agents.

Chaque outil reçoit un contexte (chiffre, modèle de langue) injecté par l'exécuteur : le texte
chiffré ne transite jamais par les arguments écrits par le modèle, qui ne fournit que des
paramètres (longueur de clé, décalage...).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from . import attaques as at
from . import chiffres as ch
from . import stats
from .langue import ModeleQuadrigrammes

SEUIL_PLAUSIBLE = -5.5   # log10 par quadrigramme ; calibré : clairs >= -4,6, mauvaises hypothèses <= -7,6


@dataclass
class ContexteOutil:
    chiffre: str
    modele: ModeleQuadrigrammes
    langue: str = "fr"
    graine: int = 0


def indice_coincidence(ctx: ContexteOutil) -> dict[str, Any]:
    return {"ic": round(stats.indice_coincidence(ctx.chiffre), 4), "ic_langue": round(
        stats.IC_FR if ctx.langue == "fr" else stats.IC_EN, 4), "ic_aleatoire": round(1 / 26, 4),
        "longueur": len(ctx.chiffre)}


def frequences(ctx: ContexteOutil) -> dict[str, Any]:
    f = stats.frequences(ctx.chiffre)
    top = sorted(f, key=f.get, reverse=True)[:6]
    return {"plus_frequentes": {c: round(f[c], 3) for c in top}}


def kasiski(ctx: ContexteOutil) -> dict[str, Any]:
    return {"meilleures_longueurs": stats.kasiski(ctx.chiffre, 20)[:5],
            "longueur_proposee": stats.longueur_kasiski(ctx.chiffre)}


def friedman(ctx: ContexteOutil) -> dict[str, Any]:
    v = stats.friedman(ctx.chiffre, ctx.langue)
    return {"longueur_estimee": None if v == float("inf") else round(v, 2)}


def longueur_ic(ctx: ContexteOutil) -> dict[str, Any]:
    return {"longueur_proposee": stats.longueur_par_ic(ctx.chiffre, 20, ctx.langue)}


def _resultat(ctx: ContexteOutil, clair: str, cle: str | None, **extra: Any) -> dict[str, Any]:
    s = ctx.modele.score_moyen(clair)
    return {"cle": cle, "clair": clair, "score_moyen": round(s, 3), "plausible": s >= SEUIL_PLAUSIBLE, **extra}


def chi2_cesar(ctx: ContexteOutil) -> dict[str, Any]:
    d, _ = at.chi2_cesar(ctx.chiffre, ctx.langue)
    return _resultat(ctx, ch.cesar_dechiffrer(ctx.chiffre, d), str(d))


def force_brute_affine(ctx: ContexteOutil) -> dict[str, Any]:
    a, b, _ = at.force_brute_affine(ctx.chiffre, ctx.modele)
    return _resultat(ctx, ch.affine_dechiffrer(ctx.chiffre, a, b), f"{a},{b}")


def _longueur(longueur: int) -> int:
    if not isinstance(longueur, int) or not 1 <= longueur <= 40:
        raise ValueError("longueur de clé hors de [1, 40]")
    return longueur


def attaque_vigenere(ctx: ContexteOutil, longueur: int) -> dict[str, Any]:
    cle, clair = at.attaque_vigenere(ctx.chiffre, _longueur(longueur), ctx.langue)
    return _resultat(ctx, clair, cle)


def attaque_beaufort(ctx: ContexteOutil, longueur: int) -> dict[str, Any]:
    cle, clair = at.attaque_beaufort(ctx.chiffre, _longueur(longueur), ctx.langue)
    return _resultat(ctx, clair, cle)


def attaque_autoclave(ctx: ContexteOutil) -> dict[str, Any]:
    cle, clair, _ = at.attaque_autoclave(ctx.chiffre, ctx.modele)
    return _resultat(ctx, clair, cle)


def attaque_substitution(ctx: ContexteOutil) -> dict[str, Any]:
    cle, clair, _ = at.attaque_substitution(ctx.chiffre, ctx.modele, graine=ctx.graine, langue=ctx.langue)
    return _resultat(ctx, clair, cle)


def score_quadrigrammes(ctx: ContexteOutil, texte: str) -> dict[str, Any]:
    """Outil du Linguiste : le texte à juger est celui du candidat, lu dans l'état par l'exécuteur."""
    s = ctx.modele.score_moyen(texte)
    return {"score_moyen": round(s, 3), "seuil": SEUIL_PLAUSIBLE, "plausible": s >= SEUIL_PLAUSIBLE}


OUTILS: dict[str, Callable[..., dict[str, Any]]] = {
    f.__name__: f for f in (
        indice_coincidence, frequences, kasiski, friedman, longueur_ic, chi2_cesar, force_brute_affine,
        attaque_vigenere, attaque_beaufort, attaque_autoclave, attaque_substitution, score_quadrigrammes)
}

# Listes fermées : un agent ne peut appeler que les outils de sa liste.
OUTILS_PAR_AGENT: dict[str, frozenset[str]] = {
    "classifieur": frozenset({"indice_coincidence", "frequences"}),
    "cryptanalyste": frozenset({"kasiski", "friedman", "longueur_ic", "chi2_cesar", "force_brute_affine",
                                "attaque_vigenere", "attaque_beaufort", "attaque_autoclave",
                                "attaque_substitution"}),
    "linguiste": frozenset({"score_quadrigrammes"}),
    "pedagogue": frozenset(),
}
