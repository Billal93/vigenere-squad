# Audit de reproductibilité

Audit fait le 30 octobre 2026 sur un clone neuf du dépôt public (commit `155e358`), dans un dossier vide, sur Windows 11, Python 3.12, uv.

| Contrôle | Résultat |
|---|---|
| `uv sync` depuis `uv.lock` | réussi |
| `python data/generer_corpus.py --seed 42` | régénère les 4 variantes de 180 chiffrés ; `git status` reste vide : les données publiées sont identiques à celles régénérées |
| `pytest --cov --cov-fail-under=70` | 62 tests réussis, couverture 93,6 % |
| gitleaks (16 commits) | aucune fuite de secret détectée |
| Fichiers privés dans le dépôt | aucun (`PROGRESS.md` et `TODO_HUMAIN.md` sont locaux ; `*.key` ignorés) |

## À savoir

- Lancé sans `make data`, le test `test_resultat_falsifie_mais_plausible_est_ecarte` échoue : il lit le modèle de quadrigrammes (`data/modeles/quadrigrammes_fr.npy`), qui est généré et non versionné. `make test` le génère avant de tester.
- Les évaluations avec modèle (Ollama) n'ont pas été relancées pendant cet audit : leurs résultats viennent de `results/metrics.json`, produit lors des exécutions décrites dans le rapport. Elles dépendent du matériel (processeur seul) et ne sont pas bit à bit reproductibles.
- Intégrité : `SHA256SUMS` liste l'empreinte de chaque fichier suivi par git ; il est signé avec minisign (`SHA256SUMS.minisig`, clé publique `minisign.pub`).
