# Prüfplan — Seite „Kennlinienschreiber“ (Fassung 1.0, 29.09.2026)

Prof. Dr.-Ing. Ralph Wystup M.Sc. — erstellt mit KI und Agent (Claude Code, Anthropic)

Die Seite trägt den Messplatz als Simulation: das reduzierte Gummel-Poon-Modell mit dem Parametersatz aus dem Gesamtausgleich (`bjt_fit.py`: n = 1,004; I_S = 4,765·10⁻¹⁴ A; β_F = 253,2; V_A = 126,6 V; I_KF = 4,05 A; R_BB = 18,8 Ω; V_AB = 1390 V), die Kaskadenregelung mit den echten Grenzen des Geräts (16-Bit-Umsetzer in beiden Richtungen, k_DA = 188,010 µV und k_AD = 184,659 µV je Zählschritt, Mittelwert über NMIW = 10 ganzzahlig), die Registeranzeige wie am Gerät, die vier Quadranten mit den gemessenen BC337-25-Punkten über der Simulation, und h- und A-Parameter laufend aus dem Modell. Dokumentation (Manuskript, Anleitung) als Reiter. Jede Zeile hat eine Schranke; alle Zahlen stammen aus dem Lauf vom 29.09.2026.

| Nr. | Kriterium | Prüfmittel | Schranke | Ergebnis |
|:--|:--|:--|:--|:--|
| K1 | keine Konsolenfehler | `pruefe_seite.mjs` (Playwright, Chromium) | keine | ok |
| K2 | Werkzeug vor Text: erster Knopf bei 244 px | `pruefe_seite.mjs` (Playwright, Chromium) | oberhalb 400 px | ok |
| K3 | Simulation gegen Messung: I_C(U_CE) 146 Punkte, RMS 0,621 %, größte Abweichung 1,771 %; I_C(I_B) 69 Punkte, RMS 0,573 %, größte 1,299 % | `pruefe_seite.mjs` (Playwright, Chromium) | größte Abweichung ≤ 2,5 % bzw. ≤ 2,0 % | ok |
| K4 | dieselben Zahlen wie die Python-Rechnung: 1,771 % gegen 1,771 % und 1,299 % gegen 1,299 %, Unterschied 0,0000 Prozentpunkte | `pruefe_seite.mjs` gegen `bjt_kennwerte.py` | ≤ 0,02 Prozentpunkte, gleiche Punktzahl | ok |
| K5 | Kaskade rastet ein: 163 Regelschritte, Restabweichung I_B 0,208 % = 0,20 Zählschritte, U_CE 3,15 mV; I_C = 5,3209 mA, h_FE = 265,5 | `pruefe_seite.mjs` (Playwright, Chromium) | ≤ 1,5 Zählschritte (ein Schritt = 211 nA = 1,05 %), U_CE ≤ 5 mV, < 250 Schritte | ok |
| K6 | Registerrechnung: Wandlung Klemme → Registerwert auf ≤ 1 Zählschritt; Mittelwert = ganzzahlige Division der Summe über 10 Abtastungen; Rückrechnung Register 5 → U_CE 4,99706 V gegen 4,99706 V (0,00 Zählschritte) | `pruefe_seite.mjs` (Playwright, Chromium) | Rohwert ≤ 1 Schritt, Mittelwert exakt, Rückrechnung ≤ 2 Schritte | ok |
| K7 | h-Parameter bei I_C = 5 mA, U_CE = 5 V: h11e 1397,2 Ω, h21e 269,15, h22e 34,388 µS, h12e −1,872·10⁻⁵ — identisch mit `bjt_kennwerte.py` | `pruefe_seite.mjs` gegen Python | größter Unterschied ≤ 0,5 % (erreicht 0,0000 %) | ok |
| K8 | Emitterschaltung (U_CC 15 V, R_C 1 k, R_B 510 k, R_L 10 k, R_i 1 k): U_CE 7,364 V, I_C 7,636 mA, r_ein 944,3 Ω, r_aus 948,6 Ω, A_v −254,29, A_vs −123,50 — identisch mit Python | `pruefe_seite.mjs` gegen Python | größter Unterschied ≤ 0,5 % (erreicht 0,0000 %) | ok |
| K9 | Kennlinienfeld bis U_CE = 6 V mit R_C = 470 Ω: 5 Basisstromkurven, 80 Punkte einzeln eingeregelt, Regelschritte insgesamt 14759, längster Punkt 219 Schritte | `pruefe_seite.mjs` (Playwright, Chromium) | 0 Punkte nicht erreicht | ok |
| K10 | Regelreserve: bis U_CE = 11 V bleiben 15 von 80 Punkten unerreichbar; bei jedem steht der Stellwert am oberen Anschlag (65535 = 12,32 V) und der zurückgerechnete Speisepunkt an der Grenze des Messwegs (12,102 V) | `pruefe_seite.mjs` (Playwright, Chromium) | jeder nicht erreichte Punkt am Anschlag (≥ 99 % der Grenze), kein erreichter Punkt am Anschlag | ok |
| K11 | Dokumentation in der Seite: Kaskadenregelung, Registerplan, Gummel, Kettenmatrix, Stolperfallen, Steckwiderstände | `pruefe_seite.mjs` (Playwright, Chromium) | alle sechs Stichworte vorhanden | ok |
| K12 | Seite neutralisiert: kein Kennwort, kein Netzname, keine Netzadresse, kein Rechnerpfad, keiner der sechs Firmennamen | `pruefe_seite.mjs` (Playwright, Chromium); die Firmennamen stehen in `pruefe_privat.json` daneben, die nicht mitgeliefert wird | keiner der Suchausdrücke findet etwas; in diesem Lauf waren sechs Firmennamen in der Liste | ok |
| K13 | Kopf: Fassung 1.0 · 29.09.2026 · Prof. Dr.-Ing. Ralph Wystup M.Sc. — erstellt mit KI und Agent (Claude Code, Anthropic) | `pruefe_seite.mjs` (Playwright, Chromium) | Fassung, Datum, Name | ok |

Stand: 2026-09-29T19:41 · 0 Beanstandung(en).

Bildschirmfotos angesehen: Messplatz mit Registertabelle und Einschwingverlauf (I_B steigt monoton auf den Sollwert, U_CE pendelt sich mit drei abklingenden Schwingungen ein); aufgenommenes Kennlinienfeld mit fünf Basisstromkurven zu je 16 einzeln eingeregelten Punkten; Vierquadrantenbild mit Messpunkten in allen vier Feldern (Quadrant 3 und 4 aus je zwei Messdateien über den gemeinsamen Kollektorstrom rekonstruiert) und durchgezogenem Arbeitspunkt; Kleinsignalblatt mit h-Parametern, Kettenmatrix, Emitterschaltung und Arbeitsgeraden; Manuskript- und Anleitungsreiter mit gesetzten Formeln, Tabellen und Bildern.

## Was die Prüfung gefunden hat

Drei Befunde, die ohne die Prüfung im Browser nicht aufgefallen wären:

1. **Der erste Reglerentwurf schwang auf.** Mit dem Beiwert 0,75 im inneren Kreis lief die Kaskade in eine Dauerschwingung; U_CE blieb 3 V unter dem Sollwert. Ursache ist die Mittelwertbildung über zehn Abtastungen: sie wirkt wie eine Totzeit von 4,5 Durchläufen, und ein Integralregler wird damit oberhalb von K = 0,60 instabil (Rechnung im Manuskript, Abschnitt 3.2). Die Seite arbeitet jetzt mit 0,35 und 0,12.
2. **Die Auflösung des Basisstroms war im Manuskript zu gut angegeben.** Die erste Fassung rechnete nur die Differenzmessung über R_B (34,8 nA). Tatsächlich geht U_RB2 zweimal ein — auch in den Ableitstrom durch R_B_GND —, und das ergibt 272 nA, also den Faktor 7,8 mehr. Die Schranke für die Restabweichung steht deshalb in Zählschritten und nicht in Prozent: feiner als ein Zählschritt zu treffen ist Zufall, keine Leistung.
3. **Der Messweg kommt vor dem Stellweg an den Anschlag.** Bei R_C = 470 Ω und I_B = 40 µA ist über U_CE ≈ 7,2 V nichts mehr zu holen; die Kennlinie bleibt stehen statt abzubrechen. Kriterium K10 prüft, dass die Seite genau das anzeigt und nicht etwa einen Reglerfehler.
