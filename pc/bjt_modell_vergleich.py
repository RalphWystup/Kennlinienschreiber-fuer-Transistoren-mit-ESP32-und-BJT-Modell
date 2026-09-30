"""
Vergleich Messung <-> Modell (Gummel-Poon, vereinfacht)
=======================================================
Stellt die gemessenen Kennlinien (Punkte) und die aus den MODELLGLEICHUNGEN
mit den bestimmten Parametern berechneten Kurven (Linien) gemeinsam dar.

Benoetigt nur numpy + matplotlib.  Aufruf:  python bjt_modell_vergleich.py

Gleichungen (aus der Skizze):
  Ic       = Is * exp(Vbe/(n*Vt)) * (1 + Vce/VA)
  beta_eff = Beta_F / sqrt(1 + Ic/IKF)
  Vbe_eff  = Vbe - Ib*RB
  Ib       = (Is/beta_eff) * exp(Vbe_eff/(n*Vt)) * (1 + Vce/Vab)
"""
import numpy as np
import matplotlib.pyplot as plt

# ===========================================================================
#  BESTIMMTE PARAMETER  (hier bei Bedarf aendern)
# ===========================================================================
P = dict(
    Is     = 4.8e-14,     # Saettigungsstrom [A]
    n      = 1.004,       # Emissionskoeffizient
    Beta_F = 272.0,       # Vorwaerts-Stromverstaerkung
    VA     = 146.0,       # Early-Spannung vorwaerts [V]
    IKF    = 0.1,         # Kniestrom [A]      (nicht messbar -> gross)
    Vab    = 1e6,         # Early Basis [V]    (nicht messbar -> Term ~1)
    RB     = 10.0,        # interner Basiswiderstand [Ohm] (Default)
    Vt     = 0.025852,    # Thermospannung bei 300 K [V]
)

# ===========================================================================
#  MODELLGLEICHUNGEN
# ===========================================================================
def ic_model(vbe, vce, P):
    return P["Is"] * np.exp(vbe / (P["n"] * P["Vt"])) * (1 + vce / P["VA"])

def ib_model(vbe, vce, P):
    ic = ic_model(vbe, vce, P)                      # Ic haengt nur von Vbe ab
    beta_eff = P["Beta_F"] / np.sqrt(1 + ic / P["IKF"])
    ib = ic / beta_eff                              # Startwert
    for _ in range(40):                             # Fixpunkt fuer Vbe_eff = Vbe - Ib*RB
        vbe_eff = vbe - ib * P["RB"]
        ib_new = (P["Is"] / beta_eff) * np.exp(vbe_eff / (P["n"] * P["Vt"])) * (1 + vce / P["Vab"])
        if np.all(np.abs(ib_new - ib) <= 1e-18 + 1e-9 * np.abs(ib_new)):
            ib = ib_new; break
        ib = ib_new
    return ib

def solve_vbe_for_ib(ib_target, vce, P, lo=0.2, hi=1.0):
    """Bisektion: finde Vbe, so dass Ib(Modell)=ib_target (Ib monoton in Vbe)."""
    lo = np.full_like(vce, lo, dtype=float)
    hi = np.full_like(vce, hi, dtype=float)
    for _ in range(70):
        mid = 0.5 * (lo + hi)
        f = ib_model(mid, vce, P) - ib_target
        hi = np.where(f > 0, mid, hi)
        lo = np.where(f <= 0, mid, lo)
    return 0.5 * (lo + hi)

# ===========================================================================
#  MESSDATEN LADEN
# ===========================================================================
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

# ===========================================================================
#  DARSTELLUNG
# ===========================================================================
fig, ax = plt.subplots(2, 3, figsize=(16, 9))
fig.suptitle("BJT: Messung (Punkte) vs. Modell aus den Gleichungen (Linien)", fontsize=13)

# --- (0,0) Gummel Ic-Vbe -----------------------------------------------------
a = ax[0, 0]
tr, xs, ys = load("Ic_Vbe.txt")
for lab, vbe, ic_mA in zip(tr, xs, ys):
    vce = tv(lab)
    if vce < 1: continue
    col = a.semilogy(vbe, ic_mA * 1e-3, ".", ms=4, label=lab)[0].get_color()
    xx = np.linspace(0.45, np.nanmax(vbe), 100)
    a.semilogy(xx, ic_model(xx, vce, P), "-", lw=1.2, color=col)
a.set(xlabel="Vbe [V]", ylabel="Ic [A]", title="Ic–Vbe (Gummel)")
a.set_ylim(1e-7, 2e-2); a.grid(True, which="both", alpha=0.3); a.legend(fontsize=7)

# --- (0,1) Ausgangskennlinie Ic-Vce (konst. Ib) -----------------------------
a = ax[0, 1]
tr, xs, ys = load("Ic_Vce.txt")
for lab, vce, ic_mA in zip(tr, xs, ys):
    ib = tv(lab) * 1e-6
    col = a.plot(vce, ic_mA, ".", ms=3, label=lab)[0].get_color()
    xx = np.linspace(0.3, np.nanmax(vce), 60)
    vbe = solve_vbe_for_ib(ib, xx, P)
    a.plot(xx, ic_model(vbe, xx, P) * 1e3, "-", lw=1.2, color=col)
a.set(xlabel="Vce [V]", ylabel="Ic [mA]", title="Ic–Vce (Ausgang, konst. Ib)")
a.grid(True, alpha=0.3); a.legend(fontsize=7)

# --- (0,2) hFE-Vce -----------------------------------------------------------
a = ax[0, 2]
tr, xs, ys = load("hFE_Vce.txt")
for lab, vce, hfe in zip(tr, xs, ys):
    ib = tv(lab) * 1e-6
    col = a.plot(vce, hfe, ".", ms=3, label=lab)[0].get_color()
    xx = np.linspace(0.3, np.nanmax(vce), 60)
    vbe = solve_vbe_for_ib(ib, xx, P)
    a.plot(xx, ic_model(vbe, xx, P) / ib, "-", lw=1.2, color=col)
a.set(xlabel="Vce [V]", ylabel="hFE", title="hFE–Vce"); a.set_ylim(0, 320)
a.grid(True, alpha=0.3); a.legend(fontsize=7)

# --- (1,0) hFE-Ic ------------------------------------------------------------
a = ax[1, 0]
tr, xs, ys = load("hFE_Ic.txt")
for lab, ic_mA, hfe in zip(tr, xs, ys):
    vce = tv(lab)
    col = a.plot(ic_mA, hfe, ".", ms=4, label=lab)[0].get_color()
    ib_axis = np.linspace(5e-6, 45e-6, 60)
    vbe = solve_vbe_for_ib(ib_axis, np.full_like(ib_axis, vce), P)
    ic = ic_model(vbe, vce, P)
    a.plot(ic * 1e3, ic / ib_axis, "-", lw=1.2, color=col)
a.set(xlabel="Ic [mA]", ylabel="hFE", title="hFE–Ic"); a.set_ylim(0, 320)
a.grid(True, alpha=0.3); a.legend(fontsize=7)

# --- (1,1) Ic-Ib -------------------------------------------------------------
a = ax[1, 1]
tr, xs, ys = load("Ic_Ib.txt")
for lab, ib_uA, ic_mA in zip(tr, xs, ys):
    vce = tv(lab)
    col = a.plot(ib_uA, ic_mA, ".", ms=4, label=lab)[0].get_color()
    xx = np.linspace(np.nanmin(ib_uA), np.nanmax(ib_uA), 40) * 1e-6
    vbe = solve_vbe_for_ib(xx, np.full_like(xx, vce), P)
    a.plot(xx * 1e6, ic_model(vbe, vce, P) * 1e3, "-", lw=1.2, color=col)
a.set(xlabel="Ib [µA]", ylabel="Ic [mA]", title="Ic–Ib")
a.grid(True, alpha=0.3); a.legend(fontsize=7)

# --- (1,2) Parameter-Box -----------------------------------------------------
a = ax[1, 2]; a.axis("off")
txt = "Verwendete Parameter\n" + "-"*24 + "\n"
txt += f"Is     = {P['Is']:.3e} A\n"
txt += f"n      = {P['n']:.3f}\n"
txt += f"Beta_F = {P['Beta_F']:.0f}\n"
txt += f"VA     = {P['VA']:.0f} V\n"
txt += f"IKF    = {P['IKF']:.3g} A   (nicht messbar)\n"
txt += f"Vab    = {P['Vab']:.0e} V  (nicht messbar)\n"
txt += f"RB     = {P['RB']:.0f} Ohm  (Default)\n"
txt += f"Vt     = {P['Vt']*1e3:.2f} mV (300 K)\n"
a.text(0.02, 0.98, txt, va="top", ha="left", family="monospace", fontsize=11)

fig.tight_layout(rect=[0, 0, 1, 0.97])
fig.savefig("bjt_modell_vergleich.png", dpi=110)
print("Bild gespeichert: bjt_modell_vergleich.png")
plt.show()
