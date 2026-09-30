"""
===========================================================================
 EMITTERSCHALTUNG KOMPLETT (BC337-25) - VIERPOLRECHNUNG MIT A-PARAMETERN
 Arbeitspunkt -> h-Vierpol -> Kettenmatrizen -> Kettenschaltung ->
 Eingangs-/Ausgangswiderstand und Verstaerkung
===========================================================================
 Vereint Transistor_20.py (Arbeitspunkt aus Vcc, Rb, Rc) und bjt_hparam.py
 (h-Parameter aus dem gefitteten Kurventracer-Modell). Gerechnet wird
 klassisch mit Kettenmatrizen (A-Parametern):

   1. Arbeitspunkt der realen Schaltung mit NEWTON-RAPHSON loesen (wie in
      Transistor_20.py): Maschengleichungen an Basis und Kollektor gegen
      das gefittete Transistormodell, Jacobi-Matrix numerisch.
      R_B kann vorgegeben ODER automatisch fuer V_CE = V_CC/2 bestimmt
      werden (mit Vorschlag des naechsten E24-Normwerts).

   2. Transistor als h-Vierpol im Arbeitspunkt (Tor 1 = Basis,
      Tor 2 = Kollektor, Emitter gemeinsam):
        [vbe]   [h11e  h12e] [ib ]
        [ic ] = [h21e  h22e] [vce]

   3. Alle Glieder als Kettenmatrix (A-Parameter), Definition
        [U1]   [A11  A12] [U2]
        [I1] = [A21  A22] [I2]     (I2 in Kettenpfeilrichtung)

      Transistor (Umrechnung h -> A):   A_T = 1/h21 * [-Dh   -h11]
                                                      [-h22  -1  ]
      Querwiderstand (reduzierter Vierpol, Vcc = Wechselstrom-Masse):
        A_RB = [1     0]        A_RC = [1     0]
               [1/RB  1]               [1/RC  1]

   4. Kettenschaltung = Matrixmultiplikation in Signalrichtung:
        A_ges = A_RB * A_T * A_RC

   5. Impedanzen und Verstaerkung aus der Gesamt-Kettenmatrix:
        r_ein = (A11*RL + A12) / (A21*RL + A22)     (Ausgang mit RL belastet)
        r_aus = (A22*Ri + A12) / (A21*Ri + A11)     (Eingang mit Ri belastet)
        A_v   = U2/U1       =  RL / (A11*RL + A12)
        A_i   = I2/I1       =   1 / (A21*RL + A22)
        A_vs  = U2/U_quelle =  A_v * r_ein/(r_ein + Ri)

 Annahmen: Emitterschaltung, Emitter an Masse, ein Basiswiderstand R_B
 nach Vcc, Last und Quelle ueber ideale Koppelkondensatoren.
 Nur numpy + matplotlib.   Aufruf:  python bjt_verstaerker.py
"""
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import gridspec

# =====================  SCHALTUNG VORGEBEN  ================================
V_CC = 15.0        # Versorgungsspannung [V]
R_C  = 1e3         # Kollektorwiderstand [Ohm]
R_B  = None        # Basiswiderstand [Ohm];  None = automatisch fuer Vce=Vcc/2
R_L  = 10e3        # Lastwiderstand am Ausgang [Ohm]  (ueber Koppel-C)
R_I  = 1e3         # Innenwiderstand Ri der Signalquelle [Ohm]
V_BB = V_CC        # Basisspeisung (wie Transistor_20.py: aus Vcc)
# ==========================================================================

VT = 0.025852
# Parametersatz BC337-25 (Fit aus den Kurventracer-Dateien, s. bjt_dashboard.py)
P = dict(n=1.004, Is=4.726e-14, Beta_F=249.9, VA=146.0,
         IKF=0.9, RB=60.0, Vab=1e6)
TRC = ["#0E7C86", "#C77400", "#3B7A57", "#B3261E", "#6A4C93"]
ACC, QCOL = "#0E7C86", "#B3261E"

# ------------------------------------------------------------------ Modell (aus bjt_hparam.py)
def ic_model(vbe, vce, P):
    return P["Is"] * np.exp(vbe / (P["n"] * VT)) * (1 + vce / P["VA"])

def ib_model(vbe, vce, P):
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

# ------------------------------------------------------------------ 1) Arbeitspunkt der Schaltung
# Nichtlineares Gleichungssystem wie in Transistor_20.py, geloest mit
# Newton-Raphson - nur stehen rechts jetzt die gefitteten Modellgleichungen:
#   eq1: (Vbb - Vbe)/Rb - Ib_Modell(Vbe, Vce) = 0     (Basismasche)
#   eq2: (Vcc - Vce)/Rc - Ic_Modell(Vbe, Vce) = 0     (Kollektormasche)
def F_system(vbe, vce, rb):
    return np.array([(V_BB - vbe) / rb - float(ib_model(vbe, vce, P)),
                     (V_CC - vce) / R_C - float(ic_model(vbe, vce, P))])

def J_system(vbe, vce, rb):
    """Jacobi-Matrix, numerisch (zentrale Differenzen) - das Modell ist
    implizit (innere Iteration in ib_model), daher nicht analytisch."""
    hb, hc = 1e-6, 1e-4
    dFb = (F_system(vbe + hb, vce, rb) - F_system(vbe - hb, vce, rb)) / (2 * hb)
    dFc = (F_system(vbe, vce + hc, rb) - F_system(vbe, vce - hc, rb)) / (2 * hc)
    return np.column_stack([dFb, dFc])

def arbeitspunkt(rb, start=(0.65, None), tol=1e-12, max_iter=60):
    """Newton-Raphson wie in Transistor_20.py; Rueckgabe (Vbe, Vce, Iterationen)."""
    x = np.array([start[0], V_CC / 2 if start[1] is None else start[1]], float)
    for i in range(max_iter):
        f = F_system(x[0], x[1], rb)
        if np.all(np.abs(f) < tol):
            return x[0], x[1], i + 1
        delta = np.linalg.solve(J_system(x[0], x[1], rb), -f)
        # Daempfung: Schrittweite begrenzen, damit die Exponentialfunktion
        # nicht ueberschossen wird (klassischer Newton-Stolperstein)
        delta[0] = np.clip(delta[0], -0.05, 0.05)
        delta[1] = np.clip(delta[1], -2.0, 2.0)
        x += delta
        x[0] = min(max(x[0], 0.2), 1.0)          # physikalisch sinnvoll halten
        x[1] = min(max(x[1], 1e-3), V_CC)
    raise ValueError("Newton-Raphson konvergiert nicht")

def arbeitspunkt_bisektion(rb):
    """Rueckfallebene: verschachtelte Bisektion (langsam, aber unkaputtbar)."""
    def vce_von_vbe(vbe):
        lo, hi = 1e-3, V_CC
        for _ in range(60):
            mid = 0.5 * (lo + hi)
            f = V_CC - R_C * ic_model(vbe, mid, P) - mid
            lo, hi = (mid, hi) if f > 0 else (lo, mid)
        return 0.5 * (lo + hi)
    lo, hi = 0.3, 0.95
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        rest = (V_BB - mid) / rb - float(ib_model(mid, vce_von_vbe(mid), P))
        lo, hi = (mid, hi) if rest > 0 else (lo, mid)
    return 0.5 * (lo + hi), vce_von_vbe(0.5 * (lo + hi))

E24 = [1.0, 1.1, 1.2, 1.3, 1.5, 1.6, 1.8, 2.0, 2.2, 2.4, 2.7, 3.0,
       3.3, 3.6, 3.9, 4.3, 4.7, 5.1, 5.6, 6.2, 6.8, 7.5, 8.2, 9.1]
def e24_naechster(r):
    dek = 10 ** np.floor(np.log10(r))
    kand = [m * dek for m in E24] + [E24[0] * dek * 10]
    return min(kand, key=lambda x: abs(np.log(x / r)))

RB_INFO = ""
if R_B is None:
    # Ziel Vce=Vcc/2 -> Ic -> Vbe (Klemmen) -> Ib -> exaktes Rb -> E24-Wert
    vce_z = V_CC / 2
    ic_z = (V_CC - vce_z) / R_C
    vbe_k = float(vbe_from_ic(ic_z, vce_z, P))
    for _ in range(30):
        f = float(ic_model(vbe_k, vce_z, P)) - ic_z
        vbe_k -= f / (float(ic_model(vbe_k, vce_z, P)) / (P["n"] * VT))
    ib_z = float(ib_model(vbe_k, vce_z, P))
    rb_exakt = (V_BB - vbe_k) / ib_z
    R_B = e24_naechster(rb_exakt)
    RB_INFO = ("R_B automatisch fuer Vce=Vcc/2: exakt %.1f kOhm -> E24-Wert %.0f kOhm"
               % (rb_exakt / 1e3, R_B / 1e3))

try:
    VBE_Q, VCE_Q, NEWTON_ITER = arbeitspunkt(R_B)
    AP_METHODE = "Newton-Raphson, %d Iterationen" % NEWTON_ITER
except ValueError:
    VBE_Q, VCE_Q = arbeitspunkt_bisektion(R_B)
    AP_METHODE = "Bisektion (Newton konvergierte nicht)"
IB_Q = float(ib_model(VBE_Q, VCE_Q, P))
IC_Q = float(ic_model(VBE_Q, VCE_Q, P))
SAETTIGUNG = VCE_Q < 0.3

# ------------------------------------------------------------------ 2) h-Vierpol des Transistors
# Steigungen der gefitteten Kennlinien im Arbeitspunkt (zentrale Differenzen)
dVb, dVc = 1e-4, 1e-2
dIc_dVbe = (ic_model(VBE_Q + dVb, VCE_Q, P) - ic_model(VBE_Q - dVb, VCE_Q, P)) / (2 * dVb)
dIc_dVce = (ic_model(VBE_Q, VCE_Q + dVc, P) - ic_model(VBE_Q, VCE_Q - dVc, P)) / (2 * dVc)
dIb_dVbe = (ib_model(VBE_Q + dVb, VCE_Q, P) - ib_model(VBE_Q - dVb, VCE_Q, P)) / (2 * dVb)
dIb_dVce = (ib_model(VBE_Q, VCE_Q + dVc, P) - ib_model(VBE_Q, VCE_Q - dVc, P)) / (2 * dVc)

h11 = 1.0 / dIb_dVbe                       # dVbe/dIb  [Ohm]
h21 = dIc_dVbe / dIb_dVbe                  # dIc/dIb   [-]
h12 = -dIb_dVce / dIb_dVbe                 # dVbe/dVce [-]
h22 = dIc_dVce - dIc_dVbe * dIb_dVce / dIb_dVbe   # dIc/dVce [S]
Dh  = h11 * h22 - h12 * h21

# ------------------------------------------------------------------ 3) Kettenmatrizen (A-Parameter)
def h_zu_a(h11, h12, h21, h22):
    """Umrechnung Hybridmatrix -> Kettenmatrix (Standard-Vierpoltheorie)."""
    Dh = h11 * h22 - h12 * h21
    return (1.0 / h21) * np.array([[-Dh,  -h11],
                                   [-h22, -1.0]])

def a_quer(R):
    """Kettenmatrix eines Querwiderstands (Laengszweig durchverbunden)."""
    return np.array([[1.0, 0.0], [1.0 / R, 1.0]])

A_T  = h_zu_a(h11, h12, h21, h22)     # Transistor
A_RB = a_quer(R_B)                    # Basiswiderstand (nach Vcc = AC-Masse)
A_RC = a_quer(R_C)                    # Kollektorwiderstand (nach Vcc = AC-Masse)

# ------------------------------------------------------------------ 4) Kettenschaltung
A = A_RB @ A_T @ A_RC                 # Matrixprodukt in Signalrichtung

# ------------------------------------------------------------------ 5) Impedanzen und Verstaerkung
R_EIN = (A[0, 0] * R_L + A[0, 1]) / (A[1, 0] * R_L + A[1, 1])
R_AUS = (A[1, 1] * R_I + A[0, 1]) / (A[1, 0] * R_I + A[0, 0])
A_V   = R_L / (A[0, 0] * R_L + A[0, 1])         # U2/U1
A_I   = 1.0 / (A[1, 0] * R_L + A[1, 1])         # I2/I1
A_VS  = A_V * R_EIN / (R_EIN + R_I)             # U2/U_quelle

# ------------------------------------------------------------------ Konsole
def matrix_txt(M):
    return ("      [%12.4e  %12.4e]\n      [%12.4e  %12.4e]"
            % (M[0, 0], M[0, 1], M[1, 0], M[1, 1]))

print("=" * 66)
print("  EMITTERSCHALTUNG BC337-25 - KETTENMATRIX-RECHNUNG (A-PARAMETER)")
print("-" * 66)
print(f"  Schaltung:  Vcc={V_CC:g} V   Rc={R_C/1e3:g} k   Rb={R_B/1e3:g} k")
print(f"              Last RL={R_L/1e3:g} k   Quelle Ri={R_I/1e3:g} k")
if RB_INFO: print("  " + RB_INFO)
print("-" * 66)
print(f"  1) Arbeitspunkt ({AP_METHODE}):")
print(f"                    VBE={VBE_Q*1e3:6.1f} mV   IB={IB_Q*1e6:6.2f} uA")
print(f"                    VCE={VCE_Q:6.2f} V    IC={IC_Q*1e3:6.2f} mA   hFE={IC_Q/IB_Q:.0f}")
if SAETTIGUNG:
    print("  ACHTUNG: Vce < 0.3 V -> Saettigung, Ergebnisse unbrauchbar!")
print("-" * 66)
print("  2) h-Vierpol des Transistors:")
print(f"      h11e = {h11:9.1f} Ohm    h12e = {h12:10.2e}")
print(f"      h21e = {h21:9.1f}        h22e = {h22*1e6:8.2f} uS      (Dh = {Dh:.4f})")
print("  3) Kettenmatrizen:")
print("      A_T (Transistor, aus h umgerechnet):")
print(matrix_txt(A_T))
print("      A_RB, A_RC: Querwiderstaende  [1 0; 1/R 1]  mit")
print("      1/RB = %.3e S,   1/RC = %.3e S" % (1 / R_B, 1 / R_C))
print("  4) Zusammengefasster Vierpol  A_ges = A_RB * A_T * A_RC:")
print(matrix_txt(A))
print("      Beschaltung: Eingang Quelle mit Ri, Ausgang Last RL")
print("-" * 66)
print("  5) Impedanzen und Verstaerkung des belasteten Gesamtvierpols:")
print(f"      r_ein = (A11*RL+A12)/(A21*RL+A22) = {R_EIN/1e3:7.3f} kOhm")
print(f"      r_aus = (A22*Ri+A12)/(A21*Ri+A11) = {R_AUS/1e3:7.3f} kOhm")
print(f"      A_v   = RL/(A11*RL+A12)  = {A_V:8.1f}   ({20*np.log10(abs(A_V)):.1f} dB, invertierend)")
print(f"      A_i   = 1/(A21*RL+A22)   = {A_I:8.1f}")
print(f"      A_vs  = A_v*r_ein/(r_ein+Ri) = {A_VS:8.1f}   ({20*np.log10(abs(A_VS)):.1f} dB)")
print("=" * 66)

# ------------------------------------------------------------------ Messdaten (optional, nur Anzeige)
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
try:
    MESS = load("Ic_Vce.txt")
except OSError:
    MESS = None

# ================================================================== DASHBOARD
plt.rcParams.update({"font.size": 10, "axes.edgecolor": "#b9c3c6",
                     "xtick.color": "#51606a", "ytick.color": "#51606a", "font.family": "DejaVu Sans"})
fig = plt.figure(figsize=(16, 9.5))
fig.suptitle(f"Emitterschaltung als Vierpol-Kette  ·  Vcc={V_CC:g} V, Rc={R_C/1e3:g} k, Rb={R_B/1e3:g} k, "
             f"RL={R_L/1e3:g} k, Ri={R_I/1e3:g} k   (BC337-25)",
             fontsize=15, weight="bold", color="#12303a", y=0.98)
gs = gridspec.GridSpec(2, 2, figure=fig, hspace=0.32, wspace=0.22,
                       left=0.06, right=0.975, top=0.90, bottom=0.07)

def base(ax, title, xl, yl):
    ax.set_title(title, fontsize=11.5, color="#12303a", weight="bold", pad=8)
    ax.set_xlabel(xl); ax.set_ylabel(yl); ax.grid(True, color="#e7ecee", lw=0.8)
    for s in ("top", "right"): ax.spines[s].set_visible(False)

def mark_Q(ax, x, y):
    ax.axvline(x, color="#c9ced1", lw=0.8, ls=":"); ax.axhline(y, color="#c9ced1", lw=0.8, ls=":")
    ax.plot([x], [y], "o", ms=8, mfc=QCOL, mec="white", mew=1.2, zorder=5)

# (0,0) Ausgangskennlinie + Gleich- und Wechselstrom-Arbeitsgerade
ax = fig.add_subplot(gs[0, 0])
vc = np.linspace(0.2, V_CC, 200)
vb = solve_vbe_for_ib(IB_Q, vc, P)
ax.plot(vc, ic_model(vb, vc, P) * 1e3, "-", color=TRC[0], lw=2,
        label=f"Kennlinie (Ib={IB_Q*1e6:.1f} µA)")
if MESS:
    labs = MESS[0]; vals = [tv(l) for l in labs]
    j = int(np.argmin([abs(v - IB_Q * 1e6) for v in vals]))
    ax.plot(MESS[1][j], MESS[2][j], "o", ms=3, color=TRC[1], alpha=.7,
            label=f"Messung (Ib={vals[j]:g} µA)")
ax.plot(vc, (V_CC - vc) / R_C * 1e3, "k--", lw=1.4, label="DC-Lastgerade (Rc)")
RLs = R_C * R_L / (R_C + R_L)
xw = np.array([max(0.2, VCE_Q - 4), min(V_CC, VCE_Q + 4)])
ax.plot(xw, (IC_Q - (xw - VCE_Q) / RLs) * 1e3, "--", color=TRC[4], lw=1.6,
        label=f"AC-Lastgerade (Rc||RL={RLs/1e3:.2f} k)")
mark_Q(ax, VCE_Q, IC_Q * 1e3)
ax.set_xlim(0, V_CC); ax.set_ylim(0, V_CC / R_C * 1e3 * 1.15)
base(ax, "1) Arbeitspunkt und Arbeitsgeraden", "Vce [V]", "Ic [mA]")
ax.legend(fontsize=8, frameon=False, loc="upper right")

# (0,1) Verstaerkung ueber der Last (aus der Gesamt-Kettenmatrix)
ax = fig.add_subplot(gs[0, 1])
rl = np.logspace(1.5, 6, 250)
av = np.abs(rl / (A[0, 0] * rl + A[0, 1]))
ax.semilogx(rl, av, "-", color=TRC[0], lw=2)
ax.axvline(R_L, color=QCOL, lw=1.2, ls=":")
ax.plot([R_L], [abs(A_V)], "o", ms=8, mfc=QCOL, mec="white", mew=1.2, zorder=5)
ax.annotate(f"RL={R_L/1e3:g} k\n|A_v|={abs(A_V):.0f}", (R_L, abs(A_V)),
            textcoords="offset points", xytext=(10, -25), fontsize=9.5, color="#12303a")
base(ax, "5) Spannungsverstärkung |A_v| über der Last RL", "RL [Ω]", "|A_v|")

# (1,0) Vierpol-Kette als Tafel
ax = fig.add_subplot(gs[1, 0]); ax.axis("off")
ax.set_title("2)–4) Kettenschaltung:  A_ges = A_RB · A_T · A_RC",
             fontsize=12, color="#12303a", weight="bold", loc="left")
def zeile(y, links, rechts):
    ax.text(0.02, y, links, family="monospace", fontsize=10.5, va="top", color=ACC, weight="bold", transform=ax.transAxes)
    ax.text(0.32, y, rechts, family="monospace", fontsize=10.5, va="top", color="#12303a", transform=ax.transAxes)
zeile(0.90, "H_Transistor", f"[{h11:9.1f} Ω   {h12:9.1e}  ]")
zeile(0.82, "",             f"[{h21:9.1f}     {h22*1e6:7.2f} µS]")
zeile(0.68, "A_T = H→A",    f"[{A_T[0,0]:10.3e}  {A_T[0,1]:10.3e}]")
zeile(0.60, "",             f"[{A_T[1,0]:10.3e}  {A_T[1,1]:10.3e}]")
zeile(0.46, "A_RB, A_RC",   f"[1 0; 1/R 1]  R = {R_B/1e3:g} k bzw. {R_C/1e3:g} k")
zeile(0.32, "A_ges",        f"[{A[0,0]:10.3e}  {A[0,1]:10.3e}]")
zeile(0.24, "",             f"[{A[1,0]:10.3e}  {A[1,1]:10.3e}]")
ax.text(0.02, 0.10, "Kettenschaltung  →  Kettenmatrizen multiplizieren (in Signalrichtung)",
        fontsize=9.5, style="italic", color="#51606a", transform=ax.transAxes)

# (1,1) Ergebnis-Tafel
ax = fig.add_subplot(gs[1, 1]); ax.axis("off")
ax.set_title("5) Ergebnis aus A_ges", fontsize=12, color="#12303a", weight="bold", loc="left")
rows = [("r_ein", f"{R_EIN/1e3:.3f} kΩ", f"(A11·RL+A12)/(A21·RL+A22),  RL={R_L/1e3:g} k"),
        ("r_aus", f"{R_AUS/1e3:.3f} kΩ", f"(A22·Ri+A12)/(A21·Ri+A11),  Ri={R_I/1e3:g} k"),
        ("A_v",  f"{A_V:.1f}", f"RL/(A11·RL+A12)  ({20*np.log10(abs(A_V)):.1f} dB, invertierend)"),
        ("A_i",  f"{A_I:.1f}", "1/(A21·RL+A22)"),
        ("A_vs", f"{A_VS:.1f}", "A_v·r_ein/(r_ein+Ri), inkl. Teiler an Ri")]
y = 0.86
for k, v, d in rows:
    ax.text(0.02, y, k, family="monospace", fontsize=13, va="top", color=ACC, weight="bold", transform=ax.transAxes)
    ax.text(0.20, y, v, family="monospace", fontsize=13, va="top", color="#12303a", weight="bold", transform=ax.transAxes)
    ax.text(0.44, y, d, fontsize=9.5, va="top", color="#51606a", transform=ax.transAxes)
    y -= 0.15
if SAETTIGUNG:
    ax.text(0.02, y - 0.02, "ACHTUNG: Arbeitspunkt in der Sättigung!", fontsize=11,
            color=QCOL, weight="bold", transform=ax.transAxes)
elif RB_INFO:
    ax.text(0.02, y - 0.02, RB_INFO, fontsize=9, va="top", color="#51606a",
            style="italic", transform=ax.transAxes)

fig.savefig("bjt_verstaerker.png", dpi=110)
print("Bild gespeichert: bjt_verstaerker.png")
plt.show()
