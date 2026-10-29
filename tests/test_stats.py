import math

from vigenere_squad.outils import chiffres as ch
from vigenere_squad.outils import stats

TEXTE = ch.normaliser(
    "Il etait une fois un petit village au bord de la mer ou chaque matin les pecheurs partaient "
    "avant le lever du soleil pour ramener des filets pleins de poissons argentes que les enfants "
    "attendaient sur la plage en jouant avec les galets blancs et les coquillages que la marée "
    "avait laisses pendant la nuit et le soir tout le monde se retrouvait autour du grand feu"
) * 3


def test_ic_texte_constant():
    assert stats.indice_coincidence("AAAA") == 1.0
    assert stats.indice_coincidence("A") == 0.0


def test_ic_texte_francais_proche_de_la_langue():
    assert 0.06 < stats.indice_coincidence(TEXTE) < 0.09


def test_ic_vigenere_plus_bas_que_clair():
    chiffre = ch.vigenere_chiffrer(TEXTE, "CLEFSECRETE")
    assert stats.indice_coincidence(chiffre) < stats.indice_coincidence(TEXTE) - 0.01


def test_frequences_somment_a_un():
    f = stats.frequences("ABBC")
    assert math.isclose(sum(f.values()), 1.0)
    assert f["B"] == 0.5


def test_chi2_francais_plus_petit_que_chiffre():
    assert stats.chi2(TEXTE) < stats.chi2(ch.cesar_chiffrer(TEXTE, 5))
    assert stats.chi2("") == float("inf")


def test_kasiski_trouve_la_longueur_de_cle():
    chiffre = ch.vigenere_chiffrer(TEXTE, "SOLEIL")
    assert stats.longueur_kasiski(chiffre) in (6, 3, 2)  # les diviseurs de 6 se répètent aussi
    scores = dict(stats.kasiski(chiffre))
    assert scores[6] >= scores[7]


def test_kasiski_sans_repetition():
    assert stats.longueur_kasiski("ABCDEFGHIJKLMNOPQRSTUVWXYZ") is None


def test_friedman_ordre_de_grandeur():
    chiffre = ch.vigenere_chiffrer(TEXTE, "SOLEILCOUCHANT")
    estimation = stats.friedman(chiffre)
    assert 3 < estimation < 40
    assert stats.friedman("AAAAAAAA") < 2


def test_friedman_denominateur_negatif_donne_infini():
    assert stats.friedman("ABCDEFGHIJKLMNOPQRSTUVWXYZ" * 2) == float("inf")


def test_longueur_par_ic():
    chiffre = ch.vigenere_chiffrer(TEXTE, "SOLEIL")
    assert stats.longueur_par_ic(chiffre) == 6
    # Texte non répété : un chiffrement monoalphabétique n'a pas de structure en colonnes.
    unique = ch.normaliser(
        "Un matin de printemps le vieux jardinier ouvrit la porte de la serre et constata que les "
        "orchidees avaient fleuri pendant la nuit ce qui le rendit si joyeux qu'il appela sa femme "
        "pour lui montrer les couleurs inattendues dont il avait si longtemps reve sans jamais oser "
        "esperer les voir un jour apparaitre ainsi devant ses yeux fatigues par tant d'annees de travail"
    )
    assert stats.longueur_par_ic(ch.cesar_chiffrer(unique, 4)) == 1
