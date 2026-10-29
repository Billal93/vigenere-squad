"""Contrôle de cohérence : le clair proposé, rechiffré avec la clé annoncée, doit redonner exactement le chiffré.

Ce contrôle est calculé par le code, hors des agents : il écarte un résultat d'outil falsifié ou une clé qui ne
correspond pas au clair annoncé, même si ce clair est du français parfaitement plausible.
"""

from __future__ import annotations

from . import chiffres as ch


def rechiffrer(procede: str, cle: str | None, clair: str) -> str | None:
    """Rechiffre `clair` (lettres) avec la clé telle que l'outil de cryptanalyse l'annonce ; None si clé illisible."""
    if cle is None:
        return None
    try:
        if procede == "cesar":
            return ch.cesar_chiffrer(clair, int(cle))
        if procede == "affine":
            a, b = (int(x) for x in cle.split(","))
            return ch.affine_chiffrer(clair, a, b)
        if procede == "vigenere":
            return ch.vigenere_chiffrer(clair, cle)
        if procede == "beaufort":
            return ch.beaufort(clair, cle)
        if procede == "autoclave":
            return ch.autoclave_chiffrer(clair, cle)
        if procede == "substitution":
            return ch.substitution_chiffrer(clair, cle)
    except (ValueError, KeyError, IndexError):
        return None
    return None


def coherent(procede: str, cle: str | None, clair: str, chiffre: str) -> bool:
    return rechiffrer(procede, cle, ch.normaliser(clair)) == chiffre
