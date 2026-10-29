"""Statistiques de cryptanalyse : IC, fréquences, Kasiski, Friedman, chi²."""

from __future__ import annotations

from collections import Counter

from .chiffres import ALPHABET

# Fréquences des lettres (en %), français et anglais.
FREQ_FR = dict(zip(ALPHABET, [
    7.636, 0.901, 3.260, 3.669, 14.715, 1.066, 0.866, 0.737, 7.529, 0.613, 0.049, 5.456, 2.968,
    7.095, 5.796, 2.521, 1.362, 6.693, 7.948, 7.244, 6.311, 1.838, 0.074, 0.427, 0.128, 0.326,
]))
FREQ_EN = dict(zip(ALPHABET, [
    8.167, 1.492, 2.782, 4.253, 12.702, 2.228, 2.015, 6.094, 6.966, 0.153, 0.772, 4.025, 2.406,
    6.749, 7.507, 1.929, 0.095, 5.987, 6.327, 9.056, 2.758, 0.978, 2.360, 0.150, 1.974, 0.074,
]))
FREQUENCES = {"fr": FREQ_FR, "en": FREQ_EN}

IC_FR = sum((f / 100) ** 2 for f in FREQ_FR.values())
IC_EN = sum((f / 100) ** 2 for f in FREQ_EN.values())
IC_ALEATOIRE = 1 / 26


def indice_coincidence(texte: str) -> float:
    n = len(texte)
    if n < 2:
        return 0.0
    return sum(v * (v - 1) for v in Counter(texte).values()) / (n * (n - 1))


def frequences(texte: str) -> dict[str, float]:
    """Fréquence relative (0 à 1) de chaque lettre."""
    n = len(texte)
    cpt = Counter(texte)
    return {c: (cpt[c] / n if n else 0.0) for c in ALPHABET}


def chi2(texte: str, langue: str = "fr") -> float:
    """Distance du khi-deux entre le texte et la langue ; petit = proche de la langue."""
    n = len(texte)
    if n == 0:
        return float("inf")
    cpt = Counter(texte)
    ref = FREQUENCES[langue]
    return sum((cpt[c] - n * ref[c] / 100) ** 2 / (n * ref[c] / 100) for c in ALPHABET)


def colonnes(texte: str, longueur: int) -> list[str]:
    return [texte[i::longueur] for i in range(longueur)]


def ic_moyen_colonnes(texte: str, longueur: int) -> float:
    cols = [c for c in colonnes(texte, longueur) if len(c) > 1]
    return sum(indice_coincidence(c) for c in cols) / len(cols) if cols else 0.0


def kasiski(texte: str, longueur_max: int = 20, taille_motif: int = 3) -> list[tuple[int, int]]:
    """Pour chaque longueur candidate, nombre de distances entre motifs répétés qu'elle divise.

    Renvoie la liste triée (longueur, score) par score décroissant.
    """
    positions: dict[str, list[int]] = {}
    for i in range(len(texte) - taille_motif + 1):
        positions.setdefault(texte[i:i + taille_motif], []).append(i)
    distances = [p[j] - p[i] for p in positions.values() if len(p) > 1
                 for i in range(len(p)) for j in range(i + 1, len(p))]
    scores = [(L, sum(1 for d in distances if d % L == 0)) for L in range(2, longueur_max + 1)]
    return sorted(scores, key=lambda x: (-x[1], x[0]))


def longueur_kasiski(texte: str, longueur_max: int = 20, seuil: float = 0.7) -> int | None:
    """La plus petite longueur dont le score atteint `seuil` fois le meilleur, ou None sans répétition."""
    scores = kasiski(texte, longueur_max)
    meilleur = scores[0][1]
    if meilleur == 0:
        return None
    return min(L for L, s in scores if s >= seuil * meilleur)


def friedman(texte: str, langue: str = "fr") -> float:
    """Estimation de la longueur de clé par la formule de Friedman (valeur réelle)."""
    n = len(texte)
    ic = indice_coincidence(texte)
    kp = IC_FR if langue == "fr" else IC_EN
    kr = IC_ALEATOIRE
    denom = (n - 1) * ic - kr * n + kp
    if denom <= 0:
        return float("inf")
    return (kp - kr) * n / denom


def longueur_par_ic(texte: str, longueur_max: int = 20, langue: str = "fr") -> int:
    """Longueur de clé estimée par l'IC moyen des colonnes.

    Plus fiable que Kasiski sur les textes courts. Si l'IC du texte entier est déjà celui de la
    langue, le texte est monoalphabétique : longueur 1 (sur un texte court, le maximum des IC de
    colonnes longues est biaisé vers le haut et ne doit pas être comparé à lui). Sinon on prend la
    plus petite longueur qui atteint 90 % du meilleur IC moyen, ce qui écarte les multiples.
    """
    cible = IC_FR if langue == "fr" else IC_EN
    if indice_coincidence(texte) >= 0.85 * cible:
        return 1
    mesures = {L: ic_moyen_colonnes(texte, L) for L in range(2, longueur_max + 1)}
    meilleur = max(mesures.values())
    return min(L for L, v in mesures.items() if v >= 0.9 * meilleur)
