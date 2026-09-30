"""
===========================================================================
 VIERQUADRANTEN-KENNLINIENFELD (BC337-25)  -  Fachbuch-Darstellung
===========================================================================
 Zeigt alle vier Kennfelder auf einmal, mit dem Arbeitspunkt durch alle
 Quadranten "durchgezogen" (Konstruktionslinien) und den Tangenten, deren
 Steigung die h-Parameter liefert:

     Q2 Uebertragung (h21e) | Q1 Ausgang (h22e)
     -----------------------+---------------------
     Q3 Eingang    (h11e)   | Q4 Rueckwirkung (h12e)

 Arbeitspunkt oben im Skript vorgeben (IC_Q, VCE_Q).
 Nur numpy + matplotlib.   Aufruf:  python bjt_4quadrant.py
"""
import numpy as np
import matplotlib.pyplot as plt

# =====================  ARBEITSPUNKT  =====================================
IC_Q  = 5.0e-3     # A
VCE_Q = 5.0        # V
# ==========================================================================

VT = 0.025852
P = dict(n=1.004, Is=4.726e-14, Beta_F=249.9, VA=146.0,
         IKF=0.9, RB=60.0, Vab=1e6)   # nur deine 4 Gleichungen (kein Leckterm)

# Achsen-Grenzen des Kennfelds
VCE_MAX, IC_MAX, IB_MAX, VBE_MAX = 11.0, 11.5, 45.0, 0.75   # V, mA, µA, V
IB_FAMILY = [8, 16, 24, 32, 40]                              # µA (Ausgangskennlinien)
ACC, ACC2, QCOL, FAM = "#0E7C86", "#0b616a", "#B3261E", "#9aa7ad"

# ------------------------------------------------------------------ Modell
def ic_model(vbe, vce, P):
    return P["Is"] * np.exp(vbe / (P["n"] * VT)) * (1 + vce / P["VA"])
def ib_model(vbe, vce, P):
    # I_B = (I_S/beta_eff) * exp(V_BE,eff/(n*V_T)) * (1 + V_CE/V_AB)   [deine Gleichung]
    ic = ic_model(vbe, vce, P); be = P["Beta_F"] / np.sqrt(1 + ic / P["IKF"])
    ib = ic / be
    for _ in range(40):
        ibn = (P["Is"] / be) * np.exp((vbe - ib * P["RB"]) / (P["n"] * VT)) * (1 + vce / P["Vab"])
        if np.all(np.abs(ibn - ib) <= 1e-20 + 1e-10 * np.abs(ibn)): ib = ibn; break
        ib = ibn
    return ib
def vbe_from_ic(ic, vce, P):
    return np.log(ic / (P["Is"] * (1 + vce / P["VA"]))) * (P["n"] * VT)
def solve_vbe_for_ib(ib, vce, P):
    ib = np.asarray(ib, float); vce = np.asarray(vce, float) + 0 * ib
    lo = np.full_like(vce, 0.2); hi = np.full_like(vce, 1.0)
    for _ in range(50):
        mid = 0.5 * (lo + hi); f = ib_model(mid, vce, P) - ib
        hi = np.where(f > 0, mid, hi); lo = np.where(f <= 0, mid, lo)
    return 0.5 * (lo + hi)

# ------------------------------------------------------------------ Messdaten
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
DATA = {n: load(n + ".txt") for n in ["Ic_Vce", "Ic_Ib", "Ic_Vbe"]}
MESS = "#233b45"   # Farbe der Messpunkte

def interp_sorted(x, xp, fp):
    xp = np.asarray(xp, float); fp = np.asarray(fp, float)
    ok = np.isfinite(xp) & np.isfinite(fp); xp, fp = xp[ok], fp[ok]
    o = np.argsort(xp); return np.interp(x, xp[o], fp[o])

# ------------------------------------------------------------------ Arbeitspunkt + h-Parameter
VBE_Q = float(vbe_from_ic(IC_Q, VCE_Q, P))
IB_Q  = float(ib_model(VBE_Q, VCE_Q, P))
dVb, dVc = 1e-4, 1e-2
gm  = (ic_model(VBE_Q + dVb, VCE_Q, P) - ic_model(VBE_Q - dVb, VCE_Q, P)) / (2 * dVb)
go  = (ic_model(VBE_Q, VCE_Q + dVc, P) - ic_model(VBE_Q, VCE_Q - dVc, P)) / (2 * dVc)
gpi = (ib_model(VBE_Q + dVb, VCE_Q, P) - ib_model(VBE_Q - dVb, VCE_Q, P)) / (2 * dVb)
gmu = (ib_model(VBE_Q, VCE_Q + dVc, P) - ib_model(VBE_Q, VCE_Q - dVc, P)) / (2 * dVc)
h11 = 1 / gpi; h21 = gm / gpi; h12 = -gmu / gpi; h22 = go - gm * gmu / gpi

# ================================================================== FIGUR
plt.rcParams.update({"font.size": 10, "font.family": "DejaVu Sans",
                     "axes.edgecolor": "#5a6a72", "xtick.color": "#41505a", "ytick.color": "#41505a"})
fig, axs = plt.subplots(2, 2, figsize=(13.5, 11.5), gridspec_kw=dict(wspace=0, hspace=0))
Q2, Q1 = axs[0, 0], axs[0, 1]
Q3, Q4 = axs[1, 0], axs[1, 1]
fig.suptitle("Vierquadranten-Kennlinienfeld  ·  BC337-25", fontsize=16, weight="bold", color="#12303a", y=0.965)
fig.text(0.5, 0.925, f"Arbeitspunkt:  IC = {IC_Q*1e3:.1f} mA,  VCE = {VCE_Q:.1f} V"
         f"   →   VBE = {VBE_Q*1e3:.0f} mV,  IB = {IB_Q*1e6:.1f} µA",
         ha="center", fontsize=11.5, color="#41505a")

# Achsengrenzen (inkl. Inversionen fuer das echte Quadrantenbild)
Q1.set_xlim(0, VCE_MAX);  Q1.set_ylim(0, IC_MAX)
Q2.set_xlim(IB_MAX, 0);   Q2.set_ylim(0, IC_MAX)
Q3.set_xlim(IB_MAX, 0);   Q3.set_ylim(VBE_MAX, 0)
Q4.set_xlim(0, VCE_MAX);  Q4.set_ylim(VBE_MAX, 0)
for ax in (Q1, Q2, Q3, Q4):
    ax.grid(True, color="#e7ecee", lw=0.8)
Q1.tick_params(labelbottom=False, labelleft=False)
Q2.tick_params(labelbottom=False)
Q4.tick_params(labelleft=False)
Q2.set_ylabel("I_C  [mA]", fontsize=11)
Q3.set_ylabel("V_BE  [V]", fontsize=11); Q3.set_xlabel("I_B  [µA]", fontsize=11)
Q4.set_xlabel("V_CE  [V]", fontsize=11)

# ---- Q1: Ausgangskennlinienfeld — Modellschar (Linien) + ECHTE MESSUNG (Punkte)
for ib0 in IB_FAMILY:
    vce = np.linspace(0.25, VCE_MAX, 140); vbe = solve_vbe_for_ib(ib0 * 1e-6, vce, P)
    Q1.plot(vce, ic_model(vbe, vce, P) * 1e3, "-", lw=1.1, color=FAM, zorder=2)
    Q1.text(VCE_MAX * 0.985, ic_model(solve_vbe_for_ib(ib0 * 1e-6, VCE_MAX, P), VCE_MAX, P) * 1e3,
            f"{ib0}µA", fontsize=7.5, color="#6a7a82", ha="right", va="bottom")
for lab, vce, ic in zip(*DATA["Ic_Vce"]):            # echte Messpunkte
    Q1.plot(vce, ic, ".", ms=2.6, color=MESS, alpha=.65, zorder=3)
# Betriebskurve (Ib = IB_Q) hervorgehoben
vce = np.linspace(0.25, VCE_MAX, 160); vbe = solve_vbe_for_ib(IB_Q, vce, P)
Q1.plot(vce, ic_model(vbe, vce, P) * 1e3, "-", lw=2.4, color=ACC, zorder=4)

# Q2: Uebertragung Ic(Ib) bei Vce_Q — Modell (Linie) + ECHTE MESSUNG (Punkte)
vb = np.linspace(0.45, VBE_Q + 0.03, 300)
Q2.plot(ib_model(vb, VCE_Q, P) * 1e6, ic_model(vb, VCE_Q, P) * 1e3, "-", lw=2.4, color=ACC, zorder=4)
j = int(np.argmin([abs(tv(l) - VCE_Q) for l in DATA["Ic_Ib"][0]]))
Q2.plot(DATA["Ic_Ib"][1][j], DATA["Ic_Ib"][2][j], ".", ms=4, color=MESS, alpha=.7, zorder=3,
        label=f"Messung (Vce={tv(DATA['Ic_Ib'][0][j]):g}V)")

# Q3: Eingangskennlinie Vbe(Ib) — Modell-Linie + aus Messung REKONSTRUIERT
Q3.plot(ib_model(vb, VCE_Q, P) * 1e6, vb, "-", lw=2.4, color=ACC, zorder=4)
#   Rekonstruktion: Ic-Vbe und Ic-Ib beim gemeinsamen Vce ueber Ic verknuepfen
vbe_vces = {round(tv(l)): i for i, l in enumerate(DATA["Ic_Vbe"][0]) if tv(l) >= 1}
ib_vces  = {round(tv(l)): i for i, l in enumerate(DATA["Ic_Ib"][0])}
common = sorted(set(vbe_vces) & set(ib_vces), key=lambda v: abs(v - VCE_Q))
if common:
    Vc0 = common[0]; iv, ii = vbe_vces[Vc0], ib_vces[Vc0]
    vbe_a, ic_a = DATA["Ic_Vbe"][1][iv], DATA["Ic_Vbe"][2][iv]      # Vbe, Ic(mA)
    ib_b,  ic_b = DATA["Ic_Ib"][1][ii],  DATA["Ic_Ib"][2][ii]       # Ib(µA), Ic(mA)
    lo = max(0.5, np.nanmin(ic_b)); hi = min(np.nanmax(ic_a), np.nanmax(ic_b))
    ic_s = np.linspace(lo, hi, 14)
    Q3.plot(interp_sorted(ic_s, ic_b, ib_b), interp_sorted(ic_s, ic_a, vbe_a),
            "s", ms=4.5, color=MESS, alpha=.75, zorder=5,
            label=f"Messung↺ (Vce={Vc0}V)")

# Q4: Rueckwirkung Vbe(Vce) — Modell-Linie + aus Messung REKONSTRUIERT
vc = np.linspace(0.3, VCE_MAX, 160); vbe4 = solve_vbe_for_ib(IB_Q, vc, P)
Q4.plot(vc, vbe4, "-", lw=2.4, color=ACC, zorder=4)
#   Rekonstruktion: fuer Ib0 (naechste Messkurve) Ic(Vce) aus Ic-Vce, dann Vbe(Ic) aus Ic-Vbe
jout = int(np.argmin([abs(tv(l) - IB_Q * 1e6) for l in DATA["Ic_Vce"][0]]))
Ib0 = tv(DATA["Ic_Vce"][0][jout])
vce_o, ic_o = DATA["Ic_Vce"][1][jout], DATA["Ic_Vce"][2][jout]      # Vce, Ic(mA)
pts = []
for i, l in enumerate(DATA["Ic_Vbe"][0]):
    vcx = tv(l)
    if vcx < 1: continue
    vbe_a, ic_a = DATA["Ic_Vbe"][1][i], DATA["Ic_Vbe"][2][i]
    ic_at = float(interp_sorted(vcx, vce_o, ic_o))
    if 0.5 < ic_at < np.nanmax(ic_a):
        pts.append((vcx, float(interp_sorted(ic_at, ic_a, vbe_a))))
if pts:
    Q4.plot([p[0] for p in pts], [p[1] for p in pts], "s", ms=4.5, color=MESS, alpha=.75,
            zorder=5, label=f"Messung↺ (Ib={Ib0:g}µA)")

# ---- Konstruktionslinien: Arbeitspunkt durch alle Quadranten ----
LS = dict(color=QCOL, lw=1.1, ls="-", alpha=0.55, zorder=2)
Q1.axhline(IC_Q * 1e3, **LS); Q2.axhline(IC_Q * 1e3, **LS)      # Ic = const
Q2.axvline(IB_Q * 1e6, **LS); Q3.axvline(IB_Q * 1e6, **LS)      # Ib = const
Q3.axhline(VBE_Q, **LS);      Q4.axhline(VBE_Q, **LS)           # Vbe = const
Q1.axvline(VCE_Q, **LS);      Q4.axvline(VCE_Q, **LS)           # Vce = const

# ---- Arbeitspunkte ----
def Qdot(ax, x, y): ax.plot([x], [y], "o", ms=9, mfc=QCOL, mec="white", mew=1.4, zorder=6)
Qdot(Q1, VCE_Q, IC_Q * 1e3); Qdot(Q2, IB_Q * 1e6, IC_Q * 1e3)
Qdot(Q3, IB_Q * 1e6, VBE_Q); Qdot(Q4, VCE_Q, VBE_Q)

# ---- Tangenten + Steigungswerte ----
def tangent(ax, x0, y0, slope, xspan, txt, tx, ty, ha="left"):
    xx = np.array([x0 - xspan, x0 + xspan])
    ax.plot(xx, y0 + slope * (xx - x0), "--", color=QCOL, lw=2, zorder=5)
    ax.text(tx, ty, txt, transform=ax.transAxes, ha=ha, va="center", fontsize=12,
            family="monospace", color="#12303a", weight="bold",
            bbox=dict(boxstyle="round,pad=0.35", fc="#fdeceb", ec=QCOL, lw=1.3))

# Q1 (h22e): dIc/dVce  -> mA/V
tangent(Q1, VCE_Q, IC_Q * 1e3, h22 * 1e3, 3.2,
        f"h22e = dIc/dVce\n     = {h22*1e6:.0f} µS", 0.62, 0.24)
# Q2 (h21e): dIc/dIb  -> mA/µA
tangent(Q2, IB_Q * 1e6, IC_Q * 1e3, h21 * 1e-3, 9,
        f"h21e = dIc/dIb\n     = {h21:.0f}", 0.30, 0.80, ha="left")
# Q3 (h11e): dVbe/dIb -> V/µA
tangent(Q3, IB_Q * 1e6, VBE_Q, h11 * 1e-6, 11,
        f"h11e = dVbe/dIb\n     = {h11/1e3:.2f} kΩ", 0.30, 0.24, ha="left")
# Q4 (h12e): dVbe/dVce
tangent(Q4, VCE_Q, VBE_Q, h12, 3.5,
        f"h12e = dVbe/dVce\n     ≈ {h12:.0e}", 0.60, 0.80)

# ---- Quadranten-Titel in den Außenecken ----
def corner(ax, x, y, t, ha, va):
    ax.text(x, y, t, transform=ax.transAxes, ha=ha, va=va, fontsize=11.5, weight="bold",
            color=ACC2, bbox=dict(boxstyle="round,pad=0.3", fc="#eaf6f7", ec="none"))
corner(Q1, 0.985, 0.96, "① Ausgangskennlinien  ·  h22e", "right", "top")
corner(Q2, 0.03, 0.96, "② Übertragung  ·  h21e", "left", "top")
corner(Q3, 0.03, 0.05, "③ Eingang  ·  h11e", "left", "bottom")
corner(Q4, 0.985, 0.05, "④ Rückwirkung  ·  h12e", "right", "bottom")

# Achsenpfeil-Hinweise (Richtung der geteilten Achsen)
Q2.text(0.5, 1.02, "◄  I_B", transform=Q2.transAxes, ha="center", fontsize=9, color="#6a7a82")
Q1.text(0.5, 1.02, "V_CE  ►", transform=Q1.transAxes, ha="center", fontsize=9, color="#6a7a82")

from matplotlib.lines import Line2D
handles = [
    Line2D([0], [0], marker=".", color="w", mfc=MESS, ms=11, label="Messung direkt (Q1 Ic-Vce, Q2 Ic-Ib)"),
    Line2D([0], [0], marker="s", color="w", mfc=MESS, ms=8, label="Messung rekonstruiert (Q3, Q4)"),
    Line2D([0], [0], color=ACC, lw=2.4, label="Modell = Fit an die Messdaten"),
    Line2D([0], [0], color=QCOL, lw=2, ls="--", label="Tangente → h-Parameter"),
]
fig.legend(handles=handles, loc="lower center", ncol=4, frameon=False, fontsize=9.5,
           bbox_to_anchor=(0.5, 0.012))

fig.subplots_adjust(left=0.075, right=0.965, top=0.905, bottom=0.085)
fig.savefig("bjt_4quadrant.png", dpi=115)
print("Bild gespeichert: bjt_4quadrant.png")
print(f"AP: IC={IC_Q*1e3:.2f}mA VCE={VCE_Q}V VBE={VBE_Q*1e3:.1f}mV IB={IB_Q*1e6:.2f}µA")
print(f"h11e={h11/1e3:.2f}kΩ  h21e={h21:.0f}  h22e={h22*1e6:.1f}µS  h12e={h12:.1e}")
plt.show()
