"""État partagé typé entre les agents, et modèles de sortie validés par Pydantic."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Procede = Literal["cesar", "affine", "vigenere", "autoclave", "substitution", "beaufort"]
Famille = Literal["monoalphabetique", "polyalphabetique"]


class AppelOutil(BaseModel):
    outil: str
    arguments: dict[str, int | str] = Field(default_factory=dict)


class SortieClassifieur(BaseModel):
    famille: Famille
    procedes: list[Procede] = Field(min_length=1, max_length=6)
    justification: str = Field(max_length=160)


class SortieCryptanalyste(BaseModel):
    appel: AppelOutil
    justification: str = Field(max_length=160)


class SortieLinguiste(BaseModel):
    plausible: bool
    justification: str = Field(max_length=160)


class SortiePedagogue(BaseModel):
    explication: str = Field(min_length=20, max_length=2500)


class Tentative(BaseModel):
    procede: str
    outil: str
    arguments: dict[str, int | str]
    cle: str | None
    score_moyen: float
    plausible: bool


class EtatPartage(BaseModel):
    """Seul objet que les agents lisent et écrivent, via l'orchestrateur."""

    identifiant: str
    chiffre_lettres: str                     # lettres A-Z uniquement ; jamais transmis via les arguments d'outils
    gabarit: str | None = None               # mise en forme d'origine (espaces, ponctuation) si disponible
    langue: str = "fr"
    famille: Famille | None = None
    procedes_proposes: list[str] = Field(default_factory=list)
    procedes_exclus: list[str] = Field(default_factory=list)
    tentatives: list[Tentative] = Field(default_factory=list)
    clair: str | None = None
    cle: str | None = None
    procede: str | None = None
    explication: str | None = None
    iterations: int = 0
    statut: Literal["en_cours", "succes", "echec", "abandon"] = "en_cours"
    motif: str | None = None
