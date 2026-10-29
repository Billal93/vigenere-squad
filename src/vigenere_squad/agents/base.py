"""Socle commun des agents : exécuteur d'outils à liste fermée, boucle d'appel au modèle."""

from __future__ import annotations

import concurrent.futures
import inspect
from pathlib import Path
from typing import Any, Callable

from pydantic import BaseModel, ValidationError

from ..etat import EtatPartage
from ..journal import Journal
from ..llm import ClientLLM, ErreurLLM
from ..outils.registre import OUTILS, OUTILS_PAR_AGENT, ContexteOutil

PROMPTS = Path(__file__).resolve().parent.parent / "prompts"


class OutilRefuse(Exception):
    """Appel d'un outil absent de la liste fermée de l'agent (outil halluciné ou injecté)."""


class ErreurOutil(Exception):
    """Échec, délai ou arguments invalides d'un outil autorisé."""


class Executeur:
    def __init__(self, agent: str, ctx: ContexteOutil, journal: Journal, delai_s: float = 120.0,
                 pannes: Callable[[str], None] | None = None):
        self.agent, self.ctx, self.journal, self.delai_s, self.pannes = agent, ctx, journal, delai_s, pannes
        self.autorises = OUTILS_PAR_AGENT[agent]

    def verifier_autorise(self, outil: str) -> None:
        if outil not in self.autorises:
            self.journal.ecrire("outil_refuse", self.agent, outil=outil, autorises=sorted(self.autorises))
            raise OutilRefuse(f"{self.agent} ne peut pas appeler « {outil} »")

    def appeler(self, outil: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        arguments = dict(arguments or {})
        self.verifier_autorise(outil)
        fonction = OUTILS[outil]
        parametres = set(inspect.signature(fonction).parameters) - {"ctx"}
        if set(arguments) - parametres:
            self.journal.ecrire("outil_erreur", self.agent, outil=outil, erreur="arguments inconnus",
                                arguments=arguments)
            raise ErreurOutil(f"arguments inconnus pour {outil} : {sorted(set(arguments) - parametres)}")
        self.journal.ecrire("outil_appel", self.agent, outil=outil, arguments=arguments)

        def executer() -> dict[str, Any]:
            if self.pannes is not None:
                self.pannes(outil)
            return fonction(self.ctx, **arguments)

        pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        try:
            resultat = pool.submit(executer).result(timeout=self.delai_s)
        except concurrent.futures.TimeoutError as e:
            self.journal.ecrire("outil_erreur", self.agent, outil=outil, erreur="délai dépassé")
            raise ErreurOutil(f"{outil} : délai dépassé") from e
        except Exception as e:  # noqa: BLE001 : toute panne d'outil est journalisée puis remontée
            self.journal.ecrire("outil_erreur", self.agent, outil=outil, erreur=f"{type(e).__name__}: {e}")
            raise ErreurOutil(f"{outil} : {e}") from e
        finally:
            pool.shutdown(wait=False)
        resume = {k: (v[:80] + "…" if isinstance(v, str) and len(v) > 80 else v) for k, v in resultat.items()}
        self.journal.ecrire("outil_resultat", self.agent, outil=outil, resultat=resume)
        return resultat


class Agent:
    nom: str = ""
    modele_sortie: type[BaseModel]
    max_jetons: int = 200
    version_prompt: str = "v1"

    def __init__(self, client: ClientLLM | None, executeur: Executeur, journal: Journal, essais: int = 2):
        self.client, self.executeur, self.journal, self.essais = client, executeur, journal, essais

    @property
    def prompt_systeme(self) -> str:
        return (PROMPTS / f"{self.nom}.{self.version_prompt}.md").read_text(encoding="utf-8")

    def message_utilisateur(self, etat: EtatPartage, obs: dict[str, Any]) -> str:
        raise NotImplementedError

    def repli(self, etat: EtatPartage, obs: dict[str, Any]) -> BaseModel:
        """Décision déterministe : référence sans modèle (configuration a) et solution de repli."""
        raise NotImplementedError

    def verifier(self, sortie: BaseModel) -> None:
        """Contrôle propre à l'agent, levant ValueError ou OutilRefuse si la sortie est inacceptable."""

    def decider(self, etat: EtatPartage, obs: dict[str, Any]) -> tuple[BaseModel, str]:
        if self.client is None:
            sortie = self.repli(etat, obs)
            self.journal.ecrire("decision", self.nom, source="sans_llm", sortie=sortie.model_dump())
            return sortie, "sans_llm"
        messages = [{"role": "system", "content": self.prompt_systeme},
                    {"role": "user", "content": self.message_utilisateur(etat, obs)}]
        schema = self.modele_sortie.model_json_schema()
        for essai in range(1, self.essais + 1):
            self.journal.ecrire("message", self.nom, role="user", contenu=messages[1]["content"], essai=essai,
                                modele=self.client.etiquette, version_prompt=self.version_prompt)
            try:
                rep = self.client.chat(messages, schema, self.max_jetons)
                self.journal.ecrire("message", self.nom, role="assistant", contenu=rep.contenu,
                                    jetons_entree=rep.jetons_entree, jetons_sortie=rep.jetons_sortie,
                                    duree_s=round(rep.duree_s, 2))
                sortie = self.modele_sortie.model_validate_json(rep.contenu)
                self.verifier(sortie)
            except (ErreurLLM, ValidationError, ValueError, OutilRefuse) as e:
                self.journal.ecrire("erreur_sortie", self.nom, essai=essai, erreur=f"{type(e).__name__}: {str(e)[:300]}")
                continue
            self.journal.ecrire("decision", self.nom, source="llm", sortie=sortie.model_dump())
            return sortie, "llm"
        sortie = self.repli(etat, obs)
        self.journal.ecrire("decision", self.nom, source="repli", sortie=sortie.model_dump())
        return sortie, "repli"
