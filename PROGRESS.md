# PROGRESS : Vigenère-Squad (BENNAT Billal)

Dernière mise à jour : 2026-10-29.

## Jalon 1 (29 au 31 octobre) : squelette et outils déterministes

Fait :
- Dépôt Git indépendant, identité locale `BENNAT Billal`.
- Environnement `uv` (Python 3.12), dépendances verrouillées dans `uv.lock`.
- Outils déterministes : `outils/chiffres.py` (César, affine, Vigenère, Beaufort, autoclave, substitution), `outils/stats.py` (IC, fréquences, khi², Kasiski, Friedman, IC par colonne), `outils/langue.py` (quadrigrammes), `outils/attaques.py` (César, affine, Vigenère, Beaufort, autoclave, substitution par recuit simulé).
- Corpus à graine fixe : 4 variantes de 180 chiffrés (base, sans espaces, 5 % de fautes, anglais), clairs tirés de livres Gutenberg distincts de ceux qui entraînent le modèle de quadrigrammes.
- 34 tests, couverture des outils : voir `make test`.
- Modèles Ollama téléchargés : qwen3:0.6b, qwen3:4b, qwen3:8b (digests dans `config/experiment.yaml`).

Constat à publier : sur la substitution, les échecs « clair exact » à 1000 lettres viennent de lettres rares permutées (le score du clair trouvé dépasse celui du vrai clair), pas d'un défaut du recuit. La métrique de précision par lettre sera publiée à côté du taux de clair exact.

Bloquant : aucun.

Prochaine étape : agents (Pydantic, outils en liste fermée), orchestrateur avec boucle de correction, journal JSONL.

Action humaine attendue : voir `TODO_HUMAIN.md` (local, non publié).
