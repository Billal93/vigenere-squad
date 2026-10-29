"""Les quatre agents : Classifieur, Cryptanalyste, Linguiste, Pédagogue."""

from __future__ import annotations

from typing import Any

from ..etat import (AppelOutil, EtatPartage, SortieClassifieur, SortieCryptanalyste, SortieLinguiste,
                    SortiePedagogue)
from ..outils.chiffres import PROCEDES
from ..outils.registre import SEUIL_PLAUSIBLE
from .base import Agent

FAMILLE_DE = {"cesar": "monoalphabetique", "affine": "monoalphabetique", "substitution": "monoalphabetique",
              "vigenere": "polyalphabetique", "beaufort": "polyalphabetique", "autoclave": "polyalphabetique"}
# Ordre de repli : du moins coûteux au plus coûteux, famille par famille.
ORDRE_MONO = ["cesar", "affine", "substitution"]
ORDRE_POLY = ["vigenere", "beaufort", "autoclave"]


class Classifieur(Agent):
    nom = "classifieur"
    modele_sortie = SortieClassifieur
    max_jetons = 160

    def observer(self, etat: EtatPartage) -> dict[str, Any]:
        """Les deux outils du Classifieur sont lus avant la décision ; chaque appel est journalisé."""
        return {"ic": self.executeur.appeler("indice_coincidence"),
                "frequences": self.executeur.appeler("frequences")}

    def message_utilisateur(self, etat, obs):
        return (f"Procédés possibles : {', '.join(PROCEDES)}.\nProcédés déjà écartés : "
                f"{etat.procedes_exclus or 'aucun'}.\nIndice de coïncidence : {obs['ic']}\n"
                f"Lettres les plus fréquentes : {obs['frequences']}")

    def repli(self, etat, obs):
        mono = obs["ic"]["ic"] >= 0.85 * obs["ic"]["ic_langue"]
        ordre = ORDRE_MONO if mono else ORDRE_POLY
        return SortieClassifieur(famille="monoalphabetique" if mono else "polyalphabetique",
                                 procedes=[p for p in ordre if p not in etat.procedes_exclus] or ordre,
                                 justification="IC comparé à 85 % de celui de la langue (règle codée en dur).")

    def verifier(self, sortie):
        if any(FAMILLE_DE[p] != sortie.famille for p in sortie.procedes):
            raise ValueError("procédés incohérents avec la famille annoncée")


class Cryptanalyste(Agent):
    nom = "cryptanalyste"
    modele_sortie = SortieCryptanalyste
    max_jetons = 120

    def observer(self, etat: EtatPartage) -> dict[str, Any]:
        if etat.famille != "polyalphabetique":
            return {}
        return {"kasiski": self.executeur.appeler("kasiski"), "friedman": self.executeur.appeler("friedman"),
                "longueur_ic": self.executeur.appeler("longueur_ic")}

    def message_utilisateur(self, etat, obs):
        return (f"Famille : {etat.famille}. Procédés à essayer, par ordre : {etat.procedes_proposes}.\n"
                f"Procédés déjà écartés : {etat.procedes_exclus or 'aucun'}.\nObservations : {obs or 'aucune'}\n"
                f"Outils : {sorted(self.executeur.autorises)}")

    def _appel_pour(self, procede: str, obs: dict[str, Any]) -> AppelOutil:
        if procede == "cesar":
            return AppelOutil(outil="chi2_cesar")
        if procede == "affine":
            return AppelOutil(outil="force_brute_affine")
        if procede in ("vigenere", "beaufort"):
            return AppelOutil(outil=f"attaque_{procede}", arguments={"longueur": obs["longueur_ic"]["longueur_proposee"]})
        return AppelOutil(outil=f"attaque_{procede}")

    def repli(self, etat, obs):
        restants = [p for p in etat.procedes_proposes if p not in etat.procedes_exclus]
        procede = (restants or etat.procedes_proposes)[0]
        return SortieCryptanalyste(appel=self._appel_pour(procede, obs),
                                   justification=f"Premier procédé non écarté : {procede}.")

    def verifier(self, sortie):
        self.executeur.verifier_autorise(sortie.appel.outil)   # lève OutilRefuse si l'outil n'est pas dans la liste


class Linguiste(Agent):
    nom = "linguiste"
    modele_sortie = SortieLinguiste
    max_jetons = 100

    def observer(self, etat: EtatPartage, clair: str) -> dict[str, Any]:
        return {"score": self.executeur.appeler("score_quadrigrammes", {"texte": clair}), "extrait": clair[:100]}

    def message_utilisateur(self, etat, obs):
        return (f"Extrait du clair candidat : « {obs['extrait']} »\nScore moyen par quadrigramme : "
                f"{obs['score']['score_moyen']} (seuil de plausibilité {SEUIL_PLAUSIBLE}).")

    def repli(self, etat, obs):
        return SortieLinguiste(plausible=obs["score"]["plausible"],
                               justification="Score de quadrigrammes comparé au seuil.")


class Pedagogue(Agent):
    nom = "pedagogue"
    modele_sortie = SortiePedagogue
    max_jetons = 380

    def message_utilisateur(self, etat, obs):
        return (f"Procédé retrouvé : {etat.procede}. Clé : {etat.cle}. Étapes tentées : "
                f"{[(t.procede, t.plausible) for t in etat.tentatives]}.\nDébut du clair : {obs['extrait']}")

    def repli(self, etat, obs):
        return SortiePedagogue(explication=(
            f"Le texte a été chiffré avec le procédé « {etat.procede} ». L'analyse des fréquences et de "
            f"l'indice de coïncidence a permis de retrouver la clé « {etat.cle} », ce qui donne un texte "
            f"français lisible."))
