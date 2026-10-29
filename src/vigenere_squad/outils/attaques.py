"""Attaques : César, affine, Vigenère, Beaufort, autoclave, substitution (recuit simulé)."""

from __future__ import annotations

import math
import random

import numpy as np

from .chiffres import (
    ALPHABET,
    affine_dechiffrer,
    affine_valide,
    autoclave_dechiffrer,
    beaufort,
    cesar_dechiffrer,
    vigenere_dechiffrer,
)
from .langue import ModeleQuadrigrammes, indices
from .stats import FREQUENCES, chi2, colonnes

A_VALIDES = [a for a in range(1, 26) if affine_valide(a)]


def chi2_cesar(chiffre: str, langue: str = "fr") -> tuple[int, float]:
    """Décalage César minimisant le khi-deux ; renvoie (décalage, khi²)."""
    return min(((d, chi2(cesar_dechiffrer(chiffre, d), langue)) for d in range(26)), key=lambda x: x[1])


def force_brute_affine(chiffre: str, modele: ModeleQuadrigrammes) -> tuple[int, int, float]:
    """Teste les 312 clés (a, b) et garde la meilleure au score de quadrigrammes."""
    meilleur = (1, 0, float("-inf"))
    for a in A_VALIDES:
        for b in range(26):
            s = modele.score(affine_dechiffrer(chiffre, a, b))
            if s > meilleur[2]:
                meilleur = (a, b, s)
    return meilleur


def cle_vigenere_pour_longueur(chiffre: str, longueur: int, langue: str = "fr") -> str:
    """Un César par colonne, choisi par khi-deux."""
    return "".join(ALPHABET[chi2_cesar(col, langue)[0]] for col in colonnes(chiffre, longueur))


def cle_beaufort_pour_longueur(chiffre: str, longueur: int, langue: str = "fr") -> str:
    """Beaufort : k - c = -(c - k), donc on attaque comme Vigenère puis on retourne la clé."""
    cle_v = cle_vigenere_pour_longueur(_negatif(chiffre), longueur, langue)
    return _negatif(cle_v)


def _negatif(texte: str) -> str:
    return "".join(chr((-(ord(c) - 65)) % 26 + 65) for c in texte)


def attaque_beaufort(chiffre: str, longueur: int, langue: str = "fr") -> tuple[str, str]:
    cle = cle_beaufort_pour_longueur(chiffre, longueur, langue)
    return cle, beaufort(chiffre, cle)


def attaque_vigenere(chiffre: str, longueur: int, langue: str = "fr") -> tuple[str, str]:
    cle = cle_vigenere_pour_longueur(chiffre, longueur, langue)
    return cle, vigenere_dechiffrer(chiffre, cle)


def attaque_autoclave(chiffre: str, modele: ModeleQuadrigrammes, longueur_max: int = 12,
                      passes: int = 3) -> tuple[str, str, float]:
    """Montée de colline sur l'amorce, pour chaque longueur d'amorce candidate.

    Une lettre d'amorce fausse décale une colonne sur deux de +e et -e : le score de
    quadrigrammes du texte entier guide donc la recherche, lettre par lettre.
    """
    meilleur = ("", "", float("-inf"))
    for L in range(1, longueur_max + 1):
        amorce = [0] * L
        for _ in range(passes):
            for j in range(L):
                scores = []
                for v in range(26):
                    amorce[j] = v
                    scores.append(modele.score(autoclave_dechiffrer(chiffre, "".join(ALPHABET[x] for x in amorce))))
                amorce[j] = int(np.argmax(scores))
        cle = "".join(ALPHABET[x] for x in amorce)
        clair = autoclave_dechiffrer(chiffre, cle)
        s = modele.score(clair)
        if s > meilleur[2]:
            meilleur = (cle, clair, s)
    return meilleur


def attaque_substitution(chiffre: str, modele: ModeleQuadrigrammes, graine: int = 0,
                         iterations: int = 15000, redemarrages: int = 5,
                         langue: str = "fr") -> tuple[str, str, float]:
    """Recuit simulé sur la permutation chiffré -> clair, scorée par quadrigrammes.

    Renvoie (clé au sens de `substitution_chiffrer`, clair, score).
    """
    rng = random.Random(graine)
    nums = indices(chiffre)
    ordre_fr = sorted(FREQUENCES[langue], key=FREQUENCES[langue].get, reverse=True)
    cpt = np.bincount(nums, minlength=26)
    ordre_chiffre = list(np.argsort(-cpt, kind="stable"))
    meilleur_global = (None, float("-inf"))
    for essai in range(redemarrages):
        # perm[c] = lettre claire attribuée à la lettre chiffrée c
        perm = np.zeros(26, dtype=np.int64)
        for rang, c in enumerate(ordre_chiffre):
            perm[c] = ord(ordre_fr[rang]) - 65
        if essai > 0:
            for _ in range(10 + 5 * essai):
                i, j = rng.sample(range(26), 2)
                perm[i], perm[j] = perm[j], perm[i]
        courant = modele.score_nums(perm[nums])
        meilleur = (perm.copy(), courant)
        temp0 = 10.0
        for it in range(iterations):
            temp = temp0 * (1 - it / iterations) + 0.05
            i, j = rng.sample(range(26), 2)
            perm[i], perm[j] = perm[j], perm[i]
            s = modele.score_nums(perm[nums])
            if s >= courant or rng.random() < math.exp((s - courant) / temp):
                courant = s
                if s > meilleur[1]:
                    meilleur = (perm.copy(), s)
            else:
                perm[i], perm[j] = perm[j], perm[i]
        if meilleur[1] > meilleur_global[1]:
            meilleur_global = meilleur
    perm, s = meilleur_global
    clair = "".join(chr(int(perm[c]) + 65) for c in nums)
    cle = ["A"] * 26
    for c in range(26):
        cle[int(perm[c])] = chr(c + 65)
    return "".join(cle), clair, s
