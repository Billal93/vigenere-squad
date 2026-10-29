"""Démonstration locale (Gradio) : coller un chiffré, voir la trace des agents, le clair et l'explication.

Lancement : `uv run --extra demo vsquad-demo` puis ouvrir http://127.0.0.1:7860. Rien n'est envoyé hors de la machine ;
sans modèle choisi, c'est la version déterministe qui répond.
"""

from __future__ import annotations

import json

from . import evaluation as ev
from .llm import ClientOllama
from .orchestrateur import Orchestrateur
from .exercices import generer_exercice, verifier_corrige


def resoudre(texte: str, modele: str, langue: str):
    mods, cfg = ev.modeles_langue(), ev.charger_config()
    client = None
    if modele != "aucun":
        m = cfg["modeles"][modele]
        client = ClientOllama(m["etiquette"], cfg["ollama"]["hote"], cfg["temperature"], 43, cfg["contexte"])
    orch = Orchestrateur(client, mods[langue])
    etat = orch.resoudre("demo", texte, langue)
    trace = "\n".join(f"{e['t'][11:23]} {e.get('agent') or '-':<13} {e['type']:<18} "
                      f"{json.dumps({k: v for k, v in e.items() if k not in ('t', 'id', 'type', 'agent')}, ensure_ascii=False)[:140]}"
                      for e in orch.dernier_journal.evenements)
    return etat.statut, etat.procede or "", json.dumps(etat.cle, ensure_ascii=False), etat.clair or "", etat.explication or "", trace


def exercice(procede: str, graine: int):
    ex = generer_exercice(procede, ev.modeles_langue()["fr"], 300, int(graine))
    ecarts = verifier_corrige(ex)
    return ex["enonce"]["consigne"], ex["enonce"]["chiffre"], json.dumps(ex["corrige"], ensure_ascii=False, indent=1), \
        "corrigé vérifié par les outils" if not ecarts else f"ÉCARTS : {ecarts}"


def construire():
    import gradio as gr
    with gr.Blocks(title="Vigenère-Squad") as app:
        gr.Markdown("# Vigenère-Squad\nCryptanalyse de chiffrements classiques par quatre agents encadrés. Exécution locale.")
        with gr.Tab("Casser un chiffré"):
            texte = gr.Textbox(label="Texte chiffré", lines=6)
            with gr.Row():
                modele = gr.Dropdown(["aucun", "tres_petit", "petit"], value="aucun", label="Modèle (Ollama)")
                langue = gr.Dropdown(["fr", "en"], value="fr", label="Langue attendue")
            bouton = gr.Button("Résoudre")
            sorties = [gr.Textbox(label=n) for n in ("Statut", "Procédé", "Clé", "Texte clair", "Explication du Pédagogue", "Trace JSONL")]
            bouton.click(resoudre, [texte, modele, langue], sorties)
        with gr.Tab("Exercice du Pédagogue"):
            proc = gr.Dropdown(["cesar", "affine", "vigenere", "beaufort", "autoclave", "substitution"], value="vigenere", label="Procédé")
            graine = gr.Number(value=1, label="Graine", precision=0)
            b2 = gr.Button("Générer")
            o2 = [gr.Textbox(label=n) for n in ("Consigne", "Chiffré", "Corrigé", "Vérification")]
            b2.click(exercice, [proc, graine], o2)
    return app


def main() -> None:
    construire().launch(server_name="127.0.0.1", server_port=7860)


if __name__ == "__main__":
    main()
