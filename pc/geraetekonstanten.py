"""
=======================================================================
 geraetekonstanten.py  -  die Umrechnungen des Kennlinienschreibers
=======================================================================
 Alles, was zwischen Registerwert und Klemmenspannung steht, aus den
 Bauteilwerten der beiden Schaltplaene gerechnet - keine Zahl getippt.

   Quelle der Bauteilwerte:  Bilder/schaltplan_cpu_adda.png (AD7682,
   DAC8565) und Bilder/schaltplan_ops.png (LTA8092-Messverstaerker mit
   R4/R10 bzw. R6/R8, R9/R2, R7/R5; TCA0372-Treiber mit R11/R1 und
   R12/R3).  Die Referenz des AD7682 folgt aus dem CFG-Wort in
   sketch/ad_da.cpp.

 Zusaetzlich: Rueckrechnung der gesteckten Widerstaende RB und RB_GND
 aus den Anzeigewerten der Trendows-Blaetter (Bilder/trendows_q*.png).

 Nur die Standardbibliothek.   Aufruf:  python3 geraetekonstanten.py
"""
import json

# ---------------------------------------------------------------- Bauteile
R4, R10 = 43_000.0, 22_000.0     # Messzweig: Vorwiderstand / Querwiderstand
R11, R1 = 22_000.0, 5_600.0      # Treiber TCA0372: Gegenkopplung / Fusspunkt
U_REF_AD = 4.096                 # AD7682, CFG-Wort REF = 001 -> interne 4,096 V
U_REF_DA = 2.5                   # DAC8565, Ausgang 0...2,5 V (Schaltplanvermerk)
N_BIT = 16
NMIW = 10                        # ad_da.cpp: NMIW_AD

stufen = 2 ** N_BIT              # Zahl der Stufen
maxwert = stufen - 1             # groesster Registerwert

# ---------------------------------------------------------------- Ausgabekette DA
v_treiber = 1.0 + R11 / R1                       # nichtinvertierender Verstaerker
k_da = U_REF_DA / stufen                         # V je Schritt am DAC-Ausgang
k_da_klemme = k_da * v_treiber                   # V je Schritt an RB1 bzw. RC1
u_da_max = maxwert * k_da_klemme

# ---------------------------------------------------------------- Eingangskette AD
teiler = R10 / (R4 + R10)                        # Spannungsteiler nach dem Folger
k_ad_adc = U_REF_AD / stufen                     # V je Schritt am ADC-Eingang
k_ad = k_ad_adc / teiler                         # V je Schritt an der Klemme
u_ad_max = maxwert * k_ad

# ---------------------------------------------------------------- Steckwiderstaende
# Anzeigewerte der Trendows-Blaetter (Bild, Urb1/V, Urb2/V, iRB/mA, iR_GNB/mA)
BLAETTER = [
    ("trendows_q1_blatt", 0.482, 0.056, 0.0570, 0.0554),
    ("trendows_q2_blatt", 0.481, 0.055, 0.0568, 0.0552),
    ("trendows_q4_blatt", 0.486, 0.056, 0.0575, 0.0557),
    # Das Blatt des dritten Quadranten arbeitet mit dem Zwanzigfachen des Basisstroms;
    # dort ist die Rundung der Anzeige um denselben Faktor weniger wert.
    ("trendows_q3_blatt", 10.611, 0.575, 1.3405, 0.5717),
]
rb_liste, rg_liste = [], []
for name, urb1, urb2, irb, ign in BLAETTER:
    rb = (urb1 - urb2) / (irb * 1e-3)
    rg = urb2 / (ign * 1e-3)
    rb_liste.append(rb); rg_liste.append(rg)
    print(f"  {name}:  RB = ({urb1:.3f} V - {urb2:.3f} V) / {irb:.4f} mA = {rb:8.1f} Ohm"
          f"   |  RB_GND = {urb2:.3f} V / {ign:.4f} mA = {rg:7.1f} Ohm")
rb_m = sum(rb_liste) / len(rb_liste); rg_m = sum(rg_liste) / len(rg_liste)

print("=" * 72)
print(f"  Treiberverstaerkung  v = 1 + R11/R1 = 1 + {R11/1000:.0f}k/{R1/1000:.1f}k = {v_treiber:.5f}")
print(f"  DA:  k = U_refDA/2^16 * v = {U_REF_DA}/{stufen} * {v_treiber:.5f} = {k_da_klemme*1e6:.3f} uV je Schritt")
print(f"       groesste Klemmenspannung bei Registerwert {maxwert}: {u_da_max:.4f} V")
print(f"  Teiler im Messzweig  t = R10/(R4+R10) = {R10/1000:.0f}k/{(R4+R10)/1000:.0f}k = {teiler:.6f}")
print(f"  AD:  k = U_refAD/2^16 / t = {U_REF_AD}/{stufen} / {teiler:.6f} = {k_ad*1e6:.3f} uV je Schritt")
print(f"       groesste messbare Klemmenspannung: {u_ad_max:.4f} V")
print(f"  Aufloesung des Stroms bei RC = 100 Ohm: {k_ad/100*1e6:.3f} uA je Schritt")
print(f"  Mittelwert ueber NMIW = {NMIW} Abtastungen (ganzzahlige Division)")
print("-" * 72)
print(f"  Steckwiderstaende aus den Anzeigewerten: RB = {rb_m:.0f} Ohm (Mittel aus {len(rb_liste)} Blaettern),"
      f"  RB_GND = {rg_m:.0f} Ohm")
print(f"  naechste E24-Werte: RB = 7500 Ohm, RB_GND = 1000 Ohm")
print("=" * 72)

json.dump(dict(R4=R4, R10=R10, R11=R11, R1=R1, U_REF_AD=U_REF_AD, U_REF_DA=U_REF_DA,
               N_BIT=N_BIT, stufen=stufen, maxwert=maxwert, NMIW=NMIW,
               v_treiber=v_treiber, k_da=k_da, k_da_klemme=k_da_klemme, u_da_max=u_da_max,
               teiler=teiler, k_ad_adc=k_ad_adc, k_ad=k_ad, u_ad_max=u_ad_max,
               rb_rueck=rb_m, rg_rueck=rg_m, rb_e24=7500.0, rg_e24=1000.0),
          open("geraet.json", "w", encoding="utf-8"), indent=1)
print("  geschrieben: geraet.json")
