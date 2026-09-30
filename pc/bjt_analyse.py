"""
=======================================================================
 BJT-Komplettanalyse  (Gummel-Poon, vereinfacht)  -  EIN Programm
=======================================================================
Macht alles in einem Durchlauf:
  1) liest die 5 Kurventracer-Dateien,
  2) BESTIMMT die Modellparameter (Is, n, beta_F, VA) aus den Messungen,
  3) rechnet die Kennlinien aus den MODELLGLEICHUNGEN mit diesen Parametern,
  4) zeigt Messung (Punkte) und Modell (Linien) gemeinsam + Fehler (RMS).

Benoetigt nur numpy + matplotlib.   Aufruf:  python bjt_analyse.py

Modellgleichungen (aus der Skizze):
  Ic       = Is * exp(Vbe/(n*Vt)) * (1 + Vce/VA)
  beta_eff = Beta_F / sqrt(1 + Ic/IKF)
  Vbe_eff  = Vbe - Ib*RB
  Ib       = (Is/beta_eff) * exp(Vbe_eff/(n*Vt)) * (1 + Vce/Vab)
"""
import numpy as np
import matplotlib.pyplot as plt

VT = 0.025852     # Thermospannung bei T=300 K [V]

# ===========================================================================
#  EINLESEN
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
#  1) + 2)  PARAMETER-EXTRAKTION
# ===========================================================================
def extrahiere_parameter():
    # --- n aus Gummel-Slope (sauberer Bereich 20uA..2mA) --------------------
    tr, xs, ys = load("Ic_Vbe.txt")
    ns = []
    for lab, vbe, ic_mA in zip(tr, xs, ys):
        vce = tv(lab)
        if vce < 1:      # Vce=0V ist nicht aktiv
            continue
        ic = ic_mA * 1e-3
        m = np.isfinite(vbe) & np.isfinite(ic) & (ic > 2e-5) & (ic < 2e-3)
        if m.sum() < 4: continue
        slope, _ = np.polyfit(vbe[m], np.log(ic[m]), 1)
        ns.append(1.0 / (slope * VT))
    n = float(np.mean(ns))

    # --- VA (Early) aus Ausgangskennlinie -----------------------------------
    tr2, xs2, ys2 = load("Ic_Vce.txt")
    VAs = []
    for lab, vce, ic_mA in zip(tr2, xs2, ys2):
        ic = ic_mA * 1e-3
        m = np.isfinite(vce) & np.isfinite(ic) & (vce >= 1.5)
        if m.sum() < 4: continue
        b, a = np.polyfit(vce[m], ic[m], 1)      # ic = a + b*vce
        VAs.append(a / b)
    VA = float(np.mean(VAs))

    # --- Is global (n, VA fix) ----------------------------------------------
    lnIs = []
    for lab, vbe, ic_mA in zip(tr, xs, ys):
        vce = tv(lab)
        if vce < 1: continue
        ic = ic_mA * 1e-3
        m = np.isfinite(vbe) & np.isfinite(ic) & (ic > 2e-5) & (ic < 2e-3)
        lnIs += list(np.log(ic[m] / (1 + vce / VA)) - vbe[m] / (n * VT))
    Is = float(np.exp(np.mean(lnIs)))

    # --- beta_F aus Ic-Ib-Steigung ------------------------------------------
    tr3, xs3, ys3 = load("Ic_Ib.txt")
    betas = []
    for lab, ib_uA, ic_mA in zip(tr3, xs3, ys3):
        m = np.isfinite(ib_uA) & np.isfinite(ic_mA)
        if m.sum() < 3: continue
        b, _ = np.polyfit(ib_uA[m] * 1e-6, ic_mA[m] * 1e-3, 1)
        betas.append(b)
    beta_F = float(np.mean(betas))

    # --- hFE-Maximum + IKF-Schranke -----------------------------------------
    tr4, xs4, ys4 = load("hFE_Ic.txt")
    hfe_max = max(np.nanmax(y) for y in ys4)
    ic_max = max(np.nanmax(y) * 1e-3 for _, _, y in [(0, 0, ic) for ic in ys])   # groesster Ic (A)

    return dict(Is=Is, n=n, Beta_F=beta_F, VA=VA,
                IKF=1.0, Vab=1e6, RB=10.0, Vt=VT), dict(
        ns=ns, VAs=VAs, betas=betas, hfe_max=hfe_max, ic_max=ic_max)

# ===========================================================================
#  3)  MODELLGLEICHUNGEN
# ===========================================================================
def ic_model(vbe, vce, P):
    return P["Is"] * np.exp(vbe / (P["n"] * P["Vt"])) * (1 + vce / P["VA"])

def ib_model(vbe, vce, P):
    ic = ic_model(vbe, vce, P)
    beta_eff = P["Beta_F"] / np.sqrt(1 + ic / P["IKF"])
    ib = ic / beta_eff
    for _ in range(40):                         # Fixpunkt fuer Vbe_eff = Vbe - Ib*RB
        vbe_eff = vbe - ib * P["RB"]
        ib_new = (P["Is"] / beta_eff) * np.exp(vbe_eff / (P["n"] * P["Vt"])) * (1 + vce / P["Vab"])
        if np.all(np.abs(ib_new - ib) <= 1e-18 + 1e-9 * np.abs(ib_new)):
            ib = ib_new; break
        ib = ib_new
    return ib

def solve_vbe_for_ib(ib_target, vce, P):
    """Bisektion: Vbe, so dass Ib(Modell)=ib_target (Ib monoton in Vbe)."""
    lo = np.full_like(vce, 0.2, dtype=float)
    hi = np.full_like(vce, 1.0, dtype=float)
    for _ in range(70):
        mid = 0.5 * (lo + hi)
        f = ib_model(mid, vce, P) - ib_target
        hi = np.where(f > 0, mid, hi)
        lo = np.where(f <= 0, mid, lo)
    return 0.5 * (lo + hi)

# ===========================================================================
#  4)  DARSTELLUNG + FEHLER
# ===========================================================================
def analyse():
    P, info = extrahiere_parameter()
    rms = {}

    fig, ax = plt.subplots(2, 3, figsize=(16, 9))
    fig.suptitle("BJT-Analyse:  Messung (Punkte) vs. Modell aus den Gleichungen (Linien)", fontsize=13)

    # (0,0) Gummel Ic-Vbe
    a = ax[0, 0]; err = []
    tr, xs, ys = load("Ic_Vbe.txt")
    for lab, vbe, ic_mA in zip(tr, xs, ys):
        vce = tv(lab)
        if vce < 1: continue
        ic = ic_mA * 1e-3
        col = a.semilogy(vbe, ic, ".", ms=4, label=lab)[0].get_color()
        xx = np.linspace(0.45, np.nanmax(vbe), 100)
        a.semilogy(xx, ic_model(xx, vce, P), "-", lw=1.2, color=col)
        m = np.isfinite(vbe) & np.isfinite(ic) & (ic > 2e-5) & (ic < 2e-3)
        err += list(np.log(ic_model(vbe[m], vce, P)) - np.log(ic[m]))
    rms["Gummel Ic (ln)"] = np.sqrt(np.mean(np.square(err)))
    a.set(xlabel="Vbe [V]", ylabel="Ic [A]", title="Ic–Vbe (Gummel)")
    a.set_ylim(1e-7, 2e-2); a.grid(True, which="both", alpha=0.3); a.legend(fontsize=7)

    # (0,1) Ausgang Ic-Vce
    a = ax[0, 1]; err = []
    tr, xs, ys = load("Ic_Vce.txt")
    for lab, vce, ic_mA in zip(tr, xs, ys):
        ib = tv(lab) * 1e-6
        col = a.plot(vce, ic_mA, ".", ms=3, label=lab)[0].get_color()
        xx = np.linspace(0.3, np.nanmax(vce), 60)
        vbe = solve_vbe_for_ib(ib, xx, P)
        a.plot(xx, ic_model(vbe, xx, P) * 1e3, "-", lw=1.2, color=col)
        m = np.isfinite(vce) & np.isfinite(ic_mA) & (vce > 1)
        vbe_m = solve_vbe_for_ib(ib, vce[m], P)
        err += list((ic_model(vbe_m, vce[m], P) * 1e3 - ic_mA[m]) / ic_mA[m])
    rms["Ausgang Ic (rel)"] = np.sqrt(np.mean(np.square(err)))
    a.set(xlabel="Vce [V]", ylabel="Ic [mA]", title="Ic–Vce (Ausgang, konst. Ib)")
    a.grid(True, alpha=0.3); a.legend(fontsize=7)

    # (0,2) hFE-Vce
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

    # (1,0) hFE-Ic
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

    # (1,1) Ic-Ib
    a = ax[1, 1]; err = []
    tr, xs, ys = load("Ic_Ib.txt")
    for lab, ib_uA, ic_mA in zip(tr, xs, ys):
        vce = tv(lab)
        col = a.plot(ib_uA, ic_mA, ".", ms=4, label=lab)[0].get_color()
        xx = np.linspace(np.nanmin(ib_uA), np.nanmax(ib_uA), 40) * 1e-6
        vbe = solve_vbe_for_ib(xx, np.full_like(xx, vce), P)
        a.plot(xx * 1e6, ic_model(vbe, vce, P) * 1e3, "-", lw=1.2, color=col)
        m = np.isfinite(ib_uA) & np.isfinite(ic_mA)
        vbe_m = solve_vbe_for_ib(ib_uA[m] * 1e-6, np.full(m.sum(), vce), P)
        err += list((ic_model(vbe_m, vce, P) * 1e3 - ic_mA[m]) / ic_mA[m])
    rms["Ic-Ib (rel)"] = np.sqrt(np.mean(np.square(err)))
    a.set(xlabel="Ib [µA]", ylabel="Ic [mA]", title="Ic–Ib")
    a.grid(True, alpha=0.3); a.legend(fontsize=7)

    # (1,2) Parameter-/Ergebnis-Box
    a = ax[1, 2]; a.axis("off")
    t = "BESTIMMTE PARAMETER\n" + "-" * 30 + "\n"
    t += f"Is     = {P['Is']:.3e} A\n"
    t += f"n      = {P['n']:.3f}\n"
    t += f"Beta_F = {P['Beta_F']:.0f}\n"
    t += f"VA     = {P['VA']:.0f} V\n"
    t += f"IKF    = {P['IKF']:.3g} A   (nicht messbar)\n"
    t += f"Vab    = {P['Vab']:.0e} V  (nicht messbar)\n"
    t += f"RB     = {P['RB']:.0f} Ohm  (Default)\n"
    t += f"Vt     = {P['Vt']*1e3:.2f} mV (300 K)\n"
    t += "-" * 30 + "\nRMS Modell vs. Messung\n" + "-" * 30 + "\n"
    for k, v in rms.items():
        if "ln" in k:
            t += f"{k:16s} {v:5.3f}  (~{(np.exp(v)-1)*100:.1f} %)\n"
        else:
            t += f"{k:16s} {v*100:5.2f} %\n"
    a.text(0.0, 1.0, t, va="top", ha="left", family="monospace", fontsize=10)

    fig.tight_layout(rect=[0, 0, 1, 0.97])
    fig.savefig("bjt_analyse.png", dpi=110)

    # Konsolen-Ausgabe
    print("=" * 60)
    print("  BJT-PARAMETER (T=300 K)")
    print("=" * 60)
    print(f"  Is     = {P['Is']:.3e} A")
    print(f"  n      = {P['n']:.3f}   (je Kurve: " + ", ".join(f"{x:.3f}" for x in info['ns']) + ")")
    print(f"  Beta_F = {P['Beta_F']:.0f}     (hFE-Max: {info['hfe_max']:.0f})")
    print(f"  VA     = {P['VA']:.0f} V   (je Kurve: " + ", ".join(f"{x:.0f}" for x in info['VAs']) + ")")
    print(f"  IKF    : nicht bestimmbar (kein Abfall bis {info['ic_max']*1e3:.0f} mA) -> Default {P['IKF']} A")
    print(f"  Vab,RB : nicht bestimmbar -> Defaults {P['Vab']:.0e} V / {P['RB']:.0f} Ohm")
    print("-" * 60)
    for k, v in rms.items():
        print(f"  RMS {k:16s} = " + (f"{v:.3f} (~{(np.exp(v)-1)*100:.1f} % in Ic)" if "ln" in k else f"{v*100:.2f} %"))
    print("=" * 60)
    print("  Bild gespeichert: bjt_analyse.png")

    plt.show()

if __name__ == "__main__":
    analyse()
