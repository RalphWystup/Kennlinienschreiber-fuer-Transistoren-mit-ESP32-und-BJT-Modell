"""
=======================================================================
 bjt_kennwerte.py  -  ein Satz Zahlen fuer Manuskript und Browser-Seite
=======================================================================
 Dieses Skript aendert keines der geprueften Skripte (bjt_extract.py,
 bjt_fit.py, bjt_gesamt.py, bjt_hparam.py, bjt_verstaerker.py,
 bjt_4quadrant.py), sondern rechnet mit deren Ergebnissen weiter:

   1) Es vergleicht die beiden im Projekt auftretenden Parametersaetze
      ("Arbeitssatz" aus bjt_hparam.py / bjt_verstaerker.py und
      "Fitsatz" aus bjt_fit.py) gegen dieselben Messdaten und gibt
      RMS- und Groesstabweichung je Kennfeld an.
   2) Es bestimmt fuer beide Saetze die h-Parameter im Arbeitspunkt
      (IC = 5 mA, VCE = 5 V) mit denselben Formeln wie bjt_hparam.py.
   3) Es rechnet fuer beide Saetze die Emitterschaltung aus
      bjt_verstaerker.py (Newton-Raphson-Arbeitspunkt, h -> A, Kette).
   4) Es schreibt alle Zahlen nach kennwerte.json; Manuskript und
      Browser-Seite lesen von dort, damit keine Zahl zweimal getippt wird.

 Nur numpy.   Aufruf:  python3 bjt_kennwerte.py
"""
import json
import numpy as np

VT = 0.025852

# --- die beiden Parametersaetze, wie sie in den geprueften Skripten stehen ---
SAETZE = {
    "Arbeitssatz": dict(n=1.004, Is=4.726e-14, Beta_F=249.9, VA=146.0,
                        IKF=0.9, RB=60.0, Vab=1e6),          # bjt_hparam.py
    "Fitsatz":     dict(n=1.004, Is=4.765e-14, Beta_F=253.2, VA=126.6,
                        IKF=4.05, RB=18.8, Vab=1.39e3),      # bjt_fit.py
}

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

DATA = {n: load(n + ".txt") for n in ["Ic_Vbe", "Ic_Vce", "Ic_Ib", "hFE_Vce", "hFE_Ic"]}

# ------------------------------------------------------------------ Modell
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
    for _ in range(60):
        mid = 0.5 * (lo + hi); f = ib_model(mid, vce, P) - ib
        hi = np.where(f > 0, mid, hi); lo = np.where(f <= 0, mid, lo)
    return 0.5 * (lo + hi)

# ------------------------------------------------------------------ 1) Abweichungen
def abweichungen(P):
    out = {}
    # Ausgangskennlinienfeld Ic(Vce) bei festem Ib, nur aktiver Bereich Vce>1V
    r = []
    for lab, vce, ic_mA in zip(*DATA["Ic_Vce"]):
        ib = tv(lab) * 1e-6
        m = np.isfinite(vce) & np.isfinite(ic_mA) & (vce > 1.0)
        vbe = solve_vbe_for_ib(ib, vce[m], P)
        r += list((ic_model(vbe, vce[m], P) * 1e3 - ic_mA[m]) / ic_mA[m])
    r = np.array(r); out["Ic_Vce"] = dict(n=len(r), rms=float(np.sqrt(np.mean(r**2))), max=float(np.max(np.abs(r))))
    # Stromsteuerkennlinie Ic(Ib)
    r = []
    for lab, ib_uA, ic_mA in zip(*DATA["Ic_Ib"]):
        vce = tv(lab)
        m = np.isfinite(ib_uA) & np.isfinite(ic_mA)
        vbe = solve_vbe_for_ib(ib_uA[m] * 1e-6, np.full(int(m.sum()), vce), P)
        r += list((ic_model(vbe, vce, P) * 1e3 - ic_mA[m]) / ic_mA[m])
    r = np.array(r); out["Ic_Ib"] = dict(n=len(r), rms=float(np.sqrt(np.mean(r**2))), max=float(np.max(np.abs(r))))
    # Gummel Ic(Vbe), log-Fehler im sauberen Bereich
    r = []
    for lab, vbe, ic_mA in zip(*DATA["Ic_Vbe"]):
        vce = tv(lab)
        if vce < 1: continue
        ic = ic_mA * 1e-3
        m = np.isfinite(vbe) & np.isfinite(ic) & (ic > 2e-5) & (ic < 2e-3)
        r += list(np.log(ic_model(vbe[m], vce, P)) - np.log(ic[m]))
    r = np.array(r); out["Ic_Vbe_ln"] = dict(n=len(r), rms=float(np.sqrt(np.mean(r**2))), max=float(np.max(np.abs(r))))
    # hFE(Vce)
    r = []
    for lab, vce, hfe in zip(*DATA["hFE_Vce"]):
        ib = tv(lab) * 1e-6
        m = np.isfinite(vce) & np.isfinite(hfe) & (vce > 1.0)
        vbe = solve_vbe_for_ib(ib, vce[m], P)
        r += list((ic_model(vbe, vce[m], P) / ib - hfe[m]) / hfe[m])
    r = np.array(r); out["hFE_Vce"] = dict(n=len(r), rms=float(np.sqrt(np.mean(r**2))), max=float(np.max(np.abs(r))))
    return out

# ------------------------------------------------------------------ 2) h-Parameter im AP
def hparameter(P, IC_Q=5.0e-3, VCE_Q=5.0):
    VBE_Q = float(vbe_from_ic(IC_Q, VCE_Q, P))
    IB_Q = float(ib_model(VBE_Q, VCE_Q, P))
    dVb, dVc = 1e-4, 1e-2
    gm = float((ic_model(VBE_Q + dVb, VCE_Q, P) - ic_model(VBE_Q - dVb, VCE_Q, P)) / (2 * dVb))
    go = float((ic_model(VBE_Q, VCE_Q + dVc, P) - ic_model(VBE_Q, VCE_Q - dVc, P)) / (2 * dVc))
    gpi = float((ib_model(VBE_Q + dVb, VCE_Q, P) - ib_model(VBE_Q - dVb, VCE_Q, P)) / (2 * dVb))
    gmu = float((ib_model(VBE_Q, VCE_Q + dVc, P) - ib_model(VBE_Q, VCE_Q - dVc, P)) / (2 * dVc))
    h11 = 1.0 / gpi; h21 = gm / gpi; h12 = -gmu / gpi; h22 = go - gm * gmu / gpi
    return dict(IC=IC_Q, VCE=VCE_Q, VBE=VBE_Q, IB=IB_Q, gm=gm,
                h11=h11, h12=h12, h21=h21, h22=h22, Dh=h11 * h22 - h12 * h21)

# ------------------------------------------------------------------ 3) Emitterschaltung
V_CC, R_C, R_L, R_I, R_B = 15.0, 1.0e3, 10.0e3, 1.0e3, 510.0e3
V_BB = V_CC

def verstaerker(P):
    def F(vbe, vce):
        return np.array([(V_BB - vbe) / R_B - float(ib_model(vbe, vce, P)),
                         (V_CC - vce) / R_C - float(ic_model(vbe, vce, P))])
    def J(vbe, vce):
        hb, hc = 1e-6, 1e-4
        return np.column_stack([(F(vbe + hb, vce) - F(vbe - hb, vce)) / (2 * hb),
                                (F(vbe, vce + hc) - F(vbe, vce - hc)) / (2 * hc)])
    x = np.array([0.65, V_CC / 2]); it = 0
    for i in range(60):
        f = F(x[0], x[1])
        if np.all(np.abs(f) < 1e-12): it = i + 1; break
        d = np.linalg.solve(J(x[0], x[1]), -f)
        d[0] = np.clip(d[0], -0.05, 0.05); d[1] = np.clip(d[1], -2.0, 2.0)
        x += d
        x[0] = min(max(x[0], 0.2), 1.0); x[1] = min(max(x[1], 1e-3), V_CC)
        it = i + 1
    VBE_Q, VCE_Q = float(x[0]), float(x[1])
    IB_Q = float(ib_model(VBE_Q, VCE_Q, P)); IC_Q = float(ic_model(VBE_Q, VCE_Q, P))
    dVb, dVc = 1e-4, 1e-2
    gm = float((ic_model(VBE_Q + dVb, VCE_Q, P) - ic_model(VBE_Q - dVb, VCE_Q, P)) / (2 * dVb))
    go = float((ic_model(VBE_Q, VCE_Q + dVc, P) - ic_model(VBE_Q, VCE_Q - dVc, P)) / (2 * dVc))
    gpi = float((ib_model(VBE_Q + dVb, VCE_Q, P) - ib_model(VBE_Q - dVb, VCE_Q, P)) / (2 * dVb))
    gmu = float((ib_model(VBE_Q, VCE_Q + dVc, P) - ib_model(VBE_Q, VCE_Q - dVc, P)) / (2 * dVc))
    h11 = 1.0 / gpi; h21 = gm / gpi; h12 = -gmu / gpi; h22 = go - gm * gmu / gpi
    Dh = h11 * h22 - h12 * h21
    A_T = (1.0 / h21) * np.array([[-Dh, -h11], [-h22, -1.0]])
    A = np.array([[1.0, 0.0], [1.0 / R_B, 1.0]]) @ A_T @ np.array([[1.0, 0.0], [1.0 / R_C, 1.0]])
    r_ein = (A[0, 0] * R_L + A[0, 1]) / (A[1, 0] * R_L + A[1, 1])
    r_aus = (A[1, 1] * R_I + A[0, 1]) / (A[1, 0] * R_I + A[0, 0])
    A_V = R_L / (A[0, 0] * R_L + A[0, 1])
    A_I = 1.0 / (A[1, 0] * R_L + A[1, 1])
    A_VS = A_V * r_ein / (r_ein + R_I)
    return dict(iter=it, VBE=VBE_Q, VCE=VCE_Q, IB=IB_Q, IC=IC_Q, hFE=IC_Q / IB_Q,
                h11=h11, h12=h12, h21=h21, h22=h22, Dh=Dh,
                A_T=A_T.tolist(), A_ges=A.tolist(),
                r_ein=float(r_ein), r_aus=float(r_aus),
                A_v=float(A_V), A_i=float(A_I), A_vs=float(A_VS))

# ------------------------------------------------------------------ Ausgabe
if __name__ == "__main__":
    erg = {"VT": VT, "schaltung": dict(Vcc=V_CC, Rc=R_C, Rb=R_B, RL=R_L, Ri=R_I), "saetze": {}}
    for name, P in SAETZE.items():
        ab = abweichungen(P); hp = hparameter(P); vs = verstaerker(P)
        erg["saetze"][name] = dict(P=P, abweichung=ab, hparam=hp, verstaerker=vs)
        print("=" * 70)
        print("  %s:  n=%.3f  Is=%.3e A  Beta_F=%.1f  VA=%.1f V  IKF=%.3g A  RB=%.3g Ohm  Vab=%.3g V"
              % (name, P["n"], P["Is"], P["Beta_F"], P["VA"], P["IKF"], P["RB"], P["Vab"]))
        print("-" * 70)
        for k, v in ab.items():
            e = "" if k == "Ic_Vbe_ln" else " %"
            f = 1.0 if k == "Ic_Vbe_ln" else 100.0
            print("    %-10s  n=%3d   RMS=%7.3f%s   groesste Abweichung=%7.3f%s"
                  % (k, v["n"], v["rms"] * f, e, v["max"] * f, e))
        print("-" * 70)
        print("    AP  IC=%.2f mA  VCE=%.2f V  ->  VBE=%.1f mV  IB=%.2f uA"
              % (hp["IC"] * 1e3, hp["VCE"], hp["VBE"] * 1e3, hp["IB"] * 1e6))
        print("    h11e=%9.1f Ohm   h21e=%7.1f   h22e=%8.2f uS   h12e=%10.3e"
              % (hp["h11"], hp["h21"], hp["h22"] * 1e6, hp["h12"]))
        print("-" * 70)
        print("    Emitterschaltung: AP VBE=%.1f mV VCE=%.2f V IB=%.2f uA IC=%.2f mA hFE=%.0f"
              % (vs["VBE"] * 1e3, vs["VCE"], vs["IB"] * 1e6, vs["IC"] * 1e3, vs["hFE"]))
        print("    r_ein=%.0f Ohm  r_aus=%.0f Ohm  A_v=%.1f  A_i=%.1f  A_vs=%.1f"
              % (vs["r_ein"], vs["r_aus"], vs["A_v"], vs["A_i"], vs["A_vs"]))
    print("=" * 70)
    json.dump(erg, open("kennwerte.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print("  geschrieben: kennwerte.json")
