.PHONY: data test reproduce reproduce-small

data:
	uv run python data/generer_corpus.py --seed 42

test: data
	uv run pytest -q --cov --cov-fail-under=70

# Les cibles reproduce et reproduce-small seront complétées avec l'orchestrateur et l'évaluation.
reproduce:
	@echo "non implémenté : jalon évaluation" && exit 1

reproduce-small:
	@echo "non implémenté : jalon évaluation" && exit 1
