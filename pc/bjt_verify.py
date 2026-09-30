"""
Verifikation: extrahierte Parameter -> Modellgleichungen -> ueber Messung legen.
Erzeugt bjt_verify.png und RMS-Abweichungen auf stdout.
"""
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

VT = 0.025852

# ---- extrahierte Parameter -------------------------------------------------
n_p    = 1.004
VA     = 146.0
beta_F = 272.0
# Is wird gleich global (mit n, VA fix) bestmoeglich gefittet.
# nicht bestimmbare -> unkritische Defaults (in diesem Messbereich ~ neutral):
IKF, VAB, RB = 1.0, 1e6, 0.0

def load(fname):
    lines = open(fname, encoding="utf-8-sig").read().splitlines()
    for i, ln in enumerate(lines):
        c = ln.split("\t")
        if c[0] == "Trace:": traces = [x for x in c[1:] if x.strip()]
        if c[0] == "Point": hdr = i; break
    data = [[float(x.strip().replace(",", ".")) if x.strip() else np.nan
             for x in ln.split("\t")] for ln in lines[hdr+1:] if ln.strip()]
    a = np.array(data)
    return traces, [a[:, 1+2*i] for i in range(len(traces))], [a[:, 2+2*i] for i in range(len(traces))]

def tv(label):
    s = label.split("=")[1].replace("µA", "").replace("V", "").replace(",", ".")
    return float(s)

# ---- Is global fitten (n, VA fix) -----------------------------------------
tr, xs, ys = load("Ic_Vbe.txt")
lnIs = []
for lab, vbe, ic_mA in zip(tr, xs, ys):
    vce = tv(lab)
    if vce < 1: continue
    ic = ic_mA*1e-3
    m = np.isfinite(vbe) & np.isfinite(ic) & (ic > 2e-5) & (ic < 2e-3)
    # ln(Is) = ln( Ic/(1+Vce/VA) ) - Vbe/(n*VT)
    lnIs += list(np.log(ic[m]/(1+vce/VA)) - vbe[m]/(n_p*VT))
Is = float(np.exp(np.mean(lnIs)))

def model_Ic(vbe, vce):
    return Is*np.exp(vbe/(n_p*VT))*(1+vce/VA)

# ===========================================================================
fig, ax = plt.subplots(2, 2, figsize=(13, 9))
rms = {}

# (1) Gummel: Ic-Vbe  Modell vs Messung
axg = ax[0, 0]
err = []
for lab, vbe, ic_mA in zip(tr, xs, ys):
    vce = tv(lab)
    if vce < 1: continue
    ic = ic_mA*1e-3
    p = axg.semilogy(vbe, ic, ".", ms=4, label=lab+" (Mess)")
    m = np.isfinite(vbe) & (vbe > 0.45)
    xx = np.sort(vbe[m])
    axg.semilogy(xx, model_Ic(xx, vce), "-", lw=1, color=p[0].get_color())
    mm = np.isfinite(vbe) & np.isfinite(ic) & (ic > 2e-5) & (ic < 2e-3)
    err += list(np.log(model_Ic(vbe[mm], vce)) - np.log(ic[mm]))
rms["Gummel ln(Ic)"] = np.sqrt(np.mean(np.array(err)**2))
axg.set_xlabel("Vbe [V]"); axg.set_ylabel("Ic [A]")
axg.set_title("Ic-Vbe: Modell (Linie) vs Messung (Punkte)")
axg.set_ylim(1e-7, 2e-2); axg.grid(True, which="both", alpha=0.3); axg.legend(fontsize=6)

# (2) Ausgangskennlinie: Ic = beta_F*Ib*(1+Vce/VA)
axo = ax[0, 1]
tr2, xs2, ys2 = load("Ic_Vce.txt")
err = []
for lab, vce, ic_mA in zip(tr2, xs2, ys2):
    ib = tv(lab)*1e-6
    p = axo.plot(vce, ic_mA, ".", ms=3, label=lab)
    xx = np.linspace(0.2, np.nanmax(vce), 50)
    ic_mod = beta_F*ib*(1+xx/VA)*1e3
    axo.plot(xx, ic_mod, "-", lw=1, color=p[0].get_color())
    m = np.isfinite(vce) & np.isfinite(ic_mA) & (vce > 1)
    ic_m = beta_F*ib*(1+vce[m]/VA)*1e3
    err += list((ic_m - ic_mA[m])/ic_mA[m])
rms["Ausgang Ic (rel)"] = np.sqrt(np.mean(np.array(err)**2))
axo.set_xlabel("Vce [V]"); axo.set_ylabel("Ic [mA]")
axo.set_title("Ausgangskennlinie: Modell vs Messung")
axo.grid(True, alpha=0.3); axo.legend(fontsize=6)

# (3) hFE-Vce: hFE = beta_F*(1+Vce/VA)
axh = ax[1, 0]
tr3, xs3, ys3 = load("hFE_Vce.txt")
err = []
for lab, vce, hfe in zip(tr3, xs3, ys3):
    axh.plot(vce, hfe, ".", ms=3, label=lab)
    m = np.isfinite(vce) & np.isfinite(hfe) & (vce > 1)
    err += list((beta_F*(1+vce[m]/VA) - hfe[m])/hfe[m])
xx = np.linspace(0.5, 11, 50)
axh.plot(xx, beta_F*(1+xx/VA), "k-", lw=1.5, label="Modell")
rms["hFE-Vce (rel)"] = np.sqrt(np.mean(np.array(err)**2))
axh.set_xlabel("Vce [V]"); axh.set_ylabel("hFE")
axh.set_title("hFE-Vce: Modell vs Messung")
axh.grid(True, alpha=0.3); axh.legend(fontsize=6)

# (4) Ic-Ib: Steigung beta_F*(1+Vce/VA)
axb = ax[1, 1]
tr4, xs4, ys4 = load("Ic_Ib.txt")
err = []
for lab, ib_uA, ic_mA in zip(tr4, xs4, ys4):
    vce = tv(lab)
    p = axb.plot(ib_uA, ic_mA, ".", ms=4, label=lab)
    xx = np.linspace(np.nanmin(ib_uA), np.nanmax(ib_uA), 20)
    axb.plot(xx, beta_F*(1+vce/VA)*xx*1e-6*1e3, "-", lw=0.8, color=p[0].get_color())
    m = np.isfinite(ib_uA) & np.isfinite(ic_mA)
    ic_m = beta_F*(1+vce/VA)*ib_uA[m]*1e-6*1e3
    err += list((ic_m - ic_mA[m])/ic_mA[m])
rms["Ic-Ib (rel)"] = np.sqrt(np.mean(np.array(err)**2))
axb.set_xlabel("Ib [µA]"); axb.set_ylabel("Ic [mA]")
axb.set_title("Ic-Ib: Modell vs Messung")
axb.grid(True, alpha=0.3); axb.legend(fontsize=6)

fig.tight_layout(); fig.savefig("bjt_verify.png", dpi=110)

print("="*60)
print("  VERIFIKATION  (Modell mit extrahierten Parametern)")
print("="*60)
print(f"  Is     = {Is:.3e} A   (global gefittet, n & VA fix)")
print(f"  n      = {n_p:.3f}")
print(f"  beta_F = {beta_F:.0f}")
print(f"  V_A    = {VA:.0f} V")
print("-"*60)
for k, v in rms.items():
    if "rel" in k:
        print(f"  RMS {k:20s} = {v*100:5.2f} %")
    else:
        print(f"  RMS {k:20s} = {v:5.3f}  (~{(np.exp(v)-1)*100:.1f} % in Ic)")
print("="*60)
