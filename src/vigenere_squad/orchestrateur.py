"""Orchestrateur explicite : Classifieur, Cryptanalyste, Linguiste, puis Pédagogue.

Boucle de vérification : si le Linguiste juge le clair non plausible, le procédé est écarté et
le Classifieur est consulté de nouveau, dans la limite de `max_iterations`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from .agents.base import ErreurOutil, Executeur, OutilRefuse
from .agents.roles import Classifieur, Cryptanalyste, Linguiste, Pedagogue
from .corpus import remettre_en_forme
from .etat import EtatPartage, Tentative
from .journal import Journal
from .llm import ClientLLM
from .outils import chiffres as ch
from .outils.langue import ModeleQuadrigrammes
from .outils.registre import ContexteOutil

PROCEDE_DE_OUTIL = {"chi2_cesar": "cesar", "force_brute_affine": "affine"}


def _procede(outil: str) -> str:
    return PROCEDE_DE_OUTIL.get(outil) or outil.removeprefix("attaque_")


class Orchestrateur:
    def __init__(self, client: ClientLLM | None, modele: ModeleQuadrigrammes, dossier_traces: Path | None = None,
                 max_iterations: int = 4, delai_outil_s: float = 120.0, graine: int = 0,
                 pannes: Callable[[str], None] | None = None, avec_pedagogue: bool = True):
        self.client, self.modele, self.dossier_traces = client, modele, dossier_traces
        self.max_iterations, self.delai_outil_s, self.graine = max_iterations, delai_outil_s, graine
        self.pannes, self.avec_pedagogue = pannes, avec_pedagogue

    def resoudre(self, identifiant: str, chiffre_brut: str, langue: str = "fr") -> EtatPartage:
        lettres = ch.normaliser(chiffre_brut)
        nom_fichier = identifiant.replace("#", "_")
        journal = Journal(self.dossier_traces / f"{nom_fichier}.jsonl" if self.dossier_traces else None, identifiant)
        self.dernier_journal = journal
        etat = EtatPartage(identifiant=identifiant, chiffre_lettres=lettres, langue=langue,
                           gabarit=chiffre_brut if chiffre_brut != lettres else None)
        journal.ecrire("debut", "orchestrateur", longueur=len(lettres), langue=langue,
                       modele=self.client.etiquette if self.client else "sans_llm")
        try:
            self._boucle(etat, journal)
        except OutilRefuse as e:   # ne devrait pas arriver : les sorties sont vérifiées avant exécution
            etat.statut, etat.motif = "abandon", f"outil refusé : {e}"
        journal.ecrire("fin", "orchestrateur", statut=etat.statut, motif=etat.motif, procede=etat.procede,
                       iterations=etat.iterations)
        return etat

    def _executeur(self, agent: str, ctx: ContexteOutil, journal: Journal) -> Executeur:
        return Executeur(agent, ctx, journal, self.delai_outil_s, self.pannes)

    def _boucle(self, etat: EtatPartage, journal: Journal) -> None:
        ctx = ContexteOutil(etat.chiffre_lettres, self.modele, etat.langue, self.graine)
        agents = {nom: cls(self.client, self._executeur(nom, ctx, journal), journal) for nom, cls in (
            ("classifieur", Classifieur), ("cryptanalyste", Cryptanalyste), ("linguiste", Linguiste),
            ("pedagogue", Pedagogue))}
        for it in range(1, self.max_iterations + 1):
            etat.iterations = it
            try:
                self._iteration(etat, journal, agents)
            except ErreurOutil as e:
                journal.ecrire("reessai", "orchestrateur", erreur=str(e))
                try:
                    self._iteration(etat, journal, agents)
                except ErreurOutil as e2:
                    etat.statut, etat.motif = "abandon", f"outil en panne après réessai : {e2}"
                    return
            if etat.statut == "succes":
                break
        else:
            etat.statut, etat.motif = "echec", "aucune hypothèse plausible dans la limite d'itérations"
            meilleure = max(etat.tentatives, key=lambda t: t.score_moyen, default=None)
            etat.procede = meilleure.procede if meilleure else None
        if etat.statut == "succes" and self.avec_pedagogue:
            ped = agents["pedagogue"]
            sortie, _ = ped.decider(etat, {"extrait": (etat.clair or "")[:120]})
            etat.explication = sortie.explication

    def _iteration(self, etat: EtatPartage, journal: Journal, agents: dict) -> None:
        cl, cr, li = agents["classifieur"], agents["cryptanalyste"], agents["linguiste"]
        obs = cl.observer(etat)
        sortie_cl, _ = cl.decider(etat, obs)
        etat.famille = sortie_cl.famille
        propose = [p for p in sortie_cl.procedes if p not in etat.procedes_exclus]
        if not propose:
            propose = [p for p in cl.repli(etat, obs).procedes if p not in etat.procedes_exclus]
        if not propose:
            etat.statut, etat.motif = "echec", "tous les procédés de la famille sont écartés"
            return
        etat.procedes_proposes = propose

        obs_cr = cr.observer(etat)
        sortie_cr, _ = cr.decider(etat, obs_cr)
        appel = sortie_cr.appel
        resultat = cr.executeur.appeler(appel.outil, appel.arguments)
        procede = _procede(appel.outil)

        obs_li = li.observer(etat, resultat["clair"])
        sortie_li, source = li.decider(etat, obs_li)
        plausible = obs_li["score"]["plausible"]       # le code fait foi ; l'avis du modèle est journalisé
        if source == "llm" and sortie_li.plausible != plausible:
            journal.ecrire("desaccord_linguiste", "linguiste", avis_modele=sortie_li.plausible, score=plausible)
        etat.tentatives.append(Tentative(procede=procede, outil=appel.outil, arguments=appel.arguments,
                                         cle=resultat["cle"], score_moyen=resultat["score_moyen"],
                                         plausible=plausible))
        if plausible:
            etat.procede, etat.cle = procede, resultat["cle"]
            etat.clair = (remettre_en_forme(resultat["clair"], etat.gabarit)
                          if etat.gabarit else resultat["clair"])
            etat.statut = "succes"
        else:
            etat.procedes_exclus.append(procede)
            journal.ecrire("hypothese_ecartee", "orchestrateur", procede=procede, score=resultat["score_moyen"])
