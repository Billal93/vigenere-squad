# Usage de l'IA dans ce projet

## Dans le produit
Le système lui-même utilise des modèles de langage locaux (Ollama : qwen3:0.6b et qwen3:4b) dans quatre rôles
d'agents (voir `SYSTEM_CARD.md`). Les modèles ne font aucune opération cryptographique : ils choisissent un outil dans
une liste fermée, jugent la plausibilité (le code décide) et rédigent des explications.

## Dans la fabrication du projet
Le code, les tests, les prompts, la documentation et ce dépôt ont été écrits par **Claude Code** (assistant d'Anthropic,
modèle Claude Sonnet 5.5) à partir du cahier des charges du cours et de mes instructions, dans une session de travail
dont j'ai gardé la trace. L'assistant a aussi lancé les évaluations, relevé les résultats et rédigé le rapport à partir
de `results/metrics.json`.

## Mon rôle (BENNAT Billal)
Le sujet 1 (Vigenère-Squad) a été comparé aux autres et proposé par l'assistant (`PLAN.md`), puis je l'ai validé.

Les concepts viennent du cours : je les connaissais et c'est moi qui les ai donnés à l'assistant (par exemple la cryptanalyse classique, l'indice de coïncidence, Kasiski, la distance d'unicité, le principe « le modèle propose, le code décide »). Je me suis
en revanche beaucoup aidé de Claude Code pour tout ce qui est rédaction technique : le code, les tests, le rapport, les
scripts d'évaluation, la page de résultats et la préparation de la vidéo. Je ne suis pas développeur de métier : je n'ai pas
écrit le code ligne à ligne, et je ne prétends pas l'avoir fait.

Ce que j'ai décidé ou validé : le sujet, les règles d'intégrité (aucune valeur inventée, résultats négatifs publiés, aucun secret dans
le dépôt), le périmètre, la réduction du protocole d'évaluation (quelques minutes de calcul, pour montrer le concept), et les
actions de publication. Les évaluations avec modèle sont donc volontairement minuscules, et le rapport le dit.

## Ce qui a été vérifié automatiquement
Tests unitaires et d'intégration (dont pannes injectées), couverture des outils déterministes, gitleaks, génération des
chiffres du rapport directement depuis `results/metrics.json`. Ces contrôles réduisent le risque d'erreur mais ne
remplacent pas une relecture humaine.

## Points d'attention
Un code et un rapport écrits avec une IA peuvent contenir des erreurs que seule une exécution révèle. Les écarts connus
et les limites sont consignés dans `SYSTEM_CARD.md` et dans le rapport (section Limites). Tout désaccord entre ce dépôt et
`results/metrics.json` doit être traité comme une erreur du dépôt.
