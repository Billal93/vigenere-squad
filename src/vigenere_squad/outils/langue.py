"""Modèle de langue à quadrigrammes : score de plausibilité d'un clair."""

from __future__ import annotations

from pathlib import Path

import numpy as np

TAILLE = 26 ** 4


def indices(texte: str) -> np.ndarray:
    """Tableau numpy des numéros de lettres (0 à 25)."""
    return np.frombuffer(texte.encode("ascii"), dtype=np.uint8).astype(np.int64) - 65


def indices_quadrigrammes(nums: np.ndarray) -> np.ndarray:
    return ((nums[:-3] * 26 + nums[1:-2]) * 26 + nums[2:-1]) * 26 + nums[3:]


class ModeleQuadrigrammes:
    def __init__(self, table: np.ndarray):
        if table.shape != (TAILLE,):
            raise ValueError("table de quadrigrammes de taille inattendue")
        self.table = table.astype(np.float64)

    @classmethod
    def entrainer(cls, texte: str) -> "ModeleQuadrigrammes":
        """log10 des fréquences, avec un plancher pour les quadrigrammes jamais vus."""
        nums = indices(texte)
        comptes = np.bincount(indices_quadrigrammes(nums), minlength=TAILLE).astype(np.float64)
        total = comptes.sum()
        plancher = np.log10(0.01 / total)
        table = np.full(TAILLE, plancher)
        vus = comptes > 0
        table[vus] = np.log10(comptes[vus] / total)
        return cls(table)

    def sauver(self, chemin: Path) -> None:
        np.save(chemin, self.table.astype(np.float32))

    @classmethod
    def charger(cls, chemin: Path) -> "ModeleQuadrigrammes":
        return cls(np.load(chemin))

    def score_nums(self, nums: np.ndarray) -> float:
        if len(nums) < 4:
            return float("-inf")
        return float(self.table[indices_quadrigrammes(nums)].sum())

    def score(self, texte: str) -> float:
        """Score total (log10 de vraisemblance) du texte."""
        return self.score_nums(indices(texte))

    def score_moyen(self, texte: str) -> float:
        """Score par quadrigramme : comparable entre textes de longueurs différentes."""
        n = len(texte) - 3
        return self.score(texte) / n if n > 0 else float("-inf")
