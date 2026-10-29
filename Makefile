.PHONY: data test models environment reproduce-small reproduce metrics site audit

UV ?= uv

# Corpus d'évaluation (chiffrés à graine fixe) et modèles de langue de quadrigrammes.
# Télécharge les livres de Project Gutenberg listés dans src/vigenere_squad/corpus.py et vérifie leurs empreintes.
data:
	$(UV) run python data/generer_corpus.py --seed 42

test: data
	$(UV) run pytest -q --cov --cov-fail-under=70

models:
	$(UV) run python scripts/verifier_modeles.py

environment:
	$(UV) run python scripts/capturer_environnement.py

metrics:
	$(UV) run python -m vigenere_squad.metriques
	$(UV) run python site/generer_site.py

# Version courte : quelques minutes, qwen3:0.6b seulement. C'est ce que lance la CI.
reproduce-small: export VSQUAD_RESULTATS = results_small
reproduce-small: data environment
	$(UV) run python scripts/verifier_modeles.py qwen3:0.6b
	$(UV) run vsquad evaluer baseline --variantes base --limite 36
	$(UV) run vsquad evaluer kasiski
	$(UV) run vsquad evaluer menaces
	$(UV) run vsquad evaluer exercices
	$(UV) run vsquad evaluer llm --modele tres_petit --repetitions 1 --limite 6
	$(MAKE) metrics

# Version complète : plusieurs heures sur CPU (voir docs/rapport.pdf, section Reproductibilité).
reproduce: data environment models
	$(UV) run vsquad evaluer baseline
	$(UV) run vsquad evaluer kasiski
	$(UV) run vsquad evaluer shannon
	$(UV) run vsquad evaluer menaces
	$(UV) run vsquad evaluer exercices
	$(UV) run vsquad evaluer llm --modele tres_petit
	$(UV) run vsquad evaluer llm --modele petit
	$(UV) run vsquad evaluer injection --modele tres_petit
	$(MAKE) metrics

audit:
	sha256sum -c SHA256SUMS
