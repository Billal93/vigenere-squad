"""Client Ollama. Aucune opération cryptographique ne passe par ici."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

import httpx


class ErreurLLM(Exception):
    """Échec de l'appel au modèle (réseau, délai, réponse vide)."""


@dataclass
class Reponse:
    contenu: str
    jetons_entree: int = 0
    jetons_sortie: int = 0
    duree_s: float = 0.0


class ClientLLM(Protocol):
    etiquette: str

    def chat(self, messages: list[dict[str, str]], schema: dict[str, Any], max_jetons: int) -> Reponse: ...


class ClientOllama:
    def __init__(self, etiquette: str, hote: str = "http://localhost:11434", temperature: float = 0.0,
                 graine: int = 42, contexte: int = 8192, delai_s: float = 300.0):
        self.etiquette = etiquette
        self.hote = hote
        self.options = {"temperature": temperature, "seed": graine, "num_ctx": contexte}
        self.delai_s = delai_s

    def chat(self, messages: list[dict[str, str]], schema: dict[str, Any], max_jetons: int = 256) -> Reponse:
        corps = {"model": self.etiquette, "messages": messages, "stream": False, "think": False,
                 "format": schema, "options": {**self.options, "num_predict": max_jetons}}
        try:
            r = httpx.post(f"{self.hote}/api/chat", json=corps, timeout=self.delai_s)
            r.raise_for_status()
            j = r.json()
        except (httpx.HTTPError, ValueError) as e:
            raise ErreurLLM(f"{type(e).__name__}: {e}") from e
        contenu = j.get("message", {}).get("content", "")
        if not contenu.strip():
            raise ErreurLLM("réponse vide")
        return Reponse(contenu, j.get("prompt_eval_count", 0), j.get("eval_count", 0),
                       j.get("total_duration", 0) / 1e9)
