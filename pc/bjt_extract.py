"""
Parameter-Extraktion fuer das (vereinfachte Gummel-Poon-) Modell aus
Kurventracer-Messungen.  Bestimmt: Is, n, beta_F, V_A  (+ Grenzen fuer IKF).

Aufruf:  python bjt_extract.py
Erzeugt: bjt_extraction.png  und eine Parameter-Tabelle auf stdout.übrigens ein BC337
"""
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

VT = 0.025852          # Thermospannung bei T=300 K (Annahme Raumtemperatur)

# ---------------------------------------------------------------------------
def load(fname):
    with open(fname, encoding="utf-8-sig") as fh:
        lines = fh.read().splitlines()
    traces, hdr_idx = [], None
    for i, ln in enumerate(lines):
        cols = ln.split("\t")
        if cols[0] == "Trace:":
            traces = [c for c in cols[1:] if c.strip()]
        if cols[0] == "Point":
            hdr_idx = i
            break
    data = []
    for ln in lines[hdr_idx + 1:]:
        if not ln.strip():
            continue
        row = [float(c.strip().replace(",", ".")) if c.strip() != "" else np.nan
               for c in ln.split("\t")]
        data.append(row)
    arr = np.array(data, dtype=float)
    xs = [arr[:, 1 + 2 * i] for i in range(len(traces))]
    ys = [arr[:, 2 + 2 * i] for i in range(len(traces))]
    return traces, xs, ys

def trace_value(label):
    # "Vce=3,00V" -> 3.0 ; "Ib=40µA" -> 40 ; "Vce=2,0V" -> 2.0
    num = label.split("=")[1]
    num = num.replace("µA", "").replace("V", "").replace(",", ".").strip()
    return float(num)

# ===========================================================================
# 1) Is und n  aus dem Gummel-Plot (Ic-Vbe), exponentieller Bereich
# ===========================================================================
tr, xs, ys = load("Ic_Vbe.txt")
fig, ax = plt.subplots(2, 2, figsize=(13, 9))

ns, is_eff = [], []
gummel = []
for lab, vbe, ic_mA in zip(tr, xs, ys):
    vce = trace_value(lab)
    if vce < 1:            # Vce=0V-Kurve ist nicht im aktiven Bereich -> weg
        continue
    ic = ic_mA * 1e-3      # A
    # sauberer exponentieller Bereich: oberhalb des Rausch-/Quantisierungs-
    # bodens (~5 uA) und unterhalb Hochstrom/RB (~2 mA)
    m = np.isfinite(vbe) & np.isfinite(ic) & (ic > 2e-5) & (ic < 2e-3)
    if m.sum() < 4:
        continue
    slope, intercept = np.polyfit(vbe[m], np.log(ic[m]), 1)
    n = 1.0 / (slope * VT)
    ns.append(n)
    is_eff.append((vce, np.exp(intercept)))     # = Is*(1+Vce/Va)
    gummel.append((lab, vce, vbe, ic, slope, intercept, m))

n_mean = float(np.mean(ns))

# ===========================================================================
# 2) V_A (Early) aus Ausgangskennlinie Ic-Vce
# ===========================================================================
tr2, xs2, ys2 = load("Ic_Vce.txt")
VAs = []
early_lines = []
for lab, vce, ic_mA in zip(tr2, xs2, ys2):
    ic = ic_mA * 1e-3
    m = np.isfinite(vce) & np.isfinite(ic) & (vce >= 1.5)   # aktiver, flacher Ast
    if m.sum() < 4:
        continue
    b, a = np.polyfit(vce[m], ic[m], 1)     # ic = a + b*vce
    VA = a / b                              # x-Achsenschnitt bei -VA
    VAs.append(VA)
    early_lines.append((lab, vce, ic, a, b))
VA_mean = float(np.mean(VAs))

# Jetzt Is aus is_eff mit Va-Korrektur:  Is = Is_eff/(1+Vce/Va)
Is_vals = [ie / (1 + vce / VA_mean) for (vce, ie) in is_eff]
Is_mean = float(np.mean(Is_vals))

# ===========================================================================
# 3) beta_F  aus Ic-Ib (Steigung) und aus hFE
# ===========================================================================
tr3, xs3, ys3 = load("Ic_Ib.txt")
betas = []
for lab, ib_uA, ic_mA in zip(tr3, xs3, ys3):
    ib = ib_uA * 1e-6
    ic = ic_mA * 1e-3
    m = np.isfinite(ib) & np.isfinite(ic)
    if m.sum() < 3:
        continue
    b, a = np.polyfit(ib[m], ic[m], 1)      # ic = a + b*ib -> b = beta
    betas.append((trace_value(lab), b))
beta_slope = float(np.mean([b for _, b in betas]))

tr4, xs4, ys4 = load("hFE_Ic.txt")
hfe_max = max(np.nanmax(y) for y in ys4)

tr5, xs5, ys5 = load("hFE_Vce.txt")
hfe_max_vce = max(np.nanmax(y) for y in ys5)
beta_F = hfe_max_vce      # Plateau/Maximum von hFE ~ beta_F

# IKF: kein Abfall sichtbar -> untere Schranke
ic_max_seen = max(np.nanmax(y * 1e-3) for y in ys)   # groesster gemessener Ic (A)

# ===========================================================================
# PLOTS
# ===========================================================================
# (1) Gummel
axg = ax[0, 0]
for lab, vce, vbe, ic, slope, intercept, m in gummel:
    axg.semilogy(vbe, ic, ".", ms=4, label=lab)
    xx = np.linspace(vbe[m].min(), vbe[m].max(), 20)
    axg.semilogy(xx, np.exp(intercept + slope * xx), "k-", lw=0.8)
axg.set_xlabel("Vbe [V]"); axg.set_ylabel("Ic [A]")
axg.set_title("Gummel-Plot Ic–Vbe (+ Fit)  ->  Is, n")
axg.grid(True, which="both", alpha=0.3); axg.legend(fontsize=7)

# (2) Output + Early-Extrapolation
axo = ax[0, 1]
for lab, vce, ic, a, b in early_lines:
    p = axo.plot(vce, ic * 1e3, ".", ms=4, label=lab)
    xx = np.linspace(-VA_mean, vce[np.isfinite(vce)].max(), 30)
    axo.plot(xx, (a + b * xx) * 1e3, "-", lw=0.7, color=p[0].get_color())
axo.axhline(0, color="k", lw=0.5); axo.axvline(0, color="k", lw=0.5)
axo.axvline(-VA_mean, color="r", ls="--", lw=1, label=f"-VA≈{-VA_mean:.0f} V")
axo.set_xlabel("Vce [V]"); axo.set_ylabel("Ic [mA]")
axo.set_title("Ausgangskennlinie  ->  V_A (Early)")
axo.grid(True, alpha=0.3); axo.legend(fontsize=7)

# (3) hFE vs Ic
axh = ax[1, 0]
for lab, ic_mA, hfe in zip(tr4, xs4, ys4):
    axh.plot(ic_mA, hfe, ".-", ms=4, lw=0.6, label=lab)
axh.set_xlabel("Ic [mA]"); axh.set_ylabel("hFE")
axh.set_title(f"hFE–Ic (kein Hochstromabfall -> IKF >> {ic_max_seen*1e3:.0f} mA)")
axh.grid(True, alpha=0.3); axh.legend(fontsize=7)

# (4) Ic vs Ib
axb = ax[1, 1]
for lab, ib_uA, ic_mA in zip(tr3, xs3, ys3):
    axb.plot(ib_uA, ic_mA, ".-", ms=4, lw=0.6, label=lab)
axb.set_xlabel("Ib [µA]"); axb.set_ylabel("Ic [mA]")
axb.set_title(f"Ic–Ib  ->  beta ≈ {beta_slope:.0f}")
axb.grid(True, alpha=0.3); axb.legend(fontsize=7)

fig.tight_layout()
fig.savefig("bjt_extraction.png", dpi=110)

# ===========================================================================
# AUSGABE
# ===========================================================================
print("="*64)
print("  PARAMETER-EXTRAKTION  (T=300 K, VT = %.4f V)" % VT)
print("="*64)
print("  n (Emissionskoeffizient) je aktiver Kurve:",
      ", ".join("%.3f" % x for x in ns))
print("  -> n        = %.3f" % n_mean)
print()
print("  Is je Kurve [A]:", ", ".join("%.3e" % v for v in Is_vals))
print("  -> Is       = %.3e A" % Is_mean)
print()
print("  V_A je Ib-Kurve [V]:", ", ".join("%.1f" % v for v in VAs))
print("  -> V_A      = %.1f V" % VA_mean)
print()
print("  beta aus Ic-Ib-Steigung je Vce:",
      ", ".join("%.0f" % b for _, b in betas))
print("  -> beta_F (Steigung)      = %.0f" % beta_slope)
print("  -> beta_F (hFE-Maximum)   = %.0f" % beta_F)
print("     (hFE-Max ueber alle Daten: %.0f)" % hfe_max)
print()
print("  IKF : kein Hochstromabfall bis %.1f mA sichtbar" % (ic_max_seen*1e3))
print("        -> nur untere Schranke: IKF >> %.0f mA" % (ic_max_seen*1e3))
print()
print("  V_AB, R_B : aus diesen (Konstant-Ib-)Daten nicht robust bestimmbar")
print("="*64)
