---
title: "Kennlinienschreiber: Anschluss, Einrichtung, Betrieb"
subtitle: "Arbeitsanleitung zum Messplatz mit ESP32, AD7682 und DAC8565"
author: "Prof. Dr.-Ing. Ralph Wystup M.Sc. — erstellt mit KI und Agent (Claude Code, Anthropic)"
date: "Fassung 1.0 · 29.09.2026"
lang: de
---

# 1 Wozu diese Anleitung

Das Manuskript erklärt, **warum** der Messplatz so rechnet. Diese Anleitung sagt,
**was zu tun ist**, damit er misst — in der Reihenfolge, in der es getan wird. Sie
setzt den Aufbau als fertig voraus: bestückte Leiterplatte, Firmware aufgespielt,
Netzteil vorhanden.

# 2 Was gebraucht wird

| Teil | Angabe |
|:--|:--|
| Leiterplatte | „Kennlinien-Schreiber V2.0" mit aufgestecktem Mikrorechnermodul |
| Speisung | 24 V Gleichspannung an der zweipoligen Klemme, mindestens 1 A |
| Verbindung zum Rechner | USB-Kabel zum Mikrorechnermodul (ist zugleich die serielle Schnittstelle) |
| Steckwiderstände | $R_C$ im Kollektorzweig, $R_B$ im Basiszweig; Richtwerte $R_B = 7{,}5$ k$\Omega$, $R_{B\_GND} = 1$ k$\Omega$ |
| Prüfling | npn- oder pnp-Transistor, an der jeweiligen Klemmenreihe |
| Leitstand | ein Programm, das Modbus RTU über eine serielle Schnittstelle spricht |

Die Klemmenreihen sind auf der Leiterplatte beschriftet: oben `NPN: Rc C E B Rb GND`,
darunter `PNP: E C Rb B Rc GND`. Ein Prüfling wird immer an genau eine der beiden
Reihen gelegt.

# 3 Die Widerstände wählen

Die drei gesteckten Widerstände legen die Messbereiche fest. Für den Kollektorzweig
gilt: der Abfall über $R_C$ geht dem Prüfling an Spannung verloren.

$$U_{RC1} = U_{CE} + I_C\,R_C \;\le\; 12{,}3\ \text{V}$$

Beispiel: soll $U_{CE}$ bis 10 V reichen und $I_C$ bis 60 mA, so darf
$I_C R_C \le 2{,}3$ V sein, also $R_C \le 38\ \Omega$. Mit $R_C = 33\ \Omega$ beträgt
die Stromauflösung $k_{AD}/R_C = 184{,}7\ \mu\text{V}/33\ \Omega = 5{,}6\ \mu$A je
Zählschritt — bei 60 mA sind das 0,009 %.

Für den Basiszweig gilt dasselbe:

$$U_{RB1} = U_{BE} + I_B\,R_B + \frac{R_B}{R_{B\_GND}}\,U_{BE} \;\le\; 12{,}3\ \text{V}$$

Der dritte Summand ist der Ableitstrom durch $R_{B\_GND}$, der ebenfalls durch $R_B$
fließen muss. Mit $R_B = 7{,}5$ k$\Omega$, $R_{B\_GND} = 1$ k$\Omega$ und
$U_{BE} = 0{,}7$ V bleiben für $I_B R_B$ noch $12{,}3 - 0{,}7 - 5{,}3 = 6{,}3$ V,
also $I_B \le 0{,}84$ mA. Für Leistungstransistoren mit Basisströmen um 1 mA ist $R_B$
also kleiner zu wählen; für Kleinsignaltransistoren mit 10 … 50 $\mu$A darf er deutlich
größer sein, was die Auflösung verbessert.

Die Auflösung des Basisstroms hängt an **beiden** Widerständen:

$$\Delta I_B = k_{AD}\sqrt{\left(\frac{1}{R_B}\right)^2 + \left(\frac{1}{R_B}+\frac{1}{R_{B\_GND}}\right)^2}$$

Mit $R_B = 7{,}5$ k$\Omega$ und $R_{B\_GND} = 1$ k$\Omega$ sind das 272 nA; bei
$I_B = 20\ \mu$A also 1,4 %. Der Ableitwiderstand ist dabei der größere Anteil: mit
$R_{B\_GND} = 10$ k$\Omega$ sinkt die Zahl auf 62 nA.

**Zwei Faustregeln:** $R_B$ so groß wie möglich, solange die Spannungsrechnung oben noch
aufgeht — und $R_{B\_GND}$ so groß, wie der Aufbau es ohne Zappeln erlaubt. Beides
verbessert die Auflösung, und beides kostet Spannungsreserve am Speisepunkt.

# 4 Anschließen — in dieser Reihenfolge

1. Speisung **aus**.
2. Steckwiderstände einsetzen. Die Werte notieren; der Leitstand braucht sie, sonst
   rechnet er falsche Ströme aus richtigen Spannungen.
3. Prüfling an die passende Klemmenreihe. Bei Leistungstransistoren im Metallgehäuse
   ist das Gehäuse der Kollektor — beim Ablegen auf eine leitende Unterlage aufpassen.
4. USB-Kabel zum Rechner. Der Mikrorechner läuft damit schon, die Endstufen aber nicht.
5. Speisung **ein**. Die Leuchtdiode am Mikrorechnermodul zeigt jeden gültigen
   Modbus-Rahmen durch kurzes Aufleuchten an.

Abbauen in umgekehrter Reihenfolge; besonders: Speisung aus, **bevor** der Prüfling
gewechselt wird.

# 5 Den Leitstand einrichten

## 5.1 Schnittstelle

| Feld | Wert |
|:--|:--|
| Schnittstelle | die serielle Schnittstelle des Mikrorechnermoduls |
| Übertragungsrate | 115200 Bit/s, 8 Datenbits, keine Parität, 1 Stoppbit |
| Teilnehmeradresse | 1 |
| Wortreihenfolge | einfache 16-Bit-Register, keine Umordnung (es gibt keine 32-Bit-Werte) |
| Abfragezyklus | 100 … 500 ms |

Nur **ein** Programm darf die Schnittstelle belegen. Ein noch offenes Terminal oder ein
zweites Prüfprogramm blockiert sie; der Leitstand meldet dann „keine Antwort", obwohl
das Gerät in Ordnung ist.

## 5.2 Kanaltabelle

Die Register sind in zwei Blöcken einzutragen — die Stellregister werden geschrieben,
die Messregister gelesen:

| Nr. | Typ | Anzahl | Adressversatz | Bedeutung |
|:--:|:--|:--:|:--:|:--|
| 1 | WO (16) | 2 | 0 | Stellwerte: 0 = Kollektorzweig, 1 = Basiszweig |
| 2 | WI (4) | 8 | 4 | Messwerte: 4…7 roh, 8…11 als Mittelwert |

Die Zahl in Klammern ist der Modbus-Funktionscode. Das Gerät versteht zum Lesen die
Codes 3 und 4, zum Schreiben 6 und 16 (und quittiert 1, 2, 5, 8, 15). Wer nur die
Mittelwerte braucht, trägt stattdessen einen Block WI (4), Anzahl 4, Versatz 8 ein.

Ein Schreibbefehl auf die Register 4 und höher wird quittiert, aber nicht ausgeführt —
Messwerte lassen sich nicht überschreiben.

## 5.3 Umrechnungen im Leitstand

Diese fünf Zeilen sind alles, was der Leitstand rechnen muss:

| Größe | Formel |
|:--|:--|
| Klemmenspannung aus Messregister | $U = 184{,}659\ \mu\text{V} \cdot \text{Registerwert}$ |
| Stellregister aus Sollspannung | $\text{Registerwert} = U / 188{,}010\ \mu\text{V}$ |
| Kollektorstrom | $I_C = (U_{RC1} - U_{RC2}) / R_C$ |
| Basisstrom | $I_B = (U_{RB1} - U_{RB2})/R_B - U_{RB2}/R_{B\_GND}$ |
| Kollektor-Emitter-Spannung | $U_{CE} = U_{RC2}$ |

Dabei sind $U_{RC1}, U_{RC2}, U_{RB1}, U_{RB2}$ die Register 8, 9, 10, 11 (Mittelwerte)
beziehungsweise 4, 5, 6, 7 (roh).

## 5.4 Die beiden Regler

Der Leitstand regelt in Kaskade:

* **innerer Kreis, schnell:** Sollwert $U_{CE}$, Istwert aus Register 9,
  Stellgröße Register 0;
* **äußerer Kreis, langsam:** Sollwert $I_B$, Istwert aus Registern 10 und 11 nach der
  Formel oben, Stellgröße Register 1.

Der innere Kreis muss deutlich schneller eingestellt sein als der äußere — mindestens
um den Faktor drei bis fünf. Wird diese Regel verletzt, schaukeln sich beide
gegeneinander auf, und die Kennlinie zeigt ein Zittern, das kein Bauteileffekt ist.

# 6 Eine Kennlinie aufnehmen

1. Basisstrom-Sollwert auf die erste Stufe setzen (Beispiel: 0,2 mA) und warten, bis
   der äußere Kreis steht.
2. $U_{CE}$-Sollwert von 0 an in Schritten erhöhen (Beispiel: 0,1 V). Bei jedem Schritt
   warten, bis **beide** Regelabweichungen unter der Schranke liegen.
3. Den Punkt $(U_{CE}, I_C)$ ablegen.
4. Nach der letzten $U_{CE}$-Stufe zur nächsten Basisstromstufe gehen und bei 2
   fortfahren.
5. Fertig, wenn die letzte $U_{CE}$-Stufe der letzten Basisstromstufe erreicht ist.

Für die anderen Quadranten werden Soll- und Laufgröße vertauscht: im zweiten Quadranten
läuft der Basisstrom und $U_{CE}$ steht fest, im dritten und vierten wird zusätzlich
$U_{BE}$ aus Register 11 aufgezeichnet.

**Schrittweite:** in Bereichen, in denen sich $I_C$ kaum ändert (also im aktiven
Bereich), darf die Schrittweite wachsen. Im Knie unterhalb von 0,5 V sollte sie klein
bleiben — dort steckt die Aussage über die Sättigungsspannung.

# 7 Prüfen, ob alles stimmt

Vom Sichtbaren zum Messbaren:

1. **Rahmen kommen an.** Die Leuchtdiode blinkt im Takt des Abfragezyklus. Tut sie das
   nicht, stimmen Schnittstelle, Übertragungsrate oder Adresse nicht.
2. **Messwerte bewegen sich.** Ohne Prüfling und ohne Stellwert müssen alle vier
   Messregister nahe Null stehen.
3. **Stellweg wirkt.** Register 0 auf den Wert 10000 (dezimal) setzen: $U_{RC1}$ muss auf
   $10000 \cdot 188{,}010\ \mu\text{V} = 1{,}88$ V gehen, und Register 8 muss
   $1{,}88\ \text{V}/184{,}659\ \mu\text{V} = 10181$ (dezimal) anzeigen — 1,8 % über dem
   Stellwert, weil Stell- und Messweg verschiedene Referenzen haben. Weicht es stark
   ab, ist ein Bauteil im Teiler oder in der Gegenkopplung falsch.
4. **Kurzschlussprobe.** $R_C$ durch eine Brücke ersetzen: dann müssen die Register 8
   und 9 gleich sein, also $I_C = 0$. Ist die Differenz größer als zwei Zählschritte,
   liegt ein Versatz zwischen den Kanälen vor, den der Leitstand herausrechnen muss.
5. **Erst dann den Prüfling einsetzen.**

# 8 Stolperfallen

* **Widerstandswerte nicht nachgeführt.** Der häufigste Fehler: $R_C$ gewechselt, im
  Leitstand steht noch der alte Wert. Die Spannungen stimmen, die Ströme nicht.
* **Nur ein Programm an der Schnittstelle.** Terminal, Prüfskript und Leitstand
  schließen sich gegenseitig aus.
* **Zu schneller äußerer Kreis.** Siehe 5.4 — das Zittern in der Kennlinie kommt vom
  Regler, nicht vom Bauteil.
* **Messregister beschreiben.** Wird quittiert, wirkt aber nicht; wer sich darauf
  verlässt, sucht den Fehler an der falschen Stelle.
* **Rohwerte statt Mittelwerte.** Die Register 4…7 rauschen sichtbar mehr als 8…11.
  Für die Regelung und für die Aufzeichnung gehören die Mittelwerte genommen.
* **Sättigungsbereich überfahren.** Wird $U_{RC1}$ zu klein gewählt, geht der Prüfling
  in die Sättigung, der Basisstrom bricht ein, und der äußere Regler fährt gegen den
  Anschlag. Die Kennlinie zeigt dann eine senkrechte Linie bei kleinem $U_{CE}$ — das
  ist kein Bauteileffekt, sondern fehlende Regelreserve.
* **Prüfling heiß.** Das Kennfeld verschiebt sich mit der Temperatur um etwa
  $-2$ mV/K in $U_{BE}$. Bei Leistungstransistoren zwischen den Kurven abkühlen lassen
  oder die Aufnahme im Impulsbetrieb fahren.

# 9 Im Fehlerfall

| Beobachtung | Zuerst prüfen |
|:--|:--|
| keine Antwort | Schnittstelle belegt? Adresse 1? 115200 Bit/s? |
| Leuchtdiode blinkt, Werte bleiben 0 | Speisung 24 V fehlt — der Mikrorechner läuft über USB auch ohne sie |
| alle Messwerte am Anschlag | Stellwert zu groß, oder Prüfling fehlt und der Basiszweig steht offen |
| Ströme negativ | $R_C$ oder $R_B$ vertauscht, oder Prüfling an der falschen Klemmenreihe |
| Kennlinie zittert | Reglerbeiwerte (5.4) |
| Kennlinie bricht bei kleinem $U_{CE}$ senkrecht ab | fehlende Regelreserve, siehe oben |
