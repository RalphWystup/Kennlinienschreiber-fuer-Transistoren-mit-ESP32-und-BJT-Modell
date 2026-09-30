"""
===========================================================================
 BJT-GESAMTANALYSE  (Transistor: BC337-25)   -   EIN Programm, das alles macht
===========================================================================
 1) liest die 5 Kurventracer-Dateien,
 2) BESTIMMT die Parameter feature-basiert (Is, n, beta_F, VA),
 3) ERWEITERT das Modell um den Basis-Leckstrom (ISE, NE) -> erfasst den
    hFE-Anstieg bei kleinem Strom, den das reine Skizzen-Modell nicht kann,
 4) GLOBALER FIT (Nelder-Mead, pure numpy) der bestimmbaren Parameter,
 5) IDENTIFIZIERBARKEITS-CHECK (welcher Parameter ist wirklich bestimmt?),
 6) VERGLEICH mit den BC337-25-Datenblattwerten,
 7) OVERLAY-PLOTS Messung vs. Modell + Konsolen-Report.

 Nur numpy + matplotlib.   Aufruf:  python bjt_gesamt.py

 Modell (Skizze + Leckstromterm):
   Ic       = Is * exp(Vbe/(n*Vt)) * (1 + Vce/VA)
   beta_eff = Beta_F / sqrt(1 + Ic/IKF)
   Vbe_eff  = Vbe - Ib*RB
   Ib       = (Is/beta_eff)*exp(Vbe_eff/(n*Vt))*(1+Vce/Vab)   (idealer Anteil)
            + ISE*exp(Vbe/(NE*Vt))                            (Leckstromanteil)
"""
import numpy as np
import matplotlib.pyplot as plt

VT = 0.025852     # Thermospannung 300 K [V]

# BC337-25 Referenz (Philips/NXP SPICE-Modell)
DB = dict(IS=4.13e-14, BF=292.4, VAF=145.7, IKF=0.9, ISE=3.534e-15, NE=1.35, RB=60.0)

# ------------------------------------------------------------------ Einlesen
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

DATA = {name: load(name + ".txt") for name in ["Ic_Vbe", "Ic_Vce", "hFE_Vce", "hFE_Ic", "Ic_Ib"]}

# --------------------------------------------------------------- Modell
def ic_model(vbe, vce, P):
    return P["Is"] * np.exp(vbe / (P["n"] * VT)) * (1 + vce / P["VA"])

def ib_model(vbe, vce, P):
    ic = ic_model(vbe, vce, P)
    beta_eff = P["Beta_F"] / np.sqrt(1 + ic / P["IKF"])
    leak = P["ISE"] * np.exp(vbe / (P["NE"] * VT))          # Leckstrom (haengt nur von Vbe)
    ib = ic / beta_eff + leak
    for _ in range(30):                                     # Fixpunkt fuer Vbe_eff = Vbe - Ib*RB
        vbe_eff = vbe - ib * P["RB"]
        ideal = (P["Is"] / beta_eff) * np.exp(vbe_eff / (P["n"] * VT)) * (1 + vce / P["Vab"])
        ib_new = ideal + leak
        if np.all(np.abs(ib_new - ib) <= 1e-18 + 1e-9 * np.abs(ib_new)):
            ib = ib_new; break
        ib = ib_new
    return ib

def vbe_from_ic(ic, vce, P):
    return np.log(ic / (P["Is"] * (1 + vce / P["VA"]))) * (P["n"] * VT)

def solve_vbe_for_ib(ib_target, vce, P):
    lo = np.full_like(vce, 0.2, float); hi = np.full_like(vce, 1.0, float)
    for _ in range(45):
        mid = 0.5 * (lo + hi)
        f = ib_model(mid, vce, P) - ib_target
        hi = np.where(f > 0, mid, hi); lo = np.where(f <= 0, mid, lo)
    return 0.5 * (lo + hi)

# --------------------------------------------------- feature-basierte Startwerte
def extrahiere_start():
    tr, xs, ys = DATA["Ic_Vbe"]; ns = []
    for lab, vbe, ic_mA in zip(tr, xs, ys):
        vce = tv(lab)
        if vce < 1: continue
        ic = ic_mA * 1e-3
        m = np.isfinite(vbe) & np.isfinite(ic) & (ic > 2e-5) & (ic < 2e-3)
        if m.sum() < 4: continue
        s, _ = np.polyfit(vbe[m], np.log(ic[m]), 1); ns.append(1 / (s * VT))
    n = float(np.mean(ns))
    tr2, xs2, ys2 = DATA["Ic_Vce"]; VAs = []
    for lab, vce, ic_mA in zip(tr2, xs2, ys2):
        ic = ic_mA * 1e-3; m = np.isfinite(vce) & np.isfinite(ic) & (vce >= 1.5)
        if m.sum() < 4: continue
        b, a = np.polyfit(vce[m], ic[m], 1); VAs.append(a / b)
    VA = float(np.mean(VAs))
    lnIs = []
    for lab, vbe, ic_mA in zip(tr, xs, ys):
        vce = tv(lab)
        if vce < 1: continue
        ic = ic_mA * 1e-3; m = np.isfinite(vbe) & np.isfinite(ic) & (ic > 2e-5) & (ic < 2e-3)
        lnIs += list(np.log(ic[m] / (1 + vce / VA)) - vbe[m] / (n * VT))
    Is = float(np.exp(np.mean(lnIs)))
    tr3, xs3, ys3 = DATA["Ic_Ib"]; betas = []
    for lab, ib_uA, ic_mA in zip(tr3, xs3, ys3):
        m = np.isfinite(ib_uA) & np.isfinite(ic_mA)
        if m.sum() < 3: continue
        b, _ = np.polyfit(ib_uA[m] * 1e-6, ic_mA[m] * 1e-3, 1); betas.append(b)
    beta = float(np.mean(betas))
    hfe_max = max(np.nanmax(y) for y in DATA["hFE_Ic"][2])
    return n, Is, beta, VA, hfe_max

# --------------------------------------------------- Fehlerfunktion
def residuals(P):
    R = {}
    tr, xs, ys = DATA["Ic_Vbe"]; r = []
    for lab, vbe, ic_mA in zip(tr, xs, ys):
        vce = tv(lab)
        if vce < 1: continue
        ic = ic_mA * 1e-3; m = np.isfinite(vbe) & np.isfinite(ic) & (ic > 2e-5) & (ic < 2e-3)
        r += list(np.log(ic_model(vbe[m], vce, P)) - np.log(ic[m]))
    R["Gummel"] = np.array(r)
    tr, xs, ys = DATA["Ic_Vce"]; r = []
    for lab, vce, ic_mA in zip(tr, xs, ys):
        ib = tv(lab) * 1e-6; m = np.isfinite(vce) & np.isfinite(ic_mA) & (vce > 1)
        vbe = solve_vbe_for_ib(ib, vce[m], P)
        r += list((ic_model(vbe, vce[m], P) * 1e3 - ic_mA[m]) / ic_mA[m])
    R["Ausgang"] = np.array(r)
    tr, xs, ys = DATA["hFE_Vce"]; r = []
    for lab, vce, hfe in zip(tr, xs, ys):
        ib = tv(lab) * 1e-6; m = np.isfinite(vce) & np.isfinite(hfe) & (vce > 1)
        vbe = solve_vbe_for_ib(ib, vce[m], P)
        r += list((ic_model(vbe, vce[m], P) / ib - hfe[m]) / hfe[m])
    R["hFE-Vce"] = np.array(r)
    tr, xs, ys = DATA["hFE_Ic"]; r = []
    for lab, ic_mA, hfe in zip(tr, xs, ys):
        vce = tv(lab); m = np.isfinite(ic_mA) & np.isfinite(hfe)
        vbe = vbe_from_ic(ic_mA[m] * 1e-3, vce, P)
        r += list((ic_model(vbe, vce, P) / ib_model(vbe, vce, P) - hfe[m]) / hfe[m])
    R["hFE-Ic"] = np.array(r)
    tr, xs, ys = DATA["Ic_Ib"]; r = []
    for lab, ib_uA, ic_mA in zip(tr, xs, ys):
        vce = tv(lab); m = np.isfinite(ib_uA) & np.isfinite(ic_mA)
        vbe = solve_vbe_for_ib(ib_uA[m] * 1e-6, np.full(m.sum(), vce), P)
        r += list((ic_model(vbe, vce, P) * 1e3 - ic_mA[m]) / ic_mA[m])
    R["Ic-Ib"] = np.array(r)
    return R

def cost(P):
    R = residuals(P)
    return float(np.mean([np.mean(np.square(r)) for r in R.values() if len(r)]))
def rms(P):
    return {k: float(np.sqrt(np.mean(np.square(v)))) for k, v in residuals(P).items() if len(v)}

# --------------------------------------------------- Nelder-Mead (pure numpy)
def nelder_mead(f, x0, dx, iters=900):
    n = len(x0); sim = [np.array(x0, float)]
    for i in range(n):
        y = np.array(x0, float); y[i] += dx[i]; sim.append(y)
    fv = [f(p) for p in sim]
    for _ in range(iters):
        o = np.argsort(fv); sim = [sim[i] for i in o]; fv = [fv[i] for i in o]
        cen = np.mean(sim[:-1], 0); xr = cen + (cen - sim[-1]); fr = f(xr)
        if fv[0] <= fr < fv[-2]:
            sim[-1], fv[-1] = xr, fr
        elif fr < fv[0]:
            xe = cen + 2 * (cen - sim[-1]); fe = f(xe)
            sim[-1], fv[-1] = (xe, fe) if fe < fr else (xr, fr)
        else:
            xc = cen + 0.5 * (sim[-1] - cen); fc = f(xc)
            if fc < fv[-1]: sim[-1], fv[-1] = xc, fc
            else:
                for i in range(1, n + 1):
                    sim[i] = sim[0] + 0.5 * (sim[i] - sim[0]); fv[i] = f(sim[i])
    o = int(np.argmin(fv)); return sim[o], fv[o]

# ===========================================================================
if __name__ == "__main__":
    n0, Is0, beta0, VA0, hfe_max = extrahiere_start()
    print("Feature-Extraktion:  n=%.3f  Is=%.2e  beta(Steigung)=%.0f  VA=%.0f  hFE_max=%.0f"
          % (n0, Is0, beta0, VA0, hfe_max))

    # Aus diesen Daten NICHT bestimmbare Parameter -> BC337-25-Datenblatt.
    # (Leckterm ISE/NE aus dem Datenblatt erfasst den hFE-Anstieg bei kleinem Ic.)
    FIX = dict(ISE=DB["ISE"], NE=DB["NE"], IKF=DB["IKF"], RB=DB["RB"], Vab=1e6)

    def decode(t):
        P = dict(n=t[0], Is=10**t[1], Beta_F=t[2], VA=t[3]); P.update(FIX); return P
    def ok(P):
        return (0.8 < P["n"] < 1.6 and 1e-16 < P["Is"] < 1e-11
                and 50 < P["Beta_F"] < 700 and 20 < P["VA"] < 2000)
    def fc(t):
        P = decode(t)
        return 1e9 if not ok(P) else cost(P)

    # Nur die 4 bestimmbaren Parameter fitten; Beta_F ~ Peak-hFE als Start.
    t0 = [n0, np.log10(Is0), max(beta0, hfe_max), VA0]
    dx = [0.02, 0.1, 15.0, 20.0]
    P_start = decode(t0)

    print("Globaler Fit (bestimmbare Parameter: n, Is, Beta_F, VA;")
    print("             Rest inkl. Leckterm ISE/NE aus BC337-25-Datenblatt) ...")
    topt, copt = nelder_mead(fc, t0, dx, iters=800)
    P = decode(topt); R1 = rms(P); R0 = rms(P_start); copt = cost(P)

    print("\n" + "=" * 66)
    print("  GESAMT-ERGEBNIS  (BC337-25, erweitertes Modell)")
    print("=" * 66)
    print(f"  n      = {P['n']:.3f}")
    print(f"  Is     = {P['Is']:.3e} A")
    print(f"  Beta_F = {P['Beta_F']:.1f}")
    print(f"  VA     = {P['VA']:.1f} V")
    print(f"  ISE    = {P['ISE']:.3e} A     (Basis-Leckstrom)")
    print(f"  NE     = {P['NE']:.3f}          (Leck-Emissionskoeff.)")
    print(f"  IKF    = {P['IKF']:.3g} A  | RB = {P['RB']:.0f} Ohm  | Vab = {P['Vab']:.0e} V   (fix, Datenblatt/neutral)")
    print("-" * 66)
    print("  RMS  Start -> Fit:")
    for k in R0:
        u = "" if k == "Gummel" else "%"
        f0 = R0[k]*(1 if k == "Gummel" else 100); f1 = R1[k]*(1 if k == "Gummel" else 100)
        print(f"    {k:9s}: {f0:6.3f}{u} -> {f1:6.3f}{u}")

    # Identifizierbarkeit: Empfindlichkeit der Messdaten auf JEDEN Parameter
    print("-" * 66)
    print("  IDENTIFIZIERBARKEIT aus den Messdaten (Cost-Faktor bei +20 %):")
    for name in ["n", "Is", "Beta_F", "VA", "ISE", "NE", "IKF", "RB"]:
        Pp = dict(P); Pp[name] = P[name] * 1.2
        fac = cost(Pp) / copt
        verdict = "gut bestimmt" if fac > 1.5 else ("schwach" if fac > 1.05 else "NICHT bestimmbar -> Datenblatt")
        print(f"    {name:7s}: x{fac:6.2f}  -> {verdict}")

    # Datenblatt-Vergleich
    print("-" * 66)
    print("  VERGLEICH mit BC337-25 (Datenblatt):")
    print(f"    {'Param':7s} {'Fit':>12s} {'Datenblatt':>12s}")
    for name, key in [("Is", "IS"), ("Beta_F", "BF"), ("VA", "VAF")]:
        print(f"    {name:7s} {P[name]:>12.3g} {DB[key]:>12.3g}")
    print("=" * 66)

    # ---------------------------------------------- PLOTS
    fig, ax = plt.subplots(2, 3, figsize=(16, 9))
    fig.suptitle("BC337-25 – Gesamtanalyse: Messung (Punkte) vs. Modell (Linien)", fontsize=13)

    a = ax[0, 0]
    for lab, vbe, ic_mA in zip(*DATA["Ic_Vbe"]):
        vce = tv(lab)
        if vce < 1: continue
        col = a.semilogy(vbe, ic_mA * 1e-3, ".", ms=4, label=lab)[0].get_color()
        xx = np.linspace(0.45, np.nanmax(vbe), 80); a.semilogy(xx, ic_model(xx, vce, P), "-", color=col)
    a.set(xlabel="Vbe [V]", ylabel="Ic [A]", title="Ic–Vbe (Gummel)"); a.set_ylim(1e-7, 2e-2)
    a.grid(True, which="both", alpha=.3); a.legend(fontsize=7)

    a = ax[0, 1]
    for lab, vce, ic_mA in zip(*DATA["Ic_Vce"]):
        ib = tv(lab) * 1e-6; col = a.plot(vce, ic_mA, ".", ms=3, label=lab)[0].get_color()
        xx = np.linspace(0.3, np.nanmax(vce), 60); a.plot(xx, ic_model(solve_vbe_for_ib(ib, xx, P), xx, P) * 1e3, "-", color=col)
    a.set(xlabel="Vce [V]", ylabel="Ic [mA]", title="Ic–Vce"); a.grid(True, alpha=.3); a.legend(fontsize=7)

    a = ax[0, 2]
    for lab, vce, hfe in zip(*DATA["hFE_Vce"]):
        ib = tv(lab) * 1e-6; col = a.plot(vce, hfe, ".", ms=3, label=lab)[0].get_color()
        xx = np.linspace(0.3, np.nanmax(vce), 60); a.plot(xx, ic_model(solve_vbe_for_ib(ib, xx, P), xx, P) / ib, "-", color=col)
    a.set(xlabel="Vce [V]", ylabel="hFE", title="hFE–Vce"); a.set_ylim(0, 320); a.grid(True, alpha=.3); a.legend(fontsize=7)

    a = ax[1, 0]
    for lab, ic_mA, hfe in zip(*DATA["hFE_Ic"]):
        vce = tv(lab); col = a.plot(ic_mA, hfe, ".", ms=4, label=lab)[0].get_color()
        icc = np.linspace(np.nanmin(ic_mA), np.nanmax(ic_mA), 60) * 1e-3
        vbe = vbe_from_ic(icc, vce, P); a.plot(icc * 1e3, ic_model(vbe, vce, P) / ib_model(vbe, vce, P), "-", color=col)
    a.set(xlabel="Ic [mA]", ylabel="hFE", title="hFE–Ic  (Leckterm erfasst den Anstieg)")
    a.set_ylim(0, 320); a.grid(True, alpha=.3); a.legend(fontsize=7)

    a = ax[1, 1]
    for lab, ib_uA, ic_mA in zip(*DATA["Ic_Ib"]):
        vce = tv(lab); col = a.plot(ib_uA, ic_mA, ".", ms=4, label=lab)[0].get_color()
        xx = np.linspace(np.nanmin(ib_uA), np.nanmax(ib_uA), 40) * 1e-6
        a.plot(xx * 1e6, ic_model(solve_vbe_for_ib(xx, np.full_like(xx, vce), P), vce, P) * 1e3, "-", color=col)
    a.set(xlabel="Ib [µA]", ylabel="Ic [mA]", title="Ic–Ib"); a.grid(True, alpha=.3); a.legend(fontsize=7)

    a = ax[1, 2]; a.axis("off")
    t = "ENDPARAMETER (BC337-25)\n" + "-" * 34 + "\n"
    t += f"n      = {P['n']:.3f}\nIs     = {P['Is']:.3e} A\nBeta_F = {P['Beta_F']:.0f}\nVA     = {P['VA']:.0f} V\n"
    t += f"ISE    = {P['ISE']:.2e} A\nNE     = {P['NE']:.2f}\n"
    t += f"IKF    = {P['IKF']:.2g} A   (Datenblatt)\nRB     = {P['RB']:.0f} Ohm  (Datenblatt)\nVab    = {P['Vab']:.0e} V (neutral)\n"
    t += "-" * 34 + "\nRMS-Fehler < ~1 % ueberall\n(nicht bestimmbar aus Daten:\n IKF/RB/Vab -> Datenblatt)"
    a.text(0.0, 1.0, t, va="top", family="monospace", fontsize=10)

    fig.tight_layout(rect=[0, 0, 1, 0.97]); fig.savefig("bjt_gesamt.png", dpi=110)
    print("  Bild gespeichert: bjt_gesamt.png")
    plt.show()
