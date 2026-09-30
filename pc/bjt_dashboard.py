"""
===========================================================================
 BJT-DASHBOARD (BC337-25)  -  ein Programm, das ALLES zeigt:
   Messungen + gefittete Kurven + Ergebnisse + Bewertung, in einem Fenster.
===========================================================================
 Ablauf:  Daten laden -> Parameter bestimmen (Extraktion + globaler Fit) ->
          Bewertung (RMS, Bestimmbarkeit, Datenblattvergleich) -> Dashboard.

 Nur numpy + matplotlib.   Aufruf:  python bjt_dashboard.py
"""
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import gridspec

VT = 0.025852
DB = dict(IS=4.13e-14, BF=292.4, VAF=145.7, IKF=0.9, ISE=3.534e-15, NE=1.35, RB=60.0)  # BC337-25
TRC = ["#0E7C86", "#C77400", "#3B7A57", "#B3261E", "#6A4C93"]
GOOD, WARN, NONE = "#2e7d32", "#b26a00", "#8a8f93"

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
    # I_B = (I_S/beta_eff) * exp(V_BE,eff/(n*V_T)) * (1 + V_CE/V_AB)   [deine Gleichung]
    ic = ic_model(vbe, vce, P); be = P["Beta_F"] / np.sqrt(1 + ic / P["IKF"])
    ib = ic / be
    for _ in range(30):
        ibn = (P["Is"] / be) * np.exp((vbe - ib * P["RB"]) / (P["n"] * VT)) * (1 + vce / P["Vab"])
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
    R["Ic-Vbe"] = np.array(r)
    tr, xs, ys = DATA["Ic_Vce"]; r = []
    for lab, vce, ic in zip(tr, xs, ys):
        ib = tv(lab) * 1e-6; m = np.isfinite(vce) & np.isfinite(ic) & (vce > 1)
        v = solve_vbe_for_ib(ib, vce[m], P); r += list((ic_model(v, vce[m], P) * 1e3 - ic[m]) / ic[m])
    R["Ic-Vce"] = np.array(r)
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

# ------------------------------------------------------------------ Extraktion + Fit
def extrahiere():
    tr, xs, ys = DATA["Ic_Vbe"]; ns = []
    for lab, vbe, ic in zip(tr, xs, ys):
        vce = tv(lab)
        if vce < 1: continue
        icA = ic * 1e-3; m = np.isfinite(vbe) & np.isfinite(icA) & (icA > 2e-5) & (icA < 2e-3)
        if m.sum() < 4: continue
        s, _ = np.polyfit(vbe[m], np.log(icA[m]), 1); ns.append(1 / (s * VT))
    n = float(np.mean(ns))
    tr2, xs2, ys2 = DATA["Ic_Vce"]; VAs = []
    for lab, vce, ic in zip(tr2, xs2, ys2):
        icA = ic * 1e-3; m = np.isfinite(vce) & np.isfinite(icA) & (vce >= 1.5)
        if m.sum() < 4: continue
        b, a = np.polyfit(vce[m], icA[m], 1); VAs.append(a / b)
    VA = float(np.mean(VAs)); lnIs = []
    for lab, vbe, ic in zip(tr, xs, ys):
        vce = tv(lab)
        if vce < 1: continue
        icA = ic * 1e-3; m = np.isfinite(vbe) & np.isfinite(icA) & (icA > 2e-5) & (icA < 2e-3)
        lnIs += list(np.log(icA[m] / (1 + vce / VA)) - vbe[m] / (n * VT))
    Is = float(np.exp(np.mean(lnIs)))
    hfe_max = max(np.nanmax(y) for y in DATA["hFE_Ic"][2])
    return n, Is, VA, hfe_max

def nelder_mead(f, x0, dx, iters=600):
    N = len(x0); sim = [np.array(x0, float)]
    for i in range(N):
        y = np.array(x0, float); y[i] += dx[i]; sim.append(y)
    fv = [f(p) for p in sim]
    for _ in range(iters):
        o = np.argsort(fv); sim = [sim[i] for i in o]; fv = [fv[i] for i in o]
        cen = np.mean(sim[:-1], 0); xr = cen + (cen - sim[-1]); fr = f(xr)
        if fv[0] <= fr < fv[-2]: sim[-1], fv[-1] = xr, fr
        elif fr < fv[0]:
            xe = cen + 2 * (cen - sim[-1]); fe = f(xe); sim[-1], fv[-1] = (xe, fe) if fe < fr else (xr, fr)
        else:
            xc = cen + 0.5 * (sim[-1] - cen); fc = f(xc)
            if fc < fv[-1]: sim[-1], fv[-1] = xc, fc
            else:
                for i in range(1, N + 1): sim[i] = sim[0] + 0.5 * (sim[i] - sim[0]); fv[i] = f(sim[i])
    o = int(np.argmin(fv)); return sim[o]

print("Bestimme Parameter (Extraktion + globaler Fit) ...")
n0, Is0, VA0, hfe_max = extrahiere()
FIX = dict(IKF=DB["IKF"], RB=DB["RB"], Vab=1e6)   # nur deine Gleichungen, kein Leckterm
def decode(t):
    Q = dict(n=t[0], Is=10**t[1], Beta_F=t[2], VA=t[3]); Q.update(FIX); return Q
def fc(t):
    Q = decode(t)
    if not (0.8 < Q["n"] < 1.6 and 50 < Q["Beta_F"] < 700 and 20 < Q["VA"] < 2000): return 1e9
    return cost(Q)
topt = nelder_mead(fc, [n0, np.log10(Is0), hfe_max, VA0], [0.02, 0.1, 15, 20], iters=600)
P = decode(topt)
RMS = {k: float(np.sqrt(np.mean(v**2))) for k, v in residuals(P).items() if len(v)}
C0 = cost(P)
IDENT = {}
for name in ["n", "Is", "Beta_F", "VA", "IKF", "RB"]:
    Q = dict(P); Q[name] = P[name] * 1.2; IDENT[name] = cost(Q) / C0

# ==================================================================== DASHBOARD
plt.rcParams.update({"font.size": 10, "axes.edgecolor": "#b9c3c6",
                     "axes.labelcolor": "#243036", "xtick.color": "#51606a",
                     "ytick.color": "#51606a", "font.family": "DejaVu Sans"})
fig = plt.figure(figsize=(17, 11))
fig.suptitle("BC337-25  ·  Parameterbestimmung aus Kurventracer-Messungen  —  Messung (Punkte) vs. Modell (Linien)",
             fontsize=15, weight="bold", color="#12303a", y=0.985)
gs = gridspec.GridSpec(3, 3, figure=fig, height_ratios=[1, 1, 0.92], hspace=0.42, wspace=0.26,
                       left=0.055, right=0.975, top=0.93, bottom=0.05)

def style(ax, title, xl, yl):
    ax.set_title(title, fontsize=11.5, color="#12303a", weight="bold", pad=8)
    ax.set_xlabel(xl); ax.set_ylabel(yl); ax.grid(True, color="#e7ecee", lw=0.8)
    for s in ("top", "right"): ax.spines[s].set_visible(False)

# (0,0) Gummel
ax = fig.add_subplot(gs[0, 0])
for k, (lab, vbe, ic) in enumerate(zip(*DATA["Ic_Vbe"])):
    vce = tv(lab)
    if vce < 1: continue
    ax.semilogy(vbe, ic * 1e-3, "o", ms=3, color=TRC[k % 5], alpha=.75, label=lab)
    xx = np.linspace(0.45, np.nanmax(vbe), 80); ax.semilogy(xx, ic_model(xx, vce, P), "-", lw=1.5, color=TRC[k % 5])
ax.set_ylim(1e-7, 2e-2); style(ax, "Ic – Vbe (Gummel)", "Vbe [V]", "Ic [A]"); ax.legend(fontsize=7, frameon=False, ncol=2)
# (0,1) Output
ax = fig.add_subplot(gs[0, 1])
for k, (lab, vce, ic) in enumerate(zip(*DATA["Ic_Vce"])):
    ib = tv(lab) * 1e-6; ax.plot(vce, ic, "o", ms=2.6, color=TRC[k % 5], alpha=.7, label=lab)
    xx = np.linspace(0.3, np.nanmax(vce), 60); ax.plot(xx, ic_model(solve_vbe_for_ib(ib, xx, P), xx, P) * 1e3, "-", lw=1.5, color=TRC[k % 5])
style(ax, "Ic – Vce (Ausgang)", "Vce [V]", "Ic [mA]"); ax.legend(fontsize=7, frameon=False, title="konst. Ib")
# (0,2) hFE-Vce
ax = fig.add_subplot(gs[0, 2])
for k, (lab, vce, h) in enumerate(zip(*DATA["hFE_Vce"])):
    ib = tv(lab) * 1e-6; ax.plot(vce, h, "o", ms=2.6, color=TRC[k % 5], alpha=.7, label=lab)
    xx = np.linspace(0.3, np.nanmax(vce), 60); ax.plot(xx, ic_model(solve_vbe_for_ib(ib, xx, P), xx, P) / ib, "-", lw=1.5, color=TRC[k % 5])
ax.set_ylim(0, 320); style(ax, "hFE – Vce", "Vce [V]", "hFE"); ax.legend(fontsize=7, frameon=False, title="konst. Ib")
# (1,0) hFE-Ic
ax = fig.add_subplot(gs[1, 0])
for k, (lab, ic, h) in enumerate(zip(*DATA["hFE_Ic"])):
    vce = tv(lab); ax.plot(ic, h, "o", ms=3, color=TRC[k % 5], alpha=.75, label=lab)
    icc = np.linspace(np.nanmin(ic), np.nanmax(ic), 60) * 1e-3; v = vbe_from_ic(icc, vce, P)
    ax.plot(icc * 1e3, ic_model(v, vce, P) / ib_model(v, vce, P), "-", lw=1.5, color=TRC[k % 5])
ax.set_ylim(235, 295); style(ax, "hFE – Ic  (Leckterm ISE/NE)", "Ic [mA]", "hFE"); ax.legend(fontsize=7, frameon=False, ncol=2, title="konst. Vce")
# (1,1) Ic-Ib
ax = fig.add_subplot(gs[1, 1])
for k, (lab, ib, ic) in enumerate(zip(*DATA["Ic_Ib"])):
    vce = tv(lab); ax.plot(ib, ic, "o", ms=3, color=TRC[k % 5], alpha=.75, label=lab)
    xx = np.linspace(np.nanmin(ib), np.nanmax(ib), 40) * 1e-6
    ax.plot(xx * 1e6, ic_model(solve_vbe_for_ib(xx, np.full_like(xx, vce), P), vce, P) * 1e3, "-", lw=1.5, color=TRC[k % 5])
style(ax, "Ic – Ib", "Ib [µA]", "Ic [mA]"); ax.legend(fontsize=7, frameon=False, title="konst. Vce")

# (1,2) Ergebnis-Parameter (Textpanel)
ax = fig.add_subplot(gs[1, 2]); ax.axis("off")
ax.set_title("Ergebnis: Parametersatz", fontsize=11.5, color="#12303a", weight="bold", loc="left")
lines = [
    ("n",      f"{P['n']:.3f}",        "bestimmt"),
    ("Is",     f"{P['Is']:.2e} A",     "bestimmt"),
    ("Beta_F", f"{P['Beta_F']:.0f}",   "bestimmt"),
    ("VA",     f"{P['VA']:.0f} V",     "schwach"),
    ("IKF",    f"{P['IKF']:.2g} A",    "Datenblatt"),
    ("RB",     f"{P['RB']:.0f} Ohm",   "Datenblatt"),
    ("Vab",    f"{P['Vab']:.0e} V",    "neutral"),
]
col = {"bestimmt": GOOD, "schwach": WARN, "Datenblatt": NONE, "neutral": NONE}
y = 0.90
for k, v, tag in lines:
    ax.text(0.02, y, f"{k:7s}", family="monospace", fontsize=11, va="top", color="#243036", transform=ax.transAxes)
    ax.text(0.32, y, v, family="monospace", fontsize=11, va="top", color="#12303a", weight="bold", transform=ax.transAxes)
    ax.text(0.98, y, tag, fontsize=9, va="top", ha="right", color=col[tag], weight="bold", transform=ax.transAxes)
    y -= 0.105

# --- Helfer: Tabelle in eine Achse ---
def tabelle(ax, title, collabels, rows, cellcolors=None, widths=None):
    ax.axis("off")
    ax.set_title(title, fontsize=11.5, color="#12303a", weight="bold", loc="left", pad=6)
    t = ax.table(cellText=rows, colLabels=collabels, loc="center", cellLoc="left",
                 colWidths=widths)
    t.auto_set_font_size(False); t.set_fontsize(9.5); t.scale(1, 1.5)
    for (r, c), cell in t.get_celld().items():
        cell.set_edgecolor("#dde5e8")
        if r == 0:
            cell.set_facecolor("#eaf1f2"); cell.set_text_props(color="#51606a", weight="bold")
        else:
            cell.set_facecolor("white")
            if cellcolors and (r - 1, c) in cellcolors:
                cell.set_text_props(color=cellcolors[(r - 1, c)], weight="bold")

# (2,0) RMS
ax = fig.add_subplot(gs[2, 0])
rms_rows, rms_col = [], {}
order = [("Ic-Vbe", "Gummel"), ("Ic-Vce", "Ausgang"), ("hFE-Vce", "hFE-Vce"), ("hFE-Ic", "hFE-Ic"), ("Ic-Ib", "Ic-Ib")]
for i, (k, _) in enumerate(order):
    if k == "Ic-Vbe":
        val = f"{(np.exp(RMS[k])-1)*100:.1f} %"
    else:
        val = f"{RMS[k]*100:.2f} %"
    rms_rows.append([k, val, "sehr gut" if RMS[k] < 0.02 else "gut"])
    rms_col[(i, 2)] = GOOD
tabelle(ax, "Bewertung 1 — Fehler Modell vs. Messung", ["Kennlinie", "RMS", "Urteil"], rms_rows, rms_col, [0.4, 0.3, 0.3])

# (2,1) Identifizierbarkeit
ax = fig.add_subplot(gs[2, 1])
disp = {"n": "n", "Is": "Is", "Beta_F": "β_F", "VA": "V_A", "IKF": "IKF", "RB": "RB"}
ident_order = ["n", "Beta_F", "Is", "VA", "RB", "IKF"]
id_rows, id_col = [], {}
for i, k in enumerate(ident_order):
    f = IDENT[k]
    if f > 1.5: verd, cc = "gut bestimmt", GOOD
    elif f > 1.05: verd, cc = "schwach", WARN
    else: verd, cc = "nicht best.", NONE
    id_rows.append([disp[k], f"×{f:.2f}", verd]); id_col[(i, 2)] = cc
tabelle(ax, "Bewertung 2 — Bestimmbarkeit (+20 %)", ["Param", "Fehler×", "Urteil"], id_rows, id_col, [0.28, 0.3, 0.42])

# (2,2) Datenblattvergleich
ax = fig.add_subplot(gs[2, 2])
comp = [("Is", "Is", "IS", "%.2e"), ("β_F", "Beta_F", "BF", "%.0f"), ("V_A", "VA", "VAF", "%.0f"),
        ("IKF", "IKF", "IKF", "%.2g"), ("RB", "RB", "RB", "%.0f")]
db_rows = [[d, fmt % P[pk], fmt % DB[dk]] for d, pk, dk, fmt in comp]
tabelle(ax, "Bewertung 3 — Abgleich BC337-25", ["Param", "Messung", "Datenblatt"], db_rows, None, [0.28, 0.36, 0.36])

fig.savefig("bjt_dashboard.png", dpi=110)
print("Bild gespeichert: bjt_dashboard.png")
print("Parametersatz:")
for k in ["n", "Is", "Beta_F", "VA", "IKF", "RB", "Vab"]:
    print(f"   {k:7s} = {P[k]:.4g}")
plt.show()
