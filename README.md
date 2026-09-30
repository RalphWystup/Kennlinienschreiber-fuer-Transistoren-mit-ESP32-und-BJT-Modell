# Kennlinienschreiber für Transistoren mit ESP32 und BJT-Modell

<img src="Foto_Ralph_Wystup.jpg" align="right" width="140" alt="Prof. Dr.-Ing. Ralph Wystup">

Prof. Dr.-Ing. Ralph Wystup M.Sc. — erstellt mit KI und Agent (Claude Code, Anthropic)

**Seite öffnen:** https://ralphwystup.github.io/Kennlinienschreiber-fuer-Transistoren-mit-ESP32-und-BJT-Modell/ — der Messplatz als Simulation im Browser: Basisstrom und Kollektor-Emitter-Spannung
vorgeben, der Kaskadenregelung beim Einrasten zusehen, die Register wie am Gerät ablesen, ein Kennlinienfeld
Punkt für Punkt aufnehmen; daneben das Vierquadranten-Kennfeld mit den gemessenen Punkten über der Simulation
und die Kleinsignalrechnung (h-Parameter, Kettenmatrix, Emitterschaltung). Manuskript und Anleitung sind als
Reiter in der Seite. Läuft offline.

Ein Messplatz nimmt das Kennfeld eines Transistors auf: ein Mikrorechner mit einem 16-Bit-Analog-Digital-Umsetzer
(AD7682), einem 16-Bit-Digital-Analog-Umsetzer (DAC8565), zwei Treiberverstärkern und drei gesteckten
Widerständen, nach außen ein gewöhnlicher Modbus-RTU-Teilnehmer. Geregelt wird in Kaskade — der äußere Kreis
stellt den Basisstrom über <code>I_B = (U_RB1−U_RB2)/R_B − U_RB2/R_B_GND</code>, der innere die
Kollektor-Emitter-Spannung <code>U_CE = U_RC2</code>; gemessen wird erst nach dem Einschwingen beider Kreise der
Kollektorstrom <code>I_C = (U_RC1−U_RC2)/R_C</code>.

Aus dem gemessenen Kennfeld werden die Parameter eines reduzierten Gummel-Poon-Modells bestimmt — erst
merkmalsweise mit Bleistift und Papier, dann als Gesamtausgleich über alle fünf Kennfelder, und zuletzt wird
geprüft, welcher Parameter aus diesen Daten überhaupt bestimmbar ist (drei von sieben sind es nicht). Aus dem
angepassten Modell folgen die h-Parameter als Ableitungen im Arbeitspunkt, daraus die Kettenmatrix, und damit
wird eine vollständige Emitterschaltung durchgerechnet — jeder Schritt von Hand nachrechenbar.

![Das Vierquadranten-Kennfeld mit durchgezogenem Arbeitspunkt](bilder/bjt_4quadrant.png)

## Was drin ist

| Datei | Inhalt |
|:--|:--|
| [`Kennlinienschreiber_1.1.html`](Kennlinienschreiber_1.1.html) | Messplatz-Simulation, Kennlinienfeld, vier Quadranten, Kleinsignal, Dokumentation |
| [`MANUSKRIPT_Kennlinienschreiber.pdf`](MANUSKRIPT_Kennlinienschreiber.pdf) | Messprinzip und Schaltung mit allen Umrechnungen, Registerplan, Kaskadenregelung mit Herleitung, Parameterbestimmung in drei Wegen, Bestimmbarkeitsprobe, h-Parameter, Kettenmatrix, Emitterschaltung |
| [`ANLEITUNG_Kennlinienschreiber.pdf`](ANLEITUNG_Kennlinienschreiber.pdf) | Arbeitsanleitung: Widerstände wählen, anschließen, Leitstand einrichten, Kennlinie aufnehmen, prüfen, Stolperfallen |
| [`PRUEFPLAN_Seite.md`](PRUEFPLAN_Seite.md) | dreizehn Kriterien mit Schranken, im echten Browser geprüft, mit den drei Befunden der Prüfung |
| `firmware/` | die Firmware des Messplatzes: Hauptschleife, SPI-Treiber für Umsetzer und Wandler mit Mittelwertbildung, Modbus-RTU-Teilnehmer |
| `pc/` | die Auswerteprogramme (`bjt_*.py`, nur numpy und matplotlib), die Gerätekonstanten (`geraetekonstanten.py`) und die fünf Messdateien des BC337-25 |
| `seite/` | Erzeuger der Seite (`erstelle_kennlinienschreiber_seite.py` mit `vorlage.html`, Fassungsnummer nur in `VERSION`) und das Prüfprogramm (`pruefe_seite.mjs`, Playwright) |
| `bilder/` | Übersichtsplan, Schaltpläne, Leiterplatte, die vier Quadranten am Tesla KU611, die Bedienblätter und die gerechneten Bilder |
| `index.html` | leitet auf die Seite weiter, damit GitHub Pages sie unter der Adresse oben zeigt |

In dieser Veröffentlichung stehen keine Zugangsdaten: der Messplatz hat keine Netzanbindung, und weder Firmware
noch Auswerteprogramme enthalten Netznamen oder Kennwörter.

## Wohin die Messungen führen

Dieses Gerät ist der Anfang einer Kette. Was mit seinen Kennlinien weiter geschieht — die Parameter eines
Gummel-Poon-Modells daraus bestimmen, mit diesen Parametern den Arbeitspunkt und die Verstärkung einer
ganzen Schaltung rechnen, und das Ergebnis gegen LTspice halten —, steht in einer eigenen Arbeit:

**[Transistoren, der Transistortester und die daraus erzeugten Modelle](https://ralphwystup.github.io/Transistoren-Transistortester-und-daraus-erzeugte-Modelle/)**

Dort sind die Manuskripte zur Sache versammelt, und jede Rechnung läuft im Browser mit. Die Platine, die
Funktionsübersicht und der Schaltplan von hier stehen dort ebenfalls, damit der Weg von Anfang an sichtbar
ist; die Herleitung der Gerätekonstanten und die Kaskadenregelung bleiben hier.

Das Verfahren, mit dem eine Schaltung aus nichtlinearen Bauteilen überhaupt gerechnet wird — Knotenpotential\-
verfahren, Newton-Raphson und Euler —, ist wiederum in einer dritten Arbeit hergeleitet:
**[Schaltungssimulation von nichtlinearen Differentialgleichungssystemen](https://ralphwystup.github.io/Schaltungssimulation-von-nichtlinearen-Differentialgleichungssystemen/)**.
Seit ihrem Teil XII ist der Transistor dort als Netzlisten-Bauteil eingebaut.

## Lizenz

MIT, siehe [LICENSE](LICENSE).
