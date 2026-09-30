#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Erzeugt die eigenständige Browser-Seite zum Kennlinienschreiber.

Eine Regel: die Fassungsnummer steht nur in der Datei VERSION, alles andere wird daraus gebaut.
Die Seite ist offline lauffähig — kein Nachladen, keine Fremdbibliothek, Bilder als Daten-Adresse eingebettet.
Sie enthält: den simulierten Messplatz mit Kaskadenregelung und Registeranzeige, das Vierquadranten-Kennfeld
mit den gemessenen BC337-Punkten über der Simulation, die Kleinsignalrechnung (h-Parameter, Kettenmatrix,
Emitterschaltung) und die beiden Dokumente als Reiter.

Zugangsdaten kommen in dieser Arbeit nicht vor: die Firmware spricht Modbus über die serielle Schnittstelle,
es gibt weder Netznamen noch Kennwort. Die Ersetzungsliste `neutral()` bleibt trotzdem bestehen — sie ist die
Stelle, an der ein später hinzukommendes Kennwort durch eine gleich lange Folge „x" ersetzt würde.

  python3 erstelle_kennlinienschreiber_seite.py
"""
from __future__ import annotations

import base64
import io
import json
import re
from pathlib import Path

H = Path(__file__).resolve().parent
Q = H.parent
R = Q / "rechnung"
B = Q / "Bilder"
VERSION = (H / "VERSION").read_text(encoding="utf-8").strip()
DATUM = "30.09.2026"
NAMENSNENNUNG = "Prof. Dr.-Ing. Ralph Wystup M.Sc. — erstellt mit KI und Agent (Claude Code, Anthropic)"

# --------------------------------------------------------------------------- Neutralisierung
# Netznamen bleiben sprechende Platzhalter, Kennwörter werden durch gleich viele „x" ersetzt
# (Vorgabe des Verfassers vom 29.09.2026). In diesem Projekt greift nichts davon; die Liste ist leer,
# damit hier kein Geheimnis steht — die Ersetzungen selbst stehen in neutral_privat.json, falls es
# eines Tages welche gibt. Diese Datei wird nicht mitgeliefert.
def _liste() -> list[tuple[str, str]]:
    p = H / "neutral_privat.json"
    return [tuple(x) for x in json.loads(p.read_text(encoding="utf-8"))] if p.is_file() else []


def neutral(t: str) -> str:
    """Text für die Veröffentlichung säubern: Netzname → Platzhalter, Kennwort → gleich viele „x"."""
    for alt, neu in _liste():
        t = t.replace(alt, neu)
    t = re.sub(r'((?:WIFI|WLAN)_(?:PASSWORT|WORT|PASSWORD)\s*=\s*")([^"]*)(")',
               lambda m: m.group(1) + "x" * len(m.group(2)) + m.group(3), t)
    t = re.sub(r'((?:passwor[dt]|kennwort)\s*[:=]\s*")([^"]*)(")',
               lambda m: m.group(1) + "x" * len(m.group(2)) + m.group(3), t, flags=re.I)
    return t


# --------------------------------------------------------------------------- Messdaten einlesen
def lade(name: str) -> list[dict]:
    """Eine Ausgabedatei des Kurvenschreibers lesen: Kurvenname, x-Spalte, y-Spalte."""
    zeilen = (R / f"{name}.txt").read_text(encoding="utf-8-sig").splitlines()
    kopf, spuren = 0, []
    for i, z in enumerate(zeilen):
        c = z.split("\t")
        if c[0] == "Trace:":
            spuren = [x.strip() for x in c[1:] if x.strip()]
        if c[0] == "Point":
            kopf = i
            break
    werte = []
    for z in zeilen[kopf + 1:]:
        if not z.strip():
            continue
        werte.append([float(x.strip().replace(",", ".")) if x.strip() else None for x in z.split("\t")])
    aus = []
    for i, s in enumerate(spuren):
        x = [w[1 + 2 * i] if len(w) > 1 + 2 * i else None for w in werte]
        y = [w[2 + 2 * i] if len(w) > 2 + 2 * i else None for w in werte]
        paare = [(round(a, 6), round(b, 6)) for a, b in zip(x, y) if a is not None and b is not None]
        aus.append(dict(name=s, wert=float(re.sub(r"[^0-9.,-]", "", s.split("=")[1]).replace(",", ".")),
                        x=[p[0] for p in paare], y=[p[1] for p in paare]))
    return aus


# --------------------------------------------------------------------------- Bilder einbetten
def bild(name: str, breite: int = 1150, qualitaet: int = 80) -> str:
    """Bild verkleinern und als Daten-Adresse zurückgeben — die Seite bleibt eine einzige Datei."""
    from PIL import Image
    im = Image.open(B / name)
    if im.width > breite:
        im = im.resize((breite, max(1, round(im.height * breite / im.width))), Image.LANCZOS)
    puffer = io.BytesIO()
    if name.lower().endswith((".jpg", ".jpeg")):
        im.convert("RGB").save(puffer, "JPEG", quality=qualitaet, optimize=True)
        art = "image/jpeg"
    else:
        im.convert("RGB").quantize(colors=128, method=Image.MEDIANCUT).save(puffer, "PNG", optimize=True)
        art = "image/png"
    return f"data:{art};base64," + base64.b64encode(puffer.getvalue()).decode("ascii")


BILDER = ["uebersichtsplan_skizze.png", "schaltplan_cpu_adda.png", "schaltplan_ops.png",
          "platine_layout.png", "platine_foto.jpg", "vierpol_transistor.png",
          "ku611_q1_ic_uce.png", "ku611_q2_ic_ib.png", "ku611_q3_ube_ib.png", "ku611_q4.png",
          "trendows_q1_blatt.png", "matlab_curve_fitter.png",
          "bjt_extraction.png", "bjt_fit.png", "bjt_gesamt.png",
          "bjt_hparam.png", "bjt_4quadrant.png", "bjt_verstaerker.png"]


# --------------------------------------------------------------------------- Formelsatz
TEX = [
    (r"\\begin\{pmatrix\}", "⎡ "), (r"\\end\{pmatrix\}", " ⎤"),
    (r"\\\\", " ;  "), (r"&", "  "),
    (r"\\underbrace\{([^{}]*)\}_\{[^{}]*\}", r"\1"),
    (r"\\boxed\{", "▸ "), (r"\\left[.]", ""), (r"\\right\|", "|"), (r"\\left", ""), (r"\\right", ""),
    (r"\\mathrm\{([^{}]*)\}", r"\1"), (r"\\text\{([^{}]*)\}", r"\1"), (r"\\mathbf\{([^{}]*)\}", r"\1"),
    # Abstandsbefehle und das Komma-Paar zuerst: sonst stehen in den Zaehlern und Nennern
    # noch geschweifte Klammern, und die Bruchregel greift nicht.
    (r"\{,\}", ","), (r"\\quad", "   "), (r"\\qquad", "      "),
    (r"\\,", " "), (r"\\;", " "), (r"\\!", ""),
    (r"\\sum_\{([^{}]*)\}\^\{([^{}]*)\}", r"Σ[\1..\2] "),
    (r"\\lfloor", "⌊"), (r"\\rfloor", "⌋"),
    (r"\\partial", "∂"), (r"\\cdot", "·"), (r"\\times", "×"),
    (r"\\approx", "≈"), (r"\\le\b", "≤"), (r"\\ge\b", "≥"), (r"\\neq", "≠"),
    (r"\\parallel", "∥"), (r"\\Longrightarrow", "⟹"), (r"\\Rightarrow", "⟹"),
    (r"\\rightarrow", "→"), (r"\\pm", "±"), (r"\\infty", "∞"),
    (r"\\Omega", "Ω"), (r"\\mu", "µ"), (r"\\pi", "π"), (r"\\beta", "β"),
    (r"\\alpha", "α"), (r"\\delta", "δ"), (r"\\Delta", "Δ"),
    (r"\\overline\{([^{}]*)\}", "\\1\u0304"),
    (r"\\exp", "exp"), (r"\\ln\b", "ln"), (r"\\log(?![a-z])", "log"), (r"\\max(?![a-z])", "max"), (r"\\min(?![a-z])", "min"),
    (r"\\ldots", "…"), (r"\\dots", "…"), (r"\\cdots", "⋯"),
    (r"\\\|", "∥"),
]


# Bruch und Wurzel koennen eine Klammerebene enthalten (\frac{I_S}{\beta_{eff}});
# deshalb ein eigener Ausdruck mit einer Verschachtelungsstufe, mehrfach angewandt.
KLAMMER = r"(?:[^{}]|\{(?:[^{}]|\{[^{}]*\})*\})*"      # zwei Verschachtelungsstufen genuegen hier
FRAC = re.compile(r"\\frac\{(" + KLAMMER + r")\}\{(" + KLAMMER + r")\}")
WURZEL = re.compile(r"\\sqrt\{(" + KLAMMER + r")\}")
SUB = re.compile(r"_\{((?:[^{}]|\{[^{}]*\})*)\}")
SUP = re.compile(r"\^\{((?:[^{}]|\{[^{}]*\})*)\}")


def formel(t: str) -> str:
    """TeX auf den Vorrat beschränken, der in diesen beiden Dokumenten vorkommt, und in Unicode setzen."""
    t = t.replace(r"\_", "\u0001")          # geschuetzter Unterstrich (R_{B\_GND}) — kein Tiefstellungszeichen
    for a, b in TEX:
        t = re.sub(a, b, t)
    for _ in range(4):
        neu2 = FRAC.sub(r"(\1)/(\2)", WURZEL.sub(r"√(\1)", t))   # Wurzel zuerst: sie steckt in Bruechen
        if neu2 == t:
            break
        t = neu2
    t = t.replace("\\sqrt", "√")                        # Restfaelle ohne geschweifte Klammer
    for _ in range(3):                                   # Tief- und Hochstellung, eine Klammerebene tief
        t2 = SUP.sub(r"<sup>\1</sup>", SUB.sub(r"<sub>\1</sub>", t))
        if t2 == t:
            break
        t = t2
    t = re.sub(r"_([A-Za-z0-9πβµαδΔ])", r"<sub>\1</sub>", t)
    t = re.sub(r"\^([A-Za-z0-9])", r"<sup>\1</sup>", t)
    t = t.replace("{", "").replace("}", "").replace("\\", "").replace("\u0001", "_")
    return re.sub(r"[ \t]{2,}", "  ", t).strip()


def zeile(t: str) -> str:
    """Fließtext: Formeln, Fettdruck, Schreibmaschine, Anführungszeichen."""
    t = (t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))
    t = re.sub(r"`([^`]+)`", lambda m: "<code>" + m.group(1) + "</code>", t)
    t = re.sub(r"\$([^$]+)\$", lambda m: '<span class="f">' + formel(m.group(1)) + "</span>", t)
    t = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", t)
    return t


def markdown(t: str, bilder: dict) -> str:
    """Genügend Markdown für diese beiden Dokumente: Überschriften, Absätze, Listen, Tabellen, Bilder, Formeln."""
    t = re.sub(r"^---\n.*?\n---\n", "", t, flags=re.S)
    t = t.replace("\\newpage", "")
    aus, zeilen, i = [], t.split("\n"), 0
    while i < len(zeilen):
        z = zeilen[i]
        if z.startswith("$$"):                                   # abgesetzte Formel
            block = [z]
            # einzeilig, wenn die Zeile mit $$ anfaengt UND aufhoert; sonst bis zur Schlusszeile lesen
            if not (z.rstrip().endswith("$$") and len(z.strip()) > 4):
                while i + 1 < len(zeilen):
                    i += 1
                    block.append(zeilen[i])
                    if zeilen[i].rstrip().endswith("$$"):
                        break
            roh = " ".join(block).replace("$$", " ").strip()
            aus.append('<div class="fb">' + formel(roh) + "</div>")
        elif z.startswith("```"):                                 # Quelltextblock
            i += 1
            block = []
            while i < len(zeilen) and not zeilen[i].startswith("```"):
                block.append(zeilen[i])
                i += 1
            aus.append("<pre>" + "\n".join(block).replace("&", "&amp;").replace("<", "&lt;") + "</pre>")
        elif z.startswith("!["):                                  # Bild
            m = re.match(r"!\[(.*?)\]\((.*?)\)", z)
            if m:
                n = Path(m.group(2)).name
                if n in bilder:
                    aus.append(f'<figure><img src="{bilder[n]}" alt="{m.group(1)[:80]}">'
                               f'<figcaption>{zeile(m.group(1))}</figcaption></figure>')
        elif z.startswith("#"):                                   # Überschrift
            n = len(z) - len(z.lstrip("#"))
            aus.append(f"<h{min(n+1,5)}>{zeile(z.lstrip('# ').strip())}</h{min(n+1,5)}>")
        elif z.startswith("|"):                                   # Tabelle
            block = []
            while i < len(zeilen) and zeilen[i].startswith("|"):
                block.append(zeilen[i])
                i += 1
            i -= 1
            reihen = [[c.strip() for c in r.strip("|").split("|")] for r in block]
            reihen = [r for r in reihen if not all(set(c) <= set(":- ") for c in r)]
            if reihen:
                kopf = "".join(f"<th>{zeile(c)}</th>" for c in reihen[0])
                leib = "".join("<tr>" + "".join(f"<td>{zeile(c)}</td>" for c in r) + "</tr>" for r in reihen[1:])
                aus.append(f"<table><thead><tr>{kopf}</tr></thead><tbody>{leib}</tbody></table>")
        elif re.match(r"^\s*[*-]\s+", z) or re.match(r"^\s*\d+\.\s+", z):   # Liste
            art = "ol" if re.match(r"^\s*\d+\.\s+", z) else "ul"
            block = []
            while i < len(zeilen) and (re.match(r"^\s*[*-]\s+", zeilen[i]) or re.match(r"^\s*\d+\.\s+", zeilen[i])
                                       or (block and zeilen[i].startswith("  ") and zeilen[i].strip())):
                s = re.sub(r"^\s*(?:[*-]|\d+\.)\s+", "", zeilen[i])
                if re.match(r"^\s*(?:[*-]|\d+\.)\s+", zeilen[i]) or not block:
                    block.append(s)
                else:
                    block[-1] += " " + s.strip()
                i += 1
            i -= 1
            aus.append(f"<{art}>" + "".join(f"<li>{zeile(x)}</li>" for x in block) + f"</{art}>")
        elif z.strip():                                           # Absatz
            block = []
            while i < len(zeilen) and zeilen[i].strip() and not zeilen[i].startswith(("#", "|", "$$", "```", "![")) \
                    and not re.match(r"^\s*(?:[*-]|\d+\.)\s+", zeilen[i]):
                block.append(zeilen[i])
                i += 1
            i -= 1
            aus.append("<p>" + zeile(" ".join(block)) + "</p>")
        i += 1
    return "\n".join(aus)


# --------------------------------------------------------------------------- Seite bauen
def main() -> int:
    kenn = json.loads((R / "kennwerte.json").read_text(encoding="utf-8"))
    ger = json.loads((R / "geraet.json").read_text(encoding="utf-8"))
    daten = {n: lade(n) for n in ["Ic_Vce", "Ic_Ib", "Ic_Vbe"]}
    bilder = {n: bild(n) for n in BILDER}

    P = kenn["saetze"]["Fitsatz"]["P"]
    PV = kenn["saetze"]["Arbeitssatz"]["P"]
    stand = dict(
        VERSION=VERSION, DATUM=DATUM,
        P=P, PV=PV, VT=kenn["VT"], schaltung=kenn["schaltung"],
        geraet=ger,
        pruefwerte=dict(
            hparam=kenn["saetze"]["Fitsatz"]["hparam"],
            verstaerker={k: v for k, v in kenn["saetze"]["Fitsatz"]["verstaerker"].items()
                         if k not in ("A_T", "A_ges")},
            abweichung=kenn["saetze"]["Fitsatz"]["abweichung"],
        ),
    )

    doku = {
        "manuskript": markdown(neutral((Q / "MANUSKRIPT_Kennlinienschreiber.md").read_text(encoding="utf-8")), bilder),
        "anleitung": markdown(neutral((Q / "ANLEITUNG_Kennlinienschreiber.md").read_text(encoding="utf-8")), bilder),
    }

    html = (SEITE
            .replace("/*DATEN*/", json.dumps(daten, ensure_ascii=False, separators=(",", ":")))
            .replace("/*STAND*/", json.dumps(stand, ensure_ascii=False))
            .replace("<!--MANUSKRIPT-->", doku["manuskript"])
            .replace("<!--ANLEITUNG-->", doku["anleitung"])
            .replace("{{V}}", VERSION).replace("{{DATUM}}", DATUM).replace("{{NAME}}", NAMENSNENNUNG)
            .replace("{{BILD_UEBERSICHT}}", bilder["uebersichtsplan_skizze.png"])
            .replace("{{BILD_BLATT}}", bilder["trendows_q1_blatt.png"]))
    ziel = H / f"Kennlinienschreiber_{VERSION}.html"
    ziel.write_text(html, encoding="utf-8")
    print(f"{ziel.name}: {len(html)/1024:.0f} kB · Fassung {VERSION} · {DATUM}")
    return 0


SEITE = (H / "vorlage.html").read_text(encoding="utf-8")

if __name__ == "__main__":
    raise SystemExit(main())
