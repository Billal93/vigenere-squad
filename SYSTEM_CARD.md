# Carte du système : Vigenère-Squad

## Objectif et périmètre
Casser automatiquement des textes chiffrés par six procédés classiques (César, affine, Vigenère, Beaufort, autoclave,
substitution simple), en français et en anglais, et produire une explication pédagogique. Usage prévu : enseignement
et étude de la cryptanalyse classique. Hors périmètre : tout chiffrement moderne (AES, RSA, etc.) ; toute utilisation
contre des communications réelles sans autorisation.

## Architecture
Orchestrateur explicite en Python ; quatre agents (Classifieur, Cryptanalyste, Linguiste, Pédagogue) ; état partagé typé
(Pydantic) ; outils déterministes avec liste fermée par agent ; boucle de vérification (le Linguiste juge le clair, le procédé
est écarté si le score est sous le seuil, puis nouvelle itération, 4 au plus) ; journal JSONL de tout message et appel d'outil.
Les prompts sont dans `src/vigenere_squad/prompts/` (versionnés, historique dans `CHANGELOG.md`).

## Modèles
Ollama 0.40.13, exécution locale sur CPU. Évalués : `qwen3:4b` (sha256:359d7dd4…) et `qwen3:0.6b` (sha256:7df6b6e0…) ;
`qwen3:8b` est téléchargé mais non évalué (trop lent sur cette machine). Sortie contrainte par schéma JSON,
température 0,3, graines 43, 44, 45 pour les trois répétitions, contexte 8192. Config : `config/experiment.yaml`.

## Données
Textes de Project Gutenberg (domaine public), liste et empreintes dans `src/vigenere_squad/corpus.py` et
`data/gutenberg_sha256.json`. Livres d'apprentissage du modèle de langue et livres des clairs **disjoints**.
Corpus d'évaluation : 4 variantes (base, sans espaces, fautes à 5 %, anglais) de 180 chiffrés à graine fixe
(6 procédés × 6 longueurs × 5 chiffrés). Aucune donnée personnelle.

## Évaluation
Voir `results/metrics.json` et `docs/rapport.pdf`. Trois configurations comparées pour l'ablation : sans modèle,
petit modèle (qwen3:0.6b), second modèle de taille différente (qwen3:4b). Les mesures dépendant du modèle sont
répétées trois fois quand le protocole le permet (moyenne ± écart-type). Protocole réduit, CPU seul, démonstration du concept :
3 chiffrés × 3 répétitions pour qwen3:0.6b, 1 chiffré × 1 répétition pour qwen3:4b, 2 chiffrés pour l'injection ; la référence
sans modèle porte sur les 720 chiffrés. Aucun pourcentage obtenu avec un modèle n'a de valeur statistique.

## Limites connues
- Les chiffrés très courts (quelques dizaines de lettres) produisent des faux positifs : un clair absurde peut obtenir un score plausible.
- La substitution simple demande des textes longs ; l'attaque est un recuit simulé stochastique (graine fixée).
- Le seuil de plausibilité (−5,5 par quadrigramme) est calibré sur le français et l'anglais des corpus utilisés ; d'autres langues ne sont pas prises en charge.
- Les modèles évalués sont petits : leurs résultats ne se généralisent pas à des modèles plus grands.
- Le calcul disponible (CPU seul, 15 Go) a limité la taille de l'évaluation avec modèle.

## Risques et garde-fous
Voir `docs/MENACES.md`. Aucun accès réseau pour les agents, aucun outil d'exécution de commandes, aucun secret.
L'outil ne sert qu'à casser des chiffrements historiques ; il n'a pas de capacité contre la cryptographie moderne.

## Maintenance
Projet de cours, non maintenu après l'évaluation. Version publiée : 1.0.0 (DOI Zenodo indiqué dans `CITATION.cff` après publication).
