// Prüfung der Kennlinienschreiber-Seite im echten Browser (Playwright, Chromium).
// K1 lädt ohne Konsolenfehler · K2 Werkzeug vor Text · K3 Simulation gegen die Messpunkte (Schranke in Prozent)
// K4 dieselben Abweichungen wie die Python-Rechnung · K5 die Kaskade rastet auf den Sollstrom ein
// K6 Registerrechnung: Wandlung und ganzzahliger Mittelwert · K7 h-Parameter gegen Python
// K8 Kettenmatrix und Emitterschaltung gegen Python · K9 Kennlinienfeld vollständig eingeregelt
// K10 Dokumentation vorhanden und neutralisiert (kein Kennwort, kein Netzname, keine Netzadresse, kein Rechnerpfad)
// K11 Kopfzeile.  Ergebnis nach pruefe_seite.json, Bildschirmfotos in den Kritzelordner.
import { createRequire } from 'node:module';
import fs from 'node:fs';
const require = createRequire(import.meta.url);
const { chromium } = require('/tmp/node_modules/playwright');
const H = '/workspace/Kennlinienschreiber/Seite/';
const V = fs.readFileSync(H + 'VERSION', 'utf8').trim();
const S = '/tmp/claude-1000/-workspace/905236e7-aea4-4c03-805a-5e5668f5230d/scratchpad/';

let fehler = 0; const BEF = [];
const sage = (gut, t) => { console.log(`  ${gut ? 'ok    ' : 'FEHLER'} ${t}`); BEF.push({ gut, text: t }); if (!gut) fehler++; };
const pz = (a, b) => Math.abs(b) < 1e-30 ? Math.abs(a - b) : Math.abs(a - b) / Math.abs(b) * 100;

const b = await chromium.launch();
const p = await b.newPage({ viewport: { width: 1500, height: 1050 } });
const konsole = [];
p.on('pageerror', e => konsole.push(e.message));
p.on('console', m => { if (m.type() === 'error') konsole.push(m.text()); });
await p.goto(`file://${H}Kennlinienschreiber_${V}.html`, { waitUntil: 'load', timeout: 180000 });
await p.waitForTimeout(1500);

// ---- K1, K2
sage(konsole.length === 0, 'keine Konsolenfehler' + (konsole.length ? ': ' + konsole[0].slice(0, 140) : ''));
const lage = await p.evaluate(() => document.getElementById('messen').getBoundingClientRect().top);
sage(lage < 400, `Werkzeug vor Text: erster Knopf bei ${lage.toFixed(0)} px (Schranke 400 px)`);

// ---- K3/K4 Simulation gegen Messung
const v = await p.evaluate(() => window.LABOR.vergleich());
const pv = await p.evaluate(() => window.LABOR.stand.pruefwerte.abweichung);
sage(v.Ic_Vce.max <= 2.5 && v.Ic_Ib.max <= 2.0,
  `Simulation gegen Messung: I_C(U_CE) ${v.Ic_Vce.n} Punkte, RMS ${v.Ic_Vce.rms.toFixed(3)} %, größte ${v.Ic_Vce.max.toFixed(3)} % (Schranke 2,5 %); ` +
  `I_C(I_B) ${v.Ic_Ib.n} Punkte, RMS ${v.Ic_Ib.rms.toFixed(3)} %, größte ${v.Ic_Ib.max.toFixed(3)} % (Schranke 2,0 %)`);
const d1 = Math.abs(v.Ic_Vce.max - pv.Ic_Vce.max * 100), d2 = Math.abs(v.Ic_Ib.max - pv.Ic_Ib.max * 100);
sage(d1 <= 0.02 && d2 <= 0.02 && v.Ic_Vce.n === pv.Ic_Vce.n && v.Ic_Ib.n === pv.Ic_Ib.n,
  `Seite gegen Python (bjt_kennwerte.py): größte Abweichung ${v.Ic_Vce.max.toFixed(3)} % gegen ${(pv.Ic_Vce.max * 100).toFixed(3)} % ` +
  `und ${v.Ic_Ib.max.toFixed(3)} % gegen ${(pv.Ic_Ib.max * 100).toFixed(3)} % — Unterschied ${Math.max(d1, d2).toFixed(4)} Prozentpunkte (Schranke 0,02)`);

// ---- K5 Kaskade
await p.click('#messen'); await p.waitForTimeout(400);
const k = await p.evaluate(() => window.LABOR.letzt);
sage(k.erreicht && Math.abs(k.restIBq) <= 1.5 && Math.abs(k.restUCE) <= 5 && k.schritte < 250,
  `Kaskade rastet ein: ${k.schritte} Regelschritte (Schranke 250); Restabweichung I_B ${k.restIB.toFixed(3)} % ` +
  `= ${k.restIBq.toFixed(2)} Zählschritte (Schranke 1,5 — feiner kann die Messung nicht auflösen: ` +
  `ein Zählschritt sind ${(k.qIB * 1e9).toFixed(0)} nA = ${(k.qIB / k.ib * 100).toFixed(2)} %); ` +
  `U_CE ${k.restUCE.toFixed(2)} mV (Schranke 5 mV); I_C = ${(k.ic * 1e3).toFixed(4)} mA, h_FE = ${(k.ic / k.ib).toFixed(1)}`);

// ---- K6 Registerrechnung
const reg = await p.evaluate(() => {
  const L = window.LABOR, l = L.letzt, G = L.stand.geraet, f = [];
  for (let i = 0; i < 4; i++) {
    f.push({
      roh: l.reg[4 + i], soll: Math.round(l.knoten[i] / G.k_ad),
      mw: l.reg[8 + i], mwsoll: Math.floor(l.ringe[i].reduce((a, c) => a + c, 0) / G.NMIW),
      volt: l.reg[4 + i] * G.k_ad, mvolt: l.reg[8 + i] * G.k_ad
    });
  }
  return { f: f, uce: l.vce, kad: G.k_ad, N: G.NMIW };
});
const rohOk = reg.f.every(x => Math.abs(x.roh - x.soll) <= 1);
const mwOk = reg.f.every(x => x.mw === x.mwsoll);
const uceOk = Math.abs(reg.f[1].volt - reg.uce) <= 2 * reg.kad;
sage(rohOk && mwOk && uceOk,
  `Register: Wandlung Klemme→Registerwert auf ≤ 1 Zählschritt genau (${rohOk ? 'ja' : 'nein'}); ` +
  `Mittelwert = ganzzahlige Division der Summe über ${reg.N} Abtastungen (${mwOk ? 'ja' : 'nein'}); ` +
  `Rückrechnung Register 5 (roh) → U_CE: ${reg.f[1].volt.toFixed(5)} V gegen ${reg.uce.toFixed(5)} V, ` +
  `Unterschied ${((reg.f[1].volt - reg.uce) / reg.kad).toFixed(2)} Zählschritte (Schranke 2); ` +
  `Register 9 (Mittelwert) liegt ${((reg.f[1].mvolt - reg.uce) / reg.kad).toFixed(1)} Zählschritte daneben — ` +
  `das ist der Nachlauf des Mittelwerts innerhalb des Toleranzbandes`);

// ---- K7 h-Parameter
const h = await p.evaluate(() => window.LABOR.hParam(5e-3, 5.0));
const hp = await p.evaluate(() => window.LABOR.stand.pruefwerte.hparam);
const dh = Math.max(pz(h.h11, hp.h11), pz(h.h21, hp.h21), pz(h.h22, hp.h22), pz(h.h12, hp.h12), pz(h.ib, hp.IB), pz(h.vbe, hp.VBE));
sage(dh <= 0.5,
  `h-Parameter bei I_C = 5 mA, U_CE = 5 V — Seite: h11e ${h.h11.toFixed(1)} Ω, h21e ${h.h21.toFixed(2)}, ` +
  `h22e ${(h.h22 * 1e6).toFixed(3)} µS, h12e ${h.h12.toExponential(3)}; Python: ${hp.h11.toFixed(1)} Ω, ${hp.h21.toFixed(2)}, ` +
  `${(hp.h22 * 1e6).toFixed(3)} µS, ${hp.h12.toExponential(3)} — größter Unterschied ${dh.toFixed(4)} % (Schranke 0,5 %)`);

// ---- K8 Kettenmatrix und Emitterschaltung
const w = await p.evaluate(() => window.LABOR.verstaerker());
const wp = await p.evaluate(() => window.LABOR.stand.pruefwerte.verstaerker);
const dw = Math.max(pz(w.r_ein, wp.r_ein), pz(w.r_aus, wp.r_aus), pz(w.A_v, wp.A_v), pz(w.A_i, wp.A_i),
                    pz(w.A_vs, wp.A_vs), pz(w.vce, wp.VCE), pz(w.ic, wp.IC));
sage(dw <= 0.5,
  `Emitterschaltung — Seite: U_CE ${w.vce.toFixed(3)} V, I_C ${(w.ic * 1e3).toFixed(3)} mA, r_ein ${w.r_ein.toFixed(1)} Ω, ` +
  `r_aus ${w.r_aus.toFixed(1)} Ω, A_v ${w.A_v.toFixed(2)}, A_vs ${w.A_vs.toFixed(2)}; Python: ${wp.VCE.toFixed(3)} V, ` +
  `${(wp.IC * 1e3).toFixed(3)} mA, ${wp.r_ein.toFixed(1)} Ω, ${wp.r_aus.toFixed(1)} Ω, ${wp.A_v.toFixed(2)}, ${wp.A_vs.toFixed(2)} — ` +
  `größter Unterschied ${dw.toFixed(4)} % (Schranke 0,5 %)`);

await p.screenshot({ path: S + 'kls_messplatz.png' });

// ---- K9 Kennlinienfeld
await p.click('#kennlinie');
await p.waitForFunction(() => window.LABOR.feld, null, { timeout: 300000 });
const F = await p.evaluate(() => window.LABOR.feld);
const npkt = F.kurven.reduce((a, c) => a + c.x.length, 0);
const maxSchritte = Math.max(...F.punkte.map(x => x.schritte));
sage(F.kurven.length === 5 && npkt === 80 && F.nichtErreicht === 0,
  `Kennlinienfeld bis U_CE = ${F.ucemax} V mit R_C = ${F.rc} Ω: ${F.kurven.length} Basisstromkurven, ${npkt} Punkte, ` +
  `Regelschritte insgesamt ${F.schritte}, längster Punkt ${maxSchritte} Schritte, ${F.nichtErreicht} Punkte nicht erreicht (Schranke 0)`);

// ---- K9b: bis an die Grenze des Treibers — dort MUSS es klemmen, und zwar genau dort
await p.evaluate(() => { const el = document.getElementById('r_ucemax'); el.value = 11; el.dispatchEvent(new Event('input')); });
await p.evaluate(() => { window.LABOR.feld = null; });
await p.click('#kennlinie');
await p.waitForFunction(() => window.LABOR.feld, null, { timeout: 300000 });
const F2 = await p.evaluate(() => window.LABOR.feld);
const nicht = F2.punkte.filter(x => !x.erreicht);
const amAnschlag = nicht.every(x => x.anschlag && x.uRC1 >= x.grenze * 0.99);
const erreichbarOk = F2.punkte.filter(x => x.erreicht).every(x => !x.anschlag);
sage(nicht.length > 0 && amAnschlag && erreichbarOk,
  `Regelreserve: bis U_CE = ${F2.ucemax} V bleiben ${nicht.length} von ${F2.punkte.length} Punkten unerreichbar. ` +
  `Bei jedem davon steht der Stellwert am oberen Anschlag (Registerwert ${nicht.length ? nicht[0].codeC : '—'}, ` +
  `Treiber ${nicht.length ? nicht[0].treiber.toFixed(2) : '—'} V) und der zurückgerechnete Speisepunkt liegt an der ` +
  `Grenze des Messwegs ${nicht.length ? nicht[0].grenze.toFixed(3) : '—'} V ` +
  `(kleinster Wert ${nicht.length ? Math.min(...nicht.map(x => x.uRC1)).toFixed(3) : '—'} V, Schranke 99 %); ` +
  `kein erreichter Punkt steht am Anschlag — das ist die fehlende Regelreserve, nicht ein Reglerfehler`);
await p.evaluate(() => { const el = document.getElementById('r_ucemax'); el.value = 6; el.dispatchEvent(new Event('input')); });
await p.waitForTimeout(300);
await p.screenshot({ path: S + 'kls_feld.png' });

await p.click('#reiter button[data-z=quadranten]'); await p.waitForTimeout(900);
await p.screenshot({ path: S + 'kls_quadranten.png' });
await p.click('#reiter button[data-z=kleinsignal]'); await p.waitForTimeout(700);
await p.screenshot({ path: S + 'kls_kleinsignal.png' });
await p.click('#reiter button[data-z=manuskript]'); await p.waitForTimeout(400);
await p.screenshot({ path: S + 'kls_manuskript.png' });
await p.evaluate(() => {
  const h = [...document.querySelectorAll('#s-manuskript h2')].find(x => x.textContent.includes('Kleinsignal'));
  if (h) window.scrollTo(0, h.getBoundingClientRect().top + window.scrollY - 40);
});
await p.waitForTimeout(400);
await p.screenshot({ path: S + 'kls_manuskript_formeln.png' });
await p.click('#reiter button[data-z=anleitung]'); await p.waitForTimeout(400);
await p.evaluate(() => window.scrollTo(0, 900)); await p.waitForTimeout(250);
await p.screenshot({ path: S + 'kls_anleitung.png' });
await p.evaluate(() => window.scrollTo(0, 0));

// ---- K10 Dokumentation
const doku = (await p.evaluate(() => document.body.textContent)).replace(/\s+/g, ' ');
const teile = ['Kaskadenregelung', 'Registerplan', 'Gummel', 'Kettenmatrix', 'Stolperfallen', 'Steckwiderstände'];
sage(teile.every(x => doku.includes(x)), `Dokumentation in der Seite: ${teile.join(', ')}`);
const heikel = [[/\b(?:\d{1,3}\.){3}\d{1,3}\b/, 'Netzadresse'], [/[A-Za-z]:\\{1,4}[A-Za-z_]/, 'Rechnerpfad'],
                [/[\w.+-]+@[\w-]+\.[\w.]{2,}/, 'E-Post'], [/\bSSID\b|\bWPA2?\b/i, 'Netzname'],
                [/\b(?:passwor[dt]|kennwort)\s*[:=]\s*(?!x+\b)\S+/i, 'Kennwortwert']];
// Die Firmennamen, die nirgends auftauchen duerfen, stehen nicht in dieser Datei, sondern in
// pruefe_privat.json daneben — diese wird nicht mitgeliefert (Vorbild: neutral_privat.json).
let firmen = [];
try { firmen = JSON.parse(fs.readFileSync(H + 'pruefe_privat.json', 'utf8')).map(x => new RegExp(x, 'i')); } catch (e) { firmen = null; }
const treffer = heikel.filter(([r]) => r.test(doku)).map(([, n]) => n);
if (firmen && firmen.some(r => r.test(doku))) treffer.push('Firmenname');
sage(treffer.length === 0,
  `Seite neutralisiert: kein Kennwort, kein Netzname, keine Netzadresse, kein Rechnerpfad` +
  (firmen ? `, keiner der ${firmen.length} Firmennamen aus pruefe_privat.json` : ' (Firmennamen nicht geprüft: pruefe_privat.json liegt nicht bei — sie gehört nicht in die Veröffentlichung)') +
  (treffer.length ? ' — GEFUNDEN: ' + treffer.join(', ') : ''));

// ---- K11 Kopf
const kopf = await p.$eval('#fassung', e => e.textContent);
sage(kopf.includes(`Fassung ${V}`) && /\d{2}\.\d{2}\.\d{4}/.test(kopf) && kopf.includes('Ralph Wystup'), `Kopf: ${kopf}`);

await b.close();
fs.writeFileSync(H + 'pruefe_seite.json', JSON.stringify({ datum: new Date().toISOString(), fassung: V, befunde: BEF, fehler }, null, 1));
console.log(fehler ? `${fehler} Beanstandung(en)` : 'alles in Ordnung');
process.exit(fehler ? 1 : 0);
