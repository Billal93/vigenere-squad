"""Interface en ligne de commande : résoudre un chiffré, rejouer une trace, lancer l'évaluation."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import evaluation as ev
from .journal import lire_journal
from .llm import ClientOllama
from .orchestrateur import Orchestrateur


def _afficher_trace(evenements: list[dict]) -> None:
    for e in evenements:
        t = e["t"][11:23]
        agent = e.get("agent") or "-"
        corps = {k: v for k, v in e.items() if k not in ("t", "id", "type", "agent")}
        texte = json.dumps(corps, ensure_ascii=False)
        print(f"{t} {agent:<13} {e['type']:<20} {texte[:170]}")


def cmd_resoudre(args: argparse.Namespace) -> int:
    mods = ev.modeles_langue()
    cfg = ev.charger_config()
    client = None
    if args.modele != "aucun":
        m = cfg["modeles"][args.modele]
        client = ClientOllama(m["etiquette"], cfg["ollama"]["hote"], cfg["temperature"], args.graine, cfg["contexte"])
    texte = args.texte or sys.stdin.read()
    orch = Orchestrateur(client, mods[args.langue], Path(args.traces) if args.traces else None, graine=args.graine)
    etat = orch.resoudre(args.id, texte, args.langue)
    _afficher_trace(orch.dernier_journal.evenements)
    print(f"\nstatut={etat.statut} procédé={etat.procede} clé={etat.cle} itérations={etat.iterations}")
    print(f"clair : {etat.clair}")
    if etat.explication:
        print(f"explication : {etat.explication}")
    return 0 if etat.statut == "succes" else 1


def cmd_rejouer(args: argparse.Namespace) -> int:
    """Relit une trace JSONL ; avec --verifier, contrôle que chaque appel d'outil est dans la liste de son agent."""
    from .outils.registre import OUTILS_PAR_AGENT
    evs = lire_journal(Path(args.trace))
    _afficher_trace(evs)
    if args.verifier:
        hors = [e for e in evs if e["type"] == "outil_appel" and e["outil"] not in OUTILS_PAR_AGENT[e["agent"]]]
        print(f"\nappels d'outils hors liste fermée : {len(hors)} sur {sum(e['type'] == 'outil_appel' for e in evs)}")
        return 1 if hors else 0
    return 0


def cmd_evaluer(args: argparse.Namespace) -> int:
    brut, traces = ev.RESULTATS / "raw", ev.TRACES
    if args.what == "baseline":
        for v in args.variantes:
            r = ev.evaluer_sans_llm(v, brut / f"sans_llm_{v}.jsonl", args.limite)
            print(v, sum(x["exact"] for x in r), "/", len(r))
    elif args.what == "llm":
        ev.evaluer_llm(args.modele, args.repetitions, brut / f"llm_{args.modele}.jsonl", traces, args.limite, tranche=args.tranche)
    elif args.what == "kasiski":
        ev.experience_kasiski(brut / "kasiski.jsonl")
    elif args.what == "shannon":
        ev.experience_shannon(brut / "shannon.jsonl")
    elif args.what == "menaces":
        print(json.dumps(ev.experience_menaces_deterministes(brut / "menaces.json"), ensure_ascii=False))
    elif args.what == "exercices":
        ev.experience_exercices(brut / "exercices.jsonl")
    elif args.what == "injection":
        ev.experience_injection_llm(args.modele, args.repetitions, brut / f"injection_{args.modele}.jsonl")
    return 0


def cmd_exercice(args: argparse.Namespace) -> int:
    from .exercices import generer_exercice, verifier_corrige
    ex = generer_exercice(args.procede, ev.modeles_langue()["fr"], args.longueur, args.graine)
    print(f"Exercice ({ex['procede']}, {ex['longueur']} lettres) : {ex['enonce']['consigne']}")
    print()
    print(ex["enonce"]["chiffre"])
    if not args.sans_corrige:
        ecarts = verifier_corrige(ex)
        print()
        print(f"--- Corrigé (vérifié par les outils : {'oui' if not ecarts else 'NON ' + str(ecarts)}) ---")
        print(json.dumps(ex["corrige"], ensure_ascii=False, indent=1))
    return 0


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(prog="vsquad", description="Vigenère-Squad")
    sp = p.add_subparsers(dest="cmd", required=True)
    r = sp.add_parser("resoudre", help="casser un chiffré et afficher la trace")
    r.add_argument("texte", nargs="?")
    r.add_argument("--modele", default="aucun", choices=["aucun", "petit", "tres_petit"])
    r.add_argument("--langue", default="fr", choices=["fr", "en"])
    r.add_argument("--graine", type=int, default=42)
    r.add_argument("--id", default="manuel")
    r.add_argument("--traces", help="dossier où écrire la trace JSONL")
    r.set_defaults(f=cmd_resoudre)
    j = sp.add_parser("rejouer", help="relire une trace JSONL")
    j.add_argument("trace")
    j.add_argument("--verifier", action="store_true")
    j.set_defaults(f=cmd_rejouer)
    e = sp.add_parser("evaluer", help="lancer une partie de l'évaluation")
    e.add_argument("what", choices=["baseline", "llm", "kasiski", "shannon", "menaces", "injection", "exercices"])
    e.add_argument("--variantes", nargs="+", default=["base", "sans_espaces", "fautes5", "anglais"])
    e.add_argument("--modele", default="petit", choices=["petit", "tres_petit"])
    e.add_argument("--repetitions", type=int, default=3)
    e.add_argument("--limite", type=int)
    e.add_argument("--tranche", type=int, help="protocole réduit : un chiffré par procédé à cette longueur")
    e.set_defaults(f=cmd_evaluer)
    x = sp.add_parser("exercice", help="générer un exercice avec corrigé vérifié (Pédagogue)")
    x.add_argument("--procede", default="vigenere", choices=["cesar", "affine", "vigenere", "beaufort", "autoclave", "substitution"])
    x.add_argument("--longueur", type=int, default=300); x.add_argument("--graine", type=int, default=1)
    x.add_argument("--sans-corrige", action="store_true")
    x.set_defaults(f=cmd_exercice)
    args = p.parse_args(argv)
    return args.f(args)


if __name__ == "__main__":
    raise SystemExit(main())
