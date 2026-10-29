# PROGRESS : Vigenère-Squad (BENNAT Billal)

Dernière mise à jour : 2026-10-29.

## Jalon 1 (fait) : squelette et outils déterministes
Outils (`outils/`), corpus à graine fixe (4 variantes de 180 chiffrés), modèles Ollama qwen3:0.6b, 4b, 8b déclarés avec digest dans `config/experiment.yaml`.

## Jalon 2 (fait) : agents et orchestrateur
- État partagé typé et sorties Pydantic (`etat.py`), journal JSONL horodaté (`journal.py`), client Ollama avec sortie contrainte par schéma JSON (`llm.py`).
- Quatre agents (`agents/roles.py`) : Classifieur, Cryptanalyste, Linguiste, Pédagogue. Prompts versionnés dans `prompts/` avec `CHANGELOG.md`. Liste fermée d'outils par agent (`outils/registre.py`), appliquée par l'exécuteur (`agents/base.py`) : un outil hors liste est refusé, journalisé, et l'agent se replie sur sa décision déterministe.
- Orchestrateur (`orchestrateur.py`) avec boucle de vérification : le Linguiste juge le clair, le procédé est écarté si le score de quadrigrammes est sous le seuil (−5,5, calibré : clairs ≥ −4,6, mauvaises hypothèses ≤ −7,6), le Classifieur est reconsulté. Le code fait foi sur la plausibilité ; les désaccords du modèle sont journalisés.
- Robustesse testée : JSON invalide, réponse vide, erreur réseau, mauvais schéma, outil halluciné, outil en échec (réessai puis abandon propre), outil hors délai, consigne injectée.
- 51 tests passent.

Mesures d'exploration (à ne pas citer comme résultats finaux) : la référence sans modèle résout 100 % de César et d'affine, 70 % de Vigenère, 87 % d'autoclave, 67 % de substitution, 77 % de Beaufort sur la variante de base, en 2,1 itérations en moyenne.

## Bug corrigé en route
`remettre_en_forme` désalignait les lettres après une ligature (œ, æ) : une partie du corpus anglais était faussée. Corrigé, corpus régénéré (seule `anglais.jsonl` change).

## Contrainte de calcul à connaître (important pour la suite)
Sur cette machine (CPU seul, 15 Go dont beaucoup occupés), qwen3:4b tourne à 2 à 3 jetons par seconde : environ 2 à 5 minutes par chiffré avec 3 appels de modèle. L'évaluation avec modèle ne peut donc pas porter sur les 720 chiffrés trois fois. Plan : sous-échantillon stratifié de 36 chiffrés par tranche et par procédé, 3 répétitions, pour qwen3:4b et qwen3:8b ; la référence sans modèle et les attaques seules portent sur les 720 chiffrés. Le Pédagogue n'est appelé que sur 10 chiffrés tirés au hasard.

Bloquant : aucun.

Prochaine étape : évaluation (métriques, ablation, répétitions), modèle de menace avec contre-mesures évaluées, autoclave/Kasiski (figure), figure de Shannon, interface CLI et démonstrateur Gradio, CI.

Action humaine attendue : voir `TODO_HUMAIN.md` (local).
