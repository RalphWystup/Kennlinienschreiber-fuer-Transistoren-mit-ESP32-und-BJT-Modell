
"""
===========================================================================
 h-PARAMETER-BESTIMMUNG (BC337-25, Emitterschaltung) im Arbeitspunkt
===========================================================================
 Bei Vorgabe des Arbeitspunkts (IC, VCE) werden aus dem gefitteten Modell die
 vier h-Parameter bestimmt und in den vier Kennfeldern als Tangenten gezeigt:

   h11e = dVbe/dIb |Vce   (Eingangswiderstand)  [Ohm]     -> Eingangskennlinie
   h21e = dIc /dIb |Vce   (Stromverstaerkung)   [-]       -> Uebertragungskennlinie
   h22e = dIc /dVce|Ib    (Ausgangsleitwert)    [S]       -> Ausgangskennlinie
   h12e = dVbe/dVce|Ib    (Rueckwirkung)        [-]       -> Rueckwirkungskennlinie

 Nur numpy + matplotlib.   Aufruf:  python bjt_hparam.py
"""
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import gridspec

# =====================  ARBEITSPUNKT VORGEBEN  =============================
IC_Q  = 5.0e-3     # Kollektorstrom [A]
VCE_Q = 5.0        # Kollektor-Emitter-Spannung [V]
# ==========================================================================

VT = 0.025852
# Parametersatz (bestimmt in bjt_dashboard.py; hier fest, editierbar)
P = dict(n=1.004, Is=4.726e-14, Beta_F=249.9, VA=146.0,
         IKF=0.9, RB=60.0, Vab=1e6)   # nur deine 4 Gleichungen (kein Leckterm)
TRC = ["#0E7C86", "#C77400", "#3B7A57", "#B3261E", "#6A4C93"]
ACC, QCOL = "#0E7C86", "#B3261E"

# ------------------------------------------------------------------ Daten/Modell
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
DATA = {n: load(n + ".txt") for n in ["Ic_Vce", "Ic_Ib"]}

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

# ------------------------------------------------------------------ Arbeitspunkt
VBE_Q = float(vbe_from_ic(IC_Q, VCE_Q, P))
IB_Q  = float(ib_model(VBE_Q, VCE_Q, P))

# ------------------------------------------------------------------ h-Parameter (num. Ableitungen)
dVb, dVc = 1e-4, 1e-2
gm  = (ic_model(VBE_Q + dVb, VCE_Q, P) - ic_model(VBE_Q - dVb, VCE_Q, P)) / (2 * dVb)   # dIc/dVbe
go  = (ic_model(VBE_Q, VCE_Q + dVc, P) - ic_model(VBE_Q, VCE_Q - dVc, P)) / (2 * dVc)   # dIc/dVce
gpi = (ib_model(VBE_Q + dVb, VCE_Q, P) - ib_model(VBE_Q - dVb, VCE_Q, P)) / (2 * dVb)   # dIb/dVbe
gmu = (ib_model(VBE_Q, VCE_Q + dVc, P) - ib_model(VBE_Q, VCE_Q - dVc, P)) / (2 * dVc)   # dIb/dVce

h11 = 1.0 / gpi                 # Ohm
h21 = gm / gpi                  # -
h12 = -gmu / gpi                # -
h22 = go - gm * gmu / gpi       # S

# Kleinsignal-Ersatzwerte
rpi, ro, beta_ac = h11, 1.0 / h22, h21

print("=" * 56)
print(f"  ARBEITSPUNKT:  IC={IC_Q*1e3:.2f} mA  VCE={VCE_Q:.2f} V")
print(f"                 -> VBE={VBE_Q*1e3:.1f} mV  IB={IB_Q*1e6:.2f} uA")
print("-" * 56)
print(f"  h11e = {h11:9.1f} Ohm     (Eingangswiderstand)")
print(f"  h21e = {h21:9.1f}         (Stromverstaerkung ~ beta_ac)")
print(f"  h22e = {h22*1e6:9.2f} uS      (Ausgangsleitwert; ro={ro/1e3:.1f} kOhm)")
print(f"  h12e = {h12:9.2e}         (Rueckwirkung)")
print(f"  gm   = {gm*1e3:9.2f} mS")
print("=" * 56)

def nearest_trace(datakey, target):
    labs = DATA[datakey][0]
    vals = [tv(l) for l in labs]
    j = int(np.argmin([abs(v - target) for v in vals]))
    return j, vals[j]

# ================================================================== DASHBOARD
plt.rcParams.update({"font.size": 10, "axes.edgecolor": "#b9c3c6",
                     "xtick.color": "#51606a", "ytick.color": "#51606a", "font.family": "DejaVu Sans"})
fig = plt.figure(figsize=(16, 10))
fig.suptitle(f"h-Parameter im Arbeitspunkt  ·  IC = {IC_Q*1e3:.1f} mA,  VCE = {VCE_Q:.1f} V   (BC337-25)",
             fontsize=15, weight="bold", color="#12303a", y=0.98)
gs = gridspec.GridSpec(2, 3, figure=fig, hspace=0.33, wspace=0.27,
                       left=0.06, right=0.975, top=0.90, bottom=0.07)

def base(ax, title, xl, yl):
    ax.set_title(title, fontsize=11.5, color="#12303a", weight="bold", pad=8)
    ax.set_xlabel(xl); ax.set_ylabel(yl); ax.grid(True, color="#e7ecee", lw=0.8)
    for s in ("top", "right"): ax.spines[s].set_visible(False)

def mark_Q(ax, x, y):
    ax.axvline(x, color="#c9ced1", lw=0.8, ls=":"); ax.axhline(y, color="#c9ced1", lw=0.8, ls=":")
    ax.plot([x], [y], "o", ms=8, mfc=QCOL, mec="white", mew=1.2, zorder=5)

def annot(ax, txt):
    ax.text(0.04, 0.96, txt, transform=ax.transAxes, va="top", ha="left", fontsize=11.5,
            family="monospace", color="#12303a", weight="bold",
            bbox=dict(boxstyle="round,pad=0.4", fc="#eaf6f7", ec=ACC, lw=1.2))

# (0,0) Eingangskennlinie: Ib vs Vbe (bei Vce_Q) -> h11e = 1/Steigung
ax = fig.add_subplot(gs[0, 0])
vb = np.linspace(VBE_Q - 0.05, VBE_Q + 0.035, 200)
ib = ib_model(vb, VCE_Q, P)
ax.plot(vb, ib * 1e6, "-", color=TRC[0], lw=2, label=f"Modell (Vce={VCE_Q:g} V)")
# Tangente: Ib = IB_Q + gpi*(Vbe-VBE_Q)
xt = np.array([VBE_Q - 0.02, VBE_Q + 0.02])
ax.plot(xt, (IB_Q + gpi * (xt - VBE_Q)) * 1e6, "--", color=QCOL, lw=1.6, label="Tangente")
mark_Q(ax, VBE_Q, IB_Q * 1e6)
base(ax, "Eingangskennlinie  →  h11e", "Vbe [V]", "Ib [µA]")
annot(ax, f"h11e = dVbe/dIb\n     = {h11/1e3:.2f} kΩ")
ax.legend(fontsize=8, frameon=False, loc="lower right")

# (0,1) Uebertragungskennlinie: Ic vs Ib (bei Vce_Q) -> h21e = Steigung
ax = fig.add_subplot(gs[0, 1])
vb = np.linspace(VBE_Q - 0.08, VBE_Q + 0.03, 200)
ib = ib_model(vb, VCE_Q, P); ic = ic_model(vb, VCE_Q, P)
ax.plot(ib * 1e6, ic * 1e3, "-", color=TRC[0], lw=2, label=f"Modell (Vce={VCE_Q:g} V)")
j, vval = nearest_trace("Ic_Ib", VCE_Q)
ax.plot(DATA["Ic_Ib"][1][j], DATA["Ic_Ib"][2][j], "o", ms=3.5, color=TRC[1], alpha=.7, label=f"Messung (Vce={vval:g} V)")
xt = np.array([IB_Q - 8e-6, IB_Q + 8e-6])
ax.plot(xt * 1e6, (IC_Q + h21 * (xt - IB_Q)) * 1e3, "--", color=QCOL, lw=1.6, label="Tangente")
mark_Q(ax, IB_Q * 1e6, IC_Q * 1e3)
base(ax, "Übertragungskennlinie  →  h21e", "Ib [µA]", "Ic [mA]")
annot(ax, f"h21e = dIc/dIb\n     = {h21:.0f}")
ax.legend(fontsize=8, frameon=False, loc="lower right")

# (0,2) Ausgangskennlinie: Ic vs Vce (bei Ib_Q) -> h22e = Steigung
ax = fig.add_subplot(gs[0, 2])
vc = np.linspace(0.3, max(11, VCE_Q + 3), 120)
vb = solve_vbe_for_ib(IB_Q, vc, P); ic = ic_model(vb, vc, P)
ax.plot(vc, ic * 1e3, "-", color=TRC[0], lw=2, label=f"Modell (Ib={IB_Q*1e6:.1f} µA)")
j, ibval = nearest_trace("Ic_Vce", IB_Q * 1e6)
ax.plot(DATA["Ic_Vce"][1][j], DATA["Ic_Vce"][2][j], "o", ms=3, color=TRC[1], alpha=.7, label=f"Messung (Ib={ibval:g} µA)")
xt = np.array([VCE_Q - 3, VCE_Q + 3])
ax.plot(xt, (IC_Q + h22 * (xt - VCE_Q)) * 1e3, "--", color=QCOL, lw=1.6, label="Tangente")
mark_Q(ax, VCE_Q, IC_Q * 1e3)
base(ax, "Ausgangskennlinie  →  h22e", "Vce [V]", "Ic [mA]")
annot(ax, f"h22e = dIc/dVce\n     = {h22*1e6:.1f} µS\nro   = {ro/1e3:.1f} kΩ")
ax.legend(fontsize=8, frameon=False, loc="lower right")

# (1,0) Rueckwirkungskennlinie: Vbe vs Vce (bei Ib_Q) -> h12e = Steigung
ax = fig.add_subplot(gs[1, 0])
vc = np.linspace(0.5, max(11, VCE_Q + 3), 120)
vb = solve_vbe_for_ib(IB_Q, vc, P)
ax.plot(vc, vb * 1e3, "-", color=TRC[0], lw=2, label=f"Modell (Ib={IB_Q*1e6:.1f} µA)")
xt = np.array([VCE_Q - 3, VCE_Q + 3])
ax.plot(xt, (VBE_Q + h12 * (xt - VCE_Q)) * 1e3, "--", color=QCOL, lw=1.6, label="Tangente")
mark_Q(ax, VCE_Q, VBE_Q * 1e3)
base(ax, "Rückwirkungskennlinie  →  h12e", "Vce [V]", "Vbe [mV]")
annot(ax, f"h12e = dVbe/dVce\n     = {h12:.1e}")
ax.legend(fontsize=8, frameon=False, loc="upper right")

# (1,1) Ergebnis h-Parameter
ax = fig.add_subplot(gs[1, 1]); ax.axis("off")
ax.set_title("h-Parameter (Emitterschaltung)", fontsize=12, color="#12303a", weight="bold", loc="left")
rows = [("h11e", f"{h11/1e3:.2f} kΩ", "Eingangswiderstand"),
        ("h21e", f"{h21:.0f}", "Stromverstärkung  β_ac"),
        ("h22e", f"{h22*1e6:.1f} µS", "Ausgangsleitwert"),
        ("h12e", f"{h12:.1e}", "Spannungsrückwirkung")]
y = 0.86
for k, v, d in rows:
    ax.text(0.02, y, k, family="monospace", fontsize=13, va="top", color=ACC, weight="bold", transform=ax.transAxes)
    ax.text(0.24, y, v, family="monospace", fontsize=13, va="top", color="#12303a", weight="bold", transform=ax.transAxes)
    ax.text(0.52, y, d, fontsize=10, va="top", color="#51606a", transform=ax.transAxes)
    y -= 0.16
ax.text(0.02, y - 0.02, "Kleinsignal-Ersatzbild:", fontsize=10.5, va="top", color="#12303a", weight="bold", transform=ax.transAxes)
ax.text(0.02, y - 0.14,
        f"gm = {gm*1e3:.1f} mS   rπ = {rpi/1e3:.2f} kΩ\nro = {ro/1e3:.1f} kΩ   β = {beta_ac:.0f}",
        family="monospace", fontsize=11, va="top", color="#243036", transform=ax.transAxes)

# (1,2) Arbeitspunkt
ax = fig.add_subplot(gs[1, 2]); ax.axis("off")
ax.set_title("Arbeitspunkt", fontsize=12, color="#12303a", weight="bold", loc="left")
apt = [("IC", f"{IC_Q*1e3:.2f} mA"), ("VCE", f"{VCE_Q:.2f} V"),
       ("VBE", f"{VBE_Q*1e3:.1f} mV"), ("IB", f"{IB_Q*1e6:.2f} µA"),
       ("hFE (DC)", f"{IC_Q/IB_Q:.0f}")]
y = 0.86
for k, v in apt:
    ax.text(0.04, y, k, family="monospace", fontsize=12, va="top", color="#51606a", transform=ax.transAxes)
    ax.text(0.52, y, v, family="monospace", fontsize=12, va="top", color="#12303a", weight="bold", transform=ax.transAxes)
    y -= 0.135
ax.text(0.04, y - 0.02, "Vorgabe oben im Skript:\nIC_Q, VCE_Q", fontsize=9.5, va="top",
        color="#51606a", style="italic", transform=ax.transAxes)

fig.savefig("bjt_hparam.png", dpi=110)
print("Bild gespeichert: bjt_hparam.png")
plt.show()
