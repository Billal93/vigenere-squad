"""Chiffrements classiques sur l'alphabet A-Z (texte déjà normalisé)."""

from __future__ import annotations

import math
import random
import unicodedata

ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
PROCEDES = ("cesar", "affine", "vigenere", "autoclave", "substitution", "beaufort")


def normaliser(texte: str) -> str:
    """Majuscules sans accents, uniquement les lettres A-Z."""
    texte = texte.replace("œ", "oe").replace("Œ", "OE").replace("æ", "ae").replace("Æ", "AE")
    decompose = unicodedata.normalize("NFD", texte)
    return "".join(c for c in decompose.upper() if "A" <= c <= "Z")


def _num(c: str) -> int:
    return ord(c) - 65


def _chr(n: int) -> str:
    return chr(n % 26 + 65)


def cesar_chiffrer(clair: str, decalage: int) -> str:
    return "".join(_chr(_num(c) + decalage) for c in clair)


def cesar_dechiffrer(chiffre: str, decalage: int) -> str:
    return cesar_chiffrer(chiffre, -decalage)


def affine_valide(a: int) -> bool:
    return math.gcd(a, 26) == 1


def affine_chiffrer(clair: str, a: int, b: int) -> str:
    if not affine_valide(a):
        raise ValueError(f"a={a} n'est pas inversible modulo 26")
    return "".join(_chr(a * _num(c) + b) for c in clair)


def affine_dechiffrer(chiffre: str, a: int, b: int) -> str:
    if not affine_valide(a):
        raise ValueError(f"a={a} n'est pas inversible modulo 26")
    a_inv = pow(a, -1, 26)
    return "".join(_chr(a_inv * (_num(c) - b)) for c in chiffre)


def _cle_nums(cle: str) -> list[int]:
    if not cle:
        raise ValueError("clé vide")
    return [_num(c) for c in cle]


def vigenere_chiffrer(clair: str, cle: str) -> str:
    k = _cle_nums(cle)
    return "".join(_chr(_num(c) + k[i % len(k)]) for i, c in enumerate(clair))


def vigenere_dechiffrer(chiffre: str, cle: str) -> str:
    k = _cle_nums(cle)
    return "".join(_chr(_num(c) - k[i % len(k)]) for i, c in enumerate(chiffre))


def beaufort(texte: str, cle: str) -> str:
    """Beaufort est involutif : la même fonction chiffre et déchiffre (k - t)."""
    k = _cle_nums(cle)
    return "".join(_chr(k[i % len(k)] - _num(c)) for i, c in enumerate(texte))


def autoclave_chiffrer(clair: str, amorce: str) -> str:
    """Clé = amorce suivie du clair lui-même."""
    flux = _cle_nums(amorce) + [_num(c) for c in clair]
    return "".join(_chr(_num(c) + flux[i]) for i, c in enumerate(clair))


def autoclave_dechiffrer(chiffre: str, amorce: str) -> str:
    k = _cle_nums(amorce)
    clair: list[int] = []
    for i, c in enumerate(chiffre):
        cle_i = k[i] if i < len(k) else clair[i - len(k)]
        clair.append((_num(c) - cle_i) % 26)
    return "".join(_chr(n) for n in clair)


def substitution_valide(cle: str) -> bool:
    return len(cle) == 26 and sorted(cle) == list(ALPHABET)


def substitution_chiffrer(clair: str, cle: str) -> str:
    """cle[i] est la lettre chiffrée qui remplace la lettre claire ALPHABET[i]."""
    if not substitution_valide(cle):
        raise ValueError("la clé doit être une permutation de A-Z")
    return "".join(cle[_num(c)] for c in clair)


def substitution_dechiffrer(chiffre: str, cle: str) -> str:
    if not substitution_valide(cle):
        raise ValueError("la clé doit être une permutation de A-Z")
    inverse = {c: ALPHABET[i] for i, c in enumerate(cle)}
    return "".join(inverse[c] for c in chiffre)


def cle_substitution_aleatoire(rng: random.Random) -> str:
    lettres = list(ALPHABET)
    rng.shuffle(lettres)
    return "".join(lettres)


def cle_aleatoire(rng: random.Random, longueur: int) -> str:
    return "".join(rng.choice(ALPHABET) for _ in range(longueur))
