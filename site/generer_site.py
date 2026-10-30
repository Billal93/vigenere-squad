"""Génère site/index.html à partir de results/metrics.json (aucune valeur saisie à la main).

Les figures de results/figures sont copiées dans site/figures. La page est publiée par GitHub Pages.
"""

from __future__ import annotations

import html
import json
import os
import shutil
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
RESULTATS = RACINE / os.environ.get("VSQUAD_RESULTATS", "results")
SITE = RACINE / ("site" if RESULTATS.name == "results" else RESULTATS.name + "_site")
PROCEDES = ["cesar", "affine", "vigenere", "autoclave", "substitution", "beaufort"]
NOMS = {"cesar": "César", "affine": "Affine", "vigenere": "Vigenère", "autoclave": "Autoclave",
        "substitution": "Substitution", "beaufort": "Beaufort"}


def f(x, nd=1) -> str:
    if x is None:
        return "—"
    return f"{x:.{nd}f}".replace(".", ",") if isinstance(x, float) else str(x)


def ms(d: dict) -> str:
    return f"{f(d['moyenne'])} ± {f(d['ecart_type'])}"


def tableau(entetes: list[str], lignes: list[list[str]]) -> str:
    h = "".join(f"<th>{html.escape(e)}</th>" for e in entetes)
    b = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in l) + "</tr>" for l in lignes)
    return f"<div class='tbl'><table><thead><tr>{h}</tr></thead><tbody>{b}</tbody></table></div>"


def section(titre: str, corps: str, cle: str) -> str:
    return f"<section id='{cle}'><h2>{html.escape(titre)}</h2>{corps}</section>"


def chiffre_cle(label: str, valeur: str, cle_json: str) -> str:
    return (f"<div class='kpi'><div class='v'>{valeur}</div><div class='l'>{html.escape(label)}</div>"
            f"<div class='k'>{html.escape(cle_json)}</div></div>")


def construire(m: dict, env: dict | None) -> str:
    sections, kpis = [], []
    sl = m.get("sans_llm")
    if sl:
        kpis.append(chiffre_cle("clair exact, tous procédés (référence sans modèle)", f(sl["taux_exact_global_pct"]) + " %",
                                "sans_llm.taux_exact_global_pct"))
        kpis.append(chiffre_cle("itérations moyennes", f(sl["iterations_moyennes"], 2), "sans_llm.iterations_moyennes"))
        kpis.append(chiffre_cle("temps moyen par chiffré", f(sl["temps_moyen_s_par_chiffre"], 2) + " s",
                                "sans_llm.temps_moyen_s_par_chiffre"))
        lignes = [[NOMS[p], f(sl["taux_exact_par_procede_pct"][p]) + " %", f(sl["longueur_min_succes_90_pct"][p]),
                   f(sl["iterations_moyennes_par_procede"][p], 2), f(sl["precision_lettres_moyenne_par_procede"][p] * 100) + " %"]
                  for p in PROCEDES]
        corps = tableau(["Procédé", "Clair exact", "Longueur min. pour 90 %", "Itérations", "Lettres justes"], lignes)
        corps += "<p class='fig'><img src='figures/succes_par_procede_et_longueur.png' alt='Taux de succès par procédé et longueur'></p>"
        sections.append(section("Résultats par procédé (sans modèle)", corps, "procedes"))
    rv = m.get("robustesse_variantes", {})
    if rv:
        lignes = [[html.escape(k), str(v["n"]), f(v["taux_exact_global_pct"]) + " %", f(v["famille_correcte_pct"]) + " %"]
                  for k, v in rv.items()]
        sections.append(section("Robustesse (rejeu sur variantes)",
                                "<p>La variante « sans espaces » donne les mêmes résultats que la base : le pipeline normalise le texte en "
                                "lettres avant toute analyse.</p>" + tableau(["Variante", "Chiffrés", "Clair exact", "Famille reconnue"], lignes), "robustesse"))
    ab = m.get("ablation", {})
    if ab:
        lignes = []
        for k, lab in (("sans_llm", "Sans modèle"), ("tres_petit", "qwen3:0.6b"), ("petit", "qwen3:4b")):
            if k in ab:
                d = ab[k]["taux_exact_pct"]
                lignes.append([lab, str(ab[k].get("n_chiffres", ab[k].get("chiffres_par_repetition", ""))), ms(d) + " %",
                               str(d["n"])])
        corps = tableau(["Configuration", "Chiffrés", "Clair exact (moy. ± éc.-type)", "Répétitions"], lignes)
        corps += "<p class='fig'><img src='figures/ablation.png' alt='Ablation'></p>"
        sections.append(section("Ablation : apport réel des agents", corps, "ablation"))
    ka = m.get("kasiski_contre_autoclave")
    if ka:
        lignes = [[NOMS[p], f(ka[p]["longueur_exacte_pct"]) + " %", f(ka[p]["longueur_juste_ou_diviseur_pct"]) + " %",
                   f(ka[p]["score_vrai_sur_score_max_moyen"], 2)] for p in ("vigenere", "autoclave")]
        corps = tableau(["Procédé", "Longueur exacte", "Exacte ou diviseur", "Score de la vraie longueur / score max"], lignes)
        corps += "<p class='fig'><img src='figures/kasiski_vs_autoclave.png' alt='Kasiski contre autoclave'></p>"
        sections.append(section("Kasiski contre autoclave", corps, "kasiski"))
    sh = m.get("shannon")
    if sh:
        lignes = [[k, f(sh["longueur_min_succes_90_par_cle"].get(k)), f(sh["distance_unicite_theorique_par_cle"][k])]
                  for k in sh["distance_unicite_theorique_par_cle"]]
        corps = (f"<p>Entropie conditionnelle d'ordre 3 : {f(sh['h_cond_ordre3_bits_par_lettre'], 3)} bit/lettre, redondance "
                 f"{f(sh['redondance_D_bits_par_lettre'], 3)} bit/lettre.</p>" +
                 tableau(["Longueur de clé", "Longueur min. mesurée (90 %)", "Distance d'unicité théorique"], lignes))
        corps += "<p class='fig'><img src='figures/shannon_longueur_minimale.png' alt='Figure de Shannon'></p>"
        sections.append(section("Figure de Shannon", corps, "shannon"))
    mn = m.get("menaces")
    if mn:
        dp = mn["donnees_empoisonnees_sans_controle_de_coherence"], mn["donnees_empoisonnees_avec_controle_de_coherence"]
        oh = mn["outil_hallucine"]
        lignes = [["Données d'outil empoisonnées, sans contrôle de cohérence", f"{dp[0]['faux_succes']} faux succès sur {dp[0]['essais']}"],
                  ["Données d'outil empoisonnées, avec contrôle de cohérence", f"{dp[1]['faux_succes']} faux succès sur {dp[1]['essais']}"],
                  ["Appels d'outils hallucinés refusés", f"{oh['appels_refuses']} refus, {oh['resolus_malgre_tout']} chiffrés résolus sur {oh['essais']}"]]
        for cle, lab in (("tres_petit", "qwen3:0.6b"), ("petit", "qwen3:4b")):
            inj = mn.get("injection_dans_le_clair", {}).get(cle)
            if inj:
                for mode, nom in (("sans_masquage", "sans masquage"), ("avec_masquage", "avec masquage")):
                    d = inj[mode]
                    lignes.append([f"Consigne cachée dans le clair, {lab}, {nom}",
                                   f"mot-piège dans les sorties : {f(d['canari_dans_les_sorties_des_agents_pct'])} % de {d['executions']} exécutions"])
        sections.append(section("Modèle de menace : contre-mesures évaluées", tableau(["Vecteur", "Résultat"], lignes), "menaces"))
    ex = m.get("exercices_pedagogue")
    if ex:
        sections.append(section("Exercices du Pédagogue", f"<p>{ex['generes']} exercices générés : {f(ex['publies_pct'])} % publiés, "
                                f"{f(ex['corriges_verifies_pct'])} % des corrigés vérifiés par les outils, "
                                f"{f(ex['rejets_moyens_avant_publication'], 2)} rejet en moyenne avant publication.</p>", "exercices"))
    pied = ""
    if env:
        pied = (f"<p class='meta'>Mesures effectuées sur {html.escape(env['systeme']['os'])}, {env['systeme']['coeurs_logiques']} cœurs, "
                f"{env['systeme']['ram_totale_go']} Go de RAM, sans GPU ; Python {html.escape(env['python'])} ; Ollama "
                f"{html.escape(str(env['ollama'].get('version')))} ; commit <code>{html.escape(str(env.get('commit'))[:10])}</code>.</p>")
    return PAGE.replace("{{KPIS}}", "".join(kpis)).replace("{{SECTIONS}}", "".join(sections)).replace("{{PIED}}", pied)


PAGE = """<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Vigenère-Squad : résultats</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Work+Sans:wght@400;500;600&display=swap" rel="stylesheet">
<style>
:root{--bg:#fafaf7;--fg:#1c1f24;--mu:#5d6470;--ac:#1b4f72;--li:#e4e2db;--card:#fff}
@media (prefers-color-scheme:dark){:root{--bg:#15171a;--fg:#e8e8e3;--mu:#9aa1ab;--ac:#7fb3d5;--li:#2c3036;--card:#1d2024}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.6 'Work Sans',system-ui,sans-serif}
main{max-width:920px;margin:0 auto;padding:40px 16px 64px}
h1{font-size:2rem;margin:0 0 4px;font-weight:600}h2{font-size:1.25rem;margin:40px 0 12px;font-weight:600;border-bottom:1px solid var(--li);padding-bottom:6px}
.sub{color:var(--mu);margin:0 0 28px}.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px;margin:24px 0}
.kpi{background:var(--card);border:1px solid var(--li);border-radius:8px;padding:14px 16px}.kpi .v{font-size:1.7rem;font-weight:600;color:var(--ac)}
.kpi .l{font-size:.9rem}.kpi .k{font-size:.75rem;color:var(--mu);font-family:ui-monospace,monospace;margin-top:4px}
.tbl{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:.93rem}th,td{text-align:left;padding:8px 10px;border-bottom:1px solid var(--li)}
th{font-weight:600;color:var(--mu);font-size:.82rem;text-transform:uppercase;letter-spacing:.03em}
.fig img{max-width:100%;height:auto;background:#fff;border-radius:6px;border:1px solid var(--li)}.meta{color:var(--mu);font-size:.85rem;margin-top:40px}
a{color:var(--ac)}code{font-family:ui-monospace,monospace;font-size:.9em}
</style></head><body><main>
<h1>Vigenère-Squad</h1>
<p class="sub">Cryptanalyse de chiffrements classiques par quatre agents encadrés. Cette page est générée par <code>site/generer_site.py</code> à partir de <code>results/metrics.json</code> ; chaque valeur y figure sous la clé indiquée.</p>
<div class="kpis">{{KPIS}}</div>
{{SECTIONS}}
{{PIED}}
<p class="meta"><a href="https://github.com/Billal93/vigenere-squad">Code source et données</a></p>
</main></body></html>
"""


def main() -> None:
    m = json.loads((RESULTATS / "metrics.json").read_text(encoding="utf-8"))
    env_chemin = RESULTATS / "ENVIRONMENT.json"
    env = json.loads(env_chemin.read_text(encoding="utf-8")) if env_chemin.exists() else None
    (SITE / "figures").mkdir(parents=True, exist_ok=True)
    for p in (RESULTATS / "figures").glob("*.png"):
        shutil.copy(p, SITE / "figures" / p.name)
    (SITE / "index.html").write_text(construire(m, env), encoding="utf-8", newline="\n")
    print(f"{SITE.name}/index.html écrit")


if __name__ == "__main__":
    main()
