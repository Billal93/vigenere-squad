"""Corpus de chiffrés à graine fixe, construit à partir de textes Gutenberg du domaine public.

Les livres servant à entraîner le modèle de quadrigrammes sont distincts de ceux d'où l'on
tire les clairs à chiffrer : le modèle ne connaît donc pas les textes qu'il doit retrouver.
"""

from __future__ import annotations

import hashlib
import json
import random
import re
from pathlib import Path

import httpx

from .outils import chiffres as ch
from .outils.langue import ModeleQuadrigrammes

# (identifiant Gutenberg, langue, rôle). Rôle : "modele" pour l'apprentissage, "clair" pour le corpus.
LIVRES = [
    (17489, "fr", "modele"), (14155, "fr", "modele"), (5711, "fr", "modele"),
    (13951, "fr", "modele"), (19657, "fr", "modele"),
    (17989, "fr", "clair"), (4650, "fr", "clair"), (800, "fr", "clair"),
    (5097, "fr", "clair"), (798, "fr", "clair"),
    (1342, "en", "modele"), (84, "en", "modele"), (2701, "en", "modele"),
    (11, "en", "clair"), (345, "en", "clair"), (1661, "en", "clair"),
]
TRANCHES = [80, 150, 300, 600, 1000, 2000]
PAR_CELLULE = 5
VARIANTES = ("base", "sans_espaces", "fautes5", "anglais")


def telecharger(dossier: Path) -> dict[int, Path]:
    dossier.mkdir(parents=True, exist_ok=True)
    chemins = {}
    for ident, _, _ in LIVRES:
        chemin = dossier / f"pg{ident}.txt"
        if not chemin.exists():
            url = f"https://www.gutenberg.org/cache/epub/{ident}/pg{ident}.txt"
            rep = httpx.get(url, follow_redirects=True, timeout=60)
            rep.raise_for_status()
            chemin.write_bytes(rep.content)
        chemins[ident] = chemin
    return chemins


def empreintes(chemins: dict[int, Path]) -> dict[str, str]:
    return {f"pg{i}.txt": hashlib.sha256(p.read_bytes()).hexdigest() for i, p in sorted(chemins.items())}


def corps_du_livre(chemin: Path) -> str:
    """Texte du livre sans l'en-tête ni le pied de page Project Gutenberg."""
    texte = chemin.read_text(encoding="utf-8-sig", errors="replace")
    debut = re.search(r"\*\*\* ?START OF.*?\*\*\*", texte)
    fin = re.search(r"\*\*\* ?END OF", texte)
    return texte[debut.end() if debut else 0: fin.start() if fin else len(texte)]


def construire_modeles(chemins: dict[int, Path], sortie: Path) -> None:
    sortie.mkdir(parents=True, exist_ok=True)
    for langue in ("fr", "en"):
        lettres = "".join(ch.normaliser(corps_du_livre(chemins[i]))
                          for i, lg, role in LIVRES if lg == langue and role == "modele")
        ModeleQuadrigrammes.entrainer(lettres).sauver(sortie / f"quadrigrammes_{langue}.npy")


def _fenetre(corps: str, n_lettres: int, rng: random.Random) -> str:
    """Extrait un passage commençant au début d'une ligne et contenant n_lettres lettres A-Z."""
    lignes_debut = [m.end() for m in re.finditer(r"\n", corps)]
    for _ in range(100):
        debut = rng.choice(lignes_debut[: max(1, len(lignes_debut) - 400)])
        vu, fin = 0, debut
        while fin < len(corps) and vu < n_lettres:
            vu += len(ch.normaliser(corps[fin]))
            fin += 1
        if vu == n_lettres:
            return corps[debut:fin]
    raise RuntimeError("fenêtre introuvable")


def _clef(procede: str, rng: random.Random) -> dict:
    if procede == "cesar":
        return {"decalage": rng.randint(1, 25)}
    if procede == "affine":
        return {"a": rng.choice([a for a in range(2, 26) if ch.affine_valide(a)]), "b": rng.randint(1, 25)}
    if procede == "substitution":
        return {"cle": ch.cle_substitution_aleatoire(rng)}
    return {"cle": ch.cle_aleatoire(rng, rng.randint(3, 12))}


def _chiffrer(procede: str, lettres: str, cle: dict) -> str:
    if procede == "cesar":
        return ch.cesar_chiffrer(lettres, cle["decalage"])
    if procede == "affine":
        return ch.affine_chiffrer(lettres, cle["a"], cle["b"])
    if procede == "vigenere":
        return ch.vigenere_chiffrer(lettres, cle["cle"])
    if procede == "beaufort":
        return ch.beaufort(lettres, cle["cle"])
    if procede == "autoclave":
        return ch.autoclave_chiffrer(lettres, cle["cle"])
    return ch.substitution_chiffrer(lettres, cle["cle"])


def appliquer_fautes(lettres: str, taux: float, rng: random.Random) -> str:
    """Remplace aléatoirement une proportion `taux` des lettres (fautes de frappe)."""
    sortie = list(lettres)
    for i in rng.sample(range(len(sortie)), round(taux * len(sortie))):
        sortie[i] = rng.choice([c for c in ch.ALPHABET if c != sortie[i]])
    return "".join(sortie)


def remettre_en_forme(lettres: str, gabarit: str) -> str:
    """Replace les lettres dans la mise en forme (espaces, ponctuation, casse) du texte d'origine."""
    it = iter(lettres)
    sortie = []
    for c in gabarit:
        if ch.normaliser(c):
            sortie.append(next(it))
        else:
            sortie.append(c)
    return "".join(sortie)


def generer(chemins: dict[int, Path], graine: int) -> dict[str, list[dict]]:
    """Retourne {variante: [enregistrements]} ; les variantes partagent les mêmes clairs et clés."""
    corps = {i: corps_du_livre(p) for i, p in chemins.items()}
    resultat: dict[str, list[dict]] = {v: [] for v in VARIANTES}
    for langue, variante_cible in (("fr", None), ("en", "anglais")):
        livres = [i for i, lg, role in LIVRES if lg == langue and role == "clair"]
        for procede in ch.PROCEDES:
            for tranche in TRANCHES:
                for k in range(PAR_CELLULE):
                    sem = int(hashlib.sha256(f"{graine}|{langue}|{procede}|{tranche}|{k}".encode()).hexdigest()[:12], 16)
                    rng = random.Random(sem)
                    livre = livres[(k + TRANCHES.index(tranche)) % len(livres)]
                    gabarit = _fenetre(corps[livre], tranche, rng)
                    lettres = ch.normaliser(gabarit)
                    cle = _clef(procede, rng)
                    base = {"id": f"{langue}-{procede}-{tranche}-{k}", "procede": procede, "tranche": tranche,
                            "langue": langue, "livre": livre, "cle": cle}
                    if variante_cible == "anglais":
                        resultat["anglais"].append({**base, "clair": gabarit, "chiffre": remettre_en_forme(
                            _chiffrer(procede, lettres, cle), gabarit), "variante": "anglais"})
                        continue
                    chiffre = _chiffrer(procede, lettres, cle)
                    resultat["base"].append({**base, "clair": gabarit,
                                             "chiffre": remettre_en_forme(chiffre, gabarit), "variante": "base"})
                    resultat["sans_espaces"].append({**base, "clair": lettres, "chiffre": chiffre,
                                                     "variante": "sans_espaces"})
                    fautif = appliquer_fautes(lettres, 0.05, rng)
                    resultat["fautes5"].append({**base, "clair": fautif, "chiffre": _chiffrer(procede, fautif, cle),
                                                "variante": "fautes5"})
    return resultat


def ecrire(corpus: dict[str, list[dict]], dossier: Path) -> None:
    dossier.mkdir(parents=True, exist_ok=True)
    for variante, lignes in corpus.items():
        with (dossier / f"{variante}.jsonl").open("w", encoding="utf-8", newline="\n") as f:
            for ligne in lignes:
                f.write(json.dumps(ligne, ensure_ascii=False, sort_keys=True) + "\n")


def lire(chemin: Path) -> list[dict]:
    return [json.loads(ligne) for ligne in chemin.read_text(encoding="utf-8").splitlines() if ligne]
