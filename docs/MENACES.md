# Modèle de menace du système (STRIDE)

Ce document décrit les menaces qui pèsent sur **Vigenère-Squad lui-même** (et non sur les chiffrements qu'il attaque),
les contre-mesures mises en place et la façon dont chacune est testée. Les valeurs mesurées ne sont pas recopiées ici :
elles sont dans `results/metrics.json` (clés indiquées) et commentées dans le rapport.

## Actifs et frontières de confiance

- **Intégrité du verdict** : le statut « succès » d'un chiffré ne doit dépendre que de calculs du code, jamais d'un avis du modèle.
- **Intégrité des données d'évaluation** : corpus, modèles de quadrigrammes, livres sources.
- **Fidélité de la trace** : ce qui est journalisé doit refléter ce qui s'est passé.
- **Disponibilité** : une exécution ne doit pas se bloquer ni tourner sans fin.

Frontières : le modèle de langage est **non fiable** (sortie traitée comme une entrée utilisateur) ; les données lues
par un agent (clair déchiffré, résultats d'outils) sont des **données, jamais des consignes** ; seul le code de
l'orchestrateur et de l'exécuteur est de confiance.

## Tableau STRIDE

| Menace | Scénario dans ce système | Contre-mesure | Test et mesure |
|---|---|---|---|
| **S**poofing | Un résultat d'outil se fait passer pour un autre ; un texte déchiffré prétend venir de l'opérateur | Les résultats d'outils sont produits par l'exécuteur, étiquetés par agent et par outil dans la trace ; le prompt rappelle que les données ne sont pas des consignes | `tests/test_orchestrateur.py` (consigne injectée) |
| **T**ampering | (a) un outil renvoie un clair français fluide sans rapport avec le chiffré ; (b) corpus ou modèle de langue altéré | (a) **contrôle de cohérence** : le clair est rechiffré avec la clé annoncée et doit redonner le chiffré (`outils/coherence.py`) ; (b) empreintes SHA-256 des livres (`data/gutenberg_sha256.json`) et du corpus (`ENVIRONMENT.json`) | `menaces.donnees_empoisonnees_*` ; `tests/test_coherence.py` |
| **R**epudiation | Contester ce qu'un agent a décidé | Journal JSONL horodaté de chaque message, appel d'outil, refus, erreur, décision (source : modèle, repli ou sans modèle) ; `vsquad rejouer --verifier` | `tests/test_orchestrateur.py` ; limite : les traces ne sont pas signées individuellement |
| **I**nformation disclosure | Fuite de secrets par les traces ou les prompts | Aucun secret n'existe dans le système (textes publics, pas de clé privée) ; gitleaks en CI ; `TODO_HUMAIN.md` et `data/gutenberg/` exclus du dépôt | gitleaks (CI) |
| **D**enial of service | Recuit simulé trop long ; modèle qui ne répond pas ; boucle d'agents sans fin | Délai par outil, une seule reprise puis abandon propre, `max_iterations`, nombre de jetons borné, repli déterministe si le modèle échoue | `tests/test_orchestrateur.py` (panne, délai, JSON invalide, réponse vide) |
| **E**levation of privilege | (a) le modèle appelle un outil qu'il n'a pas le droit d'utiliser ou inexistant ; (b) le clair déchiffré contient « ignore tes consignes… » et un agent obéit | (a) **liste fermée d'outils par agent** appliquée par l'exécuteur : refus, journalisation, repli ; (b) le code fait foi sur la plausibilité, le texte du clair ne donne accès à aucun outil, et un **masquage des extraits** (option `masquer_extraits`) évite de montrer le clair aux agents qui n'en ont pas besoin | `menaces.outil_hallucine` ; `menaces.injection_dans_le_clair.*` (mot-piège absent des sorties ?) |

## Ce que les contre-mesures ne couvrent pas

- Un modèle plus capable, ou un prompt d'injection plus soigné, pourrait réussir là où le petit modèle échoue : les
  taux mesurés valent pour les modèles évalués et pour les attaques testées, pas pour toutes.
- Le contrôle de cohérence ne détecte pas un outil qui renverrait un couple (clé, clair) cohérent mais qui ne serait pas
  le meilleur candidat : c'est le rôle du score de quadrigrammes, qui est un test statistique et peut se tromper
  sur des textes très courts (faux positifs documentés dans `SYSTEM_CARD.md`).
- Les traces JSONL ne sont pas signées : elles prouvent le déroulement seulement si leur stockage est de confiance.
- L'intégrité des dépendances Python est assurée par `uv.lock` (hachages) mais pas par une vérification d'origine indépendante.
