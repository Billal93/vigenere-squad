"""Télécharge les livres Gutenberg, entraîne les quadrigrammes et génère les corpus.

Usage : uv run python data/generer_corpus.py --seed 42
"""

import argparse
import json
from pathlib import Path

from vigenere_squad import corpus

RACINE = Path(__file__).resolve().parent


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--seed", type=int, default=42)
    args = p.parse_args()

    chemins = corpus.telecharger(RACINE / "gutenberg")
    attendu_fichier = RACINE / "gutenberg_sha256.json"
    obtenu = corpus.empreintes(chemins)
    if attendu_fichier.exists():
        attendu = json.loads(attendu_fichier.read_text())
        ecarts = [k for k in attendu if attendu[k] != obtenu.get(k)]
        if ecarts:
            raise SystemExit(f"empreintes différentes de celles attendues : {ecarts}")
    else:
        attendu_fichier.write_text(json.dumps(obtenu, indent=2, sort_keys=True) + "\n")

    corpus.construire_modeles(chemins, RACINE / "modeles")
    donnees = corpus.generer(chemins, args.seed)
    corpus.ecrire(donnees, RACINE / "corpus")
    print({v: len(l) for v, l in donnees.items()})


if __name__ == "__main__":
    main()
