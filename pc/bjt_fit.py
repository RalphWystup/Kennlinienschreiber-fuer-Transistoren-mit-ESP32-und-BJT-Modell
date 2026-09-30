"""
=======================================================================
 BJT global-Fit  -  die "nicht direkt messbaren" Parameter per
 Gesamt-Fehlerminimierung bestimmen (bzw. ihre Bestimmbarkeit pruefen)
=======================================================================
Vorgehen:
  1) Startwerte aus der feature-basierten Extraktion.
  2) Globaler Fit ALLER Parameter (Nelder-Mead, pure numpy) auf ALLE
     Messkurven gleichzeitig -> minimiert die Gesamtabweichung.
  3) Identifizierbarkeits-Check: welcher Parameter ist wirklich bestimmt
     (Fehler reagiert empfindlich) und welcher nicht (Fehler flach)?
  4) Overlay-Plot mit den gefitteten Parametern + Fehler vorher/nachher.

Nur numpy + matplotlib.   Aufruf:  python bjt_fit.py
"""
import numpy as np
import matplotlib.pyplot as plt

VT = 0.025852

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

DATA = {name: load(name + ".txt") for name in
        ["Ic_Vbe", "Ic_Vce", "hFE_Vce", "hFE_Ic", "Ic_Ib"]}

# --------------------------------------------------------------- Modell
def ic_model(vbe, vce, P):
    return P["Is"] * np.exp(vbe / (P["n"] * VT)) * (1 + vce / P["VA"])

def ib_model(vbe, vce, P):
    ic = ic_model(vbe, vce, P)
    beta_eff = P["Beta_F"] / np.sqrt(1 + ic / P["IKF"])
    ib = ic / beta_eff
    for _ in range(30):
        vbe_eff = vbe - ib * P["RB"]
        ib_new = (P["Is"] / beta_eff) * np.exp(vbe_eff / (P["n"] * VT)) * (1 + vce / P["Vab"])
        if np.all(np.abs(ib_new - ib) <= 1e-18 + 1e-9 * np.abs(ib_new)):
            ib = ib_new; break
        ib = ib_new
    return ib

def solve_vbe_for_ib(ib_target, vce, P):
    lo = np.full_like(vce, 0.2, float); hi = np.full_like(vce, 1.0, float)
    for _ in range(45):
        mid = 0.5 * (lo + hi)
        f = ib_model(mid, vce, P) - ib_target
        hi = np.where(f > 0, mid, hi); lo = np.where(f <= 0, mid, lo)
    return 0.5 * (lo + hi)

# --------------------------------------------------------------- Fehlerfunktion
def residuals_per_dataset(P):
    R = {}
    # Gummel (log-Fehler, sauberer Bereich)
    r = []
    for lab, vbe, ic_mA in zip(*DATA["Ic_Vbe"]):
        vce = tv(lab)
        if vce < 1: continue
        ic = ic_mA * 1e-3
        m = np.isfinite(vbe) & np.isfinite(ic) & (ic > 2e-5) & (ic < 2e-3)
        r += list(np.log(ic_model(vbe[m], vce, P)) - np.log(ic[m]))
    R["Gummel"] = np.array(r)
    # Ausgang (rel), Vce>1
    r = []
    for lab, vce, ic_mA in zip(*DATA["Ic_Vce"]):
        ib = tv(lab) * 1e-6
        m = np.isfinite(vce) & np.isfinite(ic_mA) & (vce > 1)
        vbe = solve_vbe_for_ib(ib, vce[m], P)
        r += list((ic_model(vbe, vce[m], P) * 1e3 - ic_mA[m]) / ic_mA[m])
    R["Ausgang"] = np.array(r)
    # hFE-Vce (rel), Vce>1
    r = []
    for lab, vce, hfe in zip(*DATA["hFE_Vce"]):
        ib = tv(lab) * 1e-6
        m = np.isfinite(vce) & np.isfinite(hfe) & (vce > 1)
        vbe = solve_vbe_for_ib(ib, vce[m], P)
        r += list((ic_model(vbe, vce[m], P) / ib - hfe[m]) / hfe[m])
    R["hFE-Vce"] = np.array(r)
    # hFE-Ic (rel)
    r = []
    for lab, ic_mA, hfe in zip(*DATA["hFE_Ic"]):
        vce = tv(lab)
        m = np.isfinite(ic_mA) & np.isfinite(hfe)
        # Ic ist gemessen -> passendes Ib aus Modell: hier ueber Ib-Achse abbilden
        ib = solve_vbe_for_ib  # placeholder
        # bestimme Vbe aus gemessenem Ic (Ic haengt nur von Vbe,Vce ab)
        vbe = np.log(ic_mA[m] * 1e-3 / (P["Is"] * (1 + vce / P["VA"]))) * (P["n"] * VT)
        hfe_mod = ic_model(vbe, vce, P) / ib_model(vbe, vce, P)
        r += list((hfe_mod - hfe[m]) / hfe[m])
    R["hFE-Ic"] = np.array(r)
    # Ic-Ib (rel)
    r = []
    for lab, ib_uA, ic_mA in zip(*DATA["Ic_Ib"]):
        vce = tv(lab)
        m = np.isfinite(ib_uA) & np.isfinite(ic_mA)
        vbe = solve_vbe_for_ib(ib_uA[m] * 1e-6, np.full(m.sum(), vce), P)
        r += list((ic_model(vbe, vce, P) * 1e3 - ic_mA[m]) / ic_mA[m])
    R["Ic-Ib"] = np.array(r)
    return R

def cost(P):
    R = residuals_per_dataset(P)
    # jeder Datensatz gleich gewichtet: Mittelwert der datensatzweisen MSE
    return float(np.mean([np.mean(np.square(r)) for r in R.values() if len(r)]))

def rms_report(P):
    R = residuals_per_dataset(P)
    return {k: float(np.sqrt(np.mean(np.square(v)))) for k, v in R.items() if len(v)}

# --------------------------------------------------- Parameter <-> Vektor
KEYS = ["n", "lIs", "Beta_F", "VA", "lVab", "lRB", "lIKF"]
def decode(t):
    return dict(n=t[0], Is=10**t[1], Beta_F=t[2], VA=t[3],
                Vab=10**t[4], RB=10**t[5], IKF=10**t[6])
def bounds_ok(P):
    return (0.8 < P["n"] < 1.6 and 1e-16 < P["Is"] < 1e-11 and
            50 < P["Beta_F"] < 600 and 20 < P["VA"] < 2000 and
            10 < P["Vab"] < 1e9 and 0.01 < P["RB"] < 2000 and 1e-3 < P["IKF"] < 1e4)
def fcost(t):
    P = decode(t)
    if not bounds_ok(P): return 1e9
    return cost(P)

# --------------------------------------------------- Nelder-Mead (pure numpy)
def nelder_mead(f, x0, dx, iters=600, a=1.0, g=2.0, r=0.5, s=0.5):
    n = len(x0)
    sim = [np.array(x0, float)]
    for i in range(n):
        y = np.array(x0, float); y[i] += dx[i]; sim.append(y)
    fv = [f(p) for p in sim]
    for _ in range(iters):
        idx = np.argsort(fv); sim = [sim[i] for i in idx]; fv = [fv[i] for i in idx]
        cen = np.mean(sim[:-1], axis=0)
        xr = cen + a * (cen - sim[-1]); fr = f(xr)
        if fv[0] <= fr < fv[-2]:
            sim[-1], fv[-1] = xr, fr
        elif fr < fv[0]:
            xe = cen + g * (cen - sim[-1]); fe = f(xe)
            if fe < fr: sim[-1], fv[-1] = xe, fe
            else:       sim[-1], fv[-1] = xr, fr
        else:
            xc = cen + r * (sim[-1] - cen); fc = f(xc)
            if fc < fv[-1]:
                sim[-1], fv[-1] = xc, fc
            else:
                for i in range(1, n + 1):
                    sim[i] = sim[0] + s * (sim[i] - sim[0]); fv[i] = f(sim[i])
    idx = int(np.argmin(fv))
    return sim[idx], fv[idx]

# =====================================================================
if __name__ == "__main__":
    # Startwerte (aus feature-basierter Extraktion)
    P0 = dict(n=1.004, Is=4.85e-14, Beta_F=272.0, VA=146.0,
              Vab=200.0, RB=20.0, IKF=0.1)     # freie in "sensiblen" Startbereich
    t0 = [P0["n"], np.log10(P0["Is"]), P0["Beta_F"], P0["VA"],
          np.log10(P0["Vab"]), np.log10(P0["RB"]), np.log10(P0["IKF"])]
    dx = [0.02, 0.1, 10.0, 20.0, 0.5, 0.5, 0.5]

    rms0 = rms_report(decode(t0))
    print("Start (Extraktion) RMS:", {k: f"{v*100:.2f}%" if k != "Gummel" else f"{v:.3f}" for k, v in rms0.items()})
    print("Optimiere ... (Nelder-Mead)")
    topt, copt = nelder_mead(fcost, t0, dx, iters=800)
    Pf = decode(topt)
    rms1 = rms_report(Pf)

    print("\n" + "=" * 60)
    print("  GLOBAL GEFITTETE PARAMETER")
    print("=" * 60)
    print(f"  n      = {Pf['n']:.3f}")
    print(f"  Is     = {Pf['Is']:.3e} A")
    print(f"  Beta_F = {Pf['Beta_F']:.1f}")
    print(f"  VA     = {Pf['VA']:.1f} V")
    print(f"  Vab    = {Pf['Vab']:.3g} V")
    print(f"  RB     = {Pf['RB']:.3g} Ohm")
    print(f"  IKF    = {Pf['IKF']:.3g} A")
    print("-" * 60)
    print("  RMS vorher -> nachher:")
    for k in rms0:
        u = "" if k == "Gummel" else "%"
        f0 = rms0[k]*(1 if k=="Gummel" else 100); f1 = rms1[k]*(1 if k=="Gummel" else 100)
        print(f"    {k:9s}: {f0:6.3f}{u} -> {f1:6.3f}{u}")
    print(f"  Gesamt-Cost: {fcost(t0):.3e} -> {copt:.3e}")

    # ---- Identifizierbarkeit: Cost-Empfindlichkeit je Parameter -----------
    print("-" * 60)
    print("  IDENTIFIZIERBARKEIT (Cost-Anstieg bei +20 % Parameteraenderung):")
    base = copt
    for j, name in enumerate(["n", "Is", "Beta_F", "VA", "Vab", "RB", "IKF"]):
        tp = list(topt)
        if name in ("Is", "Vab", "RB", "IKF"):
            tp[j] += np.log10(1.2)          # +20 % (log-Parameter)
        else:
            tp[j] *= 1.2
        rel = fcost(tp) / base - 1.0
        verdict = "gut bestimmt" if rel > 0.5 else ("schwach" if rel > 0.05 else "NICHT bestimmbar (flach)")
        print(f"    {name:7s}: Cost x{fcost(tp)/base:6.2f}   -> {verdict}")
    print("=" * 60)

    # ---- Overlay-Plot mit gefitteten Parametern ---------------------------
    fig, ax = plt.subplots(2, 3, figsize=(16, 9))
    fig.suptitle("Globaler Fit: Messung (Punkte) vs. Modell (Linien)", fontsize=13)
    a = ax[0, 0]
    for lab, vbe, ic_mA in zip(*DATA["Ic_Vbe"]):
        vce = tv(lab)
        if vce < 1: continue
        col = a.semilogy(vbe, ic_mA*1e-3, ".", ms=4, label=lab)[0].get_color()
        xx = np.linspace(0.45, np.nanmax(vbe), 80); a.semilogy(xx, ic_model(xx, vce, Pf), "-", color=col)
    a.set(xlabel="Vbe [V]", ylabel="Ic [A]", title="Ic–Vbe"); a.set_ylim(1e-7, 2e-2); a.grid(True, which="both", alpha=.3); a.legend(fontsize=7)
    a = ax[0, 1]
    for lab, vce, ic_mA in zip(*DATA["Ic_Vce"]):
        ib = tv(lab)*1e-6; col = a.plot(vce, ic_mA, ".", ms=3, label=lab)[0].get_color()
        xx = np.linspace(0.3, np.nanmax(vce), 60); a.plot(xx, ic_model(solve_vbe_for_ib(ib, xx, Pf), xx, Pf)*1e3, "-", color=col)
    a.set(xlabel="Vce [V]", ylabel="Ic [mA]", title="Ic–Vce"); a.grid(True, alpha=.3); a.legend(fontsize=7)
    a = ax[0, 2]
    for lab, vce, hfe in zip(*DATA["hFE_Vce"]):
        ib = tv(lab)*1e-6; col = a.plot(vce, hfe, ".", ms=3, label=lab)[0].get_color()
        xx = np.linspace(0.3, np.nanmax(vce), 60); a.plot(xx, ic_model(solve_vbe_for_ib(ib, xx, Pf), xx, Pf)/ib, "-", color=col)
    a.set(xlabel="Vce [V]", ylabel="hFE", title="hFE–Vce"); a.set_ylim(0, 320); a.grid(True, alpha=.3); a.legend(fontsize=7)
    a = ax[1, 0]
    for lab, ic_mA, hfe in zip(*DATA["hFE_Ic"]):
        vce = tv(lab); col = a.plot(ic_mA, hfe, ".", ms=4, label=lab)[0].get_color()
        ib_ax = np.linspace(5e-6, 45e-6, 60); vbe = solve_vbe_for_ib(ib_ax, np.full_like(ib_ax, vce), Pf)
        ic = ic_model(vbe, vce, Pf); a.plot(ic*1e3, ic/ib_ax, "-", color=col)
    a.set(xlabel="Ic [mA]", ylabel="hFE", title="hFE–Ic"); a.set_ylim(0, 320); a.grid(True, alpha=.3); a.legend(fontsize=7)
    a = ax[1, 1]
    for lab, ib_uA, ic_mA in zip(*DATA["Ic_Ib"]):
        vce = tv(lab); col = a.plot(ib_uA, ic_mA, ".", ms=4, label=lab)[0].get_color()
        xx = np.linspace(np.nanmin(ib_uA), np.nanmax(ib_uA), 40)*1e-6
        a.plot(xx*1e6, ic_model(solve_vbe_for_ib(xx, np.full_like(xx, vce), Pf), vce, Pf)*1e3, "-", color=col)
    a.set(xlabel="Ib [µA]", ylabel="Ic [mA]", title="Ic–Ib"); a.grid(True, alpha=.3); a.legend(fontsize=7)
    a = ax[1, 2]; a.axis("off")
    t = "GEFITTETE PARAMETER\n" + "-"*28 + "\n"
    t += f"n      = {Pf['n']:.3f}\nIs     = {Pf['Is']:.3e} A\nBeta_F = {Pf['Beta_F']:.1f}\nVA     = {Pf['VA']:.1f} V\n"
    t += f"Vab    = {Pf['Vab']:.3g} V\nRB     = {Pf['RB']:.3g} Ohm\nIKF    = {Pf['IKF']:.3g} A\n"
    a.text(0.0, 1.0, t, va="top", family="monospace", fontsize=11)
    fig.tight_layout(rect=[0, 0, 1, 0.97]); fig.savefig("bjt_fit.png", dpi=110)
    print("  Bild gespeichert: bjt_fit.png")
    plt.show()
