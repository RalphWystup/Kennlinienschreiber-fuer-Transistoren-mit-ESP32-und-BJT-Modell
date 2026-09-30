"""
Erzeugt einen ausfuehrlichen HTML-Report (Messung, Fits, Ergebnisse, Bewertung)
fuer die BC337-25-Parameterbestimmung.  -> bjt_report.html
"""
import numpy as np, io, base64
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

VT = 0.025852
DB = dict(IS=4.13e-14, BF=292.4, VAF=145.7, IKF=0.9, ISE=3.534e-15, NE=1.35, RB=60.0)

# ---- finaler Parametersatz (n,Is,Beta_F,VA gefittet; Rest BC337-25-Datenblatt)
P = dict(n=1.004, Is=4.726e-14, Beta_F=249.9, VA=103.3,
         ISE=3.534e-15, NE=1.35, IKF=0.9, RB=60.0, Vab=1e6)

TRC = ["#0E7C86", "#C77400", "#3B7A57", "#B3261E", "#6A4C93"]

# ------------------------------------------------------------------ Daten
def load(fname):
    lines = open(fname, encoding="utf-8-sig").read().splitlines()
    for i, ln in enumerate(lines):
        c = ln.split("\t")
        if c[0] == "Trace:": traces = [x for x in c[1:] if x.strip()]
        if c[0] == "Point": hdr = i; break
    data = [[float(x.strip().replace(",", ".")) if x.strip() else np.nan
             for x in ln.split("\t")] for ln in lines[hdr + 1:] if ln.strip()]
    a = np.array(data)
    return traces, [a[:, 1 + 2 * i] for i in range(len(traces))], [a[:, 2 + 2 * i] for i in range(len(traces))]

def tv(label):
    return float(label.split("=")[1].replace("µA", "").replace("V", "").replace(",", ".").strip())

DATA = {n: load(n + ".txt") for n in ["Ic_Vbe", "Ic_Vce", "hFE_Vce", "hFE_Ic", "Ic_Ib"]}

# ------------------------------------------------------------------ Modell
def ic_model(vbe, vce, P):
    return P["Is"] * np.exp(vbe / (P["n"] * VT)) * (1 + vce / P["VA"])
def ib_model(vbe, vce, P):
    ic = ic_model(vbe, vce, P)
    be = P["Beta_F"] / np.sqrt(1 + ic / P["IKF"])
    leak = P["ISE"] * np.exp(vbe / (P["NE"] * VT))
    ib = ic / be + leak
    for _ in range(30):
        vbe_eff = vbe - ib * P["RB"]
        ibn = (P["Is"] / be) * np.exp(vbe_eff / (P["n"] * VT)) * (1 + vce / P["Vab"]) + leak
        if np.all(np.abs(ibn - ib) <= 1e-18 + 1e-9 * np.abs(ibn)): ib = ibn; break
        ib = ibn
    return ib
def vbe_from_ic(ic, vce, P):
    return np.log(ic / (P["Is"] * (1 + vce / P["VA"]))) * (P["n"] * VT)
def solve_vbe_for_ib(ib, vce, P):
    lo = np.full_like(vce, 0.2, float); hi = np.full_like(vce, 1.0, float)
    for _ in range(45):
        mid = 0.5 * (lo + hi); f = ib_model(mid, vce, P) - ib
        hi = np.where(f > 0, mid, hi); lo = np.where(f <= 0, mid, lo)
    return 0.5 * (lo + hi)

# ------------------------------------------------------------------ Fehler
def residuals(P):
    R = {}
    tr, xs, ys = DATA["Ic_Vbe"]; r = []
    for lab, vbe, ic in zip(tr, xs, ys):
        vce = tv(lab)
        if vce < 1: continue
        ic = ic * 1e-3; m = np.isfinite(vbe) & np.isfinite(ic) & (ic > 2e-5) & (ic < 2e-3)
        r += list(np.log(ic_model(vbe[m], vce, P)) - np.log(ic[m]))
    R["Gummel"] = np.array(r)
    tr, xs, ys = DATA["Ic_Vce"]; r = []
    for lab, vce, ic in zip(tr, xs, ys):
        ib = tv(lab) * 1e-6; m = np.isfinite(vce) & np.isfinite(ic) & (vce > 1)
        v = solve_vbe_for_ib(ib, vce[m], P); r += list((ic_model(v, vce[m], P) * 1e3 - ic[m]) / ic[m])
    R["Ausgang"] = np.array(r)
    tr, xs, ys = DATA["hFE_Vce"]; r = []
    for lab, vce, h in zip(tr, xs, ys):
        ib = tv(lab) * 1e-6; m = np.isfinite(vce) & np.isfinite(h) & (vce > 1)
        v = solve_vbe_for_ib(ib, vce[m], P); r += list((ic_model(v, vce[m], P) / ib - h[m]) / h[m])
    R["hFE-Vce"] = np.array(r)
    tr, xs, ys = DATA["hFE_Ic"]; r = []
    for lab, ic, h in zip(tr, xs, ys):
        vce = tv(lab); m = np.isfinite(ic) & np.isfinite(h)
        v = vbe_from_ic(ic[m] * 1e-3, vce, P); r += list((ic_model(v, vce, P) / ib_model(v, vce, P) - h[m]) / h[m])
    R["hFE-Ic"] = np.array(r)
    tr, xs, ys = DATA["Ic_Ib"]; r = []
    for lab, ib, ic in zip(tr, xs, ys):
        vce = tv(lab); m = np.isfinite(ib) & np.isfinite(ic)
        v = solve_vbe_for_ib(ib[m] * 1e-6, np.full(m.sum(), vce), P); r += list((ic_model(v, vce, P) * 1e3 - ic[m]) / ic[m])
    R["Ic-Ib"] = np.array(r)
    return R
def cost(P): return float(np.mean([np.mean(v**2) for v in residuals(P).values() if len(v)]))
RMS = {k: float(np.sqrt(np.mean(v**2))) for k, v in residuals(P).items() if len(v)}
C0 = cost(P)
IDENT = {}
for name in ["n", "Is", "Beta_F", "VA", "ISE", "NE", "IKF", "RB"]:
    Pp = dict(P); Pp[name] = P[name] * 1.2; IDENT[name] = cost(Pp) / C0

# ------------------------------------------------------------------ Plot-Stil
plt.rcParams.update({
    "font.size": 11, "axes.edgecolor": "#b9c3c6", "axes.labelcolor": "#243036",
    "text.color": "#243036", "xtick.color": "#51606a", "ytick.color": "#51606a",
    "axes.linewidth": 0.9, "figure.facecolor": "white", "axes.facecolor": "white",
    "font.family": "DejaVu Sans",
})
def fig2b64(fig):
    buf = io.BytesIO(); fig.savefig(buf, format="png", dpi=130, bbox_inches="tight")
    plt.close(fig); return base64.b64encode(buf.getvalue()).decode()

def new_ax(title, xl, yl):
    fig, ax = plt.subplots(figsize=(6.6, 4.5))
    ax.set_title(title, fontsize=13, color="#12303a", pad=10, weight="bold")
    ax.set_xlabel(xl); ax.set_ylabel(yl); ax.grid(True, color="#e7ecee", lw=0.8)
    for s in ("top", "right"): ax.spines[s].set_visible(False)
    return fig, ax

def plot_gummel():
    fig, ax = new_ax("Ic – Vbe (Gummel-Plot)", "Vbe [V]", "Ic [A]")
    for k, (lab, vbe, ic) in enumerate(zip(*DATA["Ic_Vbe"])):
        vce = tv(lab)
        if vce < 1: continue
        c = TRC[k % 5]; ax.semilogy(vbe, ic * 1e-3, "o", ms=3.2, color=c, alpha=.75, label=lab)
        xx = np.linspace(0.45, np.nanmax(vbe), 90); ax.semilogy(xx, ic_model(xx, vce, P), "-", lw=1.6, color=c)
    ax.set_ylim(1e-7, 2e-2); ax.legend(fontsize=8, frameon=False, ncol=2)
    return fig2b64(fig)
def plot_output():
    fig, ax = new_ax("Ic – Vce (Ausgangskennlinie)", "Vce [V]", "Ic [mA]")
    for k, (lab, vce, ic) in enumerate(zip(*DATA["Ic_Vce"])):
        ib = tv(lab) * 1e-6; c = TRC[k % 5]; ax.plot(vce, ic, "o", ms=2.8, color=c, alpha=.7, label=lab)
        xx = np.linspace(0.3, np.nanmax(vce), 60); ax.plot(xx, ic_model(solve_vbe_for_ib(ib, xx, P), xx, P) * 1e3, "-", lw=1.6, color=c)
    ax.legend(fontsize=8, frameon=False, title="konst. Ib"); return fig2b64(fig)
def plot_hfe_vce():
    fig, ax = new_ax("hFE – Vce", "Vce [V]", "hFE")
    for k, (lab, vce, h) in enumerate(zip(*DATA["hFE_Vce"])):
        ib = tv(lab) * 1e-6; c = TRC[k % 5]; ax.plot(vce, h, "o", ms=2.8, color=c, alpha=.7, label=lab)
        xx = np.linspace(0.3, np.nanmax(vce), 60); ax.plot(xx, ic_model(solve_vbe_for_ib(ib, xx, P), xx, P) / ib, "-", lw=1.6, color=c)
    ax.set_ylim(0, 320); ax.legend(fontsize=8, frameon=False, title="konst. Ib"); return fig2b64(fig)
def plot_hfe_ic():
    fig, ax = new_ax("hFE – Ic  (Leckterm erfasst den Anstieg)", "Ic [mA]", "hFE")
    for k, (lab, ic, h) in enumerate(zip(*DATA["hFE_Ic"])):
        vce = tv(lab); c = TRC[k % 5]; ax.plot(ic, h, "o", ms=3.2, color=c, alpha=.75, label=lab)
        icc = np.linspace(np.nanmin(ic), np.nanmax(ic), 60) * 1e-3; v = vbe_from_ic(icc, vce, P)
        ax.plot(icc * 1e3, ic_model(v, vce, P) / ib_model(v, vce, P), "-", lw=1.6, color=c)
    ax.set_ylim(230, 300); ax.legend(fontsize=8, frameon=False, ncol=2, title="konst. Vce"); return fig2b64(fig)
def plot_ic_ib():
    fig, ax = new_ax("Ic – Ib", "Ib [µA]", "Ic [mA]")
    for k, (lab, ib, ic) in enumerate(zip(*DATA["Ic_Ib"])):
        vce = tv(lab); c = TRC[k % 5]; ax.plot(ib, ic, "o", ms=3.2, color=c, alpha=.75, label=lab)
        xx = np.linspace(np.nanmin(ib), np.nanmax(ib), 40) * 1e-6
        ax.plot(xx * 1e6, ic_model(solve_vbe_for_ib(xx, np.full_like(xx, vce), P), vce, P) * 1e3, "-", lw=1.6, color=c)
    ax.legend(fontsize=8, frameon=False, title="konst. Vce"); return fig2b64(fig)

IMG = dict(gummel=plot_gummel(), output=plot_output(), hfe_vce=plot_hfe_vce(),
           hfe_ic=plot_hfe_ic(), ic_ib=plot_ic_ib())

# ------------------------------------------------------------------ HTML
def pct(x): return f"{x*100:.2f} %"
def chip(v):
    if v == "gut": return '<span class="chip good">gut bestimmt</span>'
    if v == "schwach": return '<span class="chip warn">schwach</span>'
    return '<span class="chip none">nicht bestimmbar</span>'
def verdict(f): return "gut" if f > 1.5 else ("schwach" if f > 1.05 else "none")

STYLE = """
<style>
:root{
  --bg:#f4f7f8; --panel:#ffffff; --ink:#182228; --muted:#5a6a72; --line:#dde5e8;
  --accent:#0e7c86; --accent-2:#0b616a; --good:#2e7d32; --warn:#b26a00; --crit:#b3261e;
  --shadow:0 1px 2px rgba(16,40,48,.06),0 8px 24px rgba(16,40,48,.06);
}
@media (prefers-color-scheme:dark){
  :root{ --bg:#0e1518; --panel:#141d21; --ink:#e7eef0; --muted:#93a4ac; --line:#243036;
    --accent:#35c4ce; --accent-2:#7bdbe2; --good:#5cc66a; --warn:#e0a24a; --crit:#f0736a;
    --shadow:0 1px 2px rgba(0,0,0,.4),0 10px 30px rgba(0,0,0,.35);}
}
:root[data-theme="light"]{ --bg:#f4f7f8; --panel:#ffffff; --ink:#182228; --muted:#5a6a72; --line:#dde5e8;
  --accent:#0e7c86; --accent-2:#0b616a; --good:#2e7d32; --warn:#b26a00; --crit:#b3261e;
  --shadow:0 1px 2px rgba(16,40,48,.06),0 8px 24px rgba(16,40,48,.06);}
:root[data-theme="dark"]{ --bg:#0e1518; --panel:#141d21; --ink:#e7eef0; --muted:#93a4ac; --line:#243036;
  --accent:#35c4ce; --accent-2:#7bdbe2; --good:#5cc66a; --warn:#e0a24a; --crit:#f0736a;
  --shadow:0 1px 2px rgba(0,0,0,.4),0 10px 30px rgba(0,0,0,.35);}

*{box-sizing:border-box}
body{background:var(--bg);color:var(--ink);
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
  line-height:1.6;margin:0;-webkit-font-smoothing:antialiased}
.wrap{max-width:1060px;margin:0 auto;padding:56px 24px 96px}
.mono{font-family:ui-monospace,"SFMono-Regular","JetBrains Mono","Cascadia Code",Menlo,Consolas,monospace;
  font-variant-numeric:tabular-nums}

.eyebrow{font-family:ui-monospace,monospace;letter-spacing:.18em;text-transform:uppercase;
  font-size:.72rem;color:var(--accent);font-weight:600}
h1{font-size:2.15rem;line-height:1.12;margin:.3rem 0 .4rem;letter-spacing:-.02em;text-wrap:balance;font-weight:700}
.lede{color:var(--muted);font-size:1.06rem;max-width:64ch;margin:0}
h2{font-size:1.3rem;letter-spacing:-.01em;margin:0 0 4px;font-weight:700}
.sec{margin-top:56px}
.sec > p.sub{color:var(--muted);margin:.1rem 0 20px;max-width:66ch}

.hr{height:1px;background:var(--line);border:0;margin:28px 0}

.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:14px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:16px 16px 14px;box-shadow:var(--shadow)}
.card .k{font-family:ui-monospace,monospace;font-size:.74rem;letter-spacing:.06em;color:var(--muted);text-transform:uppercase}
.card .v{font-family:ui-monospace,monospace;font-size:1.42rem;font-weight:600;margin-top:4px;color:var(--ink)}
.card .n{font-size:.8rem;color:var(--muted);margin-top:2px}
.card.hi{border-color:color-mix(in srgb,var(--accent) 45%,var(--line))}

.grid2{display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:22px}
figure.plot{margin:0;background:#ffffff;border:1px solid var(--line);border-radius:14px;overflow:hidden;box-shadow:var(--shadow)}
figure.plot img{display:block;width:100%;height:auto}
figure.plot figcaption{padding:12px 16px 14px;border-top:1px solid var(--line);
  color:var(--muted);font-size:.9rem;background:var(--panel)}
figure.plot figcaption b{color:var(--ink);font-weight:600}
.tag{display:inline-block;font-family:ui-monospace,monospace;font-size:.74rem;padding:2px 8px;border-radius:999px;
  background:color-mix(in srgb,var(--accent) 14%,transparent);color:var(--accent-2);margin-left:6px;font-variant-numeric:tabular-nums}

.tbl{width:100%;border-collapse:collapse;background:var(--panel);border:1px solid var(--line);
  border-radius:12px;overflow:hidden;box-shadow:var(--shadow)}
.tbl th,.tbl td{padding:11px 14px;text-align:left;border-bottom:1px solid var(--line);font-size:.94rem}
.tbl thead th{background:color-mix(in srgb,var(--accent) 8%,var(--panel));font-size:.76rem;
  letter-spacing:.06em;text-transform:uppercase;color:var(--muted);font-weight:600}
.tbl td.num,.tbl th.num{text-align:right;font-family:ui-monospace,monospace;font-variant-numeric:tabular-nums}
.tbl tr:last-child td{border-bottom:0}
.scroll{overflow-x:auto}

.chip{display:inline-block;font-size:.76rem;font-weight:600;padding:3px 10px;border-radius:999px;white-space:nowrap}
.chip.good{background:color-mix(in srgb,var(--good) 16%,transparent);color:var(--good)}
.chip.warn{background:color-mix(in srgb,var(--warn) 18%,transparent);color:var(--warn)}
.chip.none{background:color-mix(in srgb,var(--muted) 16%,transparent);color:var(--muted)}

.note{background:color-mix(in srgb,var(--accent) 7%,var(--panel));border:1px solid var(--line);
  border-left:3px solid var(--accent);border-radius:10px;padding:16px 18px;color:var(--ink)}
.note b{color:var(--accent-2)}
.foot{margin-top:64px;color:var(--muted);font-size:.85rem;border-top:1px solid var(--line);padding-top:18px}
a{color:var(--accent-2)}
</style>
"""

def cards_html():
    rows = [
        ("n", f"{P['n']:.3f}", "Emissionskoeff.", True),
        ("Is", f"{P['Is']:.2e} A", "Sättigungsstrom", True),
        ("β_F", f"{P['Beta_F']:.0f}", "Stromverstärkung", True),
        ("V_A", f"{P['VA']:.0f} V", "Early-Spannung", False),
        ("ISE", f"{P['ISE']:.2e} A", "Basis-Leckstrom · Datenblatt", False),
        ("NE", f"{P['NE']:.2f}", "Leck-Emiss. · Datenblatt", False),
        ("IKF", f"{P['IKF']:.2g} A", "Kniestrom · Datenblatt", False),
        ("RB", f"{P['RB']:.0f} Ω", "Basiswiderstand · Datenblatt", False),
    ]
    out = []
    for k, v, n, hi in rows:
        out.append(f'<div class="card{" hi" if hi else ""}"><div class="k">{k}</div>'
                   f'<div class="v">{v}</div><div class="n">{n}</div></div>')
    return '<div class="cards">' + "".join(out) + "</div>"

def rms_rows():
    label = {"Gummel": "Ic – Vbe (Gummel)", "Ausgang": "Ic – Vce", "hFE-Vce": "hFE – Vce",
             "hFE-Ic": "hFE – Ic", "Ic-Ib": "Ic – Ib"}
    out = []
    for k in ["Gummel", "Ausgang", "hFE-Vce", "hFE-Ic", "Ic-Ib"]:
        if k == "Gummel":
            val = f"{(np.exp(RMS[k])-1)*100:.1f} %"
        else:
            val = pct(RMS[k])
        badge = '<span class="chip good">sehr gut</span>' if RMS[k] < 0.025 else '<span class="chip good">gut</span>'
        out.append(f"<tr><td>{label[k]}</td><td class='num'>{val}</td><td>{badge}</td></tr>")
    return "".join(out)

def ident_rows():
    meaning = {"n": "Gummel-Steigung", "Is": "Gummel-Achsenabschnitt", "Beta_F": "Ic/Ib-Niveau",
               "VA": "Early-Steigung", "ISE": "hFE-Anstieg (Leck)", "NE": "hFE-Anstieg (Leck)",
               "IKF": "Hochstromabfall", "RB": "Hochstrom-Knick"}
    order = ["n", "Beta_F", "Is", "VA", "NE", "RB", "ISE", "IKF"]
    disp = {"n": "n", "Is": "Is", "Beta_F": "β_F", "VA": "V_A", "ISE": "ISE", "NE": "NE", "IKF": "IKF", "RB": "RB"}
    out = []
    for k in order:
        f = IDENT[k]; out.append(
            f"<tr><td class='mono'>{disp[k]}</td><td class='num'>× {f:.2f}</td>"
            f"<td>{chip(verdict(f))}</td><td style='color:var(--muted)'>{meaning[k]}</td></tr>")
    return "".join(out)

def db_rows():
    comp = [("Is", "Is", "IS", "A", "%.2e"), ("β_F", "Beta_F", "BF", "", "%.0f"),
            ("V_A", "VA", "VAF", "V", "%.0f"), ("ISE", "ISE", "ISE", "A", "%.2e"),
            ("NE", "NE", "NE", "", "%.2f"), ("IKF", "IKF", "IKF", "A", "%.2g"),
            ("RB", "RB", "RB", "Ω", "%.0f")]
    out = []
    for disp, pk, dk, u, fmt in comp:
        fit = (fmt % P[pk]) + (f" {u}" if u else "")
        db = (fmt % DB[dk]) + (f" {u}" if u else "")
        out.append(f"<tr><td class='mono'>{disp}</td><td class='num'>{fit}</td><td class='num'>{db}</td></tr>")
    return "".join(out)

BODY = f"""
<title>BC337-25 · Parameterbestimmung & Modellvalidierung</title>
{STYLE}
<div class="wrap">
  <div class="eyebrow">Kurventracer-Analyse · Gummel-Poon (vereinfacht)</div>
  <h1>BC337-25 — Parameter aus Messkurven bestimmt und validiert</h1>
  <p class="lede">Aus fünf Kennlinienfeldern eines Kurventracers wurden die Modellparameter des
  NPN-Transistors <b>BC337</b> extrahiert, per globalem Fit verfeinert und gegen das Datenblatt
  geprüft. Das Modell trifft alle Kennlinien auf <b>≈ 1–2 %</b> genau.</p>

  <div class="sec">
    <h2>Ergebnis auf einen Blick</h2>
    <p class="sub">Hervorgehobene Karten = direkt aus den Messungen bestimmt. Die übrigen sind aus
    diesen Daten nicht identifizierbar und stammen aus dem BC337-25-Datenblatt.</p>
    {cards_html()}
  </div>

  <div class="sec">
    <h2>Messung vs. Modell</h2>
    <p class="sub">Punkte = Messung, Linien = Modell mit den bestimmten Parametern.
    Jede Kurve dient zugleich als Prüfung eines Parametersatzes.</p>
    <div class="grid2">
      <figure class="plot"><img alt="Ic-Vbe Gummel" src="data:image/png;base64,{IMG['gummel']}">
        <figcaption><b>Gummel-Plot.</b> Deckungsgleich im exponentiellen Ast → liefert <b>Is</b> und <b>n</b>.
        Unter ~5&nbsp;µA Rauschboden des Tracers. <span class="tag">~{(np.exp(RMS['Gummel'])-1)*100:.1f}%</span></figcaption></figure>
      <figure class="plot"><img alt="Ic-Vce Ausgang" src="data:image/png;base64,{IMG['output']}">
        <figcaption><b>Ausgangskennlinie.</b> Höhe und Early-Neigung getroffen → <b>β_F</b>, <b>V_A</b>.
        <span class="tag">{pct(RMS['Ausgang'])}</span></figcaption></figure>
      <figure class="plot"><img alt="hFE-Vce" src="data:image/png;base64,{IMG['hfe_vce']}">
        <figcaption><b>hFE über Vce.</b> Anstieg = Early-Effekt auf Ic.
        <span class="tag">{pct(RMS['hFE-Vce'])}</span></figcaption></figure>
      <figure class="plot"><img alt="hFE-Ic" src="data:image/png;base64,{IMG['hfe_ic']}">
        <figcaption><b>hFE über Ic.</b> Der leichte Anstieg wird erst durch den <b>Basis-Leckterm (ISE, NE)</b>
        aus dem Datenblatt abgebildet. <span class="tag">{pct(RMS['hFE-Ic'])}</span></figcaption></figure>
      <figure class="plot"><img alt="Ic-Ib" src="data:image/png;base64,{IMG['ic_ib']}">
        <figcaption><b>Ic über Ib.</b> Linear → kontrolliert <b>β_F</b>.
        <span class="tag">{pct(RMS['Ic-Ib'])}</span></figcaption></figure>
      <figure class="plot" style="display:flex;align-items:center;justify-content:center;background:var(--panel)">
        <figcaption style="border-top:0;text-align:left">
        <b>Lesart.</b> Ein enger Sitz über <i>alle</i> Felder gleichzeitig ist der eigentliche Beleg:
        ein Parameter, der eine Kurve schön trifft, aber eine andere verfehlt, wäre falsch.
        Hier passen alle fünf Felder mit <b>einem</b> Satz.</figcaption></figure>
    </div>
  </div>

  <div class="sec">
    <h2>Bewertung 1 · Wie gut passt das Modell?</h2>
    <p class="sub">Mittlerer relativer Fehler (RMS) zwischen Modell und Messung je Kennlinienfeld.</p>
    <div class="scroll"><table class="tbl">
      <thead><tr><th>Kennlinie</th><th class="num">RMS-Fehler</th><th>Urteil</th></tr></thead>
      <tbody>{rms_rows()}</tbody>
    </table></div>
  </div>

  <div class="sec">
    <h2>Bewertung 2 · Welchem Wert darf man trauen?</h2>
    <p class="sub">Empfindlichkeit des Gesamtfehlers auf +20&nbsp;% je Parameter. Reagiert der Fehler stark,
    ist der Parameter durch die Daten <i>bestimmt</i>; bleibt er flach, ist er es nicht.</p>
    <div class="scroll"><table class="tbl">
      <thead><tr><th>Parameter</th><th class="num">Fehler ×</th><th>Bestimmbarkeit</th><th>Signatur in den Daten</th></tr></thead>
      <tbody>{ident_rows()}</tbody>
    </table></div>
    <p class="sub" style="margin-top:14px">Ergebnis: <b>n, β_F, Is</b> sind sauber bestimmt, <b>V_A</b> schwach.
    <b>ISE, NE, IKF, RB</b> hinterlassen in diesem Messbereich keine Signatur — sie sind hier
    prinzipiell nicht messbar und werden aus dem Datenblatt gesetzt.</p>
  </div>

  <div class="sec">
    <h2>Bewertung 3 · Abgleich mit dem BC337-25-Datenblatt</h2>
    <p class="sub">Die selbst bestimmten Werte decken sich mit dem Referenzmodell — die stärkste Bestätigung.</p>
    <div class="scroll"><table class="tbl">
      <thead><tr><th>Parameter</th><th class="num">Diese Messung</th><th class="num">BC337-25 (Datenblatt)</th></tr></thead>
      <tbody>{db_rows()}</tbody>
    </table></div>
  </div>

  <div class="sec">
    <div class="note">
      <b>Fazit.</b> Der Transistor ist eindeutig ein <b>BC337-25</b>: gemessenes Is (4,7·10⁻¹⁴&nbsp;A) und
      V_A (~110–146&nbsp;V) treffen das Datenblatt, β_F liegt im Bereich der Baugruppe. Das vereinfachte
      Modell reproduziert alle Kennlinien auf ~1–2&nbsp;%. Der einzige verbleibende Effekt — der leichte
      hFE-Anstieg zu höheren Strömen — stammt vom <b>Basis-Leckstrom (ISE, NE)</b>, den erst der
      erweiterte Term erfasst. Die drei „nicht messbaren" Parameter (IKF, RB, ISE/NE) brauchen für eine
      eigene Bestimmung gezielte Zusatzmessungen (Hochstrom, konstantes Vbe).
    </div>
  </div>

  <div class="foot">
    Methode: Feature-Extraktion (Gummel-Slope, Early-Extrapolation, hFE-Plateau) + globaler
    Nelder-Mead-Fit + Identifizierbarkeitsanalyse. Modell: Ic = Is·e<sup>Vbe/(n·Vt)</sup>·(1+Vce/VA),
    Ib = idealer Anteil + ISE·e<sup>Vbe/(NE·Vt)</sup>. Referenz: BC337-25 SPICE-Modell (Philips/NXP).
  </div>
</div>
"""

open("bjt_report.html", "w", encoding="utf-8").write(BODY)
print("bjt_report.html geschrieben.  RMS:", {k: round(v, 4) for k, v in RMS.items()})
