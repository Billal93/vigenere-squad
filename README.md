# Vigenère-Squad

[![CI](https://github.com/Billal93/vigenere-squad/actions/workflows/ci.yml/badge.svg)](https://github.com/Billal93/vigenere-squad/actions/workflows/ci.yml)
[![Licence code : MIT](https://img.shields.io/badge/code-MIT-blue.svg)](LICENSE)
[![Licence docs et données : CC BY 4.0](https://img.shields.io/badge/docs%20et%20donn%C3%A9es-CC%20BY%204.0-lightgrey.svg)](LICENSE-DOCS.md)

Cryptanalyse automatique de chiffrements classiques (César, affine, Vigenère, Beaufort, autoclave, substitution
simple) par un système de quatre agents LLM encadrés par du code déterministe. Projet individuel bonus du cours
« Cryptographie appliquée et IA agentique » (SUP DE VINCI, 2026), sujet 1. Auteur : BENNAT Billal.

Résultats mesurés : <https://billal93.github.io/vigenere-squad/> (page générée depuis `results/metrics.json`).
Rapport : `docs/rapport.pdf`. Audit de reproductibilité : `AUDIT.md`.

## Principe

Un orchestrateur explicite enchaîne quatre agents, chacun avec un prompt versionné, une liste **fermée** d'outils
et une sortie JSON validée par Pydantic :

| Agent | Rôle | Outils autorisés |
|---|---|---|
| Classifieur | reconnaît la famille de chiffrement | indice de coïncidence, fréquences |
| Cryptanalyste | choisit et lance l'attaque | Kasiski, Friedman, longueur par IC, χ² de César, force brute affine, attaques Vigenère/Beaufort/autoclave/substitution (recuit simulé) |
| Linguiste | juge si le clair est du français (ou de l'anglais) | score de quadrigrammes |
| Pédagogue | explique la démarche, génère des exercices | aucun (texte seul) |

Aucune opération cryptographique n'est déléguée au modèle : le texte chiffré n'est jamais passé dans les arguments
écrits par le modèle, l'exécuteur l'injecte. Le code fait foi : le verdict de plausibilité vient du score de
quadrigrammes, et un contrôle de cohérence rechiffre le clair proposé avec la clé annoncée. Si le modèle répond
mal (JSON invalide, réponse vide, outil inexistant), l'agent se replie sur sa décision déterministe et l'événement
est journalisé. Chaque message et chaque appel d'outil est écrit dans une trace JSONL rejouable.

## Installation et reproduction (5 commandes)

Prérequis : [uv](https://docs.astral.sh/uv/), [Ollama](https://ollama.com) lancé en local, `ollama pull qwen3:0.6b`.

```bash
git clone https://github.com/Billal93/vigenere-squad.git && cd vigenere-squad
uv sync
make data
make test
make reproduce-small
```

`make reproduce-small` (quelques minutes, modèle qwen3:0.6b) régénère un `results/metrics.json` réduit. `make reproduce`
refait l'évaluation du rapport (protocole réduit avec modèle, environ une heure sur CPU). Sous Windows sans `make` : `scripts/evaluer_tout.ps1`.
Le jeu de configuration (graine, température, contexte, modèles et digests) est dans `config/experiment.yaml`,
vérifié par `scripts/verifier_modeles.py` ; la machine et les versions utilisées sont consignées dans
`results/ENVIRONMENT.json`.

## Utilisation

```bash
uv run vsquad resoudre "KHOOR ZRUOG" --modele aucun            # casser un chiffré, afficher la trace
uv run vsquad resoudre "..." --modele tres_petit --traces traces/mes_essais
uv run vsquad rejouer traces/exemple.jsonl --verifier          # relire une trace, vérifier les listes d'outils
uv run vsquad exercice --procede vigenere --graine 4           # exercice et corrigé vérifié par les outils
uv run --extra demo vsquad-demo                                # interface Gradio locale (127.0.0.1:7860)
```

## Contenu du dépôt

- `src/vigenere_squad/` : outils (`outils/`), agents (`agents/`), prompts versionnés (`prompts/`), orchestrateur, évaluation, métriques.
- `config/experiment.yaml` : graine, répétitions, température, contexte, modèles avec digests.
- `data/` : scripts de génération à graine fixe et corpus d'évaluation (4 variantes de 180 chiffrés) ; les livres Project Gutenberg sont téléchargés puis vérifiés par SHA-256.
- `results/` : données brutes (`raw/`), `metrics.json`, figures, `ENVIRONMENT.json`. `traces/` : journaux JSONL des exécutions.
- `docs/` : rapport, modèle de menace (`MENACES.md`). `site/` : générateur de la page de résultats.
- `SYSTEM_CARD.md`, `AI_USAGE.md`, `AUDIT.md`, `CITATION.cff`, `.zenodo.json`, `SHA256SUMS`.

## Limites

Voir `SYSTEM_CARD.md`. Retenir surtout : les chiffrés très courts donnent des faux positifs ; la substitution simple
exige des textes longs ; l'évaluation avec modèle est volontairement minuscule (3 chiffrés pour qwen3:0.6b, 1 pour qwen3:4b) à cause du calcul disponible (CPU seul) ;
les modèles utilisés sont petits (0,6 et 4 milliards de paramètres).

## Vérifier la signature
`SHA256SUMS` est signé avec minisign (clé publique dans `minisign.pub`, identifiant `A80540466CC63A79`) :

```bash
minisign -Vm SHA256SUMS -p minisign.pub
sha256sum -c SHA256SUMS
```

## Licences

Code : MIT (`LICENSE`). Documentation, données et résultats : CC BY 4.0 (`LICENSE-DOCS.md`). Les textes de
Project Gutenberg sont du domaine public ; ils ne sont pas redistribués, seulement téléchargés.

## Citer

Voir `CITATION.cff`. Le DOI Zenodo est ajouté après la publication de la version 1.0.0.
