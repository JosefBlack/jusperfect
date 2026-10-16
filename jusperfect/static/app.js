/* jusperfect – Cowork-Arbeitsfläche.
   Ohne Abhängigkeiten. Fremder Text (Dokument, KI-Antwort) wird als Textknoten
   eingefügt; nur die Beleg-Chips sind Elemente. */
"use strict";

const K = window.JUSPERFECT_KONFIGURATION || { betriebsart: "lokal", apiBasis: "" };
const $ = (id) => document.getElementById(id);

// Der Satz fuer "niemand antwortet mehr" - an einer Stelle, damit Anmeldeseite
// und Kopfzeile nicht zweierlei sagen. Oben in der Ecke ist nur Platz fuer die
// kurze Fassung; der ganze Satz steht dort, wo auch gehandelt wird.
const NICHT_ERREICHBAR = "Das Programm antwortet nicht. Ist das schwarze Fenster noch "
  + "offen, und steht dort eine Meldung? Laeuft es noch, diese Seite neu laden - der "
  + "Browser oeffnet sich, bevor das Programm bereit ist. Wurde das Fenster "
  + "geschlossen, die Startdatei erneut ausfuehren, mit der Sie begonnen haben "
  + "(START-DEMO, START-AWS, START-KANZLEI oder START-JURNODES).";
const NICHT_ERREICHBAR_KURZ = "antwortet nicht";

let sitzung = null;        // Antwort von POST /api/sitzungen
let passagenIndex = {};    // kennung -> Passage
let belegKennungen = new Set();
// Die Quelle traegt seit Neuestem die genaue Stelle in der Passage
// (treffer_start/treffer_ende) und die harten Angaben darin (marken).
// passagenIndex haelt die vollen Passagen und wird davon nicht ueberschrieben -
// deshalb eine eigene Ablage.
let belegQuellen = {};
const ZITAT = /\[Q:\s*([^\]]+?)\s*\]/g;

// ── Anmeldung (Cognito Hosted UI, Autorisierungscode mit PKCE) ─────────────
// Das Token bleibt im Arbeitsspeicher dieser Seite: Es überlebt kein erneutes
// Laden und liegt in keinem Speicher, den anderer Code auslesen könnte. Nach
// dem Neuladen meldet die Sitzung bei Cognito ohne erneute Eingabe wieder an.

const AWS_MODUS = K.betriebsart === "aws";
let zugangstoken = null;
let tokenAblauf = 0;

function zufallstext(bytes) {
  return b64url(crypto.getRandomValues(new Uint8Array(bytes)));
}

function b64url(bytes) {
  return btoa(String.fromCharCode(...new Uint8Array(bytes)))
    .replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

async function pruefwert(verifizierer) {
  const roh = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(verifizierer));
  return b64url(roh);
}

function umleitungsziel() {
  return location.origin + location.pathname;
}

function angemeldet() {
  return !!zugangstoken && Date.now() < tokenAblauf;
}

async function anmeldungStarten() {
  const verifizierer = zufallstext(48);
  const zustand = zufallstext(12);
  sessionStorage.setItem("jusperfect.verifizierer", verifizierer);
  sessionStorage.setItem("jusperfect.zustand", zustand);
  const ziel = new URL(K.cognitoDomaene + "/oauth2/authorize");
  const felder = {
    response_type: "code", client_id: K.clientId, redirect_uri: umleitungsziel(),
    scope: "openid email profile", state: zustand,
    code_challenge_method: "S256", code_challenge: await pruefwert(verifizierer),
  };
  for (const [name, wert] of Object.entries(felder)) ziel.searchParams.set(name, wert);
  gewolltesVerlassen = true;
  location.assign(ziel.toString());
}

/* Löst den zurückgegebenen Code gegen ein Token ein. Gibt true zurück, wenn
   eine Anmeldung stattgefunden hat – gleich ob erfolgreich oder nicht. */
async function anmeldungAbschliessen() {
  const felder = new URLSearchParams(location.search);
  const code = felder.get("code");
  if (!code) return false;
  const zustand = sessionStorage.getItem("jusperfect.zustand");
  const verifizierer = sessionStorage.getItem("jusperfect.verifizierer");
  sessionStorage.removeItem("jusperfect.zustand");
  sessionStorage.removeItem("jusperfect.verifizierer");
  history.replaceState(null, "", umleitungsziel());
  // Ein fremder Zustand heißt: Diese Antwort gehört nicht zu unserer Anfrage.
  if (!zustand || felder.get("state") !== zustand || !verifizierer) {
    melden("Die Anmeldung konnte nicht zugeordnet werden. Bitte erneut anmelden.", true);
    return true;
  }
  const antwort = await fetch(K.cognitoDomaene + "/oauth2/token", {
    method: "POST", headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      grant_type: "authorization_code", client_id: K.clientId, code,
      redirect_uri: umleitungsziel(), code_verifier: verifizierer,
    }),
  });
  if (!antwort.ok) {
    melden("Die Anmeldung ist fehlgeschlagen. Bitte erneut versuchen.", true);
    return true;
  }
  const daten = await antwort.json();
  zugangstoken = daten.id_token;
  // Eine Minute Sicherheitsabstand, damit kein Aufruf in den Ablauf läuft.
  tokenAblauf = Date.now() + Math.max(0, (daten.expires_in || 3600) - 60) * 1000;
  return true;
}

function abmelden() {
  zugangstoken = null;
  tokenAblauf = 0;
  const ziel = new URL(K.cognitoDomaene + "/logout");
  ziel.searchParams.set("client_id", K.clientId);
  ziel.searchParams.set("logout_uri", umleitungsziel());
  gewolltesVerlassen = true;
  location.assign(ziel.toString());
}

function anmeldungAnzeigen() {
  const knopf = $("anmeldung");
  if (!knopf) return;
  knopf.hidden = !AWS_MODUS;
  knopf.textContent = angemeldet() ? "Abmelden" : "Anmelden";
}

// ── Die Kopfzeile: schmal oder ganz ────────────────────────────────────────
//
// Aus der Kanzlei am 14.10.2026: "Auch die obere Zeile jusperfect nimmt viel
// Platz und sollte ausklappbar sein, wenn man auf jusperfect drueckt."
//
// Schmal bleibt stehen, woran man ist - die Akte und der Weg zurueck. Weg
// sind Verbrauch, Verbindungsstand und Benutzer: drei Angaben, die man
// einmal am Tag braucht und den ganzen Tag ansieht.

function kopfzeileHerstellen() {
  const kopf = $("kopf"), schalter = $("kopf-schalter");
  if (!kopf || !schalter) return;
  let schmal = false;
  try { schmal = localStorage.getItem("jusperfect.kopf") === "schmal"; }
  catch (e) { /* dann eben ganz */ }
  const anwenden = () => {
    kopf.classList.toggle("schmal", schmal);
    schalter.setAttribute("aria-expanded", String(!schmal));
    schalter.title = schmal ? "Kopfzeile wieder aufklappen" : "Kopfzeile schmal machen";
  };
  anwenden();
  schalter.addEventListener("click", () => {
    schmal = !schmal;
    try { localStorage.setItem("jusperfect.kopf", schmal ? "schmal" : "ganz"); }
    catch (e) { /* Bequemlichkeit, keine Arbeit */ }
    anwenden();
  });
}

// ── API ──────────────────────────────────────────────────────────────────

function kopfzeilen() {
  const h = { "Content-Type": "application/json" };
  if (!AWS_MODUS) h["X-Jusperfect-Nutzer"] = ($("nutzer").value || "").trim();
  else if (zugangstoken) h["Authorization"] = "Bearer " + zugangstoken;
  return h;
}

async function api(methode, pfad, daten) {
  // Ein abgelaufenes Token führt nicht zu einem rätselhaften Fehler, sondern
  // zurück zur Anmeldung.
  if (AWS_MODUS && !angemeldet()) {
    await anmeldungStarten();
    throw new Error("Bitte anmelden.");
  }
  let antwort;
  try {
    antwort = await fetch(K.apiBasis + pfad, {
      method: methode, headers: kopfzeilen(),
      body: daten === undefined ? undefined : JSON.stringify(daten),
    });
  } catch (e) {
    // Der Browser sagt hier "Failed to fetch" - englisch, und es steht nicht
    // darin, was zu tun ist. Aus der Kanzlei: "Erkennt den Bearbeiter nicht
    // an. Failed to fetch." Es ist kein Anmeldefehler: Die Seite steht noch
    // im Browser, aber niemand antwortet mehr darauf.
    throw new Error(NICHT_ERREICHBAR);
  }
  if (antwort.status === 204) return null;
  let inhalt = null;
  try { inhalt = await antwort.json(); } catch (e) { /* leer */ }
  if (antwort.status === 401 && AWS_MODUS) {
    zugangstoken = null; tokenAblauf = 0; anmeldungAnzeigen();
    throw new Error("Die Anmeldung ist abgelaufen. Bitte erneut anmelden.");
  }
  if (!antwort.ok) throw new Error((inhalt && inhalt.fehler) || `Fehler ${antwort.status}`);
  return inhalt;
}

async function mitKnopf(knopf, arbeit) {
  // Frueher stand hier "if (!knopf) return arbeit();" - ohne try/catch. Vier
  // Aufrufer uebergeben keinen Knopf, darunter das Uebernehmen im Explorer.
  // Schlug das fehl, verschwand der Dialog, die Arbeitsflaeche ging nicht auf,
  // und es stand nirgends warum: Der Fehler landete als unbehandelte
  // Promise-Ablehnung in der Browserkonsole, die in der Kanzlei niemand
  // aufmacht. Aus der Kanzlei: "bei der grossen akte oeffnet er nicht die
  // arbeitsflaeche". Ein Fehler, der keinen Fehler zeigt, ist der teuerste.
  if (knopf) knopf.disabled = true;
  const fertig = knopf ? wartekreis(knopf) : null;
  // Mitzaehlen, was gerade laeuft. Hier und nur hier: Durch diese Funktion
  // geht jede Arbeit, die dauern kann - Analyse, Entwurf, Einlesen,
  // Uebernehmen. Ein eigener Zaehler je Vorgang liefe irgendwann auseinander.
  laufendeArbeiten++;
  try { return await arbeit(); }
  catch (e) { melden(e.message, true); }
  finally {
    laufendeArbeiten = Math.max(0, laufendeArbeiten - 1);
    if (fertig) fertig(); if (knopf) knopf.disabled = false;
  }
}

//: Wie viele Arbeiten gerade laufen. 0 heisst: nichts ist unterwegs.
let laufendeArbeiten = 0;

//: Verlassen wir die Seite mit Absicht? Dann keine Rueckfrage.
//:
//: Die An- und Abmeldung bei Cognito fuehrt ueber eine fremde Adresse. Eine
//: Rueckfrage an dieser Stelle waere eine Warnung vor dem, was der Anwender
//: gerade selbst angeklickt hat.
let gewolltesVerlassen = false;

/** Steht gerade etwas auf dem Spiel, das ein Schliessen kosten wuerde? */
function etwasStehtAufDemSpiel() {
  if (nebenfenster) return false;      // ein Spiegel haelt nichts
  if (gewolltesVerlassen) return false;
  if (laufendeArbeiten > 0 || liestGerade) return true;
  return !!(sitzung && sitzung.sitzung);
}

// Die Rueckfrage vor dem Schliessen.
//
// Aus der Kanzlei am 05.10.2026: "Koennen wir noch einbauen, dass ein
// versehentliches Schliessen ausgeschlossen ist... Rueckfrage, wollen Sie das
// Fenster wirklich schliessen. Dieses gilt insbesondere bei laufenden
// Vorgaengen."
//
// Zwei Dinge, die hier NICHT gehen, und die der Anwender wissen muss: Den
// Wortlaut der Rueckfrage bestimmt der Browser, nicht dieses Programm - jeder
// Versuch, ihn zu setzen, wird seit Jahren von allen Browsern verworfen. Und
// sie erscheint erst, wenn im Fenster einmal geklickt oder getippt wurde; ein
// Fenster, das nur angesehen wurde, geht ohne Nachfrage zu. Beides ist eine
// Schutzmassnahme der Browser gegen Seiten, die sich nicht schliessen lassen.
//
// Deshalb wird hier nicht immer gefragt, sondern nur, wenn wirklich etwas auf
// dem Spiel steht. Eine Rueckfrage, die bei jedem Schliessen kommt, wird nach
// einer Woche weggeklickt, ohne gelesen zu werden - und dann schuetzt sie
// genau dann nicht mehr, wenn es darauf ankommt.
window.addEventListener("beforeunload", (ereignis) => {
  if (!etwasStehtAufDemSpiel()) return;
  ereignis.preventDefault();
  ereignis.returnValue = "";   // aeltere Browser verlangen das noch
});

// ── Der Kreis, der sich füllt ────────────────────────────────────────────────
// Aus der Kanzlei: "Auch bei der Analyse mache einen Kreis, der sich füllt,
// neben dem Wort Analyse, damit der Bearbeiter sieht, dass die KI für die
// Bearbeitung Zeit braucht." Bisher wurde der Knopf nur grau - und eine
// Aktenanalyse über ein volles Gedächtnis dauert eine halbe Minute und länger.
// Grau heißt aber auch "kaputt"; ein Kreis, der wächst, heißt "es läuft".
//
// Wie lange es dauert, weiß vorher niemand: Das hängt am Modell, an der Länge
// der Akte und an der Leitung. Der Kreis füllt sich deshalb nach der zuletzt
// gemessenen Dauer und bleibt bei 92 Prozent stehen, bis die Antwort wirklich
// da ist. Er sagt damit "es läuft noch" - und niemals "gleich fertig", wenn
// das nicht stimmt. Erst die Antwort schließt ihn.
const WARTE_VERZUG = 400;   // Millisekunden, bevor der Kreis überhaupt erscheint
const WARTE_DECKEL = 92;    // Prozent; weiter füllt er sich nicht von allein
const WARTE_VORGABE = 20;   // Sekunden, solange nichts gemessen wurde

function warteDauer(schluessel) {
  try {
    const wert = Number(localStorage.getItem("jusperfect.dauer." + schluessel));
    if (wert > 0.5 && wert < 600) return wert;
  } catch (e) { /* Privater Modus: dann eben die Vorgabe. */ }
  return WARTE_VORGABE;
}

function warteMerken(schluessel, sekunden) {
  // Gleitender Mittelwert: Ein einzelner Ausreißer verstellt die Anzeige nicht
  // dauerhaft, eine durchweg größere Akte schon. Sehr kurze Läufe zählen nicht
  // mit - ein sofort abgewiesener Aufruf ist keine Messung der Dauer.
  if (!schluessel || !(sekunden > 1)) return;
  const neu = 0.6 * warteDauer(schluessel) + 0.4 * sekunden;
  try { localStorage.setItem("jusperfect.dauer." + schluessel, neu.toFixed(1)); } catch (e) { /* egal */ }
}

function wartekreis(knopf) {
  const schluessel = knopf.dataset.aktion || knopf.id || "";
  const dauer = warteDauer(schluessel) * 1000;
  const beginn = Date.now();
  let kreis = null, ticker = null;
  // Der Verzug ist Absicht: Ein Knopf, der ein Fenster öffnet, ist nach zwanzig
  // Millisekunden fertig. Ein Kreis, der dabei aufblitzt, wäre nur Unruhe.
  const erscheinen = setTimeout(() => {
    kreis = document.createElement("span");
    kreis.className = "warte-kreis";
    kreis.setAttribute("aria-hidden", "true");
    kreis.style.setProperty("--anteil", "0");
    knopf.appendChild(kreis);
    knopf.classList.add("wartet");
    ticker = setInterval(() => {
      const anteil = Math.min(WARTE_DECKEL, (Date.now() - beginn) / dauer * 100);
      kreis.style.setProperty("--anteil", anteil.toFixed(1));
    }, 120);
  }, WARTE_VERZUG);
  return () => {
    clearTimeout(erscheinen); clearInterval(ticker);
    warteMerken(schluessel, (Date.now() - beginn) / 1000);
    if (!kreis) return;
    kreis.style.setProperty("--anteil", "100");
    knopf.classList.remove("wartet");
    const weg = kreis; kreis = null;
    setTimeout(() => weg.remove(), 250);
  };
}

// ── Rückgängig ───────────────────────────────────────────────────────────────
// Nur für Handgriffe, die wirklich etwas wegnehmen und die sich wirklich
// zurücknehmen lassen. Ein Rückgängig, das dann doch nicht zurückkann, ist
// schlimmer als keines: Es verleitet dazu, sorgloser zu klicken.
//
// Die Leiste läuft bewusst nicht ab. Wer im Posteingang danebengegriffen hat,
// merkt es oft erst beim Blick in die Akte; eine Frist, die währenddessen
// verstreicht, wäre keine Hilfe.
let rueckgaengig = null;

function rueckgaengigAnbieten(text, tun) {
  rueckgaengig = { tun };
  $("rueckgaengig-text").textContent = text;
  $("rueckgaengig").hidden = false;
}

function rueckgaengigVerbergen() {
  rueckgaengig = null;
  $("rueckgaengig").hidden = true;
}

async function rueckgaengigMachen() {
  if (!rueckgaengig) return;
  const tun = rueckgaengig.tun;
  // Erst wegnehmen, dann ausführen: Sonst lädt ein zweiter Klick auf eine
  // langsame Antwort denselben Vorgang ein zweites Mal zurück.
  rueckgaengigVerbergen();
  await tun();
}

// Eine Meldung, die stehenbleibt, bis sie abgeloest wird: fuer Arbeit, die
// laenger dauert als ein Wimpernschlag. "melden" laeuft nach Sekunden ab und
// waere hier eine Luege - der Vorgang ist dann noch nicht fertig.
function laeuft(text) {
  const m = $("meldung");
  m.textContent = text; m.className = "meldung"; m.hidden = false;
  clearTimeout(m._t); m._t = 0;
}

function melden(text, fehler) {
  const m = $("meldung");
  m.textContent = text; m.className = "meldung" + (fehler ? " fehler" : ""); m.hidden = false;
  clearTimeout(m._t); m._t = setTimeout(() => { m.hidden = true; }, fehler ? 6000 : 3000);
}

// ── Status ─────────────────────────────────────────────────────────────────


// Aus "eu.anthropic.claude-opus-4-6-v1" wird "Opus 4.6". Nur fuer die Anzeige;
// aufgerufen wird immer die vollstaendige Kennung, und die steht im Tooltip.
//
// Warum ueberhaupt: In der Kopfzeile stand die ganze Kennung. Bei 1024 Pixeln
// schob sie die Aktenleiste aus dem Bild, und einer Anwaeltin sagt
// "-20251001-v1:0" nichts. Die genauen Kennungen zeigt der Selbsttest.
//
// Vorsichtig gebaut: Greift das Muster nicht, bleibt die Kennung stehen, wie
// sie ist. Eine falsch verkuerzte Kennung waere schlimmer als eine lange.
function kurzeKennung(kennung) {
  const roh = String(kennung || "");
  const treffer = roh.match(/^(?:eu\.|us\.)?anthropic\.claude-([a-z]+)-(\d+)-(\d+)\b/);
  if (!treffer) return roh;
  const [, name, gross, klein] = treffer;
  return `${name.charAt(0).toUpperCase()}${name.slice(1)} ${gross}.${klein}`;
}

async function ladeStatus() {
  if (!AWS_MODUS && !($("nutzer").value || "").trim()) {
    $("status").textContent = "kein Benutzer gewählt"; return false;
  }
  if (AWS_MODUS && !angemeldet()) {
    $("status").textContent = "nicht angemeldet"; anmeldungAnzeigen(); return false;
  }
  try {
    const s = await api("GET", "/api/status");
    K.letzterGrund = "";
    $("status").textContent = s.anbieter === "demo" ? "Demo (ohne KI)" : "Bedrock " + kurzeKennung(s.modell);
    $("status").title = s.anbieter === "demo" ? "" : s.modell;
    // Nur der Name wird gesetzt - Sinnbild und der Zusatz "wechseln" stehen
    // fest im HTML. Wer hier textContent auf den Knopf setzt, loescht beide.
    const wer = $("nutzer-name");
    if (wer) wer.textContent = s.nutzer.name;
    if (s.kosten) $("kosten").textContent = `${s.kosten.verbraucht_eur.toFixed(2)} / ${s.kosten.budget_eur.toFixed(0)} €`;
    // Die Vorschaltstufe Perfect Shield stand als abgeschalteter Schalter auf
    // der Startseite - an der prominentesten Stelle des Programms, mit dem
    // Zusatz "nicht aktiv". Sie ist eine bewusste Konzeptentscheidung und
    // bleibt in der Einstellung; ein Schalter, der nichts tut, gehoert aber
    // nicht dorthin, wo der Bearbeiter jeden Morgen anfaengt.
    // Posteingang: der Knopf erscheint nur, wenn ein Ordner eingerichtet ist.
    const pe = $("posteingang-oeffnen");
    if (pe) pe.hidden = !s.posteingang_aktiv;
    // Referenzen: der Knopf erscheint nur, wenn ein Referenzordner eingerichtet ist.
    const rf = document.querySelector('[data-aktion="referenzen"]');
    if (rf) rf.hidden = !s.referenzen_aktiv;
    // Haufe-Recherche: Knopf nur, wenn eine Adresse hinterlegt ist.
    K.haufe = s.haufe || null;
    K.gesetze = s.gesetze || null;
    const hf = document.querySelector('[data-aktion="haufe"]');
    if (hf) hf.hidden = !s.haufe_aktiv;
    // Der Gesetze-Knopf wird NICHT eingeblendet - er steht fest da, wie
    // Eingangspruefung und Pruefliste. Die Adresse der amtlichen Seite ist
    // im Programm hinterlegt; fehlt sie, sagt es der Klick.
    // Ohne eingerichteten Auftragsordner gibt es nichts anzulegen -
    // dann fehlt der Knopf, statt in einen Fehler zu laufen.
    K.modellprotokoll = s.modellprotokoll || null;
    selbsttestMarkeSetzen();
    K.auftraegeAktiv = !!s.auftraege_aktiv;
    K.gedaechtnisAktiv = !!s.gedaechtnis_aktiv;
    K.gedaechtnisOrt = s.gedaechtnis_ort || "";
    K.maxPassagenZeichen = s.max_passagen_zeichen || 160000;
    K.nichtVorwaehlen = s.nicht_vorwaehlen || [];
    // Der Demo-Anbieter kostet nichts; eine Schaetzung waere dort irrefuehrend.
    K.kostenpflichtig = s.anbieter !== "demo";
    const gm = document.querySelector('[data-aktion="gedaechtnis"]');
    if (gm) gm.hidden = !s.gedaechtnis_aktiv;
    // Abschluss betrifft den dauerhaften Arbeitsbereich; ohne Gedächtnis gibt es keinen.
    const ab = document.querySelector('[data-aktion="abschluss"]');
    if (ab) ab.hidden = !s.gedaechtnis_aktiv;
    // Die Aufsicht führt Akten zusammen: nur für die Verwaltung.
    const au = $("aufsicht-oeffnen");
    if (au) au.hidden = !(s.gedaechtnis_aktiv && s.verwaltung);
    return true;
  } catch (e) {
    K.letzterGrund = e.message;
    $("status").textContent = e.message === NICHT_ERREICHBAR ? NICHT_ERREICHBAR_KURZ : e.message;
    return false;
  }
}

// ── Anmeldeseite: wer arbeitet hier? ────────────────────────────────────────
// Die Frage stand bisher als Eingabefeld in der rechten oberen Ecke, neben
// Kosten und Verbindungszustand. Sie ist aber die erste Frage des Programms
// und nicht eine Anzeige unter mehreren - deshalb hat sie jetzt eine eigene
// Seite, und die Aktenliste kommt erst danach.

function anmeldenZeigen() {
  $("anmelden").hidden = false;
  $("einstieg").hidden = true;
  $("flaeche").hidden = true;
  $("akte-leiste").hidden = true;
  arbeitsstandSchliessen();
  const uebernahme = $("uebernahme");
  if (uebernahme) uebernahme.hidden = true;
  $("nutzer-wechseln").hidden = true;
}

function einstiegZeigen() {
  $("anmelden").hidden = true;
  $("einstieg").hidden = false;
  $("flaeche").hidden = true;
  // Im AWS-Betrieb fuehrt der Weg zurueck ueber das Abmelden bei Cognito,
  // nicht ueber einen Benutzerwechsel im Programm.
  $("nutzer-wechseln").hidden = AWS_MODUS;
  verlaufZeichnen();
  aufsichtMarkeLaden();
}

function anmeldeFehler(text) {
  const kasten = $("anmelde-fehler");
  if (kasten) kasten.classList.remove("wartet");
  const p = $("anmelde-fehler");
  p.textContent = text || "";
  p.hidden = !text;
}

function anmeldeHinweis(text) {
  // Bewusst NICHT der rote Kasten: Ein Programm, das gerade startet, ist keine
  // Stoerung. Die Farbe soll erst dann wechseln, wenn es eine ist.
  const feld = $("anmelde-fehler");
  if (!feld) return;
  feld.hidden = !text;
  feld.textContent = text;
  feld.classList.toggle("wartet", Boolean(text));
}


async function nutzerlisteLaden() {
  // Ohne Anmeldung und ohne Kopfzeile: Diesen Weg gibt es nur im oertlichen
  // Betrieb, und dort steht dieselbe Liste ohnehin als Datei auf demselben
  // Rechner. Im AWS-Betrieb antwortet der Server hier mit 404.
  let liste = [];
  let stand = 0;
  // Beim allerersten Aufruf wartet die Seite kurz auf das Programm, statt
  // sofort Alarm zu schlagen. Aus der Kanzlei: "Am Anfang ist dieses Bild
  // irritierend. F5 und es ist weg."
  //
  // Der Grund ist die Startdatei: Sie oeffnet den Browser, BEVOR das Programm
  // bereit ist - und beim ersten Start dauert das, weil Python und die
  // Arbeitsumgebung erst hochkommen. Die Seite war also schneller als der
  // Server und meldete das als Stoerung. Wer das sieht, glaubt, etwas sei
  // kaputt, und tut in aller Regel das Falsche.
  //
  // Nicht endlos: Nach etwa zehn Sekunden ist es keine Anlaufzeit mehr,
  // sondern ein Fehler, und dann soll er auch dastehen.
  const ANLAEUFE = 12;
  for (let versuch = 1; versuch <= ANLAEUFE; versuch++) {
    try {
      const antwort = await fetch(K.apiBasis + "/api/nutzer");
      stand = antwort.status;
      if (antwort.ok) liste = (await antwort.json()).nutzer || [];
      anmeldeFehler("");
      break;
    } catch (e) {
      // Eine 404 ist hier in Ordnung - im AWS-Betrieb gibt es diesen Weg
      // nicht, dann bleibt das Eingabefeld darunter. Antwortet dagegen
      // ueberhaupt niemand, steht die Anmeldeseite leer da und niemand weiss
      // warum. Der Grund gehoert auf die Seite, nicht erst hinter den ersten
      // Klick - aber erst, wenn es wirklich einer ist.
      if (versuch === ANLAEUFE) { anmeldeFehler(NICHT_ERREICHBAR); break; }
      anmeldeHinweis(`Das Programm startet … (${versuch})`);
      await new Promise((f) => setTimeout(f, 800));
    }
  }
  const ul = $("nutzerliste");
  ul.replaceChildren();
  for (const n of liste) {
    const li = document.createElement("li");
    const knopf = document.createElement("button");
    knopf.type = "button";
    const name = document.createElement("span"); name.className = "nname"; name.textContent = n.name;
    const kennung = document.createElement("span"); kennung.className = "nkennung"; kennung.textContent = n.id;
    knopf.append(name, kennung);
    knopf.addEventListener("click", () => mitKnopf(knopf, () => benutzerWaehlen(n.id)));
    li.appendChild(knopf);
    ul.appendChild(li);
  }
  // Eine leere Liste ohne ein Wort dazu ist das, was die Kanzlei gesehen hat:
  // "Wer arbeitet hier?" - und darunter nichts. Im AWS-Betrieb (404) ist das
  // richtig, dort tippt man die Kennung. Oertlich ist es ein Fehler, und dann
  // gehoert der Grund auf die Seite.
  if (!liste.length && stand && stand !== 404) {
    anmeldeFehler("Es ist kein Benutzer hinterlegt. Die Liste kommt aus der Datei, "
                  + "die in der Startdatei unter JUSPERFECT_NUTZER_DATEI steht – bei den "
                  + "Testakten testdaten\\nutzer.json. Sie können unten auch eine "
                  + "Kennung von Hand eintragen, etwa ra-weber.");
  }

  let zuletzt = "";
  try { zuletzt = localStorage.getItem("jusperfect.nutzer") || ""; } catch (e) {}
  if (zuletzt && !liste.some((n) => n.id === zuletzt)) $("nutzer-eigen").value = zuletzt;
}

// ── Der zweite Faktor ────────────────────────────────────────────────────
//
// Aus der Kanzlei am 15.10.2026: "Ich moechte fuer die Programmoeffnung
// jusperfect und die Moeglichkeit der Einrichtung einer
// 2-Faktor-Authentifizierung."
//
// Der Anlass steht in der Folgenabschaetzung, Risiko R7 - dem einzigen, das
// dort auf "hoch" steht: Die Anmeldung ist kein Kennwort, sondern eine
// Kennung. Wer am Rechner sitzt, kann eine andere eintragen.
//
// Der Dialog kommt NACH der Wahl des Benutzers und VOR allem anderen. Ohne
// ihn ist das Programm zu; deshalb hat er kein Kreuz und keine Esc-Taste.

async function zfStand() {
  const antwort = await fetch(K.apiBasis + "/api/anmeldung/zweiter-faktor",
                              { headers: kopfzeilen() });
  if (!antwort.ok) return { noetig: false };
  return await antwort.json();
}

async function zfSenden(pfad, code) {
  const antwort = await fetch(K.apiBasis + pfad, {
    method: "POST", headers: kopfzeilen(), body: JSON.stringify({ code }),
  });
  let inhalt = null;
  try { inhalt = await antwort.json(); } catch (e) { /* leer */ }
  if (!antwort.ok) throw new Error((inhalt && inhalt.fehler)
    || (inhalt && inhalt.detail) || `Fehler ${antwort.status}`);
  return inhalt;
}

/** Den zweiten Faktor verlangen. Liefert true, wenn der Weg frei ist. */
async function zweiterFaktorVerlangen() {
  const stand = await zfStand();
  if (!stand.noetig || stand.bestaetigt) return true;
  const dialog = $("zf-dialog");
  if (!dialog) return true;
  const feld = $("zf-code"), fehler = $("zf-fehler");
  const einrichtung = $("zf-einrichtung"), knopfEin = $("zf-einrichten");
  let eingerichtet = !!stand.eingerichtet;

  const zeigen = () => {
    $("zf-titel").textContent = eingerichtet
      ? "Zweiter Faktor" : "Zweiten Faktor einrichten";
    $("zf-text").textContent = eingerichtet
      ? "Bitte das Einmalkennwort aus Ihrer Authentifizierungs-App eingeben."
      : "Für diese Kennung ist noch kein zweiter Faktor eingerichtet. "
        + "Mit \u201EEinrichten\u201C beginnen.";
    knopfEin.hidden = eingerichtet;
    $("zf-senden").hidden = !eingerichtet && einrichtung.hidden;
    fehler.hidden = true;
    feld.value = "";
  };
  zeigen();
  einrichtung.hidden = true;
  dialog.showModal();
  feld.focus();

  return await new Promise((fertig) => {
    const schliessen = (frei) => {
      dialog.close();
      knopfEin.removeEventListener("click", aufEinrichten);
      $("zf-senden").removeEventListener("click", aufSenden);
      feld.removeEventListener("keydown", aufTaste);
      fertig(frei);
    };
    const aufEinrichten = async () => {
      try {
        const auf = await (await fetch(K.apiBasis + "/api/anmeldung/zweiter-faktor/einrichten",
                                       { method: "POST", headers: kopfzeilen() })).json();
        if (!auf.geheimnis) throw new Error(auf.fehler || "Die Einrichtung ist fehlgeschlagen.");
        $("zf-geheimnis").textContent = auf.geheimnis;
        einrichtung.hidden = false;
        knopfEin.hidden = true;
        $("zf-senden").hidden = false;
        $("zf-text").textContent = "Geheimnis in die App übernehmen, dann das "
          + "angezeigte Einmalkennwort eingeben.";
        feld.focus();
      } catch (f) { fehler.hidden = false; fehler.textContent = f.message; }
    };
    const aufSenden = async () => {
      const code = (feld.value || "").trim();
      try {
        await zfSenden(eingerichtet
          ? "/api/anmeldung/zweiter-faktor/pruefen"
          : "/api/anmeldung/zweiter-faktor/bestaetigen", code);
        schliessen(true);
      } catch (f) {
        fehler.hidden = false;
        fehler.textContent = f.message;
        feld.value = ""; feld.focus();
      }
    };
    const aufTaste = (e) => { if (e.key === "Enter") { e.preventDefault(); aufSenden(); } };
    knopfEin.addEventListener("click", aufEinrichten);
    $("zf-senden").addEventListener("click", aufSenden);
    feld.addEventListener("keydown", aufTaste);
  });
}

async function benutzerWaehlen(kennung) {
  kennung = (kennung || "").trim();
  if (!kennung) { anmeldeFehler("Bitte einen Benutzer wählen."); return; }
  $("nutzer").value = kennung;
  // Der zweite Faktor VOR dem Status: Der Status ist schon ein Zugriff, und
  // genau den soll der Faktor schützen.
  if (!(await zweiterFaktorVerlangen())) { $("nutzer").value = ""; return; }
  if (!(await ladeStatus())) {
    // Der Status traegt bereits den Grund - eine unbekannte Kennung, ein
    // Server, der nicht antwortet. Ihn hier zu wiederholen waere genauer als
    // ein allgemeiner Satz.
    $("nutzer").value = "";
    anmeldeFehler(K.letzterGrund || $("status").textContent
                  || "Diese Kennung ist nicht hinterlegt.");
    return;
  }
  try { localStorage.setItem("jusperfect.nutzer", kennung); } catch (e) {}
  anmeldeFehler("");
  einstiegZeigen();
}

async function benutzerWechseln() {
  // Eine offene Sitzung gehoert dem bisherigen Benutzer. Sie wird geschlossen,
  // nicht uebergeben - sonst arbeitete der naechste in fremden Texten weiter.
  if (sitzung) await sitzungSchliessen();
  $("nutzer").value = "";
  $("status").textContent = "kein Benutzer gewählt";
  anmeldeFehler("");
  await nutzerlisteLaden();
  anmeldenZeigen();
}

// ── Zuletzt geöffnet ────────────────────────────────────────────────────────
// Nur Aktenzeichen und Bezeichnung, nur in diesem Browser, je Benutzer
// getrennt. Kein Akteninhalt, keine Fundstelle, keine Frage - die Liste soll
// den Weg zurueck in die Akte von gestern verkuerzen und sonst nichts.

const VERLAUF_MAX = 6;

function verlaufSchluessel() {
  return "jusperfect.verlauf." + (($("nutzer").value || "").trim() || "-");
}

function verlaufLesen() {
  try { return JSON.parse(localStorage.getItem(verlaufSchluessel()) || "[]"); } catch (e) { return []; }
}

function verlaufMerken(akte) {
  if (!akte || !akte.id) return;
  const eintrag = { id: akte.id, aktenzeichen: akte.aktenzeichen || "", bezeichnung: akte.bezeichnung || "",
                    wann: Date.now() };
  const liste = [eintrag, ...verlaufLesen().filter((x) => x.id !== akte.id)].slice(0, VERLAUF_MAX);
  try { localStorage.setItem(verlaufSchluessel(), JSON.stringify(liste)); } catch (e) {}
}

function verlaufLeeren() {
  try { localStorage.removeItem(verlaufSchluessel()); } catch (e) {}
  verlaufZeichnen();
  melden("Die Liste der zuletzt geöffneten Akten wurde in diesem Browser gelöscht.");
}

function wannText(zeit) {
  const tage = Math.floor((Date.now() - zeit) / 86400000);
  if (tage <= 0) return "heute";
  if (tage === 1) return "gestern";
  if (tage < 7) return `vor ${tage} Tagen`;
  return new Date(zeit).toLocaleDateString("de-DE");
}

function verlaufZeichnen() {
  const liste = verlaufLesen();
  $("verlauf-block").hidden = !liste.length;
  const ul = $("verlauf");
  ul.replaceChildren();
  for (const a of liste) {
    const li = document.createElement("li");
    const az = document.createElement("div"); az.className = "az";
    az.textContent = [a.aktenzeichen, a.bezeichnung].filter(Boolean).join(" · ");
    const meta = document.createElement("div"); meta.className = "meta wann";
    meta.textContent = "zuletzt geöffnet " + wannText(a.wann);
    li.append(az, meta);
    akteAnklickbar(li, ul, a.id);
    ul.appendChild(li);
  }
}

async function aufsichtMarkeLaden() {
  // Der Knopf soll sagen, ob es etwas zu entscheiden gibt - sonst ist er nur
  // eine Beschriftung. Der Aufruf kostet nichts (kein Modell) und darf still
  // scheitern; die Aktenliste haengt nicht an ihm.
  const knopf = $("aufsicht-oeffnen"), marke = $("aufsicht-marke");
  if (!knopf || knopf.hidden) { if (marke) marke.hidden = true; return; }
  try {
    const daten = await api("GET", "/api/verwaltung/arbeitsbereiche");
    marke.textContent = String(daten.handlungsbedarf || 0);
    marke.hidden = !daten.handlungsbedarf;
  } catch (e) { marke.hidden = true; }
}

// ── Akten und Sitzung ───────────────────────────────────────────────────────

/** Eine Aktenzeile anklickbar machen - mit Kreis, der sich füllt.
 *
 * Aus der Kanzlei am 25.09.2026: "auch lädt er lange, um das Fenster mit der
 * Auswahl der Akten zu öffnen - man denkt, das Programm reagiert nicht."
 *
 * Hier stand "mitKnopf(null, ...)". Ohne Ziel gibt es keinen Kreis, und das
 * Öffnen einer echten Akte dauert: Alle Dokumente samt Unterordnern werden
 * abgefragt, eine Anfrage nach der anderen, weil der Hersteller je IP nur
 * eine zugleich zulässt. Ein Klick, der nichts zu tun scheint, ist schlimmer
 * als einer, der dauert.
 *
 * Derselbe Schlüssel für alle Akten: Wie lange die letzte gebraucht hat, ist
 * die beste Schätzung für die nächste.
 */
function akteAnklickbar(li, ul, akteId) {
  li.dataset.aktion = "akte-oeffnen";
  li.addEventListener("click", () => {
    if (ul.classList.contains("laedt")) return;     // kein zweiter Klick
    ul.classList.add("laedt");
    // Der Kreis allein genuegt nicht: Er sagt "es laeuft", aber nicht, WAS.
    // Aus der Kanzlei: "ein Fenster, das dem Benutzer sagt, bitte warten Sie
    // einen Moment, die Akten muessen eingelesen werden, wuerde ja auch
    // reichen." Beides zusammen: der Kreis an der Zeile, die er angeklickt
    // hat, und der Satz, der sagt, worauf er wartet.
    laeuft("Die Akte wird geöffnet – die Dokumentliste wird eingelesen. " +
           "Das dauert bei einer vollen Akte einen Moment.");
    mitKnopf(li, () => akteOeffnen(akteId))
      .finally(() => { ul.classList.remove("laedt"); });
  });
}

/** Das Zeichen für eine archivierte Akte.
 *
 * In MORGEN.md stand, über die Schnittstelle sei nicht zu sehen, ob eine Akte
 * archiviert ist. Die Beschreibung des Herstellers sagt etwas anderes, und
 * der Adapter liest den Status seit dem 23.09.2026 mit - gezeigt wurde er nie.
 *
 * Das Wort steht da, nicht nur eine Farbe: Wer die Liste überfliegt, liest
 * eher als dass er Farben unterscheidet, und eine Farbe allein trägt für
 * jemanden mit Farbsehschwäche gar nichts.
 */
function archivMarke() {
  const marke = document.createElement("span");
  marke.className = "archivmarke";
  marke.textContent = "archiviert";
  marke.title = "Diese Akte ist in jurnodes archiviert.";
  return marke;
}

async function aktenSuchen() {
  const akten = await api("GET", `/api/akten?suche=${encodeURIComponent($("suche").value.trim())}`);
  const ul = $("aktenliste"); ul.replaceChildren();
  if (!akten.length) {
    const li = document.createElement("li"); li.className = "hinweis";
    li.textContent = "Keine Akte gefunden oder keine Berechtigung."; ul.appendChild(li); return;
  }
  for (const a of akten) {
    const li = document.createElement("li");
    const az = document.createElement("div"); az.className = "az";
    az.textContent = `${a.aktenzeichen} · ${a.bezeichnung}`;
    // Archivierte Akten sahen bis zum 25.09.2026 aus wie laufende. Der
    // Status kam vom Server ohnehin mit - er wurde nur nirgends gezeigt.
    // Wer an einer abgelegten Sache arbeitet, soll das sehen, bevor er
    // anfaengt, und nicht hinterher.
    if (a.status === "archiviert") az.appendChild(archivMarke());
    const meta = document.createElement("div"); meta.className = "meta";
    meta.textContent = [a.rechtsgebiet, a.sachbearbeiter].filter(Boolean).join(" · ");
    li.append(az, meta);
    akteAnklickbar(li, ul, a.id);
    ul.appendChild(li);
  }
}

// ── Zwei-Fenster-Explorer: jurnodes ⇄ Arbeitsakte ───────────────────────────

let explorer = null;  // { karte: Map(id->dok), gewaehlt: Set, geladen: Set, initial: bool }

/** Welche Datei gerade worauf wartet: id -> "wartet" | "liest".
 *
 * Aus der Kanzlei am 16.10.2026: „Auch den Leseprozess nachvollziehbar
 * darstellen. Datei fuer Datei abhaken." Vorher gab es einen Balken mit einer
 * Prozentzahl - der sagt, WIE WEIT es ist, aber nicht, WAS gerade geschieht
 * und was schon durch ist. Hier steht jede Datei einzeln.
 */
let leseStand = new Map();
/** Laeuft der Lesevorgang gerade im Explorer? Dann bleibt der Dialog offen. */
let explorerLiest = false;

async function akteOeffnen(akteId) {
  // Die Meldung der zuletzt geschlossenen Akte hat hier nichts mehr zu suchen.
  schlussHinweisZeigen("");
  sitzung = await api("POST", "/api/sitzungen", { akte_id: akteId });
  verlaufMerken(sitzung.sitzung.akte);
  // Die Rueckfrage kommt VOR dem Dokumentfenster: Sie betrifft die Akte als
  // Ganzes, und wer erst Dokumente anhakt und dann gefragt wird, ob die Akte
  // noch laeuft, liest die Frage als Stoerung statt als Frage.
  await laeuftNochFragen();
  explorerStarten(true);
}

// ── Läuft die Akte noch? ─────────────────────────────────────────────────
//
// Aus der Kanzlei am 15.10.2026: "Du musst fragen: Laeuft die Akte noch.
// Akten laufen manchmal jahrelang. Wenn die Frage mit Ja beantwortet wird,
// dann verlaengert sich die Loeschfrist um 12 Monate."
//
// Die Zeit loest hier die FRAGE aus und nicht die Loeschung. Das ist der
// ganze Unterschied zu einer Frist, die von selbst ablaeuft - und der Grund,
// warum dieser Dialog kein Kreuz hat.

function laeuftNochZeigen(stand) {
  const dialog = $("laeuft-dialog");
  if (!dialog || !stand || !stand.faellig) return false;
  const a = (sitzung && sitzung.sitzung && sitzung.sitzung.akte) || {};
  $("laeuft-frage").textContent = stand.frage || "Läuft die Akte noch?";
  $("laeuft-akte").textContent = `${a.aktenzeichen || stand.aktenzeichen || ""} · `
    + `${a.bezeichnung || stand.bezeichnung || ""}`;
  const seit = stand.zuletzt_benutzt_am ? datumKurz(stand.zuletzt_benutzt_am) : null;
  $("laeuft-grund").textContent =
    (seit ? `In dieser Akte wurde seit dem ${seit} nicht mehr gearbeitet. ` : "")
    + `Nach ${stand.monate} Monaten ohne Sitzung wird gefragt. `
    + "Ja heißt: die Arbeitskopie bleibt und es wird in "
    + `${stand.monate} Monaten erneut gefragt. Nein heißt: Die Akte wird zum `
    + "Abschluss vorgemerkt. Es wird nichts gelöscht, solange nicht geantwortet ist.";
  dialog.showModal();
  return true;
}

async function laeuftNochFragen() {
  const stand = sitzung && sitzung.aufbewahrung;
  if (!laeuftNochZeigen(stand)) return;
  const dialog = $("laeuft-dialog");
  await new Promise((fertig) => {
    const antworten = async (laeuft) => {
      try {
        await api("POST", `/api/akten/${encodeURIComponent(stand.akte_id)}/aufbewahrung/antwort`,
                  { laeuft_noch: laeuft });
        melden(laeuft
          ? `Vermerkt: Die Akte läuft noch. Die nächste Rückfrage kommt in ${stand.monate} Monaten.`
          : "Vermerkt: Die Akte ist beendet. Sie ist zum Abschluss vorgemerkt.");
      } catch (f) {
        melden(f.message || "Die Antwort konnte nicht vermerkt werden.", true);
      }
      schliessen();
    };
    const schliessen = () => {
      dialog.close();
      ja.removeEventListener("click", aufJa);
      nein.removeEventListener("click", aufNein);
      spaeter.removeEventListener("click", aufSpaeter);
      fertig();
    };
    const ja = $("laeuft-ja"), nein = $("laeuft-nein"), spaeter = $("laeuft-spaeter");
    const aufJa = () => antworten(true);
    // Nein ist die einzige Antwort, die etwas in Gang setzt. Deshalb wird
    // sie bestaetigt - und deshalb steht im Text, was danach geschieht.
    const aufNein = () => {
      if (!confirm("Die Akte ist beendet?\n\nDie Arbeitskopie wird dann zum Abschluss "
                   + "vorgemerkt. Gelöscht wird sie erst beim Abschluss, nach dem Export "
                   + "des Arbeitsstands. Die Akte selbst bleibt unberührt.")) return;
      antworten(false);
    };
    // "Spaeter" beantwortet nichts - und genau deshalb bleibt die Frage
    // faellig und steht beim naechsten Oeffnen wieder da.
    const aufSpaeter = () => { melden("Die Frage bleibt offen und kommt wieder."); schliessen(); };
    ja.addEventListener("click", aufJa);
    nein.addEventListener("click", aufNein);
    spaeter.addEventListener("click", aufSpaeter);
  });
}

async function dokumenteVerwalten() {
  sitzung = await api("GET", `/api/sitzungen/${sitzung.sitzung.id}`);
  explorerStarten(false);
}

function explorerStarten(initial) {
  const karte = new Map();
  for (const d of (sitzung.dokumente || []))
    karte.set(d.id, { id: d.id, titel: d.titel, kategorie: d.kategorie || "",
                      datum: d.datum || "", ordner: d.ordner || "" });
  const geladen = new Set((sitzung.sitzung.geladen || []).map((g) => g.dokument_id));
  for (const g of (sitzung.sitzung.geladen || []))
    if (!karte.has(g.dokument_id)) karte.set(g.dokument_id, { id: g.dokument_id, titel: g.titel, kategorie: "", datum: "", ordner: "" });
  explorer = { karte, gewaehlt: new Set(geladen), geladen, initial, fertig: false, weg: [] };
  leseStand.clear();
  // Die Beschriftung des Knopfes setzt explorerZeigen weiter unten - sie
  // haengt daran, ob die Akte gerade erst geoeffnet wird.
  explorerLesenZeigen("");
  explorerSperren(false);
  const zeile = $("explorer-lesezeile");
  if (zeile) zeile.classList.remove("misslungen");
  const anhalten = $("explorer-anhalten");
  if (anhalten) { anhalten.disabled = false; anhalten.hidden = false; }
  const a = sitzung.sitzung.akte;
  $("explorer-titel").textContent = `${a.aktenzeichen} · ${a.bezeichnung}`;
  // Was in der E-Akte liegt und noch keinen Inhalt hat. Eine unvollstaendige
  // Liste sieht sonst aus wie eine vollstaendige - und was fehlt, faellt in
  // einer Akte erst auf, wenn es darauf ankommt.
  const eakteHinweis = $("explorer-eakte");
  if (eakteHinweis) {
    const offen = sitzung.korrespondenz_ohne_inhalt || 0;
    eakteHinweis.hidden = !offen;
    if (offen > 0) eakteHinweis.textContent =
      `${offen} Eintrag/Einträge der E-Akte (Mail, beA, Post) stehen hier nicht: `
      + `Ihr Inhalt ist noch nicht angebunden. Vermerke sind dabei.`;
    else if (offen < 0) { eakteHinweis.hidden = false;
      eakteHinweis.textContent = "Die E-Akte war nicht zu lesen; die Vermerke fehlen in dieser Liste."; }

    // E-Mails, deren Inhalt nicht geholt werden konnte. Aus der Kanzlei am
    // 08.10.2026: "bei Ueberschreitung sollte der Bearbeiter gewarnt werden
    // und aufmerksam gemacht werden." Die Zeile des Dokuments traegt die
    // Warnung schon; hier steht die Zahl, damit niemand sie zusammensuchen
    // muss. Sie wird AN den Hinweis gehaengt, nicht statt seiner - sonst
    // verdraengt die eine Warnung die andere.
    const m = sitzung.mails_ohne_inhalt || {};
    const teile = [];
    if (m.zu_gross) teile.push(`${m.zu_gross} über der Größengrenze`);
    if (m.gesamtmass) teile.push(`${m.gesamtmass} über dem Gesamtmaß der Akte`);
    if (m.ohne_antwort) teile.push(`${m.ohne_antwort} von jurnodes nicht herausgegeben`);
    if (teile.length) {
      eakteHinweis.hidden = false;
      const satz = `Bei ${teile.join(", ")} E-Mail(s) fehlt der Inhalt. `
        + `Sie stehen in der Liste mit Betreff und Datum; der Vermerk steht in der Zeile.`;
      eakteHinweis.textContent = eakteHinweis.textContent
        ? eakteHinweis.textContent + " — " + satz : satz;
    }

    // Was beim Zerlegen der Mails nicht uebernommen wurde - mit Grund.
    //
    // Befund N04 der dritten Pruefung vom 12.10.2026: Der Parser zaehlte das
    // und niemand sah es. Angezeigt wurden allein die angenommenen Anlagen,
    // und die sahen vollstaendig aus. Das Bild einer Signatur zaehlt hier
    // nicht mit - es ist kein Verlust, nur Rauschen in der Warnung.
    // Die Akte nennt keinen Dateiordner (Befund N07). Dann fehlen die
    // Dateien, und das muss oben stehen - sonst sieht die Liste aus wie eine
    // Akte, in der nur die E-Akte liegt.
    if (sitzung.akte_ohne_dateiordner) {
      eakteHinweis.hidden = false;
      const satz = "Diese Akte nennt in jurnodes keinen Dateiordner. "
        + "Die Dateien der Akte fehlen deshalb in dieser Liste; was aus der "
        + "E-Akte kommt, steht vollständig da. Bitte in jurnodes nachsehen.";
      eakteHinweis.textContent = eakteHinweis.textContent
        ? satz + " — " + eakteHinweis.textContent : satz;
    }

    const aus = sitzung.mail_ausgelassen || {};
    const verluste = Object.entries(aus)
      .filter(([grund, n]) => n > 0 && !grund.startsWith("eingebettetes Bild"))
      .map(([grund, n]) => `${n}× ${grund}`);
    if (verluste.length) {
      eakteHinweis.hidden = false;
      const satz = `Aus den E-Mails nicht übernommen: ${verluste.join(", ")}. `
        + `Welche Mail es betrifft, steht in ihrer eigenen Zeile.`;
      eakteHinweis.textContent = eakteHinweis.textContent
        ? eakteHinweis.textContent + " — " + satz : satz;
    }

    // Eintraege, an denen das Aufbauen der Liste gescheitert ist.
    //
    // Aus der Kanzlei am 13.10.2026: „Akte oeffnen nicht moeglich Vorgang
    // wurde abgebrochen interner Fehler". Ein einziger unerwarteter Eintrag
    // riss das Oeffnen der ganzen Akte mit - 54 Dokumente waren in Ordnung
    // und keines zu sehen. Jetzt faellt dieser eine aus und steht hier.
    //
    // Die Kette ist Programmtext: Ausnahmetypen und Codestellen, kein
    // Wortlaut und keine Aktenkennung. Sie steht hier, weil der Bearbeiter
    // sie weitergeben kann - sonst muesste er das schwarze Fenster lesen.
    const kaputt = sitzung.eintraege_mit_fehler || {};
    const anzahl = Object.values(kaputt).reduce((a, b) => a + b, 0);
    if (anzahl) {
      eakteHinweis.hidden = false;
      const satz = `${anzahl} Eintrag/Einträge dieser Akte ließen sich nicht `
        + `einlesen und fehlen in der Liste. Die übrigen sind vollständig. `
        + `Bitte diese Angabe weitergeben: ${Object.entries(kaputt)
            .map(([kette, n]) => `${n}× ${kette}`).join(" | ")}`;
      eakteHinweis.textContent = eakteHinweis.textContent
        ? satz + " — " + eakteHinweis.textContent : satz;
    }
  }
  $("explorer-uebernehmen").textContent = initial ? "Arbeitsfläche öffnen" : "Übernehmen";
  // Erst leeren, dann zeichnen. Umgekehrt zeigte der Explorer die Liste noch
  // nach dem Filter der VORIGEN Akte, waehrend das Suchfeld daneben schon leer
  // aussah - man sah vier von fuenfzig Dokumenten und keinen Grund dafuer.
  const suche = $("explorer-suche"); if (suche) suche.value = "";
  explorerRendern();
  $("explorer-dialog").showModal();
}

// Die Suche im Explorer. Ein Dokument passt, wenn jedes Suchwort in Titel,
// Datum oder Kategorie vorkommt - "gegner 2026-05" findet die gegnerischen
// Schriftsaetze aus dem Mai. Umlaute werden nicht normalisiert; wer "Kündigung"
// sucht, tippt sie auch so.
function suchbegriffe(feldId) {
  const feld = $(feldId);
  return feld ? feld.value.toLowerCase().split(/\s+/).filter(Boolean) : [];
}

function dokumentPasst(d, begriffe) {
  if (!begriffe.length) return true;
  const text = `${d.titel || ""} ${d.datum || ""} ${d.kategorie || ""} ${d.ordner || ""}`.toLowerCase();
  return begriffe.every((b) => text.includes(b));
}

function zahlZeigen(id, sichtbar, gesamt) {
  const el = $(id);
  el.textContent = sichtbar === gesamt ? String(gesamt) : `${sichtbar}/${gesamt}`;
  el.classList.toggle("gefiltert", sichtbar !== gesamt);
}

// Was der Explorer gerade zeigt - darauf wirken "alle ->" und "<- alle".
// Ungefiltert ist das alles; gefiltert nur, was dem Filter entspricht.
function explorerSichtbar() {
  const begriffe = suchbegriffe("explorer-suche");
  return [...explorer.karte.values()].filter((d) => dokumentPasst(d, begriffe));
}

// Wie die Akte gegliedert ist: ohne Unterordner zuerst, dann die Ordner nach
// dem Alphabet, die E-Akte zuletzt.
//
// Die E-Akte steht hinten, weil sie aus einem ANDEREN Baum kommt - Mails,
// Anlagen und Vermerke liegen nicht im Dateiordner. Sie dazwischenzumischen
// hiesse, zwei Baeume zu einem zu machen; genau diese Verwechslung hat am
// 02.10.2026 drei fremde Schriftstuecke in eine Bausache gebracht.
const EAKTE_ORDNER = "E-Akte";

/** Die sichtbaren Dokumente nach Ordnern, in Lesereihenfolge.
 *
 * Gibt eine Liste von [ordner, dokumente] zurueck. Innerhalb eines Ordners
 * bleibt die Reihenfolge, die der Aktenadapter geliefert hat.
 */
function explorerNachOrdnern(sichtbar) {
  const nach = new Map();
  for (const d of sichtbar) {
    const o = d.ordner || "";
    if (!nach.has(o)) nach.set(o, []);
    nach.get(o).push(d);
  }
  const reihe = [...nach.keys()].sort((a, b) => {
    if (a === b) return 0;
    if (a === "") return -1;
    if (b === "") return 1;
    if (a === EAKTE_ORDNER) return 1;
    if (b === EAKTE_ORDNER) return -1;
    return a.localeCompare(b, "de");
  });
  return reihe.map((o) => [o, nach.get(o)]);
}

function explorerRendern() {
  const liste = $("quelle-liste");
  liste.replaceChildren();
  const sichtbar = explorerSichtbar();
  let angehakt = 0;
  for (const d of sichtbar) if (explorer.gewaehlt.has(d.id)) angehakt++;

  // Ein einziger Ordner ist keine Gliederung - dann bleibt die Liste glatt.
  const gruppen = explorerNachOrdnern(sichtbar);
  const mitUeberschrift = gruppen.length > 1;
  for (const [ordner, dazu] of gruppen) {
    if (mitUeberschrift) liste.appendChild(explorerOrdnerzeile(ordner, dazu));
    for (const d of dazu) liste.appendChild(explorerEintrag(d, explorer.gewaehlt.has(d.id)));
  }

  zahlZeigen("quelle-zahl", sichtbar.length, explorer.karte.size);
  arbeitsspalteZeichnen(sichtbar);
  explorerArtenZeichnen(sichtbar);
  explorerUmfangZeigen();
}

// ── Die linke Spalte: was aus jeder Datei geworden ist ──────────────
//
// Aus der Kanzlei am 16.10.2026: „Es gibt beim Einlesen Fehlermeldungen, diese
// sind aber nicht nachvollziehbar. Eine Gegenueberstellung waere wichtig. …
// Veranschaulichen, welche Datei erfolgreich eingelesen wurde durch gruenen
// Haken hinter der Datei bei jusperfect."
//
// Gemeldet wurde bisher eine Bilanz: „14 von 55 Dokumenten gelesen, 41 nicht:
// 38 ohne erkennbaren Text …" Das sagt die Zahl, nicht die Datei. Wer wissen
// wollte, WELCHE 41, musste sie von Hand zusammensuchen.
//
// Hier steht jede Datei mit ihrem Ausgang: gruener Haken und Seitenzahl, oder
// der Grund. Dieselbe Reihenfolge wie rechts, damit die Zeilen einander
// gegenueberstehen.

/** Die vier Zustaende, die eine Datei in der linken Spalte haben kann. */
const LESEZEICHEN = {
  gelesen: { marke: "\u2713", klasse: "gelesen", wort: "gelesen" },
  liest:   { marke: "\u2026", klasse: "liest", wort: "wird gelesen" },
  wartet:  { marke: "\u00b7", klasse: "wartet", wort: "wartet" },
  fehler:  { marke: "\u2717", klasse: "fehler", wort: "nicht gelesen" },
};

/** Was mit dieser Datei geschehen ist - oder gerade geschieht. */
function lesebefund(id) {
  const laufend = leseStand.get(id);
  if (laufend) return { zustand: laufend };
  const g = (sitzung.sitzung.geladen || []).find((x) => x.dokument_id === id);
  if (g) return { zustand: "gelesen", eintrag: g };
  const n = (sitzung.sitzung.nicht_gelesen || []).find((x) => x.dokument_id === id);
  if (n) return { zustand: "fehler", eintrag: n };
  return null;
}

function arbeitsspalteZeichnen(sichtbar) {
  const liste = $("arbeit-liste");
  if (!liste) return;
  liste.replaceChildren();
  let gelesen = 0, gesamt = 0;
  for (const d of sichtbar) {
    const befund = lesebefund(d.id);
    // Was weder angehakt noch jemals versucht wurde, steht hier nicht: Die
    // linke Spalte zeigt die Arbeitsakte, nicht noch einmal die ganze Akte.
    if (!befund && !explorer.gewaehlt.has(d.id)) continue;
    gesamt++;
    if (befund && befund.zustand === "gelesen") gelesen++;
    liste.appendChild(arbeitsZeile(d, befund));
  }
  if (!gesamt) {
    const leer = document.createElement("li");
    leer.className = "explorer-leerzeile";
    leer.textContent = "Noch nichts in der Arbeitsakte. Rechts anhaken und \u00fcbernehmen.";
    liste.appendChild(leer);
  }
  zahlZeigen("arbeit-zahl", gelesen, gesamt);
}

function arbeitsZeile(d, befund) {
  const zustand = befund ? befund.zustand : "wartet";
  const z = LESEZEICHEN[zustand] || LESEZEICHEN.wartet;
  const li = document.createElement("li");
  li.className = `explorer-eintrag arbeit ${z.klasse}`;
  const marke = document.createElement("span");
  marke.className = "lesemarke";
  marke.textContent = z.marke;
  marke.title = z.wort;
  marke.setAttribute("aria-label", z.wort);
  const name = document.createElement("span");
  name.className = "explorer-name";
  name.textContent = d.titel;
  const meta = document.createElement("span");
  meta.className = "meta";
  const e = befund && befund.eintrag;
  if (zustand === "gelesen" && e) {
    const teile = [`${e.seiten} Seite(n)`, `${(e.zeichen || 0).toLocaleString("de-DE")} Zeichen`];
    if (e.ocr) teile.push("Texterkennung");
    if ((e.seiten_ohne_text || []).length)
      teile.push(`ohne Text: Seite ${seitenNennen(e.seiten_ohne_text)}`);
    if (e.nummer) teile.push(`D${e.nummer}`);
    meta.textContent = teile.join(" \u00b7 ");
    if ((e.seiten_ohne_text || []).length) li.classList.add("teilweise");
  } else if (zustand === "fehler" && e) {
    // Der ganze Satz, nicht die Bilanz: Er sagt, was zu tun ist.
    meta.textContent = e.grund;
    meta.title = e.grund;
  } else {
    meta.textContent = z.wort;
  }
  li.append(marke, name, meta);
  return li;
}

/** Die Ueberschrift eines Ordners - mit Zahl und einem Griff fuer den Stapel.
 *
 * In X-100-2026 stehen 55 Eintraege aus acht Ordnern. Wer ein Register der
 * Akte ganz oder gar nicht will, soll es nicht funfzehnmal anklicken muessen.
 */
function explorerOrdnerzeile(ordner, dazu) {
  const li = document.createElement("li");
  li.className = "explorer-ordner";
  const name = document.createElement("span");
  name.className = "explorer-ordnername";
  // Der leere Ordner ist kein Ordner, sondern die Akte selbst.
  name.textContent = ordner || "Unmittelbar im Aktenordner";
  if (!ordner) li.classList.add("wurzel");
  const zahl = document.createElement("span");
  zahl.className = "explorer-ordnerzahl";
  zahl.textContent = dazu.length === 1 ? "1 Dokument" : `${dazu.length} Dokumente`;

  const alleDrin = dazu.every((d) => explorer.gewaehlt.has(d.id));
  const knopf = document.createElement("button");
  knopf.type = "button";
  knopf.className = "explorer-ordnerknopf";
  knopf.textContent = alleDrin ? "Haken entfernen" : "alle anhaken";
  knopf.title = alleDrin ? `Alle Haken in „${name.textContent}" entfernen`
                         : `Alles aus „${name.textContent}" anhaken`;
  knopf.addEventListener("click", () => {
    for (const d of dazu) {
      if (alleDrin) explorer.gewaehlt.delete(d.id); else explorer.gewaehlt.add(d.id);
    }
    explorerRendern();
  });

  li.append(name, zahl, knopf);
  return li;
}

// Stapelauswahl nach Kategorie. Bei acht Dokumenten haekelt man einzeln; bei
// fuenfzig ist "alle vom Gegner" der Unterschied zwischen machbar und nicht.
function explorerArtenZeichnen(sichtbar) {
  const ziel = $("explorer-arten");
  if (!ziel) return;
  ziel.replaceChildren();
  const arten = [...new Set(sichtbar.map((d) => d.kategorie).filter(Boolean))].sort();
  if (arten.length < 2) return;          // eine Art allein ist keine Auswahl
  for (const art of arten) {
    const dazu = sichtbar.filter((d) => d.kategorie === art);
    const alleDrin = dazu.every((d) => explorer.gewaehlt.has(d.id));
    const knopf = document.createElement("button");
    knopf.type = "button";
    knopf.className = "art" + (alleDrin ? " drin" : "");
    knopf.textContent = `${art} (${dazu.length})`;
    knopf.title = alleDrin ? `Haken bei „${art}" entfernen` : `Alle „${art}" anhaken`;
    knopf.addEventListener("click", () => {
      for (const d of dazu) {
        if (alleDrin) explorer.gewaehlt.delete(d.id); else explorer.gewaehlt.add(d.id);
      }
      explorerRendern();
    });
    ziel.appendChild(knopf);
  }
}

// Wie voll ist die Arbeitsakte? Die Zeichenzahl kennt das Programm nur von
// Dokumenten, die schon gelesen sind - bei den uebrigen steht sie erst nach dem
// Uebernehmen fest. Beides wird gesagt; eine geschaetzte Zahl waere hier die
// falsche Hilfe, weil an dieser Grenze die Aktenanalyse abbricht.
function explorerUmfangZeigen() {
  const ziel = $("explorer-umfang");
  if (!ziel) return;
  const grenze = (K.maxPassagenZeichen || 160000);
  const bekannt = new Map(((sitzung && sitzung.sitzung.geladen) || []).map((g) => [g.dokument_id, g.zeichen || 0]));
  let zeichen = 0, ungelesen = 0;
  for (const id of explorer.gewaehlt) {
    if (bekannt.has(id)) zeichen += bekannt.get(id); else ungelesen++;
  }
  const teile = [`${explorer.gewaehlt.size} Dokument(e) angehakt`];
  if (zeichen) teile.push(`${zeichen.toLocaleString("de-DE")} von ${grenze.toLocaleString("de-DE")} Zeichen gelesen`);
  if (ungelesen) teile.push(`${ungelesen} noch nicht gelesen`);
  ziel.textContent = teile.join(" · ");
  ziel.classList.toggle("voll", zeichen > grenze);
}

/** Welches Wort der Ausschlussliste steht im Titel? Sonst "".
 *
 * Aus der Kanzlei am 05.10.2026: "Grundsaetzlich gehoert die Rechnung nicht
 * ins Aktengedaechtnis und Korrespondenz mit der RSV."
 *
 * Zwei Dinge, die hier bewusst NICHT geschehen:
 *
 * Es wird nichts weggelassen. Das Dokument steht im Fenster, nur ohne Haken,
 * mit dem Grund daneben. Ein Programm, das Akteninhalt heimlich auslaesst,
 * ist schlimmer als eines, das zu viel mitnimmt - was fehlt, faellt
 * niemandem auf.
 *
 * Und es wird nicht gedeutet. Geprueft wird der TITEL, nicht der Inhalt.
 * Eine Rechnung, die "Schreiben vom 14.03." heisst, geht durch. Das steht
 * auch so im Fenster: eine Hilfe, keine Gewaehr.
 */
function nichtVorwaehlenGrund(d) {
  const titel = (d.titel || "").toLowerCase();
  for (const wort of (K.nichtVorwaehlen || []))
    if (wort && titel.includes(wort.toLowerCase())) return wort;
  return "";
}

function explorerEintrag(d, drin) {
  const li = document.createElement("li");
  // Was schon im Aktengedaechtnis liegt, wird beim Uebernehmen nicht noch
  // einmal gelesen. Das zu sehen erspart die Frage, ob man gerade etwas
  // doppelt tut.
  const imGedaechtnis = gedaechtnisKennt(d.id);
  li.className = "explorer-eintrag" + (drin ? " drin" : "") + (imGedaechtnis ? " schon-drin" : "");
  const kasten = document.createElement("label");
  kasten.className = "explorer-wahl";
  const haken = document.createElement("input");
  haken.type = "checkbox";
  haken.checked = drin;
  haken.addEventListener("change", () => explorerVerschieben(d.id, haken.checked));
  const name = document.createElement("span"); name.className = "explorer-name"; name.textContent = d.titel;
  const meta = document.createElement("span"); meta.className = "meta";
  const grund = nichtVorwaehlenGrund(d);
  meta.textContent = [d.datum, d.kategorie, imGedaechtnis ? "schon im Gedächtnis" : "",
                      grund && !drin ? `nicht vorgewählt: ${grund}` : ""]
    .filter(Boolean).join(" · ");
  if (grund && !drin) li.classList.add("nicht-vorgewaehlt");
  kasten.append(haken, name, meta);
  li.appendChild(kasten);
  return li;
}

function gedaechtnisKennt(dokument_id) {
  const g = (sitzung && sitzung.gedaechtnis) || {};
  return (g.eintraege || []).some((e) => e.dokument_id === dokument_id);
}

function explorerVerschieben(id, hinein) {
  if (hinein) explorer.gewaehlt.add(id); else explorer.gewaehlt.delete(id);
  explorerRendern();
}

/** Der Dialog bleibt waehrend des Lesens offen.
 *
 * Aus der Kanzlei am 16.10.2026: \u201EAuch den Leseprozess nachvollziehbar
 * darstellen. Datei fuer Datei abhaken."
 *
 * Vorher schloss der Dialog mit dem Klick, und das Lesen lief dahinter mit
 * einem Balken. Ein Balken sagt, wie weit es ist - nicht, was gerade
 * geschieht und was schon durch ist. Jetzt bleibt die Gegenueberstellung
 * stehen und fuellt sich.
 *
 * Geschlossen wird am Ende nur, wenn ALLES gelesen wurde. Ging etwas nicht,
 * bleibt das Fenster offen: Genau dafuer ist es da.
 */
function explorerLesenZeigen(text) {
  const zeile = $("explorer-lesezeile");
  if (!zeile) return;
  zeile.hidden = !text;
  $("explorer-lesetext").textContent = text || "";
}

/** Waehrend gelesen wird, waehlt niemand aus. */
function explorerSperren(sperren) {
  explorerLiest = sperren;
  for (const id of ["alle-rein", "alle-raus", "explorer-uebernehmen",
                    "explorer-abbrechen", "explorer-suche"]) {
    const el = $(id);
    if (el) el.disabled = sperren;
  }
  const liste = $("quelle-liste");
  if (liste) liste.classList.toggle("gesperrt", sperren);
}

async function explorerUebernehmen() {
  if (explorerLiest) return;
  // Zweiter Klick nach einem Fehlschlag: Die Gegenueberstellung stand, jetzt
  // geht es weiter. Gelesen wird dabei nichts noch einmal.
  if (explorer.fertig) {
    explorer.fertig = false;
    $("explorer-dialog").close();
    await explorerNachbereiten(explorer.weg || []);
    return;
  }
  if (!explorer.gewaehlt.size) { melden("Bitte mindestens ein Dokument in die Arbeitsakte legen.", true); return; }
  const dazu = [...explorer.gewaehlt].filter((id) => !explorer.geladen.has(id));
  const weg = [...explorer.geladen].filter((id) => !explorer.gewaehlt.has(id));
  // Alles, was gleich gelesen wird, steht sofort links - als "wartet". Wer
  // zehn Dateien anhakt, soll zehn Zeilen sehen und nicht eine nach der
  // anderen auftauchen; abgehakt wird dann der Reihe nach.
  leseStand = new Map(dazu.map((id) => [id, "wartet"]));
  explorer.weg = weg;
  explorerSperren(true);
  explorerRendern();
  try {
    if (dazu.length) {
      await dokumenteInPortionenLesen(dazu, () => {
        const fertig = dazu.filter((id) => !leseStand.has(id)).length;
        explorerLesenZeigen(`${fertig} von ${dazu.length} Dateien gelesen \u2026`);
        explorerRendern();
      });
    }
    for (const id of weg)
      sitzung = await api("DELETE", `/api/sitzungen/${sitzung.sitzung.id}/dokumente/${id.split("/").map(encodeURIComponent).join("/")}`);
  } finally {
    leseStand.clear();
    explorerSperren(false);
    explorerLesenZeigen("");
  }
  // Der Stand nach dem Lesen. Die HAKEN bleiben, wie sie waren: Was nicht
  // gelesen wurde - weil es nicht ging oder weil angehalten wurde -, bleibt
  // angehakt, und ein zweites "\u00dcbernehmen" holt genau diese noch einmal.
  explorer.geladen = new Set((sitzung.sitzung.geladen || []).map((g) => g.dokument_id));
  explorerRendern();
  const misslungen = (sitzung.sitzung.nicht_gelesen || [])
    .filter((x) => dazu.includes(x.dokument_id));
  if (misslungen.length) {
    // Offen lassen und sagen, warum - und zwar IM Dialog: Eine Meldung
    // dahinter laege hinter dem Vorhang und waere nicht zu sehen. Die
    // Einzelheiten stehen links an der Datei; hier steht nur die Zahl.
    explorerLesenZeigen(misslungen.length === 1
      ? "Eine Datei wurde nicht gelesen \u2013 links steht, warum."
      : `${misslungen.length} von ${dazu.length} Dateien wurden nicht gelesen \u2013 links steht, warum.`);
    const zeile = $("explorer-lesezeile");
    if (zeile) zeile.classList.add("misslungen");
    const anhalten = $("explorer-anhalten");
    if (anhalten) anhalten.hidden = true;
    const knopf = $("explorer-uebernehmen");
    if (knopf) knopf.textContent = explorer.initial ? "Weiter zur Arbeitsakte" : "Fertig";
    explorer.fertig = true;
    return;
  }
  $("explorer-dialog").close();
  await explorerNachbereiten(weg);
}

/** Was nach dem Uebernehmen geschieht - getrennt, weil es zweimal gebraucht
 *  wird: beim glatten Durchlauf und beim Schliessen nach einem Fehlschlag. */
async function explorerNachbereiten(weg) {
  // Herausgenommene Dokumente lassen sich zurücklegen. Das ist kein
  // Schönheitsdienst: Der Auszug wird beim Zurücklegen neu gebildet, bei einem
  // Scan samt Texterkennung - das kostet Zeit und, mit Textract, Geld. Wer den
  // Weg mit einem Klick findet, macht es nicht versehentlich zweimal.
  if (weg.length && !explorer.initial) {
    const namen = weg.map((id) => (explorer.karte.get(id) || {}).titel).filter(Boolean);
    rueckgaengigAnbieten(
      weg.length === 1 ? `Aus der Arbeitsakte genommen: ${namen[0] || "1 Dokument"}`
                       : `${weg.length} Dokumente aus der Arbeitsakte genommen`,
      async () => {
        try {
          sitzung = await api("POST", `/api/sitzungen/${sitzung.sitzung.id}/dokumente`, { dokument_ids: weg });
          await passagenLaden(); zeigeBelege(); ladeStatus();
          schaetzungZeigen(sitzung.kostenschaetzung);
          chronologieZeigen();
          gedaechtnisFensterZeigen();
          melden(weg.length === 1 ? "Dokument wieder in der Arbeitsakte." : "Dokumente wieder in der Arbeitsakte.");
        } catch (e) { melden(e.message, true); }
      });
  }
  if (explorer.initial) {
    // Loest die laufende Meldung ab. Vor dem Oeffnen, nicht danach: Die
    // Arbeitsflaeche zeigt selbst einen Hinweis, wenn beim Lesen etwas
    // uebersprungen wurde, und der ist wichtiger als diese Zahl.
    const n = (sitzung.sitzung.geladen || []).length;
    melden(n === 1 ? "Ein Dokument in der Arbeitsakte." : `${n} Dokumente in der Arbeitsakte.`);
    await arbeitsflaecheOeffnen();
  } else {
    await passagenLaden(); zeigeBelege(); ladeStatus();
    schaetzungZeigen(sitzung.kostenschaetzung);
    chronologieZeigen();
    gedaechtnisFensterZeigen();
    // Auch hier: Wurde beim Lesen etwas uebersprungen, gehoert es auf den
    // Schirm und nicht in eine Meldung, die nach drei Sekunden weg ist.
    hinweiseZeigen(sitzung.sitzung.hinweise || []);
    melden("Arbeitsakte aktualisiert.");
  }
}

// ── Der Lesefortschritt ──────────────────────────────────────────────────────
//
// Aus der Kanzlei am 02.10.2026: "55 Dokumente werden gelesen ... Dauert sehr
// lange. Es waere schoen, wenn hier ein witziger Ladebalken erzeugt werden
// koennte."
//
// Bis dahin ging der ganze Stapel in EINEM Aufruf hinaus, und daran lag es:
// Ein Aufruf, der erst am Ende zurueckkommt, kann unterwegs nichts sagen. Die
// Oberflaeche liest jetzt in Portionen - derselbe Weg wie beim Einlesen ins
// Aktengedaechtnis, wo dieselbe Frage schon einmal gestellt wurde.
//
// Damit zeigt der Balken GEZAEHLTE Dokumente, keine Schaetzung. Das ist nicht
// Rechthaberei: Am selben Tag hat dieses Projekt zweimal erlebt, was eine
// Anzeige wert ist, die nicht misst - einmal einen Aufruf, der ohne Fehler
// nichts lieferte, einmal ein Probewort, das rechts aus dem Blatt lief.

//: Wie viele Dokumente je Aufruf.
//:
//: Fuenf ist ein Ausgleich: Kleiner hiesse mehr Aufrufe fuer dieselbe Arbeit,
//: groesser hiesse laengere Strecken ohne ein Lebenszeichen. Bei 55 Dokumenten
//: sind das elf Schritte, also etwa alle paar Sekunden eine neue Zahl.
const LESEPORTION = 5;

//: Was waehrend des Wartens dasteht.
//:
//: Jeder Satz sagt nebenbei, WARUM es dauert - das ist der Unterschied zu
//: einem Spruch, der nur die Zeit vertreibt. Keiner handelt vom Inhalt einer
//: Akte; auf diesem Schirm steht nichts Erfundenes ueber ein Mandat.
const LESESPRUECHE = [
  "Jedes Dokument wird einmal ganz gelesen. Das ist der Unterschied zu einer Volltextsuche.",
  "Die Scans gehen Seite für Seite durch die Texterkennung. Ein Rückschein ist schnell durch, ein Gutachten nicht.",
  "Übersprungen wird nichts. Das ist die ganze Erklärung für die Wartezeit.",
  "Noch nie hat jemand eine Akte schneller gelesen, als sie lang ist.",
  "Gelesen wird in Portionen. Wer anhält, behält das Gelesene.",
  "Eine Texterkennung liest ein Bild vom Text. Das ist langsamer als Text.",
  "Das Modell sieht die Akte erst, wenn alles gelesen ist. Vorher wäre es Raten.",
  "Ein Aktenordner, der sich selbst liest. Das dauert ungefähr so lange, wie es klingt.",
  "Hier wird gelesen, noch nicht gedacht. Das Denken kostet später ein paar Cent.",
  "Die Wartezeit ist der Preis dafür, dass hinterher jeder Satz eine Fundstelle hat.",
];

let lesenAbbrechen = false;

//: Laeuft gerade ein Lesevorgang? Und zu welcher Sitzung gehoert er?
//:
//: Aus der Kanzlei am 02.10.2026: "Bin in dem Programm gesprungen waehrend des
//: Downloads, danach hatte ich das Gefuehl, dass es Chaos gab. Keine saubere
//: Trennung."
//:
//: Das Gefuehl war richtig, und es ist eine Folge der Aenderung vom selben
//: Tag. Vorher ging der ganze Stapel in EINEM Aufruf hinaus - wer dazwischen
//: klickte, hatte ein Fenster von Sekunden. Seit das Lesen in Portionen
//: geschieht, dauert es Minuten, und in dieser Zeit war die Oberflaeche offen:
//: Wer die Akte wechselte, waehrend noch gelesen wurde, bekam die Antworten
//: des alten Vorgangs in die neue Akte geschrieben.
//:
//: Inhaltlich konnte dabei nichts Fremdes in eine Akte geraten - der Server
//: prueft bei JEDEM Dokument, ob es zu der Akte gehoert, deren Sitzung
//: gefragt wird, und weist alles andere ab. Auf dem Schirm sah es trotzdem
//: nach Durcheinander aus, und eine Oberflaeche, die so aussieht, ist bei
//: Mandatsakten nicht hinnehmbar.
let liestGerade = "";

function lesefortschritt(gelesen, gesamt, sekundenJeDokument, offen) {
  const block = $("lesefortschritt");
  // Steht der Explorer offen, sagt er es selbst - Datei fuer Datei. Der
  // Balken daneben laege halb hinter dem Vorhang und sagte dasselbe noch
  // einmal, nur ungenauer.
  if (explorerLiest) { block.hidden = true; return; }
  block.hidden = false;
  const anteil = gesamt ? Math.round((gelesen / gesamt) * 100) : 0;
  $("lese-balken").style.width = `${anteil}%`;
  $("lese-text").textContent = `${gelesen} von ${gesamt} Dokumenten gelesen · ${anteil} %`;
  // Erst schaetzen, wenn wirklich etwas gemessen ist. Eine Dauer aus einer
  // einzigen Portion schwankt um ein Vielfaches und waere geraten.
  $("lese-dauer").textContent = sekundenJeDokument && offen > 0
    ? `noch etwa ${dauerText(sekundenJeDokument * offen)}`
    : "";
}

/** Die beiden Wege aus der Akte heraus sperren, solange gelesen wird.
 *
 * Nicht alles wird gesperrt: Lesen, Blaettern und Nachsehen stoeren nicht.
 * Gesperrt werden die zwei Knoepfe, die die Akte VERLASSEN - denn nur dort
 * entsteht das Durcheinander, das die Kanzlei am 02.10.2026 gemeldet hat.
 *
 * Eine Sperre ist kein Ersatz fuer die Pruefung in der Schleife, sondern ihr
 * Vorbau: Die Sperre erklaert, die Pruefung haelt. Wer den Knopf ueber die
 * Tastatur oder einen zweiten Tab doch erreicht, laeuft in die Pruefung.
 */
function wegeSperren(sperren) {
  for (const id of ["akte-wechseln", "sitzung-schliessen"]) {
    const knopf = $(id);
    if (!knopf) continue;
    knopf.disabled = sperren;
    knopf.title = sperren
      ? "Erst wenn die Dokumente gelesen sind. Anhalten geht unten rechts."
      : knopf.dataset.titel || knopf.title;
  }
}

/**
 * Alle Dokumente der Arbeitsakte noch einmal aus der Akte lesen.
 *
 * Befund R01 der Zweitpruefung vom 15.10.2026: Ein Dokument, das in
 * jur|nodes unter DERSELBEN Kennung geaendert wurde, kam nie wieder herein.
 * Beim Oeffnen liefert das Gedaechtnis den gespeicherten Text, und das
 * Hinzufuegen ueberspringt, was es schon kennt - es wurde also gar nicht
 * nachgesehen. Dass das erneute Auswaehlen in der Arbeitsakte wie ein
 * Aktualisieren aussah, war der schlimmere Teil davon.
 *
 * Dieser Weg liest wirklich und sagt danach, was sich geaendert hat. Er ist
 * ausdruecklich und bestaetigungspflichtig: Er kostet Zeit und, bei
 * gescannten Seiten, Texterkennung.
 */
async function dokumenteNeuEinlesen() {
  const geladen = (sitzung && sitzung.sitzung && sitzung.sitzung.geladen) || [];
  if (!geladen.length) {
    melden("In der Arbeitsakte liegt noch kein Dokument.", true);
    return;
  }
  const ids = geladen.map((g) => g.dokument_id);
  if (!confirm(
      `${ids.length} Dokument(e) werden noch einmal aus der Akte gelesen.\n\n`
      + "Das dauert so lange wie beim ersten Mal und kostet bei gescannten "
      + "Seiten erneut Texterkennung. Danach steht da, was sich geändert hat.")) {
    return;
  }
  laeuft(ids.length === 1 ? "Ein Dokument wird neu gelesen …"
                          : `${ids.length} Dokumente werden neu gelesen …`);
  try {
    sitzung = await api("POST", `/api/sitzungen/${sitzung.sitzung.id}/dokumente`,
                        { dokument_ids: ids, neu_laden: true });
  } catch (e) {
    melden(e.message, true);
    return;
  }
  // Dieselbe Nachbereitung wie beim Herausnehmen: Was sich geaendert hat,
  // steht in den Passagen, in den Belegen, im Zeitstrahl und in der Schaetzung.
  await passagenLaden(); zeigeBelege(); ladeStatus();
  schaetzungZeigen(sitzung.kostenschaetzung);
  chronologieZeigen();
  gedaechtnisFensterZeigen();
  // Die Hinweise des Servers sagen, was sich geaendert hat - und sie stehen
  // ganz vorn, wenn es etwas war.
  const hinweise = (sitzung.sitzung && sitzung.sitzung.hinweise) || [];
  melden(hinweise[0] || "Alle Dokumente neu gelesen.", /ACHTUNG/.test(hinweise[0] || ""));
}

/** Die Dokumente in Portionen lesen und dabei zeigen, wie weit es ist.
 *
 * ``beiPortion`` wird vor und nach jeder Portion gerufen. Darueber haekelt die
 * linke Spalte des Explorers Datei fuer Datei ab - aus der Kanzlei am
 * 16.10.2026: „Auch den Leseprozess nachvollziehbar darstellen."
 */
async function dokumenteInPortionenLesen(dazu, beiPortion) {
  const gesamt = dazu.length;
  const melde = (ids, zustand) => {
    for (const id of ids) {
      if (zustand) leseStand.set(id, zustand); else leseStand.delete(id);
    }
    if (beiPortion) beiPortion();
  };
  // Fuer ein, zwei Dokumente lohnt der Aufbau nicht - da blitzt er nur auf.
  if (gesamt <= 2) {
    laeuft(gesamt === 1 ? "Ein Dokument wird gelesen …" : "Zwei Dokumente werden gelesen …");
    melde(dazu, "liest");
    try {
      sitzung = await api("POST", `/api/sitzungen/${sitzung.sitzung.id}/dokumente`, { dokument_ids: dazu });
    } finally {
      melde(dazu, "");
    }
    return;
  }

  lesenAbbrechen = false;
  $("lese-anhalten").disabled = false;
  // Die Sitzung, zu der dieser Vorgang gehoert. Jede Antwort wird dagegen
  // gehalten: Was zu einer anderen Akte gehoert, wird nicht uebernommen.
  const meine = sitzung.sitzung.id;
  liestGerade = meine;
  wegeSperren(true);
  const sprueche = [...LESESPRUECHE].sort(() => Math.random() - 0.5);
  let gelesen = 0, verstrichen = 0, portionen = 0;
  lesefortschritt(0, gesamt, 0, 0);
  $("lese-spruch").textContent = sprueche[0];

  try {
    for (let i = 0; i < gesamt && !lesenAbbrechen; i += LESEPORTION) {
      const teil = dazu.slice(i, i + LESEPORTION);
      const begonnen = Date.now();
      melde(teil, "liest");
      let antwort;
      try {
        antwort = await api("POST", `/api/sitzungen/${meine}/dokumente`,
                            { dokument_ids: teil });
      } finally {
        // Auch wenn der Aufruf platzt: Keine Zeile bleibt auf "wird gelesen".
        melde(teil, "");
      }
      // Zwischen Absenden und Antwort liegen Sekunden. Wurde in dieser Zeit
      // die Akte gewechselt, gehoert diese Antwort nicht mehr hierher - sie
      // wird verworfen, nicht eingetragen.
      if (!sitzung || !sitzung.sitzung || sitzung.sitzung.id !== meine) {
        melden("Der Lesevorgang gehört zu einer anderen Akte und wurde abgebrochen.", true);
        return;
      }
      sitzung = antwort;
      verstrichen += (Date.now() - begonnen) / 1000;
      gelesen += teil.length;
      portionen++;
      $("lese-spruch").textContent = sprueche[portionen % sprueche.length];
      // Nach der ersten Portion wird nichts geschaetzt: Die erste traegt den
      // Verbindungsaufbau mit und ist regelmaessig die langsamste.
      const jeDokument = portionen > 1 ? verstrichen / gelesen : 0;
      lesefortschritt(gelesen, gesamt, jeDokument, gesamt - gelesen);
      if (beiPortion) beiPortion();
    }
  } finally {
    leseStand.clear();
    if (beiPortion) beiPortion();
    liestGerade = "";
    wegeSperren(false);
    $("lesefortschritt").hidden = true;
    $("lese-balken").style.width = "0%";
  }
  if (lesenAbbrechen && gelesen < gesamt)
    melden(`Angehalten. ${gelesen} von ${gesamt} Dokumenten sind gelesen und bleiben in der Arbeitsakte.`);
}

// ── Woran zuletzt gearbeitet wurde ───────────────────────────────────────────

/** Zeigt beim Öffnen, was in dieser Akte zuletzt getan wurde.
 *
 * Aus der Kanzlei am 25.09.2026: "beim Öffnen der Akte sehen, was man als
 * Letztes gemacht hat, sodass man dann wieder daran ansetzen kann."
 *
 * Kostet nichts: Alles steht schon im Gedächtnis. Gezeigt werden die
 * eigenen Fragen im Wortlaut - keine vom Modell geschriebene Zusammenfassung,
 * die bei jedem Öffnen Geld kostete und danebenliegen könnte.
 */
function arbeitsstandZeigen() {
  const leiste = $("arbeitsstand");
  if (!leiste) return;
  const a = ((sitzung && sitzung.gedaechtnis) || {}).arbeitsstand;
  // Eine leere Leiste ist schlimmer als keine: Sie nimmt Platz und sagt
  // nichts. Beim ersten Öffnen einer Akte gibt es nichts zu berichten.
  if (!a || !a.vorhanden || !(a.fragen || []).length) { leiste.hidden = true; return; }

  $("arbeitsstand-wann").textContent = a.zuletzt ? datumKurz(a.zuletzt) : "";
  const liste = $("arbeitsstand-fragen");
  liste.replaceChildren();
  for (const f of a.fragen) {
    const li = document.createElement("li");
    li.textContent = f.frage;
    li.title = f.frage;   // die ganze Frage, wenn sie abgeschnitten ist
    liste.appendChild(li);
  }
  const teile = [];
  if (a.dokumente) teile.push(`${a.dokumente} Dokumente im Gedächtnis`);
  if (a.fragen_gesamt > a.fragen.length) teile.push(`${a.fragen_gesamt} Fragen insgesamt`);
  if (a.chronologie_bis) teile.push(`Zeitstrahl bis ${datumKurz(a.chronologie_bis)}`);
  $("arbeitsstand-zahlen").textContent = teile.join(" · ");
  leiste.hidden = false;
}

/** Was beim Lesen der Dokumente nicht ging - vollstaendig und bleibend.
 *
 * Aus der Kanzlei am 25.09.2026: "er uebernimmt beim Lesen der Dokumente
 * nicht alle, nur 24 von 38." Das Programm sagte es auch vorher - in
 * vierzehn einzelnen Saetzen, von denen die Oberflaeche einen drei Sekunden
 * lang zeigte. Wer eine Meldung ueber EIN Dokument liest, haelt es fuer
 * einen Einzelfall und zaehlt nicht nach.
 *
 * Die erste Zeile ist die Bilanz und steht hervorgehoben; darunter die
 * Einzelheiten. Weg geht das erst auf Klick.
 */
function hinweiseZeigen(hinweise) {
  const leiste = $("uebernahme");
  if (!leiste) { if (hinweise.length) melden(hinweise[0], true); return; }
  if (!hinweise.length) { leiste.hidden = true; return; }
  $("uebernahme-bilanz").textContent = hinweise[0];
  const liste = $("uebernahme-liste");
  liste.replaceChildren();
  const einzeln = hinweise.slice(1);
  for (const h of einzeln) {
    const li = document.createElement("li");
    li.textContent = h;
    liste.appendChild(li);
  }
  // Siebzehn Zeilen mit demselben Satz nehmen die halbe Arbeitsflaeche und
  // sagen nicht mehr als die Bilanz darueber. Sie bleiben erreichbar - wer
  // wissen will, WELCHES Dokument fehlt, braucht sie -, aber zugeklappt.
  const mehr = $("uebernahme-mehr");
  if (mehr) {
    mehr.hidden = einzeln.length === 0;
    mehr.open = false;
    const titel = $("uebernahme-mehr-titel");
    if (titel) {
      titel.textContent = einzeln.length === 1
        ? "Die Einzelheit dazu"
        : `Die ${einzeln.length} Einzelheiten dazu`;
    }
  }
  leiste.hidden = false;
}

function arbeitsstandSchliessen() {
  const leiste = $("arbeitsstand");
  if (leiste) leiste.hidden = true;
}

// ── Arbeitsfläche ────────────────────────────────────────────────────────────

async function arbeitsflaecheOeffnen() {
  $("einstieg").hidden = true;
  $("flaeche").hidden = false;
  $("akte-leiste").hidden = false;
  // Welche Fenster offen sind, merkt sich der Browser je Benutzer.
  fensterLaden();
  const a = sitzung.sitzung.akte;
  $("akte-name").replaceChildren();
  const b = document.createElement("b"); b.textContent = a.aktenzeichen;
  $("akte-name").append(b, document.createTextNode(` · ${a.bezeichnung}`));
  // Auch oben, waehrend gearbeitet wird: Die Akte kann archiviert worden
  // sein, seit sie zuletzt offen war.
  if (a.status === "archiviert") $("akte-name").appendChild(archivMarke());
  arbeitsstandZeigen();
  hinweiseZeigen(sitzung.sitzung.hinweise || []);
  schaetzungZeigen(sitzung.kostenschaetzung);
  // Was frueher schon analysiert wurde, steht im Aktengedaechtnis. Ohne diese
  // Zeile faenge der Zeitstrahl nach jeder Pause wieder bei den Stammdaten an.
  chronoAusAnalyse = ((sitzung.gedaechtnis || {}).chronologie || [])
    .filter((e) => e.datum && e.ereignis && (e.quellen || []).length)
    .map((e) => ({ datum: e.datum, ereignis: e.ereignis,
                   kennung: e.quellen[0].kennung, dokument_id: e.quellen[0].dokument_id }));
  // Erst die Passagen, dann der Zeitstrahl: Ob ein gespeicherter Beleg heute
  // noch passt, laesst sich nur am geladenen Passagenverzeichnis pruefen.
  await passagenLaden();
  chronologieZeigen();
  gedaechtnisFensterZeigen();
  threadWillkommen();
  gedaechtnisImThreadZeigen();
  await bibliothekLaden();
  entwurfFensterZeichnen();
  await gespeicherteAnalyseZeigen();
  zeigeBelege();
}

async function passagenLaden() {
  const daten = await api("GET", `/api/sitzungen/${sitzung.sitzung.id}/passagen`);
  passagenIndex = {};
  for (const p of daten.passagen) passagenIndex[p.kennung] = p;
  dokumentspalteZeichnen();
}

/** Die Dokumentspalte aus dem, was schon da ist - ohne einen einzigen Aufruf.
 *
 * Herausgeloest am 13.10.2026. Aus der Kanzlei: "auch die Dokumente sollen auf
 * einen Extrabildschirm zu oeffnen sein, so dass der Chat viel Platz hat."
 *
 * Bis dahin stand im Bestand, die Dokumentspalte bekomme KEIN Nebenfenster:
 * "Sie holt ihren Text selbst nach - ein Spiegel, der nachholen muss, ist kein
 * Spiegel mehr." Das stimmte, solange das Fuellen am Aufruf `passagenLaden`
 * hing. Nachgesehen: Der Spiegel bekommt `passagenIndex` ueber den Kanal
 * laengst mitgeschickt, und `zeigeDokument` liest nur daraus. Es fehlte nicht
 * die Angabe, sondern die Trennung zwischen Holen und Zeichnen.
 */
function dokumentspalteZeichnen() {
  const filter = $("dok-filter");
  if (!filter) return;
  const gewaehlt = filter.value || "";
  filter.replaceChildren();
  const alle = document.createElement("option"); alle.value = ""; alle.textContent = "Alle Dokumente"; filter.appendChild(alle);
  for (const g of ((sitzung && sitzung.sitzung && sitzung.sitzung.geladen) || [])) {
    const o = document.createElement("option"); o.value = g.dokument_id; o.textContent = g.titel; filter.appendChild(o);
  }
  // Die Wahl ueberlebt das Neuzeichnen - sonst spraenge der Spiegel bei jeder
  // Nachricht aus dem Hauptfenster auf "Alle Dokumente" zurueck.
  filter.value = [...filter.options].some((o) => o.value === gewaehlt) ? gewaehlt : "";
  filter.onchange = () => zeigeDokument(filter.value);
  zeigeDokument(filter.value);
}

// ── Von Fundstelle zu Fundstelle ────────────────────────────────────────────
//
// Aus der Kanzlei am 15.10.2026: "Haben die Lupen eine Zaehlfunktion mit
// anklicken, dass man gleich an die Stelle kommt?"
//
// Bisher nicht. Die Zahl zaehlte und war sonst nichts. Bei dreizehn
// Fundstellen in einem langen Dokument ist die Zahl aber erst die halbe
// Auskunft - die andere Haelfte ist der Weg dorthin.
//
// Gelaufen wird ueber die HERVORHEBUNGEN, nicht ueber die Absaetze: Gesucht
// wird die Stelle und nicht der Abschnitt, in dem sie steht.

const LAUF = {
  // Im Dokumenttext stehen zweierlei Marken: die der Suche und die, mit denen
  // eine angeklickte Fundstelle eingefaerbt wird (satzFaerben). Nur die der
  // Suche traegt "such-treffer" - sonst liefe der Lauf durch fremde Marken.
  dok: { bereich: "dok-text", marken: "mark.such-treffer", anzeige: "dok-lauf", stand: "dok-stand", stelle: 0 },
  chat: { bereich: "thread", marken: "mark.chat-treffer", anzeige: "chat-lauf", stand: "chat-stand", stelle: 0 },
};

function laufMarken(l) {
  const wurzel = $(l.bereich);
  return wurzel ? [...wurzel.querySelectorAll(l.marken)] : [];
}

function laufStandSetzen(l, marken) {
  marken.forEach((m, i) => m.classList.toggle("aktuell", i === l.stelle));
  const feld = $(l.stand);
  if (feld) feld.textContent = `${l.stelle + 1}/${marken.length}`;
}

/** Nach einer Suche: Zahl neu setzen, bei der ersten Fundstelle anfangen.
 *
 * `titel` traegt den ausgeschriebenen Satz - "3 von 4 Absaetzen". Er steht am
 * Knopf und nicht in der Zeile: In einer vierhundert Pixel schmalen Spalte
 * ist zwischen Dokumentwahl und Suchfeld kein Platz fuer einen Satz.
 */
function laufZeigen(name, titel) {
  const l = LAUF[name];
  if (!l) return;
  const anzeige = $(l.anzeige);
  if (!anzeige) return;
  const marken = laufMarken(l);
  anzeige.hidden = !marken.length;
  anzeige.title = titel || "";
  l.stelle = 0;
  if (!marken.length) return;
  laufStandSetzen(l, marken);
}

/** Einen Schritt weiter oder zurueck - und hin. */
function laufSpringen(name, richtung) {
  const l = LAUF[name];
  if (!l) return;
  const marken = laufMarken(l);
  if (!marken.length) return;
  l.stelle = (l.stelle + richtung + marken.length) % marken.length;
  laufStandSetzen(l, marken);
  // In die MITTE, nicht an den Rand: Eine Fundstelle unter der Oberkante
  // sieht aus wie der Anfang des Textes.
  marken[l.stelle].scrollIntoView({ behavior: "smooth", block: "center" });
}

/** Die Suchwoerter aus dem Feld - klein geschrieben, ohne Leeres. */
function dokSuchwoerter() {
  const feld = $("dok-suche");
  return feld ? feld.value.toLowerCase().split(/\s+/).filter(Boolean) : [];
}

/** Den Text einer Passage mit hervorgehobenen Treffern einsetzen.
 *
 * Mit `textContent` je Stueck, nie mit `innerHTML`: Der Text kommt aus der
 * Akte, und ein Dokument, das wie HTML aussieht, darf nicht als HTML enden.
 */
function mitHervorhebung(ziel, text, begriffe) {
  if (!begriffe.length) { ziel.textContent = text; return; }
  const klein = text.toLowerCase();
  const stellen = [];
  for (const b of begriffe) {
    let ab = 0;
    for (;;) {
      const i = klein.indexOf(b, ab);
      if (i < 0) break;
      stellen.push([i, i + b.length]);
      ab = i + b.length;
    }
  }
  if (!stellen.length) { ziel.textContent = text; return; }
  stellen.sort((a, b) => a[0] - b[0]);
  let bis = 0;
  for (const [von, ende] of stellen) {
    if (von < bis) continue;                      // ueberlappende Treffer
    if (von > bis) ziel.appendChild(document.createTextNode(text.slice(bis, von)));
    const m = document.createElement("mark");
    m.className = "such-treffer";
    m.textContent = text.slice(von, ende);
    ziel.appendChild(m);
    bis = ende;
  }
  if (bis < text.length) ziel.appendChild(document.createTextNode(text.slice(bis)));
}

/** „3", „3 und 7", „3, 7 bis 9 und 14" - wie `seiten_nennen` im Programm.
 *
 * Dieselbe Regel zweimal, einmal hier und einmal in services/extraktion.py.
 * Eine Aufzaehlung von vierzehn Einzelzahlen liest niemand; „7 bis 20" sagt
 * auf einen Blick, dass der ganze hintere Teil fehlt.
 */
function seitenNennen(nummern) {
  if (!nummern || !nummern.length) return "";
  const gruppen = [[nummern[0]]];
  for (const nr of nummern.slice(1)) {
    const letzte = gruppen[gruppen.length - 1];
    if (nr === letzte[letzte.length - 1] + 1) letzte.push(nr); else gruppen.push([nr]);
  }
  const teile = gruppen.map((g) => (g.length === 1 ? String(g[0]) : `${g[0]} bis ${g[g.length - 1]}`));
  if (teile.length === 1) return teile[0];
  return teile.slice(0, -1).join(", ") + " und " + teile[teile.length - 1];
}

/** Der Eintrag der Arbeitsakte zu einem Dokument - oder null. */
function geladenesDokument(id) {
  const geladen = (sitzung && sitzung.sitzung && sitzung.sitzung.geladen) || [];
  return geladen.find((g) => g.dokument_id === id) || null;
}

/** Was ueber einem Dokument stehen muss, bevor man es liest.
 *
 * Zwei Dinge, und beide gehoeren genau hierher - an den Text selbst und nicht
 * in eine Meldung, die nach dem naechsten Klick weg ist:
 *
 * 1. **Seiten ohne Text.** Aus der Kanzlei am 16.10.2026: „Das Programm hat
 *    beim Einlesen ganze Bloecke nicht mitgenommen und zwar an Stellen, die
 *    sehr wichtig waren." Hier stehen die Seiten, die auch nach der
 *    Texterkennung leer blieben. Eine Luecke, die man sieht, ist etwas
 *    anderes als eine, die man nicht sieht.
 * 2. **Herkunft.** Ein eingefuegtes Blatt stammt nicht aus der fuehrenden
 *    Akte. Wer spaeter liest, was darauf beruht, muss das wissen.
 */
function dokumentBand(id) {
  const g = geladenesDokument(id);
  if (!g) return null;
  const zeilen = [];
  if (g.eingefuegt) {
    zeilen.push(["dok-band-herkunft",
      "Eingef\u00fcgt \u2013 dieses Dokument stammt nicht aus der jurnodes-Akte "
      + "und bleibt nur in dieser Sitzung."]);
  }
  const ohne = g.seiten_ohne_text || [];
  if (ohne.length) {
    zeilen.push(["dok-band-luecke",
      `${ohne.length === 1 ? "Seite" : "Seiten"} ${seitenNennen(ohne)} von ${g.seiten}: `
      + "kein Text gefunden. Der Abschnitt steht hier nicht und geht in keine "
      + "Antwort ein \u2013 bitte im Original nachsehen."]);
  }
  if (!zeilen.length) return null;
  const kasten = document.createElement("div");
  kasten.className = "dok-band";
  for (const [klasse, text] of zeilen) {
    const d = document.createElement("div"); d.className = klasse; d.textContent = text;
    kasten.appendChild(d);
  }
  return kasten;
}

/** Die Dokumentspalte zeichnen - gefiltert nach Dokument UND nach Text.
 *
 * Aus der Kanzlei am 13.10.2026: "Eine Suchfunktion in den Dokumenten waere
 * sehr gut, da ich z. B. schnell Antraege finden muss."
 *
 * Gesucht wird in dem, was ohnehin schon da ist: `passagenIndex` traegt den
 * Text aller geladenen Dokumente. Es geht keine Anfrage hinaus, kein Modell
 * wird gefragt, und es kostet nichts. Jedes Suchwort muss vorkommen - "antrag
 * frist" findet die Passage, in der beides steht.
 */
function zeigeDokument(nurDokument) {
  const ziel = $("dok-text"); ziel.replaceChildren();
  const begriffe = dokSuchwoerter();
  let letzterTitel = null;
  let gefunden = 0, durchsucht = 0;
  for (const kennung of Object.keys(passagenIndex)) {
    const p = passagenIndex[kennung];
    if (nurDokument && p.dokument_id !== nurDokument) continue;
    durchsucht++;
    const text = p.text || "";
    const klein = text.toLowerCase();
    if (begriffe.length && !begriffe.every((b) => klein.includes(b))) continue;
    gefunden++;
    if (p.dokument_titel !== letzterTitel) {
      const t = document.createElement("div"); t.className = "dok-doktitel"; t.textContent = p.dokument_titel;
      ziel.appendChild(t); letzterTitel = p.dokument_titel;
      const band = dokumentBand(p.dokument_id);
      if (band) ziel.appendChild(band);
    }
    const abs = document.createElement("div"); abs.className = "passage"; abs.id = `p-${p.kennung}`;
    const kz = document.createElement("span"); kz.className = "kennung"; kz.textContent = `${p.kennung} · Seite ${p.seite}`;
    const satz = document.createElement("div"); satz.className = "satz";
    mitHervorhebung(satz, text, begriffe);
    abs.append(kz, satz); ziel.appendChild(abs);
  }
  const marke = $("dok-treffer");
  if (marke) {
    // Null Treffer ist eine Auskunft, kein leeres Fenster. Ohne diese Zeile
    // saehe "nichts gefunden" aus wie "nichts geladen".
    marke.textContent = !begriffe.length ? ""
      : gefunden === 0 ? `kein Treffer in ${durchsucht} Absatz/Absaetzen`
      : "";   // Bei Treffern sagt es der Lauf daneben, und zwar kuerzer.
    marke.classList.toggle("ohne-treffer", !!begriffe.length && gefunden === 0);
  }
  laufZeigen("dok", begriffe.length && gefunden
    ? `${gefunden} von ${durchsucht} Absaetzen - klicken springt zur naechsten Fundstelle`
    : "");
}

// Die Passage ist bis zu 1.500 Zeichen lang. Sie ganz einzufaerben hiess: Der
// Bearbeiter sucht darin noch einmal von Hand nach dem Datum. Aus der Kanzlei:
// "Das Ueberpruefen dauert bisher ja immer noch zu lange, um effizienter zu
// arbeiten." Also wird der tragende Satz blass hinterlegt und die harte Angabe
// darin - Datum, Betrag, Eigenname - kraeftig.
//
// Die Stellen rechnet der Server aus (services/fundstelle.py), ohne Modell und
// nur aus dem, was wirklich in der Passage steht. Fehlen sie, faerbt sich die
// ganze Passage wie bisher: lieber grob als falsch.
function satzFaerben(satzEl, text, quelle) {
  satzEl.replaceChildren();
  const a = quelle && Number.isInteger(quelle.treffer_start) ? quelle.treffer_start : null;
  const b = quelle && Number.isInteger(quelle.treffer_ende) ? quelle.treffer_ende : null;
  if (a === null || b === null || b <= a || b > text.length) {
    satzEl.textContent = text;
    return false;
  }
  satzEl.appendChild(document.createTextNode(text.slice(0, a)));
  const stelle = document.createElement("span"); stelle.className = "stelle";
  let pos = a;
  for (const paar of quelle.marken || []) {
    const [von, bis] = paar;
    if (!(von >= pos && bis <= b)) continue;
    stelle.appendChild(document.createTextNode(text.slice(pos, von)));
    const marke = document.createElement("mark"); marke.textContent = text.slice(von, bis);
    stelle.appendChild(marke);
    pos = bis;
  }
  stelle.appendChild(document.createTextNode(text.slice(pos, b)));
  satzEl.appendChild(stelle);
  satzEl.appendChild(document.createTextNode(text.slice(b)));
  return true;
}

function markierungenLoeschen() {
  document.querySelectorAll(".passage.markiert").forEach((el) => {
    el.classList.remove("markiert", "puls", "genau");
    const satzEl = el.querySelector(".satz");
    const p = passagenIndex[el.id.slice(2)];
    if (satzEl && p && p.text) satzEl.textContent = p.text;
  });
}

// Jeder Verweis bringt seinen eigenen Satz mit.
//
// Eine Quelle gehoert zu einer Passage, eine Fundstelle aber zu einer Aussage.
// Zitieren zwei Saetze dieselbe Passage, gibt es nur eine Quelle - und sie kann
// nur eine der beiden Stellen tragen. Der zweite Verweis sprang deshalb an die
// Stelle des ersten. Deshalb fragt jeder Klick fuer seinen eigenen Satz nach;
// das kostet nichts (kein Modell) und trifft dafuer.
async function stelleHolen(kennung, aussage) {
  if (!aussage || !sitzung) return belegQuellen[kennung];
  try {
    return await api("POST", `/api/sitzungen/${sitzung.sitzung.id}/fundstelle`,
                     { kennung, aussage });
  } catch (e) {
    // Ohne Antwort bleibt es bei dem, was die Quelle mitbrachte - schlechter
    // als genau, aber besser als gar keine Markierung.
    return belegQuellen[kennung];
  }
}

async function passageMarkieren(kennung, chip, aussage) {
  // Die Fundstelle steht links im Dokument. Ist die Spalte zugeklappt, sähe
  // der Klick aus, als täte er nichts.
  fensterOeffnen("dokument");
  markierungenLoeschen();
  document.querySelectorAll(".beleg.aktiv").forEach((el) => el.classList.remove("aktiv"));
  let el = $(`p-${kennung}`);
  // Steht der Dokumentfilter auf einem anderen Dokument, ist die Passage nicht
  // gezeichnet. Frueher kam dann eine rote Meldung - "nicht sichtbar" -, und der
  // Klick wirkte kaputt. Jetzt wird auf das Dokument der Fundstelle umgeschaltet.
  if (!el && passagenIndex[kennung]) {
    const filter = $("dok-filter");
    if (filter) { filter.value = passagenIndex[kennung].dokument_id; zeigeDokument(filter.value); }
    el = $(`p-${kennung}`);
  }
  if (!el) { melden(`Fundstelle ${kennung} ist im geladenen Text nicht enthalten.`, true); return; }
  const passage = passagenIndex[kennung];
  const satzEl = el.querySelector(".satz");
  const stelle = await stelleHolen(kennung, aussage);
  const genau = satzEl && passage && passage.text
    ? satzFaerben(satzEl, passage.text, stelle) : false;
  el.classList.add("markiert", genau ? "genau" : "puls");
  // Auf die Stelle springen, nicht auf den Absatz: Bei einer langen Passage
  // stuende die gesuchte Zeile sonst unten aus dem Bild heraus.
  const ziel = (genau && satzEl.querySelector(".stelle")) || el;
  ziel.scrollIntoView({ behavior: "smooth", block: "center" });
  if (chip) chip.classList.add("aktiv");
}

// ── Fenster ein- und ausblenden ─────────────────────────────────────────────
// Aus der Kanzlei: "Es waere ganz cool, wenn man einen Button oben hat, sodass
// man dann erst sozusagen diese Felder oeffnet und dass man die wieder
// ausblenden kann, wenn man sie nicht braucht."
//
// Vier Fenster, vier Knoepfe, eine Regel: Was oben leuchtet, ist zu sehen. Was
// aus ist, gibt seinen Platz an die Mitte ab - dort wird gefragt und gelesen,
// und dort war bisher am wenigsten Platz.
//
// Zwei Fenster gehen von selbst auf, wenn es etwas zu zeigen gibt: die Belege,
// sobald die erste Fundstelle da ist, und das Dokument, sobald man eine
// Fundstelle anklickt. Ein Klick, der ins Leere zu gehen scheint, weil das
// Fenster zu ist, waere schlimmer als ein Fenster zu viel.

const FENSTER = {
  dokument: "spalte-dokument",
  chronologie: "fenster-chronologie",
  gedaechtnis: "gedaechtnis-fenster",
  entwurf: "fenster-entwurf",
  belege: "fenster-belege",
};

// Voreinstellung: wie bisher, nur ohne das Gedaechtnisfenster - das ist neu
// und soll sich niemandem aufdraengen, der es nicht eingeschaltet hat.
// Das Vorschaufenster faengt zu an: Es hat erst etwas zu zeigen, wenn ein
// Entwurf entsteht - und dann macht es sich selbst auf.
let fensterStand = { dokument: true, chronologie: true, gedaechtnis: false,
                     entwurf: false, belege: true };

// ── Nebenfenster: ein Fenster auf den zweiten Bildschirm ────────────────────
//
// Aus der Kanzlei am 05.10.2026: "Vorschlag waere auch Oeffnen von
// Nebenfenstern in eigener Ansicht, da ich in der Regel mit zwei Bildschirmen
// arbeite und die Oberflaeche mit drei Fenstern zu klein wird."
//
// Gebaut als SPIEGEL, nicht als zweite Arbeitsflaeche. Das Nebenfenster
// oeffnet keine eigene Sitzung, holt nichts selbst und schickt nichts: Es
// zeigt, was das Hauptfenster ihm durchgibt. Drei Gruende, und der dritte
// ist der eigentliche:
//
// 1. Zwei Fenster, die unabhaengig dieselbe Sitzung aendern, sind zwei
//    Fenster, die einander ueberschreiben. Genau daran hat dieser Tag schon
//    einmal gelitten - am 02.10. beim Lesen in Portionen.
// 2. Ein Spiegel braucht keine eigene Anmeldung und kein eigenes Gedaechtnis.
// 3. In einer Mandatsakte muss jederzeit klar sein, WO gearbeitet wird. Ein
//    zweites Fenster, in dem man auch arbeiten kann, waere ein zweiter Ort,
//    an dem etwas geschieht - und der Bearbeiter muesste beide im Kopf haben.

//: Der Kanal, ueber den Haupt- und Nebenfenster miteinander sprechen.
//:
//: BroadcastChannel bleibt im Browser und auf diesem Rechner; nichts davon
//: geht ueber das Netz. Kann der Browser es nicht, bleibt alles wie bisher -
//: dann oeffnet sich kein Nebenfenster, und das Hauptfenster sagt es.
const NEBENKANAL = "jusperfect-nebenfenster";

function nebenkanal() {
  try {
    return typeof BroadcastChannel === "function" ? new BroadcastChannel(NEBENKANAL) : null;
  } catch (e) { return null; }
}

//: In welchem Fenster laeuft dieser Code? "" = Hauptfenster.
const nebenfenster = new URLSearchParams(location.search).get("nebenfenster") || "";

let kanal = null;

/** Den Stand an alle Nebenfenster durchgeben. Im Nebenfenster selbst nichts. */
function nebenfensterGleichziehen() {
  if (nebenfenster || !kanal) return;
  try {
    // Nicht nur die Sitzung: Die drei Fenster zeichnen auch aus Zustand, der
    // neben ihr liegt. Die Chronologie nimmt die Eintraege der Analyse dazu,
    // die Belege leben ganz davon. Haette dieser Aufruf nur die Sitzung
    // geschickt, waere im Nebenfenster eine Chronologie zu sehen gewesen, der
    // genau die Zeilen fehlen, die eine Analyse gerade gefunden hat - und das
    // faellt niemandem auf, weil sie ja gefuellt aussieht.
    kanal.postMessage({
      was: "stand", sitzung, gedaechtnisAktiv: !!K.gedaechtnisAktiv,
      chronoAusAnalyse, passagenIndex,
      belegKennungen: [...belegKennungen], belegQuellen,
      entwurfStand, entwurfLaeuft, entwurfVorschautext,
    });
  } catch (e) { /* ein Fenster weniger, kein Grund anzuhalten */ }
}

/** Ein Fenster herausloesen: im Hauptfenster zuklappen, daneben aufgehen. */
function nebenfensterOeffnen(name) {
  if (!nebenkanal()) {
    melden("Dieser Browser kann keine Nebenfenster verbinden.", true);
    return;
  }
  const ziel = `${location.pathname}?nebenfenster=${encodeURIComponent(name)}`;
  // Der Name macht es: Steht das Fenster schon, gibt der Browser dasselbe
  // zurueck, statt ein zweites zu oeffnen. Es muss nur nach vorn geholt
  // werden - sonst klickt jemand zweimal und sucht dann das Fenster, das
  // hinter dem Hauptfenster liegt.
  const fenster = window.open(ziel, `jusperfect-${name}`,
                              "width=620,height=940,menubar=no,toolbar=no");
  if (!fenster) {
    melden("Der Browser hat das Fenster unterdrückt. Bitte Pop-ups für diese Seite erlauben.", true);
    return;
  }
  try { fenster.focus(); } catch (e) { /* manche Browser lassen das nicht zu */ }
  // Im Hauptfenster zuklappen - das ist der Zweck: Platz schaffen.
  fensterSchliessen(name);
  // Das neue Fenster meldet sich, sobald es bereit ist; dann geht der Stand
  // hinaus. Hier nichts zu senden: Es horcht noch gar nicht.
}

/** Dieses Fenster ist ein Nebenfenster: alles ausblenden ausser dem einen. */
function alsNebenfensterEinrichten() {
  const id = FENSTER[nebenfenster];
  if (!id) {
    document.body.textContent = "Dieses Fenster kennt keine Ansicht namens „"
      + nebenfenster + "“.";
    return;
  }
  document.documentElement.dataset.nebenfenster = nebenfenster;
  document.title = "jusperfect – " + nebenfenster;
  // Die Arbeitsflaeche und die rechte Spalte stehen beide auf "hidden",
  // solange im Hauptfenster keine Akte offen ist. Hier sind sie das Fenster.
  for (const el of [$("flaeche"), $("spalte-rechts"), $(id)])
    if (el) el.hidden = false;
  // Die beiden Knoepfe am Kopf ergeben hier keinen Sinn: Zuklappen und noch
  // einmal herausloesen koennen nur im Hauptfenster etwas bewirken.
  for (const knopf of document.querySelectorAll(
      `[data-fenster-zu="${nebenfenster}"], [data-fenster-los="${nebenfenster}"]`))
    knopf.hidden = true;
  kanal = nebenkanal();
  if (!kanal) {
    document.body.textContent = "Dieser Browser kann keine Nebenfenster verbinden.";
    return;
  }
  kanal.onmessage = (nachricht) => {
    const inhalt = nachricht.data || {};
    if (inhalt.was === "stand") {
      sitzung = inhalt.sitzung || null;
      K.gedaechtnisAktiv = inhalt.gedaechtnisAktiv;
      chronoAusAnalyse = inhalt.chronoAusAnalyse || [];
      passagenIndex = inhalt.passagenIndex || {};
      belegKennungen = new Set(inhalt.belegKennungen || []);
      belegQuellen = inhalt.belegQuellen || {};
      entwurfStand = inhalt.entwurfStand || null;
      entwurfLaeuft = inhalt.entwurfLaeuft || "";
      entwurfVorschautext = inhalt.entwurfVorschautext || "";
      nebenfensterZeichnen();
    } else if (inhalt.was === "hallo") {
      // Das Hauptfenster ist (wieder) da. Noch einmal um den Stand bitten -
      // sonst zeigte dieses Fenster weiter einen Stand von vorhin.
      try { kanal.postMessage({ was: "bitte-stand" }); } catch (e) {}
    } else if (inhalt.was === "zu") {
      sitzung = null;
      chronoAusAnalyse = []; passagenIndex = {};
      belegKennungen = new Set(); belegQuellen = {};
      entwurfStand = null; entwurfLaeuft = ""; entwurfVorschautext = "";
      nebenfensterZeichnen();
    }
  };
  // Das Hauptfenster weiss nicht, dass es dieses Fenster gibt. Also fragen.
  try { kanal.postMessage({ was: "bitte-stand" }); } catch (e) {}
  // Beim Zugehen Bescheid sagen. Aus der Kanzlei am 05.10.2026: "Durch das
  // Schliessen des Fensters sollen natuerlich keine Daten verloren gehen und
  // ich kann es jederzeit wieder oeffnen."
  //
  // Verloren gehen kann hier nichts - dieses Fenster haelt nichts, es zeigt
  // nur. Aber die Ansicht war weg: Beim Herausloesen klappt das Hauptfenster
  // sie zu, und wer dieses Fenster schliesst, stuende sonst vor einer
  // Oberflaeche, in der die Chronologie fehlt und nichts sagt, warum.
  window.addEventListener("beforeunload", () => {
    try { kanal.postMessage({ was: "ende", name: nebenfenster }); } catch (e) {}
    try { kanal.close(); } catch (e) {}
  });
  nebenfensterZeichnen();
}

/** Den einen Abschnitt neu zeichnen - mit denselben Funktionen wie nebenan. */
function nebenfensterZeichnen() {
  const leer = $("neben-leer");
  if (leer) leer.hidden = !!(sitzung && sitzung.sitzung);
  if (!sitzung || !sitzung.sitzung) return;
  try {
    if (nebenfenster === "chronologie") chronologieZeigen();
    else if (nebenfenster === "belege") zeigeBelege();
    else if (nebenfenster === "gedaechtnis") gedaechtnisFensterZeigen();
    else if (nebenfenster === "dokument") dokumentspalteZeichnen();
    else if (nebenfenster === "entwurf") entwurfFensterZeichnen();
  } catch (e) {
    // Ein Spiegel, der sich am Zeichnen verschluckt, darf nicht das ganze
    // Fenster mitnehmen - nebenan wird weitergearbeitet.
    console.error(e);
  }
}

function fensterSchluessel() {
  return "jusperfect.fenster." + (($("nutzer").value || "").trim() || "-");
}

function fensterLaden() {
  try {
    const roh = JSON.parse(localStorage.getItem(fensterSchluessel()) || "null");
    if (roh) for (const name of Object.keys(FENSTER)) if (name in roh) fensterStand[name] = !!roh[name];
  } catch (e) { /* dann die Voreinstellung */ }
  fensterAnwenden();
}

function fensterSichern() {
  try { localStorage.setItem(fensterSchluessel(), JSON.stringify(fensterStand)); } catch (e) {}
}

function fensterAnwenden() {
  for (const [name, id] of Object.entries(FENSTER)) {
    const el = $(id);
    // Das Gedaechtnisfenster gibt es nur mit aktiviertem Gedaechtnis; sein
    // Knopf ebenso. Sonst waere es ein Schalter fuer ein Fenster, das nichts
    // zeigen kann.
    const moeglich = name !== "gedaechtnis" || K.gedaechtnisAktiv;
    if (el) el.hidden = !(moeglich && fensterStand[name]);
    const knopf = document.querySelector(`[data-fenster="${name}"]`);
    if (knopf) {
      knopf.hidden = !moeglich;
      knopf.setAttribute("aria-pressed", String(!!fensterStand[name] && moeglich));
    }
  }
  const rechts = $("spalte-rechts");
  if (rechts) {
    // Alle Fenster dieser Spalte, nicht drei von vieren.
    //
    // Hier standen drei Namen, und das Vorschaufenster kam am 13.10.2026
    // als viertes dazu. Wer alles andere zuklappte und nur die Vorschau
    // offenliess, bekam eine Spalte in "nur-leiste" - und die blendet ihre
    // Fenster aus. Der Entwurf war dann unsichtbar, obwohl sein Knopf
    // gedrueckt war. Gefunden im Browser, nicht im Prueflauf.
    const offen = ["chronologie", "gedaechtnis", "entwurf", "belege"].some(
      (n) => fensterStand[n] && (n !== "gedaechtnis" || K.gedaechtnisAktiv));
    // Die Spalte bleibt stehen, auch wenn alle drei Fenster zu sind: Seit dem
    // 13.10.2026 traegt sie oben die Funktionen (Analyse, Entwurf,
    // Gedaechtnis, Mehr). Waere sie dann weg, waere Analyse nicht mehr
    // erreichbar, sobald jemand die Belege zuklappt - ein Knopf, der mit dem
    // Fenster verschwindet, in dem er steht, ist eine Falle.
    //
    // Zu heisst jetzt: schmal. "ohne-rechts" gibt der Spalte nur noch die
    // Breite ihrer Leiste; der frei werdende Platz geht an den Chat.
    rechts.hidden = false;
    rechts.classList.toggle("nur-leiste", !offen);
    $("flaeche").classList.toggle("ohne-rechts", !offen);
  }
  $("flaeche").classList.toggle("ohne-links", !fensterStand.dokument);
}

function fensterSchliessen(name) {
  // Eigener Weg neben dem Umschalten: Der Pfeil am Fenster schliesst, er
  // schaltet nicht. Zweimal auf einen Schliesspfeil zu treffen, der beim
  // zweiten Mal wieder oeffnet, waere ueberraschend - und das Fenster ist nach
  // dem ersten Klick ohnehin nicht mehr da.
  if (!fensterStand[name]) return;
  fensterStand[name] = false;
  fensterAnwenden();
  fensterSichern();
}

function fensterUmschalten(name) {
  fensterStand[name] = !fensterStand[name];
  fensterAnwenden();
  fensterSichern();
}

function fensterOeffnen(name) {
  if (fensterStand[name]) return;
  fensterStand[name] = true;
  fensterAnwenden();
  fensterSichern();
}

// ── Belege ───────────────────────────────────────────────────────────────────

function belegeMerken(quellen) {
  const vorher = belegKennungen.size;
  for (const q of quellen || []) {
    if (!passagenIndex[q.kennung]) passagenIndex[q.kennung] = q;
    // Die neueste Quelle gewinnt: Sie gehoert zur Aussage, die gerade gelesen
    // wird, und ihre Stelle ist die, die jetzt interessiert.
    belegQuellen[q.kennung] = q;
    belegKennungen.add(q.kennung);
  }
  zeigeBelege();
  // Die erste Fundstelle macht das Fenster auf. Wer es zugeklappt hatte, hatte
  // nichts zu sehen - jetzt gibt es etwas.
  if (!vorher && belegKennungen.size) fensterOeffnen("belege");
}

function zeigeBelege() {
  const box = $("belege"); box.replaceChildren();
  const kennungen = [...belegKennungen].sort();
  $("beleg-stand").textContent = kennungen.length ? `${kennungen.length} Fundstellen` : "";
  if (!kennungen.length) {
    const leer = document.createElement("div"); leer.className = "belege-leer";
    leer.textContent = "Noch keine Fundstellen."; box.appendChild(leer); return;
  }
  for (const kennung of kennungen) {
    const p = passagenIndex[kennung] || {};
    // Die Quelle zur zuletzt gelesenen Aussage kennt die getroffene Stelle;
    // ihr Zitat ist der Satz, um den es geht. passagenIndex haelt dagegen die
    // ganze Passage - deren Anfang stand bisher auf der Karte, und der hat mit
    // der Aussage oft nichts zu tun.
    const q = belegQuellen[kennung];
    const karte = document.createElement("div"); karte.className = "beleg-karte";
    const k = document.createElement("div"); k.className = "k"; k.textContent = kennung;
    const titel = document.createElement("div"); titel.className = "titel";
    titel.textContent = `${p.dokument_titel || ""}${p.seite ? ", Seite " + p.seite : ""}`;
    const zitat = document.createElement("div"); zitat.className = "zitat";
    const genau = !!(q && Number.isInteger(q.treffer_start));
    if (genau) zitat.classList.add("genau");
    zitat.textContent = ((q && q.zitat) || p.zitat || p.text || "").slice(0, 240);
    karte.append(k, titel, zitat);
    // Die Aussage liess sich in der Passage NICHT wiederfinden.
    //
    // Aus der Kanzlei am 05.10.2026: "Ich kann die Dateien nicht finden.
    // Stammen die Dateien vielleicht aus gebildeten Mustern?"
    //
    // Die Frage ist berechtigt, und das Programm konnte sie bisher nicht
    // beantworten. Geprueft wird die KENNUNG: Eine erfundene faellt heraus,
    // fail closed. Der INHALT wurde nicht geprueft - fand sich die Aussage
    // nicht in der Passage wieder, stand auf der Karte still der Anfang des
    // Absatzes, und die Karte sah aus wie jede andere.
    //
    // Sie sieht jetzt nicht mehr aus wie jede andere. Das Programm sagt nicht
    // "erfunden" - das waere ein Urteil, das es nicht faellen kann; eine
    // Umschreibung mit anderen Worten findet sich zu Recht nicht wortwoertlich
    // wieder. Es sagt, was es weiss: Die Stelle liess sich nicht zuordnen,
    // hier steht der Anfang des Absatzes, bitte selbst nachlesen.
    if (!genau) {
      karte.classList.add("ungenau");
      const hinweis = document.createElement("div");
      hinweis.className = "beleg-hinweis";
      hinweis.textContent = "Die Stelle ließ sich im Absatz nicht zuordnen – "
        + "oben steht sein Anfang. Bitte nachlesen.";
      karte.appendChild(hinweis);
    }
    karte.addEventListener("click", () => passageMarkieren(kennung));
    box.appendChild(karte);
  }
  // Hier und nur hier: Wer dieses Fenster neu zeichnet, hat etwas
  // geaendert, das ein Nebenfenster angeht.
  nebenfensterGleichziehen();
}

// ── Cowork-Thread ────────────────────────────────────────────────────────────

function threadWillkommen() {
  // Ein neuer Verlauf, und im Suchfeld stuende noch das Wort von vorhin: Der
  // Zaehler daneben meldete "kein Treffer", und das saehe aus wie ein Fehler.
  chatSucheZeigen(false);
  const t = $("thread"); t.replaceChildren();
  const w = document.createElement("div"); w.className = "willkommen";
  w.textContent = "Fragen Sie die Akte.";
  t.appendChild(w);
}

function gedaechtnisImThreadZeigen() {
  const g = sitzung && sitzung.gedaechtnis;
  if (!g || !g.vorhanden) return;
  const t = $("thread");
  if (g.lebenssachverhalt) {
    const karte = document.createElement("div"); karte.className = "karte-c ai";
    const titel = document.createElement("div"); titel.className = "titelzeile"; titel.textContent = "Gedächtnis · Lebenssachverhalt";
    const inhalt = document.createElement("div"); inhalt.className = "inhalt";
    antworttext(inhalt, g.lebenssachverhalt);
    karte.append(titel, inhalt); t.appendChild(karte);
  }
  // ALLE frueheren Fragen, nicht die letzten fuenf.
  //
  // Aus der Kanzlei am 13.10.2026: "5 Fragen im Chat sind zu wenig -
  // eigentlich sollte der Chat scrollbar und zurueckverfolgbar sein. Der Chat
  // steht im Vordergrund. Der Rest ist nur Hilfsmittel."
  //
  // Die Fuenf waren eine Vorsicht ohne Anlass: Die Spalte scrollt (siehe
  // `.thread { overflow: auto }`), die Fundstellen in den alten Antworten
  // sind anklickbar wie in den neuen, und im Gedaechtnis liegen ohnehin nur
  // die letzten hundert. Abgeschnitten wurde also beim Anzeigen, nicht beim
  // Speichern - der Verlauf war da und nicht zu sehen.
  const frueher = g.fragen_antworten || [];
  for (const qa of frueher) {
    const frage = document.createElement("div"); frage.className = "karte-c user";
    const frageWer = document.createElement("div"); frageWer.className = "who"; frageWer.textContent = "Frühere Frage";
    const frageText = document.createElement("div"); frageText.className = "inhalt"; frageText.textContent = qa.frage;
    frage.append(frageWer, frageText); t.appendChild(frage);
    const antwort = document.createElement("div"); antwort.className = "karte-c ai";
    const antwortWer = document.createElement("div"); antwortWer.className = "who"; antwortWer.textContent = "jusperfect · aus dem Gedächtnis";
    const antwortText = document.createElement("div"); antwortText.className = "inhalt";
    antworttext(antwortText, qa.antwort);
    antwort.append(antwortWer, antwortText); t.appendChild(antwort);
  }
  // Eine Linie zwischen dem, was war, und dem, was jetzt kommt. Ohne sie
  // steht die erste neue Frage in derselben Reihe wie die Frage von gestern.
  if (frueher.length) {
    const strich = document.createElement("div");
    strich.className = "thread-trennung";
    strich.textContent = frueher.length === 1
      ? "1 frühere Frage aus dem Gedächtnis – darunter das Heutige"
      : `${frueher.length} frühere Fragen aus dem Gedächtnis – darunter das Heutige`;
    t.appendChild(strich);
  }
  // Unten anfangen, nicht oben: Das Juengste ist das, woran weitergearbeitet
  // wird. Bei hundert Fragen stuende sonst die aelteste im Bild.
  t.scrollTop = t.scrollHeight;
}

// ── Suche im Chat ────────────────────────────────────────────────────────────
//
// Aus der Kanzlei am 15.10.2026: "Die Lupe haette ich uebrigens auch gerne
// fuer den Chat."
//
// Der Anlass ist derselbe wie am 13.10. bei den Dokumenten, nur eine Spalte
// weiter: Seit im Chat ALLE frueheren Fragen stehen und nicht mehr die
// letzten fuenf, ist er zurueckverfolgbar - aber hundert Fragen durchblaettern
// ist kein Wiederfinden.
//
// Sie kostet nichts. Gesucht wird in dem, was ohnehin schon auf dem Bildschirm
// steht; es geht keine Anfrage hinaus, kein Modell wird gefragt, und nichts
// vom Gesuchten verlaesst den Rechner. Derselbe Grundsatz wie bei der Suche im
// Dokumenttext.

// ── Fundstellen im Text: ein und aus ─────────────────────────────
//
// Aus der Kanzlei am 15.10.2026: „Aufgrund der ganzen Quellen und Anlagen im
// Text ist der Text im Chat kaum lesbar. Es waere daher gut, wenn man das ein-
// und ausschalten koennte."
//
// Die Belegpflicht bleibt, wie sie ist: Es stroemt nur Geprueftes, eine Aussage
// ohne Beleg wird zurueckgehalten, und das Fenster „Belege" fuehrt jede
// Fundstelle mit Dokument, Seite und Wortlaut. Geaendert wird allein, ob die
// Kennungen MITTEN IM SATZ stehen - eine Frage des Lesens, keine der Pruefung.
//
// Ausgeblendet ist die Grundstellung: Gelesen wird oefter als nachgeschlagen.
// Ein Klick holt sie zurueck, und zwar dieselben anklickbaren Marken - es wird
// nichts verworfen und nichts neu geholt, nur die Anzeige umgeschaltet. Die
// Wahl bleibt in diesem Rechner stehen.

/** Stehen die Belegmarken im Text? */
let fundstellenAn = false;
try { fundstellenAn = localStorage.getItem("jusperfect.fundstellen") === "an"; } catch (e) { /* egal */ }

/** Schalter und Verlauf auf den Stand bringen. */
function fundstellenZeichnen() {
  const thread = $("thread");
  if (thread) thread.classList.toggle("ohne-fundstellen", !fundstellenAn);
  const knopf = $("chat-fundstellen");
  if (!knopf) return;
  knopf.textContent = fundstellenAn ? "Fundstellen: an" : "Fundstellen: aus";
  knopf.setAttribute("aria-pressed", fundstellenAn ? "true" : "false");
}

function fundstellenUmschalten() {
  fundstellenAn = !fundstellenAn;
  try { localStorage.setItem("jusperfect.fundstellen", fundstellenAn ? "an" : "aus"); }
  catch (e) { /* egal */ }
  fundstellenZeichnen();
  // Gezaehlt wird in dem, was zu sehen ist: Eine ausgeblendete Kennung ist
  // kein Treffer. Steht gerade eine Suche im Feld, wird sie neu gezaehlt.
  chatSuchen();
}

/** Der Text eines Beitrags so, wie er auf dem Bildschirm steht.
 *
 * `textContent` liefert auch, was ausgeblendet ist. Wer bei ausgeschalteten
 * Fundstellen nach „D1-S1-P1" sucht, bekaeme sonst einen Beitrag angezeigt,
 * in dem nichts hervorgehoben waere - ein Treffer, den man nicht findet.
 */
function sichtbarerText(el) {
  if (fundstellenAn) return el.textContent;
  const klon = el.cloneNode(true);
  for (const g of klon.querySelectorAll(".belegstelle")) g.remove();
  return klon.textContent;
}

/** Die Suchwoerter aus dem Chatfeld - klein geschrieben, ohne Leeres. */
function chatSuchwoerter() {
  const feld = $("chat-suche");
  return feld ? feld.value.toLowerCase().split(/\s+/).filter(Boolean) : [];
}

/** Alle Hervorhebungen wieder herausnehmen.
 *
 * Gesetzt wird nur in TEXTKNOTEN, und hier wird auch nur dort geraeumt: Die
 * Antworten tragen anklickbare Fundstellen, Ueberschriften und Aufzaehlungen.
 * Wer den Inhalt neu schriebe, um eine Farbe zu entfernen, nimmt dem
 * Bearbeiter die Belege unter der Hand weg.
 */
function markenEntfernen(wurzel) {
  const marken = [...wurzel.querySelectorAll("mark.chat-treffer")];
  for (const m of marken) m.replaceWith(document.createTextNode(m.textContent));
  if (marken.length) wurzel.normalize();
}

/** Die Suchwoerter in einem Beitrag hervorheben - ohne die Struktur anzufassen. */
function markenSetzen(wurzel, begriffe) {
  if (!begriffe.length) return;
  const lauf = document.createTreeWalker(wurzel, NodeFilter.SHOW_TEXT);
  const knoten = [];
  for (let n = lauf.nextNode(); n; n = lauf.nextNode()) {
    if (!n.nodeValue) continue;
    // Nichts hervorheben, was gar nicht zu sehen ist: Sonst zaehlte der Lauf
    // Stellen mit, zu denen er nicht springen kann.
    if (!fundstellenAn && n.parentElement && n.parentElement.closest(".belegstelle")) continue;
    knoten.push(n);
  }
  for (const n of knoten) {
    const text = n.nodeValue;
    const klein = text.toLowerCase();
    const stellen = [];
    for (const b of begriffe) {
      let ab = 0;
      for (;;) {
        const i = klein.indexOf(b, ab);
        if (i < 0) break;
        stellen.push([i, i + b.length]);
        ab = i + b.length;
      }
    }
    if (!stellen.length) continue;
    stellen.sort((a, b) => a[0] - b[0]);
    const stueck = document.createDocumentFragment();
    let bis = 0;
    for (const [von, ende] of stellen) {
      if (von < bis) continue;                      // ueberlappende Treffer
      if (von > bis) stueck.appendChild(document.createTextNode(text.slice(bis, von)));
      const m = document.createElement("mark");
      m.className = "chat-treffer";
      m.textContent = text.slice(von, ende);
      stueck.appendChild(m);
      bis = ende;
    }
    if (bis < text.length) stueck.appendChild(document.createTextNode(text.slice(bis)));
    n.replaceWith(stueck);
  }
}

/** Den Verlauf auf die Beitraege eindampfen, in denen jedes Suchwort vorkommt.
 *
 * Gezaehlt und gefiltert wird in BEITRAEGEN, nicht in Karten: Eine Frage
 * eroeffnet, die Antwort darunter gehoert dazu. Bliebe nur die Antwort stehen,
 * laese der Bearbeiter eine Auskunft, ohne zu wissen, worauf sie antwortet -
 * und in einer Mandatsakte ist genau das die gefaehrliche Haelfte.
 */
function chatSuchen() {
  const thread = $("thread");
  if (!thread) return;
  const begriffe = chatSuchwoerter();
  markenEntfernen(thread);

  const beitraege = [];
  let jetzt = null;
  for (const el of [...thread.children]) {
    el.hidden = false;
    if (!el.classList.contains("karte-c")) {
      // Trennstriche und der Willkommensgruss sagen beim Suchen nichts und
      // stuenden zwischen den Treffern.
      if (begriffe.length) el.hidden = true;
      continue;
    }
    if (el.classList.contains("user") || !jetzt) { jetzt = []; beitraege.push(jetzt); }
    jetzt.push(el);
  }

  let gefunden = 0;
  for (const beitrag of beitraege) {
    const text = beitrag.map((el) => sichtbarerText(el)).join(" ").toLowerCase();
    if (!begriffe.length || begriffe.every((b) => text.includes(b))) {
      gefunden++;
      for (const el of beitrag) markenSetzen(el, begriffe);
    } else {
      for (const el of beitrag) el.hidden = true;
    }
  }

  const marke = $("chat-treffer");
  if (marke) {
    // Null Treffer ist eine Auskunft, kein leerer Chat.
    marke.textContent = !begriffe.length ? ""
      : gefunden === 0 ? `kein Treffer in ${beitraege.length} ${beitraege.length === 1 ? "Beitrag" : "Beiträgen"}`
      : "";   // Bei Treffern sagt es der Lauf daneben.
    marke.classList.toggle("ohne-treffer", !!begriffe.length && gefunden === 0);
  }
  laufZeigen("chat", begriffe.length && gefunden
    ? `${gefunden} von ${beitraege.length} Beiträgen - klicken springt zur nächsten Fundstelle`
    : "");
}

/** Die Suchzeile auf- oder zuklappen. Zu heisst: ganzer Verlauf, kein Rest. */
function chatSucheZeigen(an) {
  const zeile = $("chat-suche-zeile");
  if (!zeile) return;
  zeile.hidden = !an;
  const knopf = $("chat-lupe");
  if (knopf) knopf.setAttribute("aria-expanded", an ? "true" : "false");
  const feld = $("chat-suche");
  if (!feld) return;
  if (an) { feld.focus(); feld.select(); return; }
  // Zugeklappt darf keine Karte versteckt bleiben: Ein halber Verlauf, dessen
  // Grund nicht mehr zu sehen ist, sieht aus wie ein verlorener Verlauf.
  feld.value = "";
  chatSuchen();
}

// ── Gedächtnis: was liegt drin, was fehlt, wie groß ist es ─────────────
// Ein dauerhafter Speicher, den niemand einsehen kann, ist eine Zusage ohne
// Nachweis. Das Fenster nennt den Umfang, der Explorer zeigt ihn neben der
// Akte aus jurnodes – und hebt hervor, was noch fehlt.

let gedAuswahl = new Set();

function umfangKurz(zeichen) {
  // Zeichen sind die ehrliche Größe: Gespeichert wird Text, nicht die Datei.
  if (zeichen < 1000) return `${zeichen} Zeichen`;
  if (zeichen < 1000000) return `${(zeichen / 1000).toFixed(zeichen < 10000 ? 1 : 0)} Tsd. Zeichen`;
  return `${(zeichen / 1000000).toFixed(1)} Mio. Zeichen`;
}

function gedFehlende() {
  const g = (sitzung && sitzung.gedaechtnis) || {};
  const drin = new Set((g.eintraege || []).map((e) => e.dokument_id));
  return (sitzung.dokumente || []).filter((d) => !drin.has(d.id));
}

/** Die fehlenden, die der Filter gerade stehen laesst.
 *
 * gedFehlende() zaehlt die ganze Akte - das gehoert in den Satz "x von y im
 * Gedaechtnis". Zum Anhaken darf nur zaehlen, was man auch sieht.
 */
function gedSichtbarFehlende() {
  const begriffe = suchbegriffe("ged-suche");
  return gedFehlende().filter((d) => dokumentPasst(d, begriffe));
}

function gedaechtnisFensterZeigen() {
  const fenster = $("gedaechtnis-fenster");
  if (!fenster) return;
  // Ob es sichtbar ist, entscheidet der Knopf oben - hier wird nur der Inhalt
  // gefuellt. Frueher stand beides an derselben Stelle, und ein zugeklapptes
  // Fenster ging beim naechsten Zeichnen von selbst wieder auf.
  fensterAnwenden();
  if (!K.gedaechtnisAktiv || !sitzung) return;
  const g = sitzung.gedaechtnis || {};
  const gesamt = (sitzung.dokumente || []).length;
  const drin = (g.eintraege || []).length;
  $("ged-stand").textContent = g.vorhanden ? `${drin}/${gesamt} Dok. · ${umfangKurz(g.zeichen || 0)}` : "leer";

  const ziel = $("ged-uebersicht");
  ziel.replaceChildren();
  if (!g.vorhanden) {
    const p = document.createElement("p"); p.className = "chrono-leer";
    p.textContent = "Noch nichts gespeichert. „erstellen/aktualisieren\" legt es an.";
    ziel.appendChild(p); return;
  }
  // Hier standen fuenf Zahlen untereinander: Dokumente, Umfang, fruehere
  // Fragen, Ereignisse, Stand. Jede fuer sich richtig, zusammen eine kleine
  // Statistik in einer Spalte von 300 Pixeln - und keine davon beantwortet
  // eine Frage, die man beim Arbeiten hat. Geblieben ist der eine Satz, der
  // sie beantwortet: Ist die Akte vollstaendig drin, und von wann ist der
  // Stand? Alles Weitere steht im Gedaechtnis-Fenster, einen Klick entfernt.
  const satz = document.createElement("p");
  satz.className = "ged-satz";
  const fehlend = gedFehlende();
  satz.textContent = fehlend.length
    ? `${drin} von ${gesamt} Dokumenten im Gedächtnis – ${fehlend.length} fehlen noch.`
    : `Alle ${gesamt} Dokumente im Gedächtnis.`;
  ziel.appendChild(satz);
  // Ob die Akte auch gelesen ist, steht nicht in der Dokumentzahl: Ein Auszug
  // liegt im Gedaechtnis, sobald er eingelesen wurde; in den Lebenssachverhalt
  // kommt er erst durch "Akte einlesen". Nach einem Lauf ueber sieben
  // Portionen soll man das sehen und nicht raten.
  const gelesen = document.createElement("p");
  gelesen.className = "ged-satz";
  const offene = g.offene_dokumente || 0;
  if (!g.lebenssachverhalt) {
    gelesen.textContent = "Noch nicht gelesen – „Akte einlesen“ bildet den Lebenssachverhalt.";
    gelesen.classList.add("leise");
  } else if (offene) {
    gelesen.textContent = `Gelesen bis auf ${offene} Dokument(e) · ${(g.quellen || []).length} Fundstellen.`;
  } else {
    gelesen.textContent = `Ganz gelesen · ${(g.quellen || []).length} Fundstellen im Lebenssachverhalt.`;
  }
  ziel.appendChild(gelesen);
  if (g.aktualisiert_am) {
    const stand = document.createElement("p");
    stand.className = "ged-satz leise";
    stand.textContent = "Stand " + datumKurz(g.aktualisiert_am);
    ziel.appendChild(stand);
  }
  // Hier und nur hier: Wer dieses Fenster neu zeichnet, hat etwas
  // geaendert, das ein Nebenfenster angeht.
  nebenfensterGleichziehen();
}

// Die grosse Akte: Sie passt nicht in einen Aufruf, also wird sie in Portionen
// gelesen. Jede Portion bekommt den bisherigen Lebenssachverhalt als Faden mit
// und haengt an ihn an; angehaengt wird immer, umgeschrieben nie.
//
// Der Lauf wird ausdruecklich ausgeloest und nie von selbst: Er kostet so viele
// Modellaufrufe, wie Portionen noetig sind. Deshalb steht vorher da, womit zu
// rechnen ist - und die Zahl wird geschaetzt genannt, nicht als Zusage.
// Die grosse Akte: Sie passt nicht in einen Aufruf, also wird sie in Portionen
// gelesen. Jede Portion bekommt den bisherigen Lebenssachverhalt als Faden mit
// und haengt an ihn an; angehaengt wird immer, umgeschrieben nie.
//
// Portion fuer Portion, nicht in einem Zug: Aus der Kanzlei kam der Wunsch,
// "wie bei einem Download" zu sehen, wie weit es ist. Ein einziger Aufruf ueber
// alle Portionen koennte das nicht sagen - er kommt erst am Ende zurueck. Also
// ruft die Oberflaeche denselben Weg, den auch der Nachtrag eines einzelnen
// Schriftsatzes geht, so oft, bis nichts mehr offen ist. Jede Portion ist
// einzeln gespeichert; wer anhaelt, verliert nichts.

let einlesenAbbrechen = false;

function einlesenFortschritt(gelesen, gesamt, sekundenJeSchritt, offeneSchritte) {
  const block = $("ged-fortschritt");
  block.hidden = false;
  const anteil = gesamt ? Math.round((gelesen / gesamt) * 100) : 0;
  $("ged-balken").style.width = `${anteil}%`;
  $("ged-fortschritt-text").textContent =
    `${gelesen} von ${gesamt} Dokumenten eingelesen · ${anteil} %`;
  $("ged-fortschritt-dauer").textContent = sekundenJeSchritt && offeneSchritte > 0
    ? `noch etwa ${dauerText(sekundenJeSchritt * offeneSchritte)}`
    : "";
}

function dauerText(sekunden) {
  if (sekunden < 60) return `${Math.max(5, Math.round(sekunden / 5) * 5)} Sekunden`;
  const minuten = Math.round(sekunden / 60);
  return minuten === 1 ? "eine Minute" : `${minuten} Minuten`;
}

async function gedaechtnisEinlesen() {
  const g = (sitzung && sitzung.gedaechtnis) || {};
  const gesamt = (g.eintraege || []).length;
  const offenAmAnfang = g.offene_dokumente || 0;
  // Null offene Dokumente heisst ZWEIERLEI, und die beiden sind das
  // Gegenteil voneinander.
  //
  // Aus der Kanzlei am 13.10.2026, nach dem Verwerfen: "Aktengedaechtnis ist
  // leer - Akte einlesen fuehrt zu dem Ergebnis: Akte ist schon eingelesen."
  //
  // Hier stand EIN Satz fuer beide Faelle. Liegt nichts im Gedaechtnis, ist
  // nichts offen - und das sah aus wie "fertig", waehrend in Wahrheit noch
  // gar nichts angefangen hatte. Genau nach einem Verwerfen, also genau
  // dann, wenn der Bearbeiter weitermachen will.
  //
  // `offene_dokumente` zaehlt, was IM Gedaechtnis liegt und noch nicht
  // verarbeitet ist. Dokumente kommen durch das Anhaken hinein, nicht durch
  // das Einlesen - das baut aus ihnen den Lebenssachverhalt. Wer das nicht
  // weiss, klickt hier und bekommt eine Antwort, die ihn wegschickt.
  if (!gesamt) {
    // Der Hinweis muss GELESEN werden, bevor etwas aufgeht: Das
    // Auswahlfenster ist ein modaler Dialog und legte sich sonst ueber die
    // Meldung, die ihn erklaert.
    const weg = [
      "Im Gedächtnis liegt noch kein Dokument.",
      "",
      "„Akte einlesen“ baut den Lebenssachverhalt aus dem, was im Gedächtnis",
      "liegt. Hinein kommen die Dokumente durch das Anhaken – im Fenster",
      "„Auswahl“, links in der Liste der Akte.",
      "",
      "Nach einem Verwerfen ist das Gedächtnis leer; dann fängt es hier an.",
      "",
      "Das Fenster „Auswahl“ jetzt öffnen?",
    ];
    if (confirm(weg.join("\n"))) gedaechtnisExplorerOeffnen();
    return;
  }
  if (!offenAmAnfang) { melden("Es ist schon alles eingelesen."); return; }
  const zeichen = g.zeichen || 0;
  const grenze = K.maxPassagenZeichen || 160000;
  const portionen = Math.max(1, Math.ceil(zeichen / grenze));
  const nichtDrin = (sitzung.dokumente || []).length - gesamt;
  const teile = [
    "Die Akte wird Portion für Portion ins Gedächtnis gelesen.",
    "",
    `Noch einzulesen: ${offenAmAnfang} von ${gesamt} Dokumenten (${zeichen.toLocaleString("de-DE")} Zeichen)`,
    `Zu erwarten: etwa ${portionen} Modellaufruf(e)`,
  ];
  if (nichtDrin > 0) teile.push(`${nichtDrin} Dokument(e) der Akte liegen nicht im Gedächtnis – sie gehen nicht mit.`);
  teile.push("", "Das dauert und kostet. Anhalten ist jederzeit möglich; Gelesenes bleibt erhalten.", "Fortfahren?");
  if (!confirm(teile.join("\n"))) return;

  einlesenAbbrechen = false;
  $("ged-abbrechen").disabled = false;
  einlesenFortschritt(gesamt - offenAmAnfang, gesamt, 0, 0);
  let schritte = 0, passagen = 0, offenePassagen = 0;
  let kosten = 0, verstrichen = 0;
  const hinweise = [];

  try {
    while (!einlesenAbbrechen) {
      const begonnen = Date.now();
      const daten = await api("POST", `/api/sitzungen/${sitzung.sitzung.id}/gedaechtnis/aktualisieren`);
      const lauf = daten.lauf || {};
      sitzung.gedaechtnis = daten;
      if (!lauf.portionen) break;                 // nichts mehr offen
      schritte++;
      verstrichen += (Date.now() - begonnen) / 1000;
      passagen += lauf.passagen || 0;
      offenePassagen = lauf.offene_passagen || 0;
      kosten += (lauf.kosten && lauf.kosten.betrag_eur) || 0;
      for (const h of lauf.hinweise || []) hinweise.push(h);
      gedaechtnisFensterZeigen();
      // Wie viele Portionen noch kommen, schaetzt sich aus dem bisherigen
      // Durchschnitt: So viele Passagen wie bisher je Portion, so lange wie
      // bisher je Portion. Genauer geht es nicht, und genauer muss es nicht.
      const jePortion = passagen / schritte;
      const nochSchritte = jePortion ? Math.ceil(offenePassagen / jePortion) : 0;
      const gelesen = (daten.eintraege || []).length - (daten.offene_dokumente || 0);
      einlesenFortschritt(gelesen, (daten.eintraege || []).length,
                          verstrichen / schritte, nochSchritte);
      if (!offenePassagen) break;
    }
  } finally {
    $("ged-fortschritt").hidden = true;
    $("ged-balken").style.width = "0%";
  }

  gedaechtnisFensterZeigen();
  const bericht = [`${schritte} Portion(en) gelesen`, `${passagen} Passagen`];
  if (offenePassagen) bericht.push(`${offenePassagen} Passagen blieben offen`);
  if (kosten) bericht.push(`${kosten.toFixed(4)} €`);
  melden(bericht.join(" · ") + (einlesenAbbrechen ? " – angehalten" : ""));
  // Die Hinweise sind die ehrlichen Stellen: Portionen, aus denen nichts
  // Belegtes hervorging. Sie gehoeren in den Verlauf, nicht in eine Meldung,
  // die nach drei Sekunden verschwindet.
  for (const hinweis of hinweise) hinweisImThread(hinweis);
}

function hinweisImThread(text) {
  const karte = document.createElement("div"); karte.className = "karte-c ai";
  const titel = document.createElement("div"); titel.className = "titelzeile";
  titel.textContent = "Gedächtnis · Hinweis";
  const inhalt = document.createElement("div"); inhalt.className = "inhalt"; inhalt.textContent = text;
  karte.append(titel, inhalt);
  $("thread").appendChild(karte);
}

function gedaechtnisExplorerOeffnen() {
  gedAuswahl = new Set();
  // Erst das Suchfeld leeren, dann zeichnen.
  //
  // Aus der Kanzlei am 13.10.2026: „das Programm hat aber dann nur 2
  // Dokumente eingelesen, und zwar die, die ich vorher ausgewaehlt hatte."
  //
  // Ein stehengebliebener Filter ist hier teurer als anderswo: Die Liste
  // zeigt dann vier von hundert Dokumenten, „alle fehlenden" hakt genau
  // diese vier an, und der Bearbeiter sieht nicht, warum. Er bezahlt das
  // Einlesen und bekommt vier Dokumente.
  //
  // Im Dokumentfenster ist das seit dem 12.10.2026 berichtigt - mit
  // demselben Satz im Kommentar. Hier stand es nicht: Zwei Fenster, die
  // dasselbe tun, und die Verbesserung nur im einen.
  const suche = $("ged-suche"); if (suche) suche.value = "";
  gedInhaltSchalterLaden();
  gedExplorerZeichnen();
  $("ged-dialog").showModal();
}

function gedExplorerZeichnen() {
  const g = (sitzung && sitzung.gedaechtnis) || {};
  const eintraege = g.eintraege || [];
  const drinNach = new Map(eintraege.map((e) => [e.dokument_id, e]));
  const alle = sitzung.dokumente || [];

  const begriffe = suchbegriffe("ged-suche");
  const links = $("ged-quelle-liste"); links.replaceChildren();
  const sichtbar = alle.filter((d) => dokumentPasst(d, begriffe));

  // Dieselbe Gliederung wie im Dokumentfenster - und hier zuerst. Angehakt
  // wird zuerst in diesem Fenster: ohne Gedaechtnis hat die Arbeitsakte
  // nichts, woraus sie schoepfen koennte. Ein einziger Ordner ist keine
  // Gliederung; dann bleibt die Liste glatt wie bisher.
  const gruppen = explorerNachOrdnern(sichtbar);
  const mitUeberschrift = gruppen.length > 1;
  for (const [ordner, dazu] of gruppen) {
    if (mitUeberschrift) links.appendChild(gedOrdnerzeile(ordner, dazu, drinNach));
    for (const d of dazu) links.appendChild(gedQuellzeile(d, drinNach));
  }
  zahlZeigen("ged-quelle-zahl", sichtbar.length, alle.length);

  const rechts = $("ged-drin-liste"); rechts.replaceChildren();
  let rechtsN = 0;
  for (const e of eintraege) {
    if (!dokumentPasst(e, begriffe)) continue;
    rechtsN++;
    const li = document.createElement("li"); li.className = "explorer-zeile ged-eintrag";
    li.appendChild(feld(e.titel, "explorer-titelzeile"));
    li.appendChild(feld(`${e.seiten} S. · ${umfangKurz(e.zeichen)}${e.ocr ? " · OCR" : ""}`, "explorer-marke"));
    // Bis zum 05.10.2026 ging nur alles oder nichts: GEDAECHTNIS-LEEREN.bat
    // warf das ganze Gedaechtnis weg. Wer ein einziges Dokument heraushaben
    // wollte, zahlte das Einlesen der ganzen Akte noch einmal.
    //
    // type="button": Das Formular dieses Dialogs traegt method="dialog", und
    // ein Knopf ohne diese Angabe wuerde den Dialog schliessen statt zu
    // loeschen.
    const weg = document.createElement("button");
    weg.type = "button";
    weg.className = "mini leise ged-vergessen";
    weg.textContent = "vergessen";
    weg.title = `„${e.titel}" aus dem Gedächtnis entfernen`;
    weg.addEventListener("click", (ev) => mitKnopf(ev.target, () => gedaechtnisDokumentVergessen(e)));
    li.appendChild(weg);
    rechts.appendChild(li);
  }
  zahlZeigen("ged-drin-zahl", rechtsN, eintraege.length);
  gedInhaltZeigen();
  gedUmfangZeigen();
}

/** Eine Zeile der linken Spalte: ein Dokument der Akte.
 *
 * Ein Haekchen gibt es nur bei dem, was noch fehlt. Was schon drin ist, steht
 * ausgegraut da - sichtbar, damit man es sucht und findet, aber nicht
 * waehlbar, damit es nicht ein zweites Mal aufgenommen wird.
 */
function gedQuellzeile(d, drinNach) {
  const li = document.createElement("li");
  const fehlt = !drinNach.has(d.id);
  li.className = "explorer-zeile" + (fehlt ? " fehlt" : " drin schon-drin");
  const box = document.createElement("input");
  box.type = "checkbox";
  box.checked = fehlt ? gedAuswahl.has(d.id) : true;
  box.disabled = !fehlt;
  box.title = fehlt ? "In das Gedächtnis aufnehmen" : "Liegt bereits im Gedächtnis";
  if (fehlt) {
    box.addEventListener("change", () => {
      box.checked ? gedAuswahl.add(d.id) : gedAuswahl.delete(d.id);
      gedUmfangZeigen();
    });
  }
  li.appendChild(box);
  li.appendChild(feld(d.titel, "explorer-titelzeile"));
  li.appendChild(feld(fehlt ? "fehlt" : "schon im Gedächtnis", "explorer-marke"));
  return li;
}

/** Die Ueberschrift eines Ordners in der linken Spalte.
 *
 * Die Zahl sagt nicht, wie gross der Ordner ist, sondern was hier noch zu tun
 * ist - danach wird in diesem Fenster gesucht. Der Knopf nimmt nur die
 * fehlenden; was schon im Gedaechtnis liegt, darf nicht ein zweites Mal
 * aufgenommen werden. Fehlt in einem Ordner nichts, steht kein Knopf da:
 * ein Knopf ohne Wirkung ist ein Versprechen, das nicht gehalten wird.
 */
function gedOrdnerzeile(ordner, dazu, drinNach) {
  const li = document.createElement("li");
  li.className = "explorer-ordner";
  const name = document.createElement("span");
  name.className = "explorer-ordnername";
  // Der leere Ordner ist kein Ordner, sondern die Akte selbst.
  name.textContent = ordner || "Unmittelbar im Aktenordner";
  if (!ordner) li.classList.add("wurzel");
  const fehlende = dazu.filter((d) => !drinNach.has(d.id));
  const zahl = document.createElement("span");
  zahl.className = "explorer-ordnerzahl";
  zahl.textContent = fehlende.length
    ? `${fehlende.length} von ${dazu.length} fehlen`
    : (dazu.length === 1 ? "1 Dokument · im Gedächtnis" : `${dazu.length} Dokumente · im Gedächtnis`);
  li.append(name, zahl);

  if (fehlende.length) {
    const alleDrin = fehlende.every((d) => gedAuswahl.has(d.id));
    // type="button": Das Formular dieses Dialogs traegt method="dialog", und
    // ein Knopf ohne diese Angabe wuerde den Dialog schliessen.
    const knopf = document.createElement("button");
    knopf.type = "button";
    knopf.className = "explorer-ordnerknopf";
    knopf.textContent = alleDrin ? "Haken entfernen" : "alle fehlenden";
    knopf.title = alleDrin ? `Haken in „${name.textContent}" entfernen`
                           : `Alle fehlenden aus „${name.textContent}" anhaken`;
    knopf.addEventListener("click", () => {
      for (const d of fehlende) {
        if (alleDrin) gedAuswahl.delete(d.id); else gedAuswahl.add(d.id);
      }
      gedExplorerZeichnen();
    });
    li.appendChild(knopf);
  }
  return li;
}

// Der Inhalt ist eine einschaltbare Funktion: Zu ist der Regelfall, denn die
// taegliche Frage lautet "ist die Akte vollstaendig drin?" und die beantworten
// die beiden Spalten darueber. Wer wissen will, was das Programm daraus gemacht
// hat, klappt ihn auf - und findet ihn beim naechsten Mal so wieder vor. Der
// Schalter steht in diesem Browser und enthaelt keinen Akteninhalt.
function gedInhaltSchluessel() {
  return "jusperfect.gedinhalt." + (($("nutzer").value || "").trim() || "-");
}

function gedInhaltSchalterLaden() {
  const block = $("ged-inhalt");
  if (!block) return;
  try { block.open = localStorage.getItem(gedInhaltSchluessel()) === "auf"; } catch (e) {}
}

function gedInhaltSchalterMerken() {
  try {
    localStorage.setItem(gedInhaltSchluessel(), $("ged-inhalt").open ? "auf" : "zu");
  } catch (e) { /* egal - dann merkt es sich der Browser eben nicht */ }
}

function gedInhaltZeigen() {
  // Aus der Kanzlei: "zeig auch den Inhalt in dieser Ansicht". Die beiden
  // Spalten darueber beantworten "ist die Akte vollstaendig drin?". Sie
  // beantworten nicht "was hat sich das Programm eigentlich gemerkt?" - und
  // das ist die Frage, bei der man einem Gedaechtnis vertrauen koennen muss.
  const g = (sitzung && sitzung.gedaechtnis) || {};
  const leer = $("ged-inhalt-leer");
  const teile = $("ged-inhalt-teile");
  const chronologie = g.chronologie || [];
  const fragen = g.fragen_antworten || [];
  const sachverhalt = g.lebenssachverhalt || "";

  if (!sachverhalt && !chronologie.length && !fragen.length) {
    leer.textContent = (g.eintraege || []).length
      ? "Die Dokumente liegen im Gedächtnis, gelesen ist die Akte noch nicht. "
        + "„Akte einlesen“ bildet daraus Lebenssachverhalt und Chronologie."
      : "Noch nichts gespeichert.";
    leer.hidden = false;
    teile.hidden = true;
    return;
  }
  leer.hidden = true;
  teile.hidden = false;

  // Der Text so, wie er wirklich gespeichert ist - mitsamt der Fundstellen in
  // eckigen Klammern. Wer prueft, was im Gedaechtnis steht, will nicht eine
  // aufbereitete Fassung sehen, sondern den Stand.
  $("ged-sv-text").textContent = sachverhalt || "– noch nicht gebildet –";
  $("ged-sv-zahl").textContent = sachverhalt ? umfangKurz(sachverhalt.length) : "leer";

  const chronoListe = $("ged-chrono-liste"); chronoListe.replaceChildren();
  for (const e of chronologie) {
    const li = document.createElement("li");
    li.className = "ged-block-zeile";
    li.appendChild(feld(e.datum || "", "ged-block-datum"));
    li.appendChild(feld(e.ereignis || "", "ged-block-sache"));
    chronoListe.appendChild(li);
  }
  $("ged-chrono-zahl").textContent = chronologie.length ? `${chronologie.length}` : "leer";

  const fragenListe = $("ged-fragen-liste"); fragenListe.replaceChildren();
  for (const f of fragen) {
    const li = document.createElement("li");
    li.className = "ged-block-zeile ged-block-frage";
    li.appendChild(feld(f.frage || "", "ged-block-sache stark"));
    li.appendChild(feld(f.antwort || "", "ged-block-antwort"));
    // Eine gespeicherte Antwort kann falsch oder ueberholt sein - etwa weil
    // sie aus einem Dokument stammt, das inzwischen durch eine neue Fassung
    // ersetzt wurde. Sie geht bei jeder spaeteren Frage als Vorwissen mit;
    // stehen zu lassen, was nicht mehr stimmt, ist deshalb teurer als es
    // aussieht.
    const weg = document.createElement("button");
    weg.type = "button";
    weg.className = "mini leise ged-vergessen";
    weg.textContent = "vergessen";
    weg.title = "Diese Frage und ihre Antwort aus dem Gedächtnis entfernen";
    weg.addEventListener("click", (ev) => mitKnopf(ev.target, () => gedaechtnisFrageVergessen(f)));
    li.appendChild(weg);
    fragenListe.appendChild(li);
  }
  $("ged-fragen-zahl").textContent = fragen.length ? `${fragen.length}` : "leer";
}

function gedUmfangZeigen() {
  const g = (sitzung && sitzung.gedaechtnis) || {};
  const teile = [`Gedächtnis: ${umfangKurz(g.zeichen || 0)} in ${(g.eintraege || []).length} Dokument(en)`];
  if (gedAuswahl.size) teile.push(`${gedAuswahl.size} zur Aufnahme ausgewählt`);
  // Wo der Platz liegt, haengt seit der Entscheidung der Kanzlei von der
  // Einstellung ab: entweder in der Akte selbst oder getrennt davon. Ein fest
  // eingebauter Satz wuerde in einem der beiden Faelle die Unwahrheit sagen -
  // und zwar ueber die Frage, die hier am meisten zaehlt.
  teile.push(K.gedaechtnisOrt === "akte"
    ? "gespeichert wird in der Akte selbst"
    : "gespeichert wird bei jusperfect, nicht in jurnodes");
  $("ged-umfang").textContent = teile.join(" · ");
}

/** Was faellt mit, wenn dieses Dokument aus dem Gedaechtnis geht?
 *
 * Gezaehlt, nicht geschaetzt. Eine Rueckfrage, die "vermutlich einiges" sagt,
 * hilft bei der Entscheidung nicht - und die Entscheidung laesst sich nicht
 * zurueckholen.
 *
 * Gezaehlt wird nach derselben Regel, nach der der Dienst spaeter wegnimmt:
 * Frage-Antwort-Runden und Zeitstrahleintraege fallen GANZ, sobald sie das
 * Dokument auch nur mitzitieren. Das ist strenger als noetig und Absicht -
 * ein Eintrag aus zwei Quellen stuende sonst weiter da, obwohl die Haelfte
 * seiner Grundlage fehlt.
 */
function gedaechtnisAbhaengiges(dokumentId) {
  const g = (sitzung && sitzung.gedaechtnis) || {};
  const zitiert = (x) => (x.quellen || []).some((q) => q.dokument_id === dokumentId);
  return {
    fragen: (g.fragen_antworten || []).filter(zitiert).length,
    zeitstrahl: (g.chronologie || []).filter(zitiert).length,
    sachverhalt: (g.quellen || []).some((q) => q.dokument_id === dokumentId),
  };
}

async function gedaechtnisDokumentVergessen(e) {
  const ab = gedaechtnisAbhaengiges(e.dokument_id);
  const teile = [
    `„${e.titel}" aus dem Gedächtnis entfernen?`,
    "",
    "Das fällt mit heraus:",
    `· der Auszug selbst – ${e.seiten} Seite(n), ${umfangKurz(e.zeichen)}`,
  ];
  if (ab.fragen)
    teile.push(`· ${ab.fragen} gespeicherte Frage(n), die ihn zitieren – vollständig`);
  if (ab.zeitstrahl)
    teile.push(`· ${ab.zeitstrahl} Eintrag/Einträge im Zeitstrahl – vollständig`);
  if (ab.sachverhalt)
    teile.push("· aus dem Lebenssachverhalt die Sätze, die nur auf ihm beruhen");
  if (!ab.fragen && !ab.zeitstrahl && !ab.sachverhalt)
    teile.push("· sonst nichts – auf diesen Auszug stützt sich bisher keine Antwort.");
  teile.push(
    "",
    "Die Akte in jurnodes bleibt unberührt. Entfernt wird nur, was sich",
    "jusperfect gemerkt hat.",
    "",
    "Zurücklegen ist möglich, kostet aber ein neues Einlesen – bei einem Scan",
    "mit Texterkennung. Das Abgeleitete oben kommt dadurch nicht wieder.",
    "",
    "Entfernen?");
  if (!confirm(teile.join("\n"))) return;
  const akte = encodeURIComponent(sitzung.sitzung.akte_id);
  const dok = e.dokument_id.split("/").map(encodeURIComponent).join("/");
  const gedaechtnisStand = await api("DELETE", `/api/akten/${akte}/gedaechtnis/dokumente/${dok}`);
  // Auch die offene Sitzung hat das Dokument verloren (Befund F02.3 der
  // Zweitpruefung, 05.10.2026: Sie behielt es, und die naechste Frage
  // antwortete darauf). Ohne dieses Nachladen stuende der Text weiter in der
  // linken Spalte und in den Belegen - ein Fenster, das zeigt, was es nicht
  // mehr hat.
  sitzung = await api("GET", `/api/sitzungen/${sitzung.sitzung.id}`);
  sitzung.gedaechtnis = gedaechtnisStand;
  await passagenLaden();
  // Der Zeitstrahl der Oberflaeche traegt die Eintraege aus der Analyse
  // getrennt mit. Bliebe er stehen, zeigte das Fenster weiter einen Eintrag,
  // den es im Gedaechtnis nicht mehr gibt.
  chronoAusAnalyse = chronoAusAnalyse.filter((z) => z.dokument_id !== e.dokument_id);
  gedExplorerZeichnen();
  gedaechtnisFensterZeigen();
  chronologieZeigen();
  ladeStatus();
  const nach = [];
  if (ab.fragen) nach.push(`${ab.fragen} Frage(n)`);
  if (ab.zeitstrahl) nach.push(`${ab.zeitstrahl} Zeitstrahleintrag/-einträge`);
  melden(`„${e.titel}" ist nicht mehr im Gedächtnis.`
         + (nach.length ? ` Mit entfallen: ${nach.join(", ")}.` : ""));
}

/** Das GANZE Aktengedaechtnis dieser Akte verwerfen.
 *
 * Aus der Kanzlei am 13.10.2026: Eine Akte habe bereits eine Arbeitsakte mit
 * falschen Unterlagen - ob man die loeschen koenne.
 *
 * **Einzeln ging das, ganz nicht.** Der Loeschweg bestand in der Schnittstelle
 * (`DELETE /api/akten/{akte}/gedaechtnis`) und hatte keinen Knopf. Eine
 * Funktion ohne Weg dorthin ist keine.
 *
 * **Und „Sitzung schliessen" hilft hier nicht**, auch wenn es so aussieht:
 * Beim naechsten Oeffnen legt `bei_eroeffnen` jedes Dokument des Gedaechtnisses
 * wieder in die Arbeitsakte. Was falsch im Gedaechtnis steht, kommt also
 * zurueck. Heraus muss es aus dem Gedaechtnis.
 *
 * Warum ein ganzes Verwerfen ueberhaupt gebraucht wird, und nicht nur das
 * einzelne Vergessen: Das Gedaechtnis fuehrt **Dokumentnummern** mit. Ist es
 * vor dem 08.10.2026 entstanden, kennt es die Mails und ihre Anlagen nicht -
 * und seitdem stehen die mit in der Liste. Die Nummern verschieben sich damit,
 * und ein Beleg „D47" zeigt auf ein anderes Dokument als damals. Das laesst
 * sich nicht dokumentweise richten; so ein Gedaechtnis muss neu entstehen.
 */
async function gedaechtnisGanzVerwerfen() {
  if (!sitzung) return;
  const g = (sitzung && sitzung.gedaechtnis) || {};
  const eintraege = g.eintraege || [];
  const a = sitzung.sitzung.akte;
  // Der Fall, fuer den dieser Knopf gebraucht wurde: Das Gedaechtnis ist da
  // und nicht zu lesen. Dann steht hier keine Zahl - aber der Weg ist
  // derselbe, und nur dieser eine funktioniert noch, weil das Loeschen nicht
  // liest.
  if (g.unlesbar) {
    const weg = [
      `Das Gedächtnis von ${a.aktenzeichen} verwerfen?`,
      "",
      "Es lässt sich nicht mehr einlesen; wie viel darin liegt, ist deshalb",
      "nicht zu sagen. Verworfen wird es trotzdem vollständig.",
      "",
      "Die Akte in jurnodes bleibt unberührt.",
      "",
      "Danach baut „Akte einlesen“ es neu auf. Das kostet Modellaufrufe,",
      "bei Scans zusätzlich die Texterkennung.",
      "",
      "Verwerfen?",
    ];
    if (!confirm(weg.join("\n"))) return;
    await gedaechtnisWeg();
    return;
  }
  if (!g.vorhanden) {
    melden(`Zu ${a.aktenzeichen} ist noch kein Gedächtnis gespeichert.`);
    return;
  }
  // Was weg ist, soll vor dem Klick dastehen - nicht danach. Dieselbe
  // Erwaegung wie beim einzelnen Vergessen darueber.
  const teile = [
    `Das ganze Gedächtnis von ${a.aktenzeichen} verwerfen?`,
    "",
    "Das fällt heraus:",
    `· ${eintraege.length} Dokumentauszug/-auszüge – ${umfangKurz(g.zeichen || 0)}`,
  ];
  if (g.fragen)
    teile.push(`· ${g.fragen} gespeicherte Frage(n) samt Antwort`);
  if ((g.chronologie || []).length)
    teile.push(`· ${g.chronologie.length} Eintrag/Einträge im Zeitstrahl`);
  if (g.lebenssachverhalt)
    teile.push("· der Lebenssachverhalt");
  if (g.analyse)
    teile.push("· die gespeicherte Analyse der Akte");
  teile.push(
    "",
    "Die Akte in jurnodes bleibt unberührt. Verworfen wird nur, was sich",
    "jusperfect gemerkt hat.",
    "",
    "Zurücklegen heißt: die Akte neu einlesen. Das kostet Modellaufrufe,",
    "bei Scans zusätzlich die Texterkennung. Das Abgeleitete oben kommt",
    "dadurch nicht wieder.",
    "",
    "Verwerfen?");
  if (!confirm(teile.join("\n"))) return;
  await gedaechtnisWeg();
}

/** Das Verwerfen selbst - EIN Aufruf, nicht einer je Dokument.
 *
 * Aus der Kanzlei am 13.10.2026: „Gedaechtnis verwerfen scheint nicht
 * abzuschliessen - komme ich auf das Feld, erscheint eine Sanduhr."
 *
 * Hier stand eine Schleife: erst das Gedaechtnis loeschen, dann je Dokument
 * ein DELETE an die Sitzung. Jede dieser Antworten ist eine vollstaendige
 * Sitzungsantwort, und die liest die Dokumentliste **neu bei jurnodes** -
 * Ordnerbaum und Korrespondenzverzeichnis, je Aufruf, und der Hersteller
 * laesst eine Anfrage je IP-Adresse zugleich zu. Bei fuenfzig Dokumenten
 * waren das fuenfzig Lesevorgaenge der ganzen Akte fuer einen Klick.
 *
 * Der Knopf war dabei nicht haengen geblieben - er arbeitete. Das ist der
 * unangenehmere Fall: Es sah aus wie ein Fehler und war einer, nur ein
 * anderer. Jetzt nimmt der Server die Dokumente in einem Zug mit; die
 * Oberflaeche fragt danach EINMAL den neuen Stand.
 */
async function gedaechtnisWeg() {
  const akte = encodeURIComponent(sitzung.sitzung.akte_id);
  const sid = encodeURIComponent(sitzung.sitzung.id);
  const a = sitzung.sitzung.akte;
  await api("DELETE", `/api/akten/${akte}/gedaechtnis?sitzung=${sid}`);
  sitzung = await api("GET", `/api/sitzungen/${sitzung.sitzung.id}`);
  await passagenLaden();
  // Der Zeitstrahl der Oberflaeche traegt die Eintraege aus der Analyse
  // getrennt mit. Bliebe er stehen, zeigte das Fenster einen Zeitstrahl zu
  // einem Gedaechtnis, das es nicht mehr gibt.
  chronoAusAnalyse = [];
  gedExplorerZeichnen();
  gedaechtnisFensterZeigen();
  chronologieZeigen();
  ladeStatus();
  melden(`Das Gedächtnis von ${a.aktenzeichen} ist verworfen. `
         + `„Akte einlesen" baut es neu auf.`);
}

/** Eine gespeicherte Frage samt Antwort aus dem Gedaechtnis nehmen.
 *
 * Der Server loescht nach STELLE in der Liste. Deshalb wird hier zuerst
 * frisch nachgesehen und die Stelle erst dann bestimmt: Hat in der
 * Zwischenzeit jemand an derselben Akte gearbeitet - zwei Anwaelte, zwei
 * Rechner -, zeigte die Stelle von vorhin auf eine andere Frage, und die
 * waere weg, ohne dass es jemand bemerkt.
 */
async function gedaechtnisFrageVergessen(f) {
  const frisch = await api("GET", `/api/sitzungen/${sitzung.sitzung.id}/gedaechtnis`);
  const stelle = (frisch.fragen_antworten || []).findIndex(
    (x) => x.frage === f.frage && x.antwort === f.antwort && x.zeitpunkt === f.zeitpunkt);
  if (stelle < 0) {
    sitzung.gedaechtnis = frisch;
    gedExplorerZeichnen();
    melden("Diese Frage liegt nicht mehr im Gedächtnis – jemand war schneller. "
           + "Die Ansicht steht jetzt auf dem neuen Stand.", true);
    return;
  }
  const kurz = (f.frage || "").length > 90 ? (f.frage || "").slice(0, 90) + "…" : (f.frage || "");
  const teile = [
    `„${kurz}"`,
    "",
    "Diese Frage und ihre Antwort aus dem Gedächtnis entfernen?",
    "",
    "Es fällt nur diese eine Runde heraus. Die Dokumentauszüge, der",
    "Lebenssachverhalt und der Zeitstrahl bleiben stehen.",
    "",
    "Die Akte in jurnodes bleibt unberührt.",
    "",
    "Dieselbe Frage noch einmal zu stellen kostet einen neuen Modellaufruf.",
    "",
    "Entfernen?"];
  if (!confirm(teile.join("\n"))) return;
  const akte = encodeURIComponent(sitzung.sitzung.akte_id);
  sitzung.gedaechtnis = await api("DELETE", `/api/akten/${akte}/gedaechtnis/fragen/${stelle}`);
  gedExplorerZeichnen();
  gedaechtnisFensterZeigen();
  melden("Die Frage ist nicht mehr im Gedächtnis.");
}

/** Die angehakten Dokumente holen - mit dem Balken, den es laengst gibt.
 *
 * Aus der Kanzlei am 13.10.2026: „Bei Auswahl dauert es lange, bis eingelesen
 * wird. Es waere gut, wenn hier angezeigt wird, dass das Programm arbeitet."
 *
 * Hier stand EIN Aufruf ueber alle angehakten Dokumente. Der holt jede Datei,
 * schickt jeden Scan durch die Texterkennung und schreibt alles ins
 * Gedaechtnis - bei einer ganzen Akte Minuten, und auf dem Schirm geschah
 * nichts. Der Dialog war zu, und es gab keinen Knopf mehr, an dem ein
 * Wartekreis haette haengen koennen.
 *
 * **Der Weg dafuer war schon da.** `dokumenteInPortionenLesen` ist seit dem
 * 29.09.2026 genau das: Portion fuer Portion, mit Balken, Zeitschaetzung und
 * „Anhalten". Das Dokumentfenster nimmt ihn; dieses Fenster tat es nicht.
 *
 * > Eine zweite Stelle, die dasselbe tut, hat die Verbesserung der ersten
 * > nicht. Das ist kein neuer Satz - er steht seit dem 25.09.2026 in
 * > `tests/test_starter.py`, nur fuer Startdateien.
 *
 * Gemeldet wird danach, was WIRKLICH ankam: Hier stand die Zahl der
 * Angehakten, auch wenn ein Scan unlesbar war und gar nicht hineinkam.
 */
async function gedaechtnisAufnehmen() {
  if (!gedAuswahl.size) { melden("Nichts ausgewählt."); return; }
  const ids = [...gedAuswahl];
  const vorher = ((sitzung.gedaechtnis || {}).eintraege || []).length;
  await dokumenteInPortionenLesen(ids);
  gedAuswahl = new Set();
  await passagenLaden();
  gedaechtnisFensterZeigen();
  chronologieZeigen();
  ladeStatus();
  schaetzungZeigen(sitzung.kostenschaetzung);
  const dazu = Math.max(0, ((sitzung.gedaechtnis || {}).eintraege || []).length - vorher);
  melden(dazu === ids.length
    ? `${dazu} Dokument(e) ins Gedächtnis aufgenommen.`
    : `${dazu} von ${ids.length} Dokument(en) ins Gedächtnis aufgenommen.`);
  // Was nicht hineinkam, hat einen Grund, und der steht in den Hinweisen der
  // Sitzung - nicht in einer Meldung, die nach drei Sekunden weg ist.
  if (dazu !== ids.length) hinweiseZeigen(sitzung.sitzung.hinweise || []);
}

async function chronologieAktualisieren() {
  const a = await api("POST", `/api/sitzungen/${sitzung.sitzung.id}/chronologie/aktualisieren`);
  chronoAusAnalyse = (a.chronologie || [])
    .filter((z) => z.datum && z.quellen && z.quellen.length)
    .map((z) => ({ datum: z.datum, ereignis: z.ereignis,
                   kennung: z.quellen[0].kennung, dokument_id: z.quellen[0].dokument_id }));
  if (sitzung.gedaechtnis) sitzung.gedaechtnis.chronologie = a.chronologie || [];
  chronologieZeigen();
  gedaechtnisFensterZeigen();   // sonst stünde dort weiterhin "Ereignisse 0"
  melden(a.neue_passagen
    ? `Zeitstrahl nachgetragen (${a.neue_passagen} neue Passage(n)).`
    : (a.hinweise || ["Nichts Neues."])[0]);
}

async function gedaechtnisAktualisieren() {
  // Ist das Gedaechtnis ausgeschaltet, sagt der Klick, wie es wieder angeht.
  //
  // Aus der Kanzlei am 25.09.2026: "der Button Aktengedaechtnis ist jetzt
  // komplett weg, sodass man gar nicht nachtraeglich das Aktengedaechtnis
  // erstellen koennte." Der Knopf steht seitdem fest da - etwas, das spurlos
  // verschwindet, sieht aus wie ein Fehler, und niemand erfaehrt, dass es die
  // Sache ueberhaupt gibt.
  if (!K.gedaechtnisAktiv) {
    melden("Das Gedächtnis ist ausgeschaltet. Es lässt sich in der "
           + "Startdatei wieder einschalten (JUSPERFECT_GEDAECHTNIS). "
           + "Ohne es wird jede Akte bei jeder Sitzung neu eingelesen.", true);
    return;
  }
  const g = await api("POST", `/api/sitzungen/${sitzung.sitzung.id}/gedaechtnis/aktualisieren`);
  sitzung.gedaechtnis = g;
  const karte = threadKarte("ai");
  const titel = document.createElement("div"); titel.className = "titelzeile"; titel.textContent = "Gedächtnis aktualisiert";
  const inhalt = document.createElement("div"); inhalt.className = "inhalt";
  if (g.lebenssachverhalt) antworttext(inhalt, g.lebenssachverhalt);
  else inhalt.textContent = "Noch kein belegter Lebenssachverhalt vorhanden.";
  karte.append(titel, inhalt);
  melden(g.offene_dokumente ? `${g.offene_dokumente} Dokument(e) warten noch auf Verarbeitung.` : "Alle neuen Dokumente sind verarbeitet.");
  ladeStatus();
}

function threadKarte(klasse) {
  // Eine neue Karte waehrend einer laufenden Suche waere versteckt, sobald
  // sie nicht zu den Suchwoertern passt: Der Bearbeiter fragt - und sieht
  // nichts. Wer weiterarbeitet, hat die Suche beendet.
  const suchfeld = $("chat-suche");
  if (suchfeld && suchfeld.value) chatSucheZeigen(false);
  const willkommen = $("thread").querySelector(".willkommen");
  if (willkommen) willkommen.remove();
  const karte = document.createElement("div"); karte.className = "karte-c " + klasse;
  const thread = $("thread");
  thread.appendChild(karte);
  // Ans Ende des Verlaufs, nicht an die Unterkante der Karte: Sonst schoebe
  // sich die neue Karte genau unter die schwebende Eingabe.
  thread.scrollTo({ top: thread.scrollHeight, behavior: "smooth" });
  return karte;
}

// ── Ein Dokument von Hand in die Arbeitsakte ───────────────────────
//
// Aus der Kanzlei am 16.10.2026: „Ich haette auch gerne das Dokument direkt
// in den Chat eingefuegt, hierfuer fehlt aber eine Funktion."
//
// Es ist der Weg fuer das Blatt, das gerade nicht in der E-Akte liegt: das
// soeben eingegangene Fax, der Ausdruck, der Abschnitt, den die Texterkennung
// nicht hergab. Gelesen wird es wie jedes andere Dokument - Seiten, Passagen,
// Kennungen -, damit die Belegpflicht auch dafuer traegt.
//
// Die Datei geht base64-kodiert hinaus und nicht als Formulardatei. Das spart
// ein weiteres Paket auf dem Rechner der Kanzlei; fuer ein Blatt aus einer
// Akte faellt die Kodierung nicht ins Gewicht.

/** Die gewaehlte Datei als base64 - ohne den "data:"-Vorspann. */
function dateiAlsText(datei) {
  return new Promise((erfuellen, ablehnen) => {
    const leser = new FileReader();
    leser.onerror = () => ablehnen(new Error("Die Datei lie\u00df sich nicht lesen."));
    leser.onload = () => erfuellen(String(leser.result).split(",")[1] || "");
    leser.readAsDataURL(datei);
  });
}

function einfuegenFehler(text) {
  const p = $("einfuegen-fehler");
  if (!p) return;
  p.textContent = text || "";
  p.hidden = !text;
}

/** Den Dialog aufmachen - leer, oder mit einer schon abgelegten Datei. */
function einfuegenDialogOeffnen(datei) {
  if (!sitzung) { melden("Erst eine Akte \u00f6ffnen.", true); return; }
  const dialog = $("einfuegen-dialog");
  if (!dialog) return;
  einfuegenFehler("");
  $("einfuegen-text").value = "";
  const feld = $("einfuegen-datei");
  feld.value = "";
  einfuegenDatei = datei || null;
  // Eine fallen gelassene Datei laesst sich einem <input type=file> nicht
  // zuweisen; sie wird daneben gehalten. Dass sie da ist, muss man sehen.
  $("einfuegen-titel").value = datei ? datei.name.replace(/\.[^.]+$/, "") : "";
  const name = $("einfuegen-dateiname");
  name.textContent = datei ? datei.name : "";
  name.hidden = !datei;
  dialog.showModal();
}

/** Die fallen gelassene Datei - sie passt in kein Dateifeld. */
let einfuegenDatei = null;

async function dokumentEinfuegen() {
  const datei = einfuegenDatei || ($("einfuegen-datei").files || [])[0] || null;
  const text = ($("einfuegen-text").value || "").trim();
  const titel = ($("einfuegen-titel").value || "").trim();
  if (!datei && !text) {
    einfuegenFehler("Bitte eine Datei w\u00e4hlen oder Text einf\u00fcgen.");
    $("einfuegen-dialog").showModal();
    return;
  }
  laeuft(datei ? `\u201E${datei.name}\u201C wird gelesen \u2026` : "Der Text wird gelesen \u2026");
  let antwort;
  try {
    antwort = await api("POST", `/api/sitzungen/${sitzung.sitzung.id}/dokumente/einfuegen`,
      datei
        ? { titel, dateiname: datei.name, inhalt_b64: await dateiAlsText(datei) }
        : { titel, text });
  } catch (e) {
    melden(e.message, true);
    return;
  } finally {
    einfuegenDatei = null;
  }
  sitzung = antwort;
  await passagenLaden();
  schaetzungZeigen(sitzung.kostenschaetzung);
  ladeStatus();
  einfuegenKarte(antwort.eingefuegt, (antwort.sitzung && antwort.sitzung.hinweise) || []);
  melden("Eingef\u00fcgt.");
}

/** Die Karte im Verlauf: was eingefuegt wurde, und wie man es wieder loswird. */
function einfuegenKarte(eintrag, hinweise) {
  if (!eintrag) return;
  const karte = threadKarte("ai eingefuegt");
  const titel = document.createElement("div"); titel.className = "titelzeile";
  titel.textContent = `Eingef\u00fcgt: ${eintrag.titel}`;
  karte.appendChild(titel);
  const inhalt = document.createElement("div"); inhalt.className = "inhalt";
  const zeile = document.createElement("p");
  zeile.textContent = `${eintrag.seiten} Seite(n), ${(eintrag.zeichen || 0).toLocaleString("de-DE")} Zeichen`
    + (eintrag.ocr ? ", durch die Texterkennung gegangen" : "")
    + `. Die Fundstellen tragen D${eintrag.nummer}.`;
  inhalt.appendChild(zeile);
  const hb = hinweiseBlock(hinweise); if (hb) inhalt.appendChild(hb);
  const weg = document.createElement("button");
  weg.type = "button"; weg.className = "mini leise";
  weg.textContent = "Wieder herausnehmen";
  weg.addEventListener("click", () => mitKnopf(weg, () => eingefuegtesEntfernen(eintrag)));
  inhalt.appendChild(weg);
  karte.appendChild(inhalt);
}

async function eingefuegtesEntfernen(eintrag) {
  if (!confirm(`\u201E${eintrag.titel}\u201C aus der Arbeitsakte nehmen? Der Text wird gel\u00f6scht.`)) return;
  sitzung = await api("DELETE",
    `/api/sitzungen/${sitzung.sitzung.id}/dokumente/${encodeURIComponent(eintrag.dokument_id)}`);
  await passagenLaden();
  schaetzungZeigen(sitzung.kostenschaetzung);
  ladeStatus();
  melden("Herausgenommen.");
}

/** Eine Datei auf den Verlauf fallen lassen - derselbe Weg, kuerzer. */
function einfuegenPerAblegen() {
  const thread = $("thread");
  if (!thread) return;
  const halt = (e) => { e.preventDefault(); e.stopPropagation(); };
  thread.addEventListener("dragover", (e) => { halt(e); thread.classList.add("ablegen"); });
  thread.addEventListener("dragleave", (e) => { halt(e); thread.classList.remove("ablegen"); });
  thread.addEventListener("drop", (e) => {
    halt(e);
    thread.classList.remove("ablegen");
    const datei = ((e.dataTransfer || {}).files || [])[0];
    if (datei) einfuegenDialogOeffnen(datei);
  });
}

function nutzerkarte(text) {
  const karte = threadKarte("user");
  const who = document.createElement("div"); who.className = "who"; who.textContent = "Bearbeiter";
  const inhalt = document.createElement("div"); inhalt.className = "inhalt"; inhalt.textContent = text;
  karte.append(who, inhalt);
}

// Fügt Text mit klickbaren [Q: ...]-Belegen in einen Container ein.
// Textsatz für Modellantworten
// ----------------------------
// Sprachmodelle schreiben Markdown, ob man sie darum bittet oder nicht: „##"
// für eine Überschrift, „**" für Fettes, „-" für eine Aufzählung. Wer den
// Text roh einsetzt, liest Rauten und Sternchen mit - in einem Schriftsatz
// eine Zumutung.
//
// Gesetzt wird bewusst wenig: Überschriften, Aufzählungen, Fettes, Kursives,
// Code. Tabellen und Bilder fehlen mit Absicht. Was hier nicht steht, bleibt
// als Text stehen und ist damit lesbar - anders als bei einem Satz, der an
// unbekannter Auszeichnung zerbricht.
//
// Gebaut wird ausschliesslich mit createElement und Textknoten, nie mit
// innerHTML. Der Text kommt vom Modell und damit mittelbar aus der Akte; er
// darf niemals als Markup ausgeführt werden.
const AUFZAEHLUNG = /^\s{0,3}([-*•])\s+(.*)$/;
const NUMMERIERT = /^\s{0,3}(\d{1,2})[.)]\s+(.*)$/;
const UEBERSCHRIFT = /^\s{0,3}(#{1,6})\s+(.*)$/;
const TRENNLINIE = /^\s{0,3}([-*_])\1{2,}\s*$/;
const INLINE = /(\*\*|__)(.+?)\1|(\*|_)(?!\s)(.+?)(?<!\s)\3|`([^`]+)`/g;

function inlineMitBelegen(ziel, text) {
  // Erst die Auszeichnung, dann die Fundstellen: Ein „[Q: D1-S1-P1]" steht
  // nie innerhalb von Sternchen, umgekehrt kann Fettes mitten im Satz stehen.
  let letzte = 0, m;
  INLINE.lastIndex = 0;
  while ((m = INLINE.exec(text)) !== null) {
    if (m.index > letzte) textMitBelegen(ziel, text.slice(letzte, m.index));
    let el;
    if (m[2] !== undefined) { el = document.createElement("strong"); textMitBelegen(el, m[2]); }
    else if (m[4] !== undefined) { el = document.createElement("em"); textMitBelegen(el, m[4]); }
    else { el = document.createElement("code"); el.textContent = m[5]; }
    ziel.appendChild(el);
    letzte = m.index + m[0].length;
  }
  if (letzte < text.length) textMitBelegen(ziel, text.slice(letzte));
}

function antworttext(ziel, text) {
  const zeilen = String(text || "").split(/\r?\n/);
  let absatz = [], liste = null;

  const absatzSchliessen = () => {
    if (!absatz.length) return;
    const p = document.createElement("p");
    inlineMitBelegen(p, absatz.join(" "));
    ziel.appendChild(p);
    absatz = [];
  };
  const listeSchliessen = () => { liste = null; };
  const alles = () => { absatzSchliessen(); listeSchliessen(); };

  for (const zeile of zeilen) {
    if (!zeile.trim()) { alles(); continue; }
    if (TRENNLINIE.test(zeile)) { alles(); continue; }

    const ueber = UEBERSCHRIFT.exec(zeile);
    if (ueber) {
      alles();
      // Immer h4: Die Karte hat schon eine Überschrift, und ein h1 mitten im
      // Gespräch verschöbe die Gliederung der Seite.
      const h = document.createElement("h4"); h.className = "abschnitt";
      inlineMitBelegen(h, ueber[2]);
      ziel.appendChild(h);
      continue;
    }

    const punkt = AUFZAEHLUNG.exec(zeile) || NUMMERIERT.exec(zeile);
    if (punkt) {
      absatzSchliessen();
      const nummeriert = !AUFZAEHLUNG.test(zeile);
      if (!liste || liste.nummeriert !== nummeriert) {
        const el = document.createElement(nummeriert ? "ol" : "ul");
        el.className = "aufzaehlung";
        ziel.appendChild(el);
        liste = { el, nummeriert };
      }
      const li = document.createElement("li");
      inlineMitBelegen(li, punkt[2]);
      liste.el.appendChild(li);
      continue;
    }

    listeSchliessen();
    absatz.push(zeile.trim());
  }
  alles();
}

// Die harten Angaben im Antworttext - genau die, die man nachschlagen will.
// Dieselben Muster wie in services/fundstelle.py; stimmen sie nicht ueberein,
// ist der Klick hier ohne Wirkung, aber nie falsch: Er springt immer auf die
// Fundstelle, die hinter dem Satz steht.
const ANGABE = /\b\d{1,2}\.\d{1,2}\.\d{2,4}\b|\b\d{1,3}(?:\.\d{3})*(?:,\d{1,2})?\s?(?:EUR|€)|\b\d{1,3}(?:\.\d{3})*,\d{1,2}\b|§+\s?\d+[a-z]?/g;

// ── Gesetzestexte: derselbe Weg wie Haufe ────────────────────────────────────
//
// Aus der Kanzlei am 25.09.2026: "wenn die KI argumentiert, kann man dann bei
// Belegen schnell den Gesetzestext nachlesen und schauen, ob man das Gesetz so
// auslegen kann." Und: "wie hast du Recherche Haufe eingebunden, genauso
// wollte ich das auch mit den Gesetzestexten machen."
//
// Also ein Sprung in den Browser, nichts im Programmordner. Ein Modell
// erfindet Paragrafen; der amtliche Wortlaut nicht. Wer ihn in zwei Sekunden
// danebenlegen kann, prueft auch.
//
// Erkannt wird "§ 634 Abs. 1 Nr. 4 BGB": Nummer, beliebige Zusaetze, dann das
// Kuerzel. Das Kuerzel braucht MINDESTENS ZWEI Grossbuchstaben - sonst wuerde
// "§ 634 Die Frist" als Gesetz gelesen. Lieber ein Verweis weniger als einer,
// der ins Leere fuehrt.
const GESETZESVERWEIS =
  /§§?\s?(\d+[a-z]?)((?:\s+(?:Abs\.|Absatz|Nr\.|Satz|S\.)\s?\d+[a-z]?)*)\s+([A-ZÄÖÜ][A-Za-zÄÖÜ]{1,14})\b/g;

/** Die Adresse des Paragrafen - oder "" , wenn sie sich nicht bilden laesst.
 *
 * Das Muster ist einstellbar und wurde am lebenden Server geprueft, nicht
 * geraten (JUSPERFECT_GESETZE_MUSTER). Ist es leer, gibt es keinen Sprung;
 * dann wird nur die Startseite geoeffnet - wie bei Haufe ohne Suchparameter.
 */
function gesetzesAdresse(gesetz, paragraf) {
  const cfg = K.gesetze || {};
  if (!cfg.url) return "";
  if (!cfg.muster) return cfg.url;
  const pfad = cfg.muster
    .replace("{gesetz}", encodeURIComponent(gesetz.toLowerCase()))
    .replace("{paragraf}", encodeURIComponent(paragraf.toLowerCase()));
  return cfg.url.replace(/\/+$/, "") + "/" + pfad.replace(/^\/+/, "");
}

/** Hat das Kuerzel genug Grossbuchstaben, um ein Gesetz zu sein? */
function sichtbaresKuerzel(wort) {
  return (wort.match(/[A-ZÄÖÜ]/g) || []).length >= 2;
}

/** Das kleine Zeichen hinter einem Paragrafen: fuehrt zum Wortlaut. */
function gesetzesKnopf(gesetz, paragraf, ganzerVerweis) {
  const ziel = gesetzesAdresse(gesetz, paragraf);
  if (!ziel) return null;
  const a = document.createElement("a");
  a.className = "gesetzeslink";
  a.href = ziel;
  a.target = "_blank";
  a.rel = "noopener";
  a.textContent = "Wortlaut";
  a.title = `${ganzerVerweis} auf gesetze-im-internet.de nachlesen`;
  // Der Verweis kommt zusaetzlich in die Zwischenablage. Fuehrt die Adresse
  // ins Leere - ein Gesetz, das dort anders heisst -, ist die Suche auf der
  // Seite dann ein Einfuegen entfernt. Derselbe Gedanke wie bei Haufe.
  a.addEventListener("click", () => {
    try { navigator.clipboard.writeText(ganzerVerweis); } catch (e) { /* ohne */ }
  });
  return a;
}

function angabenAnklickbar(ziel, teil, kennung) {
  // Aus der Kanzlei: "dass man vielleicht einfach auf die Information drauf
  // tippen kann und genau sieht, wo sie im Sachverhalt steht."
  //
  // Ohne Fundstelle gibt es dieses Tippen nicht - Gesetzesverweise sind davon
  // aber unabhaengig: Der Wortlaut eines Paragrafen steht nicht in der Akte.
  if (!kennung || !passagenIndex[kennung]) { gesetzeAnklickbar(ziel, teil); return; }
  const aussage = teil;
  let letzte = 0, m;
  ANGABE.lastIndex = 0;
  while ((m = ANGABE.exec(teil)) !== null) {
    if (m.index > letzte) gesetzeAnklickbar(ziel, teil.slice(letzte, m.index));
    const angabe = document.createElement("span");
    angabe.className = "angabe";
    angabe.textContent = m[0];
    angabe.title = `Im Dokument nachsehen (${kennung})`;
    angabe.addEventListener("click", () => passageMarkieren(kennung, null, aussage));
    ziel.appendChild(angabe);
    letzte = m.index + m[0].length;
    // Steht hinter dem Paragrafen ein Gesetzeskuerzel, kommt hinter den REST
    // dieses Verweises der Sprung zum Wortlaut. Der Klick auf die Nummer
    // selbst bleibt, was er war: der Weg ins Dokument. Ein Klick kann nicht
    // zweierlei tun, also stehen hier zwei Dinge nebeneinander.
    GESETZESVERWEIS.lastIndex = m.index;
    const g = GESETZESVERWEIS.exec(teil);
    if (g && g.index === m.index && sichtbaresKuerzel(g[3])) {
      ziel.appendChild(document.createTextNode(teil.slice(letzte, g.index + g[0].length)));
      letzte = g.index + g[0].length;
      const knopf = gesetzesKnopf(g[3], g[1], g[0]);
      if (knopf) ziel.appendChild(knopf);
    }
  }
  if (letzte < teil.length) gesetzeAnklickbar(ziel, teil.slice(letzte));
}

/** Gesetzesverweise in einem Stück Text, ohne Bezug zu einer Fundstelle. */
function gesetzeAnklickbar(ziel, teil) {
  if (!(K.gesetze || {}).url) { ziel.appendChild(document.createTextNode(teil)); return; }
  let letzte = 0, m;
  GESETZESVERWEIS.lastIndex = 0;
  while ((m = GESETZESVERWEIS.exec(teil)) !== null) {
    if (!sichtbaresKuerzel(m[3])) continue;
    ziel.appendChild(document.createTextNode(teil.slice(letzte, m.index + m[0].length)));
    letzte = m.index + m[0].length;
    const knopf = gesetzesKnopf(m[3], m[1], m[0]);
    if (knopf) ziel.appendChild(knopf);
  }
  if (letzte < teil.length) ziel.appendChild(document.createTextNode(teil.slice(letzte)));
}

function textMitBelegen(ziel, text) {
  let letzte = 0, m;
  ZITAT.lastIndex = 0;
  while ((m = ZITAT.exec(text)) !== null) {
    const kennungenRoh = m[1].split(",").map((k) => k.trim());
    const erste = kennungenRoh.find((k) => passagenIndex[k]);
    // Der Text VOR dem Beleg ist die Aussage, die er traegt - seine Angaben
    // gehoeren also zu dieser Fundstelle, und sie ist es auch, die den Klick
    // an die richtige Stelle fuehrt.
    const aussage = text.slice(letzte, m.index);
    // Das Leerzeichen VOR der Fundstelle gehoert zur Fundstelle und nicht zum
    // Satz. Wird sie ausgeblendet, stuende sonst "… geschlossen ." da - mit
    // einer Luecke vor dem Punkt. Dieselbe Regel wie in `ohneBelege`.
    const vorlauf = (aussage.match(/[ \t]*$/) || [""])[0];
    const satz = vorlauf ? aussage.slice(0, aussage.length - vorlauf.length) : aussage;
    if (satz) angabenAnklickbar(ziel, satz, erste);
    // Eine Gruppe je Fundstelle: Sie ist es, die der Schalter ausblendet -
    // samt Leerzeichen davor und samt der Trennzeichen zwischen zwei Marken.
    const gruppe = document.createElement("span");
    gruppe.className = "belegstelle";
    if (vorlauf) gruppe.appendChild(document.createTextNode(vorlauf));
    const kennungen = m[1].split(",");
    kennungen.forEach((roh, i) => {
      const kennung = roh.trim();
      const chip = document.createElement("span");
      const bekannt = !!passagenIndex[kennung];
      chip.className = "beleg" + (bekannt ? "" : " fehlt");
      chip.textContent = bekannt ? kennung : "ohne Beleg";
      if (bekannt) chip.addEventListener("click", () => passageMarkieren(kennung, chip, aussage));
      gruppe.appendChild(chip);
      // Zwischen zwei Fundstellen ein Leerzeichen, hinter der letzten keines:
      // Sonst steht im Satz "… zu [Beleg] ." - der Punkt rutscht ab.
      if (i < kennungen.length - 1) gruppe.appendChild(document.createTextNode(" "));
    });
    ziel.appendChild(gruppe);
    letzte = m.index + m[0].length;
  }
  if (letzte < text.length) ziel.appendChild(document.createTextNode(text.slice(letzte)));
}

function fusszeile(ergebnis) {
  const fuss = document.createElement("div"); fuss.className = "fuss";
  const teile = [];
  if (ergebnis.modell) teile.push(ergebnis.modell);
  if (ergebnis.kosten) teile.push(`${(ergebnis.kosten.eingabe_tokens + ergebnis.kosten.ausgabe_tokens)} Token`,
    `${ergebnis.kosten.betrag_eur.toFixed(4)} €`);
  for (const t of teile) { const s = document.createElement("span"); s.textContent = t; fuss.appendChild(s); }
  return fuss;
}

function hinweiseBlock(hinweise) {
  if (!hinweise || !hinweise.length) return null;
  const box = document.createElement("div"); box.className = "hinweise";
  for (const h of hinweise) { const d = document.createElement("div"); d.className = "h"; d.textContent = h; box.appendChild(d); }
  return box;
}

// ── Promptbibliothek ───────────────────────────────────────────────────────
//
// Aus der Kanzlei am 13.10.2026, in drei Schritten:
//
//   "Koennen wir noch eine Promptbibliothek anlegen. Diese fragt aber erst
//    nach dem Rechtsgebiet."
//   "Kann ich die Promptbibliothek nicht waehrend der Arbeit fuellen?"
//   "Promptbibliothek neu und dann Ueberschrift und Prompt eintragen -
//    einige sind schon vorher eingetragen."
//
// Nach dem Rechtsgebiet fragt deshalb niemand: Es steht in der Akte
// (jur|nodes: lawCategory) und kommt mit der Sitzung mit. In der Leiste steht
// die Ueberschrift, ins Eingabefeld kommt der Text - ein brauchbarer Prompt
// ist mehrere Zeilen lang und taugt nicht als Knopfbeschriftung.

/** Die zuletzt abgeschickte Frage - sie fuellt den Dialog vor. */
let letzteGestellteFrage = "";

/** Was zuletzt vom Server kam; der Dialog braucht das Rechtsgebiet. */
let bibliothekStand = null;

function bibHinweis(text) {
  const p = $("bib-hinweis");
  if (!p) return;
  p.textContent = text || "";
  p.hidden = !text;
}

/** Welches Rechtsgebiet gerade in der Leiste steht. "" = das der Akte. */
let bibGebietswahl = "";

/** Ist die ganze Bibliothek aufgeklappt? Zugeklappt ist die Voreinstellung.
 *
 * Aus der Kanzlei am 14.10.2026: "Promptbibliothek unten versperrt den
 * Chat." Vier Gruppen standen dauerhaft ueber dem Eingabefeld, auch wenn
 * gerade nur gefragt wurde. Wer sie aufklappt, findet sie beim naechsten
 * Mal offen - und wer sie zumacht, hat sie zu.
 */
function bibLadeHerstellen() {
  const kasten = $("bibliothek");
  if (!kasten) return;
  let offen = false;
  try { offen = localStorage.getItem("jusperfect.bib.offen") === "ja"; }
  catch (e) { /* dann eben zu */ }
  kasten.open = offen;
  kasten.addEventListener("toggle", () => {
    try { localStorage.setItem("jusperfect.bib.offen", kasten.open ? "ja" : "nein"); }
    catch (e) { /* Bequemlichkeit, keine Arbeit */ }
  });
}

/** Welche Reiter zugeklappt sind - je Gruppe, ueber die Sitzung hinaus. */
function bibZu() {
  try {
    return new Set(JSON.parse(localStorage.getItem("jusperfect.bib.zu") || "[]"));
  } catch (e) { return new Set(); }
}

function bibZuMerken(menge) {
  // Der Stand der Reiter ist Bequemlichkeit und nicht Arbeit: Faellt der
  // Speicher aus (privates Fenster, gesperrte Seitendaten), stehen sie beim
  // naechsten Mal eben alle offen. Kein Grund fuer eine Meldung.
  try { localStorage.setItem("jusperfect.bib.zu", JSON.stringify([...menge])); }
  catch (e) { /* dann eben nicht */ }
}

/** Die Leiste aus einer Antwort des Servers zeichnen - ein Reiter je Gruppe.
 *
 * Aus der Kanzlei am 14.10.2026: "Mit ausklappbaren Reitern und Rechtsgebiet
 * wechseln."
 *
 * Ausklappbar, weil neununddreissig Prompts in vier Gruppen auf einmal keine
 * Auswahl mehr sind, sondern eine Liste, die man durchsuchen muesste. Wer
 * eine Gruppe zuklappt, hat sie beim naechsten Mal wieder zu.
 */
function bibliothekZeichnen(daten) {
  bibliothekStand = daten;
  const kasten = $("bibliothek");
  if (!kasten) return;
  kasten.hidden = false;

  // Wie viel dahintersteckt, steht an der Ueberschrift - sonst muesste man
  // aufklappen, um zu sehen, ob sich das Aufklappen lohnt.
  const gesamt = (daten.gruppen || []).reduce((summe, g) => summe + (g.eintraege || []).length, 0);
  $("bib-anzahl").textContent = gesamt ? `${gesamt} Prompts` : "noch leer";

  // Die Wahl des Rechtsgebiets. Das der Akte steht als solches benannt da -
  // sonst weiss nach dem Wechseln niemand mehr, wozu die Akte gehoert.
  const wahl = $("bib-gebietswahl");
  wahl.replaceChildren();
  for (const gebiet of (daten.gebiete || [])) {
    const o = document.createElement("option");
    o.value = gebiet;
    o.textContent = gebiet + (gebiet === daten.gebiet_der_akte ? " (aus der Akte)" : "");
    wahl.appendChild(o);
  }
  wahl.value = daten.rechtsgebiet;

  const marke = $("bib-gebiet");
  if (daten.gewaehlt) {
    marke.textContent = "nicht das Gebiet dieser Akte";
    marke.title = "Die Akte gehört zu „" + daten.gebiet_der_akte
                + "“. Was Sie hier ablegen, landet unter „" + daten.rechtsgebiet + "“.";
    marke.hidden = false;
  } else {
    marke.textContent = daten.aus_akte ? "" : "jur|nodes nennt zu dieser Akte keines";
    marke.hidden = !marke.textContent;
  }

  const liste = $("bib-liste");
  liste.replaceChildren();
  const gruppen = (daten.gruppen || []).filter((g) => (g.eintraege || []).length);
  if (!gruppen.length) {
    const leer = document.createElement("span");
    leer.className = "bib-leer";
    leer.textContent = "Zu „" + daten.rechtsgebiet + "“ ist noch nichts abgelegt. "
      + "Ein Prompt, der sich bewährt hat, kommt über „+ Neu\u201c hierher.";
    liste.appendChild(leer);
    return;
  }
  const zu = bibZu();
  for (const gruppe of gruppen) liste.appendChild(bibReiter(gruppe, zu));
}

/** Ein Reiter: Beschriftung mit Anzahl, darunter die Knöpfe. */
function bibReiter(gruppe, zu) {
  const reiter = document.createElement("details");
  reiter.className = "bib-gruppe";
  reiter.open = !zu.has(gruppe.name);
  reiter.addEventListener("toggle", () => {
    const stand = bibZu();
    if (reiter.open) stand.delete(gruppe.name); else stand.add(gruppe.name);
    bibZuMerken(stand);
  });

  const kopf = document.createElement("summary"); kopf.className = "bib-gruppenname";
  kopf.textContent = `${gruppe.name} (${gruppe.eintraege.length})`;
  if (gruppe.basis) {
    kopf.textContent += " · mit Vorspann";
    kopf.title = "Zu dieser Gruppe gehört ein gemeinsamer Vorspann. "
               + "Er kommt sichtbar mit ins Eingabefeld.";
  }
  reiter.appendChild(kopf);

  const zeile = document.createElement("div"); zeile.className = "bib-chips";
  for (const eintrag of gruppe.eintraege) {
    const chip = document.createElement("span");
    chip.className = "bib-chip" + (eintrag.mitgeliefert ? " mitgeliefert" : "");
    const nehmen = document.createElement("button");
    nehmen.type = "button"; nehmen.className = "bib-nehmen";
    // textContent, nie als HTML: In einem abgelegten Prompt kann alles stehen.
    nehmen.textContent = eintrag.titel;
    nehmen.title = (eintrag.mitgeliefert ? "Mitgeliefert. " : "")
                 + "In das Eingabefeld übernehmen:\n\n" + eintrag.text;
    const ganz = (gruppe.basis ? gruppe.basis + "\n\n" : "") + eintrag.text;
    nehmen.addEventListener("click", () => {
      const feld = $("frage");
      feld.value = ganz;
      feld.focus();
      // Der Blick gehört ans Ende - dorthin, wo das eigentliche Modul steht.
      // Ohne das stünde der Vorspann im Bild und das Modul nicht.
      feld.setSelectionRange(ganz.length, ganz.length);
      feld.scrollTop = feld.scrollHeight;
      bibHinweis(gruppe.basis
        ? `Der gemeinsame Vorspann „${gruppe.name}“ steht mit im Feld. Er ist zu lesen und zu ändern.`
        : "");
    });
    const weg = document.createElement("button");
    weg.type = "button"; weg.className = "bib-weg";
    weg.textContent = "✕";
    weg.title = eintrag.mitgeliefert
      ? "Diesen mitgelieferten Prompt ausblenden"
      : "Diesen Prompt entfernen";
    weg.setAttribute("aria-label", "Prompt aus der Leiste nehmen");
    weg.addEventListener("click", () => mitKnopf(weg, () => bibVergessen(eintrag.titel)));
    chip.append(nehmen, weg);
    zeile.appendChild(chip);
  }
  reiter.appendChild(zeile);
  return reiter;
}

async function bibliothekLaden() {
  if (!sitzung || !sitzung.sitzung) return;
  try {
    bibliothekZeichnen(await api("GET", `/api/sitzungen/${sitzung.sitzung.id}/prompts`
      + (bibGebietswahl ? "?rechtsgebiet=" + encodeURIComponent(bibGebietswahl) : "")));
  } catch (e) {
    // Eine Bibliothek, die sich nicht lesen laesst, darf die Akte nicht
    // aufhalten: Sie ist Zugabe, der Chat ist die Arbeit.
    const kasten = $("bibliothek");
    if (kasten) kasten.hidden = false;
    $("bib-liste").replaceChildren();
    bibHinweis(e.message);
  }
}

/** Der Dialog "+ Neu" - vorgefuellt mit dem, woran gerade gearbeitet wird.
 *
 * Vorgefuellt, weil die Bibliothek waehrend der Arbeit waechst: Man legt
 * einen Prompt in dem Augenblick ab, in dem seine Antwort getaugt hat. Der
 * Text steht trotzdem zum Lesen und Aendern da - er ueberdauert die Akte,
 * und eine Frage aus der Arbeit kann einen Namen enthalten.
 */
function bibNeu() {
  const dialog = $("prompt-dialog");
  if (!dialog) return;
  const vorlage = ($("frage").value || "").trim() || letzteGestellteFrage || "";
  $("prompt-text").value = vorlage;
  $("prompt-titel").value = "";
  const stand = bibliothekStand || {};
  $("prompt-gebiet").textContent = stand.gewaehlt
    ? `Wird abgelegt unter „${stand.rechtsgebiet}“ – die Akte gehört zu „${stand.gebiet_der_akte}“.`
    : (stand.aus_akte
       ? `Rechtsgebiet dieser Akte: ${stand.rechtsgebiet}`
       : "Diese Akte nennt kein Rechtsgebiet – der Prompt landet in der gemeinsamen Liste.");
  bibHinweis("");
  dialog.showModal();
  ($("prompt-titel")).focus();
}

async function bibAblegen() {
  const titel = ($("prompt-titel").value || "").trim();
  const text = ($("prompt-text").value || "").trim();
  if (!text) { bibHinweis("Ohne Prompt gibt es nichts abzulegen."); return; }
  bibliothekZeichnen(await api("POST", `/api/sitzungen/${sitzung.sitzung.id}/prompts`,
                               { titel, text, rechtsgebiet: bibGebietswahl }));
  melden("In der Bibliothek abgelegt.");
}

async function bibVergessen(titel) {
  bibliothekZeichnen(await api("POST", `/api/sitzungen/${sitzung.sitzung.id}/prompts/vergessen`,
                               { titel, rechtsgebiet: bibGebietswahl }));
  bibHinweis("");
}

async function frageStellen() {
  const frage = $("frage").value.trim();
  if (!frage) return;
  $("frage").value = "";
  bibHinweis("");
  // Der Chat aendert den Entwurf, wenn der Umschalter an ist. Sichtbar
  // umgeschaltet und nicht heimlich: Wer eine Frage tippt und damit
  // versehentlich seinen Entwurf umschreibt, hat den Entwurf verloren, den
  // er gerade richtig bekommen hatte.
  if (entwurfAendernAn && entwurfStand) return entwurfAendern(frage);
  letzteGestellteFrage = frage;
  nutzerkarte(frage);
  const karte = threadKarte("ai");
  const who = document.createElement("div"); who.className = "who"; who.textContent = "jusperfect";
  const inhalt = document.createElement("div"); inhalt.className = "inhalt";
  const strom = document.createElement("p"); strom.className = "stromtext"; strom.textContent = "";
  inhalt.appendChild(strom); karte.append(who, inhalt);
  const thread = $("thread");

  const resp = await fetch(K.apiBasis + `/api/sitzungen/${sitzung.sitzung.id}/frage/stream`, {
    method: "POST", headers: kopfzeilen(), body: JSON.stringify({ frage }),
  });
  if (!resp.ok || !resp.body) {
    let f = null; try { f = await resp.json(); } catch (e) {}
    strom.remove(); throw new Error((f && f.fehler) || `Fehler ${resp.status}`);
  }

  // Es strömt nur Geprüftes (Befund F05 der Zweitprüfung, 05.10.2026).
  //
  // Vorher stand hier der Rohtext: schönes Schreibgefühl, und der Bearbeiter
  // sah eine Aussage, die der Abschlussfilter gleich darauf zurückhielt. Die
  // Zusage lautet "entfernen, nicht zeigen" - ein Text, der erst dasteht und
  // dann verschwindet, ist gezeigt worden.
  //
  // Bis zur ersten abgeschlossenen Aussage steht deshalb nur da, DASS
  // gearbeitet wird. Danach kommt der geprüfte Stand, und am Ende ersetzt ihn
  // die Endfassung mit klickbaren Fundstellen.
  let gepruefteAntwort = false;   // kam ein "fertig"-Ereignis?
  const finalisiere = (antwort) => {
    gepruefteAntwort = true;
    belegeMerken(antwort.quellen);
    strom.remove();
    antworttext(inhalt, antwort.text);
    const hb = hinweiseBlock(antwort.hinweise); if (hb) karte.appendChild(hb);
    karte.appendChild(fusszeile(antwort));
    thread.scrollTop = thread.scrollHeight;
  };
  const verarbeite = (zeile) => {
    if (!zeile.trim()) return;
    let ev; try { ev = JSON.parse(zeile); } catch (e) { return; }
    if (ev.type === "fortschritt") {
      // Nur wenn noch nichts Geprüftes dasteht - sonst flackerte der Text.
      if (!strom.dataset.geprueft) {
        strom.className = "stromtext wartet";
        strom.textContent = "jusperfect schreibt \u2026 (" + ev.zeichen + " Zeichen)";
      }
      thread.scrollTop = thread.scrollHeight;
    }
    else if (ev.type === "geprueft") {
      strom.dataset.geprueft = "1";
      strom.className = "stromtext";
      strom.textContent = ev.text;
      thread.scrollTop = thread.scrollHeight;
    }
    else if (ev.type === "fertig") finalisiere(ev.antwort);
    else if (ev.type === "fehler") { gepruefteAntwort = true; strom.remove(); melden(ev.detail, true); }
  };

  const leser = resp.body.getReader();
  const dekoder = new TextDecoder();
  let puffer = "";
  try {
    for (;;) {
      const { done, value } = await leser.read();
      if (done) break;
      puffer += dekoder.decode(value, { stream: true });
      let nl;
      while ((nl = puffer.indexOf("\n")) >= 0) { verarbeite(puffer.slice(0, nl)); puffer = puffer.slice(nl + 1); }
    }
    if (puffer.trim()) verarbeite(puffer);
  } catch (e) { /* abgerissene Verbindung - unten behandelt wie ein fehlendes Ende */ }

  // Der stroemende Text ist die UNGEPRUEFTE Fassung; erst "fertig" bringt die
  // belegte. Bricht der Strom vorher ab, blieb der Rohtext als scheinbar
  // fertige Antwort stehen - ohne Beleg, ohne Fusszeile, ohne Warnung. Gesehen
  // im Browser (PRUEFBERICHT-2026-09-16.md, Befund 3). Hier gilt dieselbe
  // Regel wie ueberall: Was nicht geprueft ist, bleibt nicht stehen.
  if (!gepruefteAntwort) {
    strom.remove();
    const abbruch = document.createElement("p");
    abbruch.className = "strom-abbruch";
    abbruch.textContent = "Die Antwort ist unvollständig geblieben und wurde verworfen – "
      + "sie hat die Belegprüfung nicht durchlaufen. Bitte die Frage erneut stellen.";
    inhalt.appendChild(abbruch);
    thread.scrollTop = thread.scrollHeight;
  }
  ladeStatus();
}

function belegChips(ziel, quellen) {
  if (!quellen || !quellen.length) { const s = document.createElement("span"); s.className = "beleg fehlt"; s.textContent = "ohne Beleg"; ziel.appendChild(s); return; }
  for (const q of quellen) {
    const chip = document.createElement("span"); chip.className = "beleg"; chip.textContent = q.kennung;
    chip.addEventListener("click", () => passageMarkieren(q.kennung));
    ziel.append(chip, document.createTextNode(" "));
  }
}

function tabelle(ueberschriften, zeilen, zellenFn) {
  const tab = document.createElement("table"); tab.className = "mini-t";
  const kopf = document.createElement("tr");
  for (const u of ueberschriften.concat(["Beleg"])) { const th = document.createElement("th"); th.textContent = u; kopf.appendChild(th); }
  tab.appendChild(kopf);
  for (const z of zeilen) {
    const tr = document.createElement("tr");
    for (const wert of zellenFn(z)) { const td = document.createElement("td"); td.textContent = wert; tr.appendChild(td); }
    const td = document.createElement("td"); belegChips(td, z.quellen); tr.appendChild(td); tab.appendChild(tr);
  }
  return tab;
}

const FUNKTION_NAME = { frage: "Frage", analyse: "Analyse", triage: "Eingangsprüfung", entwurf: "Entwurf" };

// Was aus einem Aufruf geworden ist, in Worten. Siehe services/ausgang.py.
//
// Bewusst zurueckhaltend formuliert: Die Zeile entsteht, BEVOR das Material
// uebergeben wird. Scheitert der Aufruf, laesst sich an dieser Stelle nicht
// mehr sagen, ob er die Leitung noch erreicht hat. "Uebertragen" zu schreiben
// waere also zu viel behauptet - und "nichts passiert" zu wenig. Was der
// Eintrag bedeutet, steht im Kopf des Fensters.
const AUSGANG_NAME = {
  fehlgeschlagen: "ohne Antwort",
  abgebrochen: "abgebrochen",
  unbekannt: "Ausgang offen",
};

async function nachweisZeigen() {
  const daten = await api("GET", "/api/nachweis?limit=25");
  mitschriftZeigen();
  const ziel = $("nachweis-liste"); ziel.replaceChildren();
  if (!daten.eintraege.length) {
    const p = document.createElement("p"); p.className = "nachweis-leer";
    p.textContent = "Noch nichts an ein Modell übertragen.";
    ziel.appendChild(p);
  }
  for (const e of daten.eintraege) {
    const zeile = document.createElement("div"); zeile.className = "nachweis-zeile";
    const kopf = document.createElement("div"); kopf.className = "nachweis-kopf";
    const wann = new Date(e.zeitpunkt).toLocaleString("de-DE");
    kopf.append(feld(FUNKTION_NAME[e.funktion] || e.funktion, "nw-funktion"),
                feld(e.akte_id, "nw-akte"));
    // Der Ausgang steht nur da, wenn er NICHT "beantwortet" ist.
    //
    // Seit dem 05.10.2026 entsteht die Nachweiszeile, bevor das Material
    // hinausgeht (Befund F10). Damit kann hier stehen, dass etwas uebertragen
    // wurde und keine Antwort kam - vorher fehlte die Zeile ganz, und das las
    // sich wie "nichts hinausgegangen". Beim Regelfall waere das Wort nur
    // Laerm; beim Fehlerfall ist es die Auskunft.
    if (e.ausgang && e.ausgang !== "beantwortet") kopf.append(feld(AUSGANG_NAME[e.ausgang] || e.ausgang, "nw-ausgang"));
    kopf.append(feld(wann, "nw-zeit"));
    const rumpf = document.createElement("div"); rumpf.className = "nachweis-rumpf";
    rumpf.append(
      feld(`Modell ${e.modell}`, "nw-detail"),
      feld(`Material ${e.material_kennung} · ${e.passagen} Passagen`, "nw-detail"),
      feld(`Antwort ${e.antwort_zeichen} Zeichen`, "nw-detail"),
      feld(`${e.eingabe_tokens}+${e.ausgabe_tokens} Token · ${e.betrag_eur.toFixed(4)} EUR`, "nw-detail"),
    );
    zeile.append(kopf, rumpf); ziel.appendChild(zeile);
  }
  $("nachweis-dialog").showModal();
}

// ── Selbsttest: Stehen die Absicherungen? ───────────────────────────────────
// Aus der Kanzlei: "ein Testlauf beim Start des Programms mit Hinweis auf den
// Testablauf, was gerade gemacht wird." Gelaufen sind die Pruefungen schon
// vorher - nur sah man sie nicht, und "nichts gesehen" ist bei einer
// Absicherung keine Auskunft.

const SELBSTTEST_ZEICHEN = { gut: "✓", offen: "!", schlecht: "✗", entfaellt: "–", ungeprueft: "?" };

function selbsttestZeile(titel, zustand, satz, hinweis) {
  const zeile = document.createElement("div");
  zeile.className = "st-zeile " + zustand;
  const marke = document.createElement("span");
  marke.className = "st-marke"; marke.textContent = SELBSTTEST_ZEICHEN[zustand] || "·";
  const haupt = document.createElement("div"); haupt.className = "st-haupt";
  const t = document.createElement("div"); t.className = "st-titel"; t.textContent = titel;
  const p = document.createElement("div"); p.className = "st-satz"; p.textContent = satz;
  haupt.append(t, p);
  if (hinweis) {
    const h = document.createElement("div"); h.className = "st-hinweis"; h.textContent = hinweis;
    haupt.appendChild(h);
  }
  zeile.append(marke, haupt);
  return zeile;
}

function selbsttestModelle(modelle) {
  const ziel = $("selbsttest-modelle"); ziel.replaceChildren();
  // Ohne echtes Modell gibt es nichts zu testen; ein Knopf, der nur die Zeile
  // "Muster im Programm" zurueckgibt, verspricht mehr als er haelt.
  const knopf = $("selbsttest-anprobieren");
  if (knopf) knopf.hidden = !(modelle || []).some((m) => m.zustand !== "entfaellt");
  for (const m of (modelle || [])) {
    // Die Kennung ist der Titel: Bei mehreren Modellen ist sie das, was sie
    // unterscheidet. Welche Arbeit das Modell tut, steht darunter.
    ziel.appendChild(selbsttestZeile(m.kennung, m.zustand, m.arbeit, m.satz));
  }
}

// Wie lange ein Punkt stehenbleibt, bevor der naechste kommt. Acht Punkte mal
// 110 ms ist knapp unter einer Sekunde - lang genug, um den Ablauf zu sehen,
// kurz genug, dass niemand wartet, der das Bild fuenfmal am Tag aufmacht.
const ST_TAKT = 110;

// Der Rennwagen zeigt in fast jeder Schrift nach LINKS. Faehrt er nach rechts,
// sieht es aus, als setze er zurueck. Aus der Kanzlei: „Der Rennwagen faehrt
// rueckwaerts." Gespiegelt wird er nach dem Verschieben - erst schieben, dann
// wenden, sonst dreht die Spiegelung auch die Fahrtrichtung um.
const ST_BLICKRICHTUNG = "scaleX(-1)";

function selbsttestRuhig() {
  try { return window.matchMedia("(prefers-reduced-motion: reduce)").matches; }
  catch (e) { return false; }
}

function selbsttestErgebnis(offen) {
  const zeile = $("selbsttest-ergebnis");
  zeile.textContent = offen
    ? `🏁 Durchgelaufen – ${offen} Punkt(e) brauchen einen Blick.`
    : "🏁 ✓ Alles in Ordnung.";
  zeile.className = "st-ergebnis " + (offen ? "offen" : "gut");
  zeile.hidden = false;
}

// Der Wagen faehrt, die Punkte erscheinen einer nach dem anderen, am Ziel steht
// die Flagge. Gibt ein Versprechen zurueck, damit der Test darauf warten kann.
function selbsttestLauf(zeilen, offen) {
  const wagen = $("st-wagen"), ziel = $("st-ziel"), ergebnis = $("selbsttest-ergebnis");
  ergebnis.hidden = true;
  ziel.classList.remove("da");
  // Die Strecke in Pixeln, nicht in Prozent: Bei einem absolut gesetzten
  // Element bezieht sich translateX(100%) auf die eigene Breite, nicht auf die
  // der Strecke - der Wagen fuhr damit gut einen Zentimeter und blieb stehen.
  const strecke = wagen.parentElement;
  const weg = Math.max(0, strecke.clientWidth - wagen.offsetWidth);
  if (selbsttestRuhig() || !zeilen.length) {
    for (const z of zeilen) z.classList.remove("st-neu");
    wagen.style.transition = "none";
    wagen.style.transform = `translateX(${weg}px) ${ST_BLICKRICHTUNG}`;
    ziel.classList.add("da");
    selbsttestErgebnis(offen);
    return Promise.resolve();
  }
  wagen.style.transition = "none";
  wagen.style.transform = `translateX(0) ${ST_BLICKRICHTUNG}`;
  // Ein Bildaufbau abwarten, sonst springt der Wagen ohne Fahrt ans Ziel.
  return new Promise((fertig) => requestAnimationFrame(() => {
    wagen.style.transition = `transform ${(zeilen.length * ST_TAKT) / 1000}s linear`;
    wagen.style.transform = `translateX(${weg}px) ${ST_BLICKRICHTUNG}`;
    zeilen.forEach((z, i) => setTimeout(() => z.classList.remove("st-neu"), i * ST_TAKT));
    setTimeout(() => {
      ziel.classList.add("da");
      selbsttestErgebnis(offen);
      fertig();
    }, zeilen.length * ST_TAKT);
  }));
}

async function selbsttestOeffnen() {
  const daten = await api("GET", "/api/selbsttest");
  const ziel = $("selbsttest-liste"); ziel.replaceChildren();
  const zeilen = daten.punkte.map((p) => {
    const z = selbsttestZeile(p.titel, p.zustand, p.satz, p.hinweis);
    z.classList.add("st-neu");
    ziel.appendChild(z);
    return z;
  });
  // Gemerkt fuer den Testlauf: Er sagt vorher, was er tun wird, und das
  // haengt daran, ob ein Schutzgelaender hinterlegt ist.
  K.selbsttestPunkte = daten.punkte || [];
  selbsttestModelle(daten.modelle);
  $("selbsttest-dialog").showModal();
  await selbsttestLauf(zeilen, daten.offen);
}

// Die Zahl am Knopf: nur offene Punkte. Steht keine da, ist nichts offen -
// dann soll der Knopf auch nicht nach Arbeit aussehen.
async function selbsttestMarkeSetzen() {
  const marke = $("selbsttest-marke");
  if (!marke) return;
  try {
    const daten = await api("GET", "/api/selbsttest");
    marke.textContent = daten.offen || "";
    marke.hidden = !daten.offen;
  } catch (e) { marke.hidden = true; }
}

async function modellTestlauf() {
  // Der Knopf heisst weiter "Modell-Testlauf" - so wollte die Kanzlei ihn. Er
  // tut jetzt aber mehr, und das muss vor dem Klick dastehen: Ist ein
  // Schutzgelaender hinterlegt, gehen fuenf erfundene Saetze aus verschiedenen
  // Rechtsgebieten mit hindurch. Die Frage, die dahintersteht, laesst sich
  // sonst nicht beantworten - naemlich ob das Gelaender die Sprache einer Akte
  // ueberhaupt durchlaesst.
  const mitGelaender = (K.selbsttestPunkte || []).some(
    (p) => p.schluessel === "guardrail" && p.zustand === "gut");
  if (!confirm("Testlauf: jedes eingebundene Modell einmal wirklich fragen"
               + (mitGelaender
                  ? " - und fuenf erfundene Saetze aus verschiedenen Rechtsgebieten "
                    + "durch das Schutzgelaender schicken, um zu sehen, ob es die "
                    + "Sprache einer Akte durchlaesst"
                  : "")
               + "? Bruchteile eines Cents. Kein Aktentext.")) return;
  const daten = await api("POST", "/api/selbsttest/modelle", {});
  selbsttestModelle(daten.modelle);
  melden("Modell-Testlauf abgeschlossen.");
}

// Schreibt AWS die Modellaufrufe mit? Der Befund stammt vom Programmstart.
// Steht er auf "an", startet das Programm gar nicht erst - hier kann also nur
// "aus" oder "unbekannt" ankommen. Genau "unbekannt" ist der Fall, den sonst
// niemand sieht: Das Programm laeuft, und die Frage ist offen.
function mitschriftZeigen() {
  const zeile = $("nachweis-mitschrift"), m = K.modellprotokoll;
  if (!zeile) return;
  if (!m) { zeile.hidden = true; return; }
  zeile.textContent = m.zustand === "unbekannt"
    ? m.satz + " Vor der ersten echten Akte muss das geklärt sein."
    : m.satz;
  zeile.className = "nachweis-mitschrift" + (m.zustand === "unbekannt" ? " offen" : " gut");
  zeile.hidden = false;
}

function feld(text, klasse) {
  const s = document.createElement("span"); s.className = klasse; s.textContent = text; return s;
}

// ── Chronologie ─────────────────────────────────────────────────────────────
// Sie ist ohne KI-Aufruf gefüllt: Dokumentdaten und Fristen stehen in den
// Stammdaten aus jurnodes. Eine Aktenanalyse reichert sie später an; bis
// dahin ist sie kein leeres Fenster, sondern der Zeitstrahl der Akte.

let chronoAusAnalyse = [];   // Einträge, die die Analyse beigesteuert hat

function chronologieZeigen() {
  const ziel = $("chronologie");
  if (!ziel || !sitzung) return;
  const eintraege = [];
  for (const d of (sitzung.dokumente || []))
    if (d.datum) eintraege.push({ datum: d.datum, was: d.titel, art: "dokument", id: d.id });
  for (const f of (sitzung.fristen || []))
    if (f.datum) eintraege.push({ datum: f.datum, was: f.bezeichnung, art: "frist" });
  for (const e of chronoAusAnalyse)
    eintraege.push({ datum: e.datum, was: e.ereignis, art: "analyse",
                     kennung: e.kennung, dokument_id: e.dokument_id });

  eintraege.sort((a, b) => String(a.datum).localeCompare(String(b.datum)));
  ziel.replaceChildren();
  if (!eintraege.length) {
    $("chrono-stand").textContent = "";
    const p = document.createElement("p"); p.className = "chrono-leer";
    p.textContent = "Noch nichts mit Datum in der Arbeitsakte.";
    ziel.appendChild(p); return;
  }

  // Nach Datum gruppieren. Eine Analyse liefert leicht drei Formulierungen
  // desselben Vorgangs; untereinander gelesen sieht das aus wie drei
  // Ereignisse. Ein Datum, eine Zeile, darunter was an dem Tag geschah.
  const nachDatum = new Map();
  for (const e of eintraege) {
    if (!nachDatum.has(e.datum)) nachDatum.set(e.datum, []);
    const gruppe = nachDatum.get(e.datum);
    // Doppelungen innerhalb eines Tages fallen weg.
    if (!gruppe.some((x) => aehnlich(x.was, e.was))) gruppe.push(e);
  }
  let gezeigt = 0;
  for (const [datum, gruppe] of nachDatum) {
    const block = document.createElement("div"); block.className = "chrono-tag";
    block.appendChild(feld(datumKurz(datum), "chrono-datum"));
    const liste = document.createElement("div"); liste.className = "chrono-was-liste";
    for (const e of gruppe) {
      const zeile = document.createElement("div");
      zeile.className = `chrono-eintrag ${e.art}`;
      zeile.appendChild(feld(e.was, "chrono-was"));
      if (e.id) zeile.addEventListener("click", () => {
        const filter = $("dok-filter");
        if (filter) { filter.value = e.id; zeigeDokument(e.id); }
      });
      else if (e.kennung && belegPasst(e)) zeile.addEventListener("click", () => passageMarkieren(e.kennung));
      liste.appendChild(zeile); gezeigt++;
    }
    block.appendChild(liste); ziel.appendChild(block);
  }
  $("chrono-stand").textContent = `${nachDatum.size} Tage · ${gezeigt} Einträge`;
  // Hier und nur hier: Wer dieses Fenster neu zeichnet, hat etwas
  // geaendert, das ein Nebenfenster angeht.
  nebenfensterGleichziehen();
}

/* Zeigt eine gespeicherte Fundstelle heute noch auf dieselbe Stelle?

   Die Kennungen zaehlen durch (D2-S1-P3), sie haengen also an der Reihenfolge
   der geladenen Dokumente. Eine Chronologie aus der vorigen Woche wurde
   vielleicht mit einer anderen Auswahl erstellt; dann meint dasselbe "D2" ein
   anderes Dokument. Der Eintrag bleibt stehen - er ist belegt gewesen -, aber
   der Sprung wird nur angeboten, wenn die Kennung heute noch zum selben
   Dokument gehoert. Lieber kein Sprung als einer auf die falsche Stelle. */
function belegPasst(e) {
  const p = passagenIndex[e.kennung];
  return !!p && (!e.dokument_id || p.dokument_id === e.dokument_id);
}

/* Zwei Formulierungen desselben Vorgangs erkennen: Wortmengen vergleichen.
   Genauer geht es nicht ohne Modell, und ungenauer wäre nutzlos. */
function aehnlich(a, b) {
  // Auf fünf Zeichen gekürzt: Deutsch beugt am Wortende ("Betriebsrat" /
  // "Betriebsrats"). Dieselbe Regel wie beim Speichern im Gedächtnis –
  // was dort ein Eintrag ist, soll hier nicht als zwei erscheinen.
  const menge = (t) => new Set((String(t).toLowerCase().match(/[a-zäöüß0-9]{4,}/g) || [])
    .map((w) => w.slice(0, 5)));
  const A = menge(a), B = menge(b);
  if (!A.size || !B.size) return a === b;
  let gemeinsam = 0;
  for (const w of A) if (B.has(w)) gemeinsam++;
  return gemeinsam / Math.min(A.size, B.size) >= 0.7;
}

function datumKurz(wert) {
  const d = new Date(wert);
  return isNaN(d) ? String(wert).slice(0, 10)
                  : d.toLocaleDateString("de-DE", { day: "2-digit", month: "2-digit", year: "2-digit" });
}

// ── Kostenschätzung vor dem Absenden ────────────────────────────────────────
// Der Nachweis sagt hinterher, was es gekostet hat. Das hilft beim Prüfen,
// nicht beim Entscheiden. Wer überlegt, ob er noch drei Dokumente hinüberzieht,
// braucht die Zahl vorher.

function schaetzungZeigen(s) {
  const ziel = $("schaetzung");
  if (!ziel) return;
  // Ohne KI kostet nichts; die Zahl wäre irreführend.
  if (!s || !K.kostenpflichtig || !s.dokumente) { ziel.hidden = true; return; }
  const cent = (eur) => (eur < 0.01 ? "unter 1 Cent" : `rund ${(eur * 100).toFixed(0)} Cent`);
  ziel.replaceChildren();
  ziel.append(feld(
    `${s.dokumente} Dokument(e), ${s.zeichen.toLocaleString("de-DE")} Zeichen · `
    + `geschätzt ${cent(s.erste_frage_eur)}`, "schaetzung-haupt"));
  // Der Unterschied lohnt die Erwähnung nur, wenn er spürbar ist.
  if (s.erste_frage_eur - s.weitere_frage_eur >= 0.01) {
    ziel.append(feld(`; jede weitere Frage zu dieser Akte ${cent(s.weitere_frage_eur)}`,
                     "schaetzung-neben"));
  }
  ziel.hidden = false;
}

// ── Abschluss der Akte ───────────────────────────────────────────────────────
// Erst exportieren, dann löschen. Die Oberfläche bildet genau diese Reihenfolge
// ab: Ohne geprüften und freigegebenen Vorschautext ist der Löschknopf gesperrt.

let abschlussVorschau = null;   // { text, text_pruefsumme } – an die Freigabe gebunden

const ABSCHLUSS_GRUND = {
  laufende_mandatsbearbeitung: "laufende Mandatsbearbeitung",
  laufendes_verfahren_ruhend: "laufendes Verfahren, derzeit ruhend",
  abschlusspruefung_erforderlich: "Abschlussprüfung erforderlich",
  status_ungeklaert_nicht_loeschen: "Status ungeklärt – es wird nicht gelöscht",
};

async function abschlussOeffnen() {
  abschlussVorschau = null;
  $("abschluss-bestaetigt").checked = false;
  await abschlussZeichnen();
  $("abschluss-dialog").showModal();
}

async function abschlussZeichnen() {
  const stand = await api("GET", `/api/akten/${encodeURIComponent(sitzung.sitzung.akte_id)}/abschluss`);
  const ziel = $("abschluss-stand"); ziel.replaceChildren();
  const zeile = (beschriftung, wert, klasse) => {
    const d = document.createElement("div"); d.className = "abschluss-zeile";
    d.append(feld(beschriftung, "abschluss-name"), feld(wert, klasse || "abschluss-wert"));
    ziel.appendChild(d);
  };
  zeile("Status in jurnodes", stand.aktenstatus);
  if (stand.abgeschlossen_am) zeile("Abschluss vorgemerkt", datum(stand.abgeschlossen_am));
  if (stand.loeschung_vorgesehen_am)
    zeile("Löschung frühestens", datum(stand.loeschung_vorgesehen_am),
          stand.faellig ? "abschluss-wert faellig" : "abschluss-wert");
  for (const h of stand.hinweise || []) {
    const p = document.createElement("p"); p.className = "abschluss-hinweis";
    p.textContent = h; ziel.appendChild(p);
  }
  if (!stand.abschlussreif) {
    const p = document.createElement("p"); p.className = "abschluss-hinweis";
    p.textContent = "Die Akte ist in jurnodes nicht abgeschlossen. Der Arbeitsbereich bleibt "
      + "unverändert erhalten; es ist nichts zu tun.";
    ziel.appendChild(p);
  }

  // Sichtbarkeit der Knöpfe folgt strikt dem Zustand.
  const vormerken = $("abschluss-vormerken"), ausfuehren = $("abschluss-ausfuehren");
  vormerken.hidden = !stand.abschlussreif || !!stand.loeschung_vorgesehen_am;
  ausfuehren.hidden = !stand.faellig;
  $("abschluss-vorschau-block").hidden = !stand.faellig;
  if (stand.faellig) {
    abschlussVorschau = await api("GET", `/api/akten/${encodeURIComponent(sitzung.sitzung.akte_id)}/abschluss/vorschau`);
    $("abschluss-vorschau").value = abschlussVorschau.text;
  }
  abschlussKnopfPruefen();
}

function abschlussKnopfPruefen() {
  const k = $("abschluss-ausfuehren");
  k.disabled = !($("abschluss-bestaetigt").checked && abschlussVorschau);
}

async function abschlussVormerken() {
  await api("POST", `/api/akten/${encodeURIComponent(sitzung.sitzung.akte_id)}/abschluss/vormerken`, {});
  await abschlussZeichnen();
  melden("Abschluss vorgemerkt. Vor Ablauf der Frist wird nichts gelöscht.");
}

async function abschlussAusfuehren() {
  if (!abschlussVorschau) return;
  const nachweis = await api("POST", `/api/akten/${encodeURIComponent(sitzung.sitzung.akte_id)}/abschluss/ausfuehren`,
                             { bestaetigung: true, text_pruefsumme: abschlussVorschau.text_pruefsumme });
  abschlussVorschau = null;
  // Der Löschnachweis ist der Beleg des Vorgangs. Er bleibt im Dialog stehen,
  // bis er weggeklickt wird – eine flüchtige Meldung wäre hier zu wenig, zumal
  // das Schließen der Sitzung gleich seine eigene Meldung setzt.
  abschlussNachweisZeigen(nachweis);
  await sitzungSchliessen();
}

function abschlussNachweisZeigen(nachweis) {
  const g = nachweis.geloescht;
  $("abschluss-vorschau-block").hidden = true;
  $("abschluss-vormerken").hidden = true;
  $("abschluss-ausfuehren").hidden = true;
  const ziel = $("abschluss-stand"); ziel.replaceChildren();
  const ueberschrift = document.createElement("p");
  ueberschrift.className = "abschluss-erledigt";
  ueberschrift.textContent = "Abschluss ausgeführt.";
  ziel.appendChild(ueberschrift);
  const zeile = (name, wert) => {
    const d = document.createElement("div"); d.className = "abschluss-zeile";
    d.append(feld(name, "abschluss-name"), feld(wert, "abschluss-wert"));
    ziel.appendChild(d);
  };
  zeile("Nach jurnodes gesichert", nachweis.jurnodes_referenz);
  zeile("Freigegeben von", nachweis.nutzer_id);
  zeile("Zeitpunkt", new Date(nachweis.zeitpunkt).toLocaleString("de-DE"));
  zeile("Gelöscht", `${g.dokumente} Dokumentauszug/-auszüge, ${g.fragen} Frage(n), `
                  + `${g.sitzungen} Sitzung(en), ${g.entwuerfe} Entwurf/Entwürfe`);
  const hinweis = document.createElement("p");
  hinweis.className = "abschluss-hinweis";
  hinweis.textContent = "Der Arbeitsbereich dieser Akte ist gelöscht. Die Akte selbst bleibt in "
    + "jurnodes unberührt; dort steht jetzt der gesicherte Arbeitsstand als Vermerk.";
  ziel.appendChild(hinweis);
}

function datum(wert) {
  return new Date(wert).toLocaleDateString("de-DE",
    { day: "2-digit", month: "2-digit", year: "numeric" });
}

// ── Aufsicht über alle Arbeitsbereiche ───────────────────────────────────────

// ── Aufbewahrung ────────────────────────────────────────────────────────────
// Die Liste zeigt Arbeitsbereiche, ueber die jusperfect nicht selbst
// entscheiden darf. Sie zeigte bisher, was die Pruefung ergeben hat:
// Aufbewahrungsgrund, Zaehlwerte, Zeitpunkte. Das ist richtig und fuer den
// Bearbeiter unbrauchbar - er muss daraus erst schliessen, was zu tun ist.
//
// Jetzt stehen zwei Saetze je Akte: was los ist, und was zu tun ist. Was
// nichts verlangt, liegt zugeklappt darunter. Aus der Kanzlei: "Wenn zu viel
// auf einer Seite ist, dann ueberfordert das den Benutzer."

function aufsichtZeile(e) {
  const zeile = document.createElement("div");
  zeile.className = "aufbewahrung-zeile" + (e.handlungsbedarf ? " handlungsbedarf" : "");

  const akte = document.createElement("div");
  akte.className = "aufbewahrung-akte";
  akte.textContent = [e.aktenzeichen || e.akte_id, e.bezeichnung].filter(Boolean).join(" · ");
  zeile.appendChild(akte);

  // Befund und Schritt gehoeren paarweise zusammen; der Server liefert sie
  // in derselben Reihenfolge.
  const hinweise = e.hinweise || [], schritte = e.schritte || [];
  for (let i = 0; i < hinweise.length; i++) {
    const was = document.createElement("p");
    was.className = "aufbewahrung-was";
    was.textContent = hinweise[i];
    zeile.appendChild(was);
    if (schritte[i]) {
      const tun = document.createElement("p");
      tun.className = "aufbewahrung-tun";
      tun.textContent = schritte[i];
      zeile.appendChild(tun);
    }
  }

  const fuss = document.createElement("div");
  fuss.className = "aufbewahrung-fuss";
  const teile = [`${e.dokumente} Dokument(e)`, `${e.fragen} Frage(n)`];
  if (e.loeschung_vorgesehen_am)
    teile.push((e.faellig ? "Löschung möglich seit " : "Löschung frühestens ") + datum(e.loeschung_vorgesehen_am));
  fuss.textContent = teile.join(" · ");
  zeile.appendChild(fuss);
  return zeile;
}

async function aufsichtOeffnen() {
  const daten = await api("GET", "/api/verwaltung/arbeitsbereiche");
  const offen = daten.eintraege.filter((e) => e.handlungsbedarf);
  const ruhig = daten.eintraege.filter((e) => !e.handlungsbedarf);

  const ziel = $("aufsicht-liste");
  ziel.replaceChildren();

  if (!daten.eintraege.length) {
    const p = document.createElement("p"); p.className = "nachweis-leer";
    p.textContent = "Es gibt noch keine Arbeitsbereiche.";
    ziel.appendChild(p);
  }

  if (offen.length) {
    const kopf = document.createElement("h3");
    kopf.className = "aufbewahrung-gruppe";
    kopf.textContent = offen.length === 1 ? "Eine Akte wartet auf eine Entscheidung"
                                          : `${offen.length} Akten warten auf eine Entscheidung`;
    ziel.appendChild(kopf);
    for (const e of offen) ziel.appendChild(aufsichtZeile(e));
  } else if (daten.eintraege.length) {
    const p = document.createElement("p");
    p.className = "aufbewahrung-ruhe";
    p.textContent = "Nichts zu entscheiden. Alle Arbeitsbereiche folgen dem Stand in jurnodes.";
    ziel.appendChild(p);
  }

  // Was nichts verlangt, steht zugeklappt darunter: nachschlagbar, aber nicht
  // im Weg. Es ist der Normalfall und damit die laengste Liste.
  if (ruhig.length) {
    const block = document.createElement("details");
    block.className = "aufbewahrung-ruhig";
    const titel = document.createElement("summary");
    titel.textContent = ruhig.length === 1 ? "1 weitere Akte, nichts zu tun"
                                           : `${ruhig.length} weitere Akten, nichts zu tun`;
    block.appendChild(titel);
    for (const e of ruhig) block.appendChild(aufsichtZeile(e));
    ziel.appendChild(block);
  }

  $("aufsicht-dialog").showModal();
}

// ── Referenzen (veröffentlichtes Material im Kontext) ────────────────────────

async function referenzenOeffnen() {
  const [verfuegbar, gewaehlt] = await Promise.all([
    api("GET", "/api/referenzen"),
    api("GET", `/api/sitzungen/${sitzung.sitzung.id}/referenzen`),
  ]);
  const aktiv = new Set(gewaehlt.namen || []);
  const ziel = $("referenzen-liste"); ziel.replaceChildren();
  if (!(verfuegbar.eintraege || []).length) {
    const p = document.createElement("p"); p.className = "nachweis-leer";
    p.textContent = "Im Referenzordner liegt noch nichts.";
    ziel.appendChild(p);
  }
  for (const r of (verfuegbar.eintraege || [])) {
    const label = document.createElement("label"); label.className = "referenz-zeile";
    const box = document.createElement("input"); box.type = "checkbox"; box.value = r.name; box.checked = aktiv.has(r.name);
    const text = r.kategorie ? `${r.kategorie} · ${r.label}` : r.label;
    label.append(box, Object.assign(document.createElement("span"), { textContent: text }));
    ziel.appendChild(label);
  }
  $("referenzen-dialog").showModal();
}

async function referenzenSpeichern() {
  const namen = [...document.querySelectorAll("#referenzen-liste input:checked")].map((b) => b.value);
  const r = await api("PUT", `/api/sitzungen/${sitzung.sitzung.id}/referenzen`, { namen });
  melden(r.namen.length ? `${r.namen.length} Referenz(en) im Kontext.` : "Keine Referenzen im Kontext.");
}

// ── Haufe-Recherche (Direktlink, Browser-Sitzung des Nutzers) ────────────────

function haufeRecherche() {
  const cfg = K.haufe || {};
  if (!cfg.url) { melden("Für Haufe ist keine Adresse hinterlegt.", true); return; }
  // Suchtext ist allein die getippte Frage. Frueher fiel das Programm auf die
  // Aktenbezeichnung zurueck, wenn das Feld leer war - dann trug ein Klick auf
  // "Recherche" die Parteinamen in die Zwischenablage, und bei eingestelltem
  // Suchparameter sogar in die Adresse. Der Haufe-Zugang ist zwar mit
  // Auftragsverarbeitungsvertrag und Loeschfunktion abgesichert; darauf kommt
  // es hier aber nicht an: Was der Bearbeiter nicht getippt hat, geht nicht
  // hinaus. Er saehe es sonst nicht einmal.
  const frage = ($("frage").value || "").trim();
  let ziel = cfg.url;
  if (frage && cfg.suche_param) {
    // Nur wenn Haufes Suchparameter bekannt/eingestellt ist – sonst nie raten.
    ziel += (ziel.includes("?") ? "&" : "?") + encodeURIComponent(cfg.suche_param) + "=" + encodeURIComponent(frage);
  } else if (frage) {
    // Robust ohne Rateei: Frage in die Zwischenablage, bei Haufe einfügen.
    try { navigator.clipboard.writeText(frage); melden("Frage in die Zwischenablage kopiert – bei Haufe mit Strg+V einfügen."); }
    catch (e) { /* ohne Zwischenablage einfach nur öffnen */ }
  } else {
    melden("Haufe wird geöffnet. Ein Suchtext geht nur mit, wenn er im Fragefeld steht.");
  }
  window.open(ziel, "_blank", "noopener");
}

/** Gesetz nachschlagen - derselbe Weg wie der Haufe-Knopf.
 *
 * Aus der Kanzlei am 25.09.2026: "ich finde unter mehr gar nicht die
 * Gesetzestexte". Der Sprung stand bis dahin nur IN einer Antwort, neben
 * einem genannten Paragrafen. Nachschlagen will man aber auch ohne Antwort.
 *
 * Steht im Fragefeld ein Verweis wie "§ 634 BGB", geht es direkt dorthin.
 * Sonst wird die Startseite geoeffnet und der getippte Text in die
 * Zwischenablage gelegt - genau wie bei Haufe ohne Suchparameter. Geraten
 * wird nichts.
 */
function gesetzNachschlagen() {
  const cfg = K.gesetze || {};
  if (!cfg.url) { melden("Für die Gesetzestexte ist keine Adresse hinterlegt.", true); return; }
  const frage = ($("frage").value || "").trim();
  let ziel = cfg.url;
  GESETZESVERWEIS.lastIndex = 0;
  const m = GESETZESVERWEIS.exec(frage);
  if (m && sichtbaresKuerzel(m[3])) {
    ziel = gesetzesAdresse(m[3], m[1]) || cfg.url;
    melden(`${m[0]} wird nachgeschlagen.`);
  } else if (frage) {
    try {
      navigator.clipboard.writeText(frage);
      melden("Kein Paragraf erkannt – der Text liegt in der Zwischenablage, auf der Seite mit Strg+V suchen.");
    } catch (e) { /* ohne Zwischenablage einfach nur oeffnen */ }
  } else {
    melden("Die Gesetzesseite wird geöffnet. Steht ein Paragraf im Fragefeld, geht es direkt dorthin.");
  }
  window.open(ziel, "_blank", "noopener");
}

// ── Posteingang (beobachteter Ordner) ────────────────────────────────────────

async function posteingangOeffnen() {
  await posteingangLaden();
  $("posteingang-dialog").showModal();
}

async function posteingangPruefen() {
  const daten = await api("POST", "/api/posteingang/pruefen");
  posteingangRendern(daten);
}

async function posteingangLaden() {
  posteingangRendern(await api("GET", "/api/posteingang"));
}

function posteingangRendern(daten) {
  const stand = $("posteingang-stand");
  const wann = daten.geprueft_am ? new Date(daten.geprueft_am).toLocaleString("de-DE") : "noch nicht";
  stand.textContent = `Ordner: ${daten.ordner || "–"} · zuletzt geprüft: ${wann}` +
    (daten.wartend ? ` · ${daten.wartend} in Übertragung` : "");
  const ziel = $("posteingang-liste"); ziel.replaceChildren();
  const fehler = Object.entries(daten.fehler || {});
  if (!daten.eintraege.length && !fehler.length) {
    const p = document.createElement("p"); p.className = "nachweis-leer";
    p.textContent = "Keine vorbereiteten Eingänge. „Prüfen“ liest den Ordner erneut.";
    ziel.appendChild(p);
  }
  for (const e of daten.eintraege) {
    const zeile = document.createElement("div"); zeile.className = "nachweis-zeile";
    const kopf = document.createElement("div"); kopf.className = "nachweis-kopf";
    kopf.append(feld(e.dateiname, "nw-funktion"),
                feld(`${e.seiten} Seiten · ${e.zeichen} Zeichen${e.ocr ? " · OCR" : ""}`, "nw-detail"));
    const knoepfe = document.createElement("div"); knoepfe.className = "posteingang-knoepfe";
    const pruef = document.createElement("button"); pruef.type = "button"; pruef.className = "mini";
    pruef.textContent = "Eingangsprüfung";
    pruef.addEventListener("click", () => mitKnopf(pruef, () => eingangPruefen(e.id, zeile)));
    const weg = document.createElement("button"); weg.type = "button"; weg.className = "mini leise";
    weg.textContent = "Verwerfen";
    weg.addEventListener("click", () => mitKnopf(weg, () => eingangVerwerfen(e.id, e.dateiname)));
    knoepfe.append(pruef, weg);
    zeile.append(kopf, knoepfe); ziel.appendChild(zeile);
  }
  for (const [name, grund] of fehler) {
    const z = document.createElement("div"); z.className = "nachweis-zeile posteingang-fehler";
    z.append(feld(name, "nw-funktion"), feld(grund, "nw-detail"));
    ziel.appendChild(z);
  }
}

async function eingangPruefen(id, zeile) {
  const t = await api("POST", `/api/posteingang/${id}/triage`);
  let box = zeile.querySelector(".posteingang-triage");
  if (box) box.remove();
  box = document.createElement("div"); box.className = "posteingang-triage";
  const zeilen = [
    ["Dokumentart", t.dokumentart], ["Absender", t.absender], ["Kernaussage", t.kernaussage],
  ].filter(([, w]) => w);
  for (const [k, w] of zeilen) {
    const p = document.createElement("p"); p.append(feld(k + ": ", "nw-detail")); p.append(document.createTextNode(w));
    box.appendChild(p);
  }
  if (t.fristausloeser && t.fristausloeser.length) {
    const p = document.createElement("p"); p.append(feld("Fristauslöser: ", "nw-detail"));
    p.append(document.createTextNode(t.fristausloeser.map((f) => f.text).join(" · ")));
    box.appendChild(p);
  }
  if (t.hinweise && t.hinweise.length) { const hb = hinweiseBlock(t.hinweise); if (hb) box.appendChild(hb); }
  zeile.appendChild(box);
}

async function eingangVerwerfen(id, dateiname) {
  await api("DELETE", `/api/posteingang/${id}`);
  await posteingangLaden();
  rueckgaengigAnbieten(`Verworfen: ${dateiname || "Vorgang"}`, async () => {
    try {
      const v = await api("POST", `/api/posteingang/${id}/zurueckholen`);
      await posteingangLaden();
      melden(`Zurückgeholt: ${v.dateiname}`);
    } catch (e) { melden(e.message, true); }
  });
}

/** Was die Oberflaeche ueber die gespeicherte Analyse weiss. */
let analyseStand = { vorhanden: false, am: null, erfasst: 0, neu: [] };

/** Die gespeicherte Analyse beim Oeffnen der Akte - ohne Modellaufruf.
 *
 * Aus der Kanzlei am 05.10.2026: "Wichtig ist, dass das Programm vielleicht
 * selber erkennt, wenn neue Dokumente in der Akte sind."
 *
 * Der Abruf kostet nichts: Er liest, was gespeichert ist, und vergleicht die
 * Dokumentliste der Akte mit der von damals. Genau deshalb darf er bei jedem
 * Oeffnen laufen.
 */
async function gespeicherteAnalyseZeigen() {
  // Zuerst zuruecksetzen. Ohne diese Zeile stuende beim Wechsel auf eine Akte
  // ohne Analyse noch der Stand der vorigen da - und der Knopf fragte nach
  // einer Analyse, die es fuer diese Akte nie gab.
  analyseStand = { vorhanden: false, am: null, erfasst: 0, neu: [] };
  let daten;
  // Eine fehlende Analyse darf das Oeffnen der Akte nicht aufhalten. Sie ist
  // eine Arbeitshilfe, keine Bedingung.
  try { daten = await api("GET", `/api/sitzungen/${sitzung.sitzung.id}/analyse`); }
  catch (e) { return; }
  analyseStand = daten.stand || analyseStand;
  if (!daten.analyse) return;
  analyseKarte(daten.analyse, analyseStand);
}

/** Der Satz ueber die Dokumente, die seit der Analyse dazugekommen sind. */
function analyseNachzuglerText(stand) {
  const neu = (stand && stand.neu) || [];
  if (!neu.length) return "";
  const namen = neu.slice(0, 5).map((d) => d.titel).join(", ");
  const rest = neu.length > 5 ? ` und ${neu.length - 5} weitere` : "";
  // Die Titel stehen am SCHLUSS und ohne Punkt dahinter. Ein Dokumenttitel
  // endet oft selbst auf einen Punkt - "Schriftsatz vom 02.10." - und mit
  // einem Satzzeichen dahinter stand da "02.10..".
  return neu.length === 1
    ? "Seit dieser Analyse ist ein Dokument in die Akte gekommen; es ist darin "
      + `nicht enthalten: ${namen}`
    : `Seit dieser Analyse sind ${neu.length} Dokumente in die Akte gekommen; `
      + `sie sind darin nicht enthalten: ${namen}${rest}`;
}

async function analyseStarten() {
  // Liegt schon eine Analyse vor, ist der Knopf eine Geldausgabe und keine
  // Auskunft. Was sie zeigen wuerde, steht bereits auf dem Schirm.
  if (analyseStand.vorhanden) {
    const nachzuegler = analyseNachzuglerText(analyseStand);
    const teile = [
      `Es liegt eine Analyse vom ${datumKurz(analyseStand.am)} vor.`,
      "",
      nachzuegler || "Seitdem ist kein Dokument in die Akte gekommen.",
      "",
      "Neu rechnen kostet einen Modellaufruf über die ganze Akte.",
      "", "Trotzdem neu rechnen?"];
    if (!confirm(teile.join("\n"))) return;
  }
  const a = await api("POST", `/api/sitzungen/${sitzung.sitzung.id}/analyse`);
  analyseStand = a.stand || { vorhanden: true, am: null, erfasst: 0, neu: [] };
  for (const liste of ["chronologie", "beteiligte", "forderungen", "beweismittel", "offene_punkte", "widersprueche"])
    for (const e of a[liste]) belegeMerken(e.quellen);
  // Was die Analyse an Ereignissen fand, gehört in das Chronologie-Fenster –
  // nur belegte Einträge, damit dort nichts Unbelegtes stehen bleibt.
  chronoAusAnalyse = (a.chronologie || [])
    .filter((z) => z.datum && z.quellen && z.quellen.length)
    .map((z) => ({ datum: z.datum, ereignis: z.ereignis,
                   kennung: z.quellen[0].kennung, dokument_id: z.quellen[0].dokument_id }));
  if (sitzung.gedaechtnis) sitzung.gedaechtnis.chronologie = a.chronologie || [];
  chronologieZeigen();
  gedaechtnisFensterZeigen();
  analyseKarte(a, null);
  ladeStatus();
}

/** Zeichnet eine Analyse in den Verlauf - frisch gerechnet oder gespeichert.
 *
 * Eine Funktion fuer beide Wege. Zwei waeren mit der Zeit zwei verschiedene
 * Darstellungen, und dann sagte dieselbe Analyse an zwei Stellen Verschiedenes.
 */
function analyseKarte(a, stand) {
  const karte = threadKarte("ai");
  const titel = document.createElement("div"); titel.className = "titelzeile";
  titel.textContent = stand && stand.am
    ? `Aktenanalyse · Stand vom ${datumKurz(stand.am)}`
    : "Aktenanalyse";
  karte.appendChild(titel);
  const inhalt = document.createElement("div"); inhalt.className = "inhalt";
  // Zuerst, was nicht darin steht. Eine Analyse, der drei Schriftstuecke
  // fehlen, sieht genauso vollstaendig aus wie eine vollstaendige - und das
  // ist der Zustand, den dieses Programm gerade verhindern soll.
  const nachzuegler = analyseNachzuglerText(stand);
  if (nachzuegler) {
    const warn = document.createElement("div"); warn.className = "analyse-veraltet";
    const satz = document.createElement("div"); satz.textContent = nachzuegler;
    const knopf = document.createElement("button");
    knopf.type = "button"; knopf.className = "mini";
    knopf.textContent = "neu rechnen";
    knopf.addEventListener("click", (ev) => mitKnopf(ev.target, analyseStarten));
    warn.append(satz, knopf);
    inhalt.appendChild(warn);
  }
  const hb = hinweiseBlock(a.hinweise); if (hb) inhalt.appendChild(hb);
  const forderungenMitGrundlage = (a.forderungen || []).some((z) => (z.status || "").trim());
  const gruppen = [
    ["Chronologie", ["Datum", "Ereignis"], a.chronologie, (z) => [z.datum, z.ereignis]],
    ["Beteiligte", ["Rolle", "Bezeichnung"], a.beteiligte, (z) => [z.rolle, z.bezeichnung]],
    // Steht für dieselbe Sache in zwei Dokumenten ein anderer Betrag, gehören
    // beide in die Tabelle - und dann muss danebenstehen, worauf jeder beruht.
    // Ohne diese Spalte stünden dort zwei Zeilen „Grundmiete", 850,00 und
    // 950,00, und niemand wüsste, welche gilt. Die Spalte erscheint nur, wenn
    // wenigstens ein Eintrag eine Grundlage nennt.
    ["Forderungen",
     forderungenMitGrundlage ? ["Gegenstand", "Betrag", "Grundlage"] : ["Gegenstand", "Betrag"],
     a.forderungen,
     forderungenMitGrundlage ? (z) => [z.gegenstand, z.betrag, z.status || "–"]
                             : (z) => [z.gegenstand, z.betrag]],
    ["Beweismittel", ["Art", "Bezeichnung"], a.beweismittel, (z) => [z.art, z.bezeichnung]],
    ["Offene Punkte", ["Priorität", "Beschreibung"], a.offene_punkte, (z) => [z.prioritaet, z.beschreibung]],
    ["Widersprüche", ["Beschreibung"], a.widersprueche, (z) => [z.beschreibung]],
  ];
  for (const [name, kopf, zeilen, fn] of gruppen) {
    if (!zeilen.length) continue;
    const h = document.createElement("div"); h.className = "titelzeile"; h.style.fontSize = "13px"; h.textContent = name; inhalt.appendChild(h);
    inhalt.appendChild(tabelle(kopf, zeilen, fn));
  }
  karte.appendChild(inhalt); karte.appendChild(fusszeile(a));
}

async function triageStarten() {
  const dok = $("dok-filter").value || (sitzung.sitzung.geladen[0] && sitzung.sitzung.geladen[0].dokument_id);
  if (!dok) { melden("Kein Dokument geladen.", true); return; }
  const t = await api("POST", `/api/sitzungen/${sitzung.sitzung.id}/triage`, { dokument_id: dok });
  belegeMerken(t.quellen); for (const f of t.fristausloeser) belegeMerken(f.quellen);
  const karte = threadKarte("ai");
  const titel = document.createElement("div"); titel.className = "titelzeile";
  titel.textContent = "Eingangsprüfung: " + (t.dokumentart || "Dokument"); karte.appendChild(titel);
  const inhalt = document.createElement("div"); inhalt.className = "inhalt";
  const hb = hinweiseBlock(t.hinweise); if (hb) inhalt.appendChild(hb);
  if (t.absender) {
    const p = document.createElement("p");
    p.textContent = `Absender: ${t.absender}`;
    inhalt.appendChild(p);
  }
  antworttext(inhalt, t.kernaussage || "");
  if (t.fristausloeser.length) {
    const h = document.createElement("div"); h.className = "titelzeile"; h.style.fontSize = "13px"; h.textContent = "Fristauslöser (Hinweis, keine Berechnung)"; inhalt.appendChild(h);
    inhalt.appendChild(tabelle(["Text"], t.fristausloeser, (z) => [z.text]));
  }
  if (t.empfohlene_schritte.length) {
    const h = document.createElement("div"); h.className = "titelzeile"; h.style.fontSize = "13px"; h.textContent = "Empfohlene Schritte"; inhalt.appendChild(h);
    const ul = document.createElement("ul"); for (const s of t.empfohlene_schritte) { const li = document.createElement("li"); li.textContent = s; ul.appendChild(li); } inhalt.appendChild(ul);
  }
  karte.appendChild(inhalt); karte.appendChild(fusszeile(t));
  ladeStatus();
}

async function entwurfDialogOeffnen() {
  // Eigene Aufträge der Kanzlei als Vorlagen anbieten, wenn ein Ordner eingerichtet ist.
  const feld = $("entwurf-auftrag-feld"), select = $("entwurf-auftrag");
  try {
    const daten = await api("GET", "/api/auftraege");
    select.replaceChildren(new Option("— keiner —", ""));
    for (const a of (daten.eintraege || [])) {
      const beschriftung = a.kategorie ? `${a.kategorie} · ${a.label}` : a.label;
      select.appendChild(new Option(beschriftung, a.name));
    }
    feld.hidden = !daten.aktiv || !(daten.eintraege || []).length;
  } catch (e) { feld.hidden = true; }
  $("entwurf-dialog").showModal();
}

async function auftragVorbelegen(name) {
  if (!name) return;
  const a = await api("GET", "/api/auftraege/" + name.split("/").map(encodeURIComponent).join("/"));
  $("entwurf-anweisung").value = a.anweisung || "";
  if (a.hat_material) melden(`Auftrag „${a.label}" – Material wird als Hintergrund mitgegeben.`);
}

// ── Das Vorschaufenster ────────────────────────────────────────────────────
//
// Aus der Kanzlei am 13.10.2026: "Hier waere dann ein Vorschaufenster sehr
// schoen, in welchem der Entwurf nach und nach entsteht und durch den Chat
// geaendert werden kann."
//
// Beides steht hier. Der Entwurf entsteht stueckweise (Strom), und der Chat
// kann ihn aendern - sichtbar umgeschaltet, nicht heimlich: Wer eine Frage
// tippt und damit versehentlich seinen Entwurf umschreibt, hat den Entwurf
// verloren, den er gerade richtig bekommen hatte.
//
// Es stroemt NUR GEPRUEFTES. Dieselbe Regel wie bei der Frage (Befund F05 der
// Zweitpruefung, 05.10.2026): Bis zur ersten abgeschlossenen, belegten
// Aussage steht nur da, DASS gearbeitet wird. Ein Text, der erst dasteht und
// dann verschwindet, ist gezeigt worden.

/** Der Entwurf, der im Vorschaufenster steht. */
let entwurfStand = null;
/** "" | "entsteht" | "aendert" - was gerade laeuft. */
let entwurfLaeuft = "";
/** Der gepruefte Zwischenstand waehrend des Stroms. */
let entwurfVorschautext = "";
/** Schreibt der Chat Aenderungen am Entwurf statt Fragen an die Akte? */
let entwurfAendernAn = false;
/** "text" oder "blatt" - als Fliesstext oder auf dem Briefbogen. */
let entwurfAnsicht = "text";
/** Das Seitenbild des Briefbogens, einmal geholt. `false` = keiner da. */
let blattBild = null;

// ── Das Blatt ──────────────────────────────────────────────────────────────
//
// Aus der Kanzlei am 13.10.2026: "Kann der Entwurf nicht gleich das fertige
// Schreiben mit Briefkopf angeben? Schliesslich muss auch optisch zum Teil
// aktualisiert werden."
//
// Richtig, und es war ein echter Mangel: Wie lang der Brief ist, wo er
// umbricht, ob er in das Anschriftenfeld laeuft - all das sah man erst nach
// dem Herunterladen in Word, und jede Aenderung kostete denselben Weg noch
// einmal.
//
// WAS HIER STEHT, IST EINE ANSICHT UND KEIN ZWEITER BRIEFBOGEN. Seitenmass,
// Raender, die festgesetzten Stuecke des Kopfes und ihre Texte kommen aus der
// Datei der Kanzlei. Nachgezeichnet ist nichts; aendert sie ihren Briefbogen,
// aendert sich die Ansicht mit. Was Word daraus setzt, bleibt die Wahrheit -
// und das sagt die Ansicht auch.

//: Bildpunkte je Millimeter im ungeskalierten Blatt. Nur ein Massstab: Das
//: fertige Blatt wird am Ende auf die Fensterbreite gerechnet.
const BLATT_PX_JE_MM = 4;

//: Ein Punkt sind 0,3528 Millimeter.
const MM_JE_PUNKT = 0.3528;

//: Schon geholte Bilder des Briefbogens, je Teil eine Objekt-Adresse.
const blattBilder = new Map();

/** Ein Bild des Briefbogens holen - MIT Anmeldung.
 *
 * Ein `<img src="…">` traegt keine eigenen Kopfzeilen: Weder die Kennung
 * des Bearbeiters im oertlichen Betrieb noch das Zugangstoken im
 * AWS-Betrieb gingen mit, und der Server antwortete mit 401. Das Blatt
 * stand dann ohne Logo da - ohne dass irgendwo stuende, warum.
 *
 * Deshalb derselbe Weg wie bei jedem anderen Aufruf: holen, als Blob
 * behalten, und dem Bild eine Objekt-Adresse geben. Einmal je Bild.
 */
async function blattBildQuelle(teil) {
  if (blattBilder.has(teil)) return blattBilder.get(teil);
  const antwort = await fetch(
    K.apiBasis + "/api/briefbogen/bild?teil=" + encodeURIComponent(teil),
    { headers: kopfzeilen() });
  if (!antwort.ok) throw new Error(`Bild ${antwort.status}`);
  const adresse = URL.createObjectURL(await antwort.blob());
  blattBilder.set(teil, adresse);
  return adresse;
}

/** Der Text ohne Belegmarken - wie ihn auch die Word-Datei bekommt. */
function ohneBelege(text) {
  return String(text || "")
    .replace(/\[Q:[^\]]*\]/g, "")
    .replace(/[ \t]+([.,;:!?)])/g, "$1")
    .replace(/[ \t]{2,}/g, " ");
}

// ── Aus der Modellsprache wird ein Brief ───────────────────────────────────
//
// Dieselbe Lesart wie `briefzeile` in services/briefbogen.py, und das ist
// der Punkt: Was dort zur Ueberschrift wird, muss hier auch eine sein. Sonst
// zeigt die Vorschau etwas anderes, als auf dem Papier steht - und genau
// darum geht es bei einer Vorschau.
//
// Aus der Kanzlei am 14.10.2026: "Formatierungen waren drin." Das Modell
// schreibt Markdown; bis hierher ging es roh in die Word-Datei und roh aufs
// Blatt.

const BRIEF_UEBERSCHRIFT = /^\s{0,3}(#{1,3})\s+(.*)$/;
const BRIEF_PUNKT = /^\s{0,3}[-*\u2022]\s+(.*)$/;
const BRIEF_NUMMER = /^\s{0,3}(\d{1,2}[.)])\s+(.*)$/;
const BRIEF_TRENNLINIE = /^\s{0,3}([-*_])\s*(?:\1\s*){2,}$/;
const BRIEF_FETT = /\*\*(.+?)\*\*|__(.+?)__/gs;
const BRIEF_KURSIV = /(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])/gs;

/** Ein Text als Stücke [Wortlaut, fett, kursiv]. Fett zuerst. */
function briefStuecke(text) {
  const fertig = [];
  const kursiv = (stueck, fett) => {
    let stelle = 0;
    for (const treffer of stueck.matchAll(BRIEF_KURSIV)) {
      if (treffer.index > stelle) fertig.push([stueck.slice(stelle, treffer.index), fett, false]);
      fertig.push([treffer[1], fett, true]);
      stelle = treffer.index + treffer[0].length;
    }
    if (stelle < stueck.length) fertig.push([stueck.slice(stelle), fett, false]);
  };
  let stelle = 0;
  for (const treffer of String(text).matchAll(BRIEF_FETT)) {
    if (treffer.index > stelle) kursiv(text.slice(stelle, treffer.index), false);
    kursiv(treffer[1] || treffer[2] || "", true);
    stelle = treffer.index + treffer[0].length;
  }
  if (stelle < text.length) kursiv(text.slice(stelle), false);
  return fertig.filter(([w]) => w);
}

/** Eine Zeile des Entwurfs als Bauplan - oder null, wenn sie entfällt. */
function briefzeile(zeile) {
  const roh = String(zeile).replace(/\s+$/, "");
  if (!roh.trim()) return { art: "leer", einzug: false, stuecke: [] };
  if (BRIEF_TRENNLINIE.test(roh)) return null;
  let treffer = BRIEF_UEBERSCHRIFT.exec(roh);
  if (treffer) return { art: "ueberschrift", einzug: false, stuecke: briefStuecke(treffer[2].trim()) };
  treffer = BRIEF_PUNKT.exec(roh);
  if (treffer)
    return { art: "punkt", einzug: true,
             stuecke: [["\u2022\u00a0\u00a0", false, false]].concat(briefStuecke(treffer[1].trim())) };
  treffer = BRIEF_NUMMER.exec(roh);
  if (treffer)
    return { art: "punkt", einzug: true,
             stuecke: [[treffer[1] + "\u00a0\u00a0", false, false]].concat(briefStuecke(treffer[2].trim())) };
  return { art: "absatz", einzug: false, stuecke: briefStuecke(roh) };
}

/** Eine Briefzeile als Element - oder null. Nie innerHTML: Es ist Modelltext. */
function briefZeileZeichnen(zeile) {
  const bauplan = briefzeile(zeile);
  if (bauplan === null) return null;
  const z = document.createElement("div");
  z.className = "blatt-zeile"
    + (bauplan.art === "ueberschrift" ? " blatt-ueberschrift" : "")
    + (bauplan.einzug ? " blatt-einzug" : "");
  if (!bauplan.stuecke.length) { z.textContent = "\u00a0"; return z; }
  for (const [wortlaut, fett, kursiv] of bauplan.stuecke) {
    const teil = document.createElement("span");
    teil.textContent = wortlaut;
    if (fett || bauplan.art === "ueberschrift") teil.style.fontWeight = "600";
    if (kursiv) teil.style.fontStyle = "italic";
    z.appendChild(teil);
  }
  return z;
}

async function blattBildHolen() {
  if (blattBild !== null) return blattBild;
  try {
    blattBild = await api("GET", "/api/briefbogen/ansicht");
  } catch (e) {
    blattBild = false;
    blattFehler = e.message;
  }
  return blattBild;
}

/** Warum es kein Blatt gibt - der Satz sagt, wohin die Vorlage gehoert. */
let blattFehler = "";

function blattSchrift(b) {
  // Die Vorlage nennt eine Schrift; der Browser hat sie vielleicht nicht.
  // Deshalb eine Reihe, die mit der genannten anfaengt und auf einer
  // Serifenschrift endet - eine Ansicht in Arial saehe anders lang aus.
  const name = (b.grundschrift && b.grundschrift.name) || "";
  return (name ? `"${name}", ` : "") + '"Times New Roman", Times, serif';
}

function blattZeile(zeile, grund_pt, mm) {
  const z = document.createElement("div");
  z.className = "blatt-zeile";
  z.textContent = zeile.text || "\u00a0";
  const pt = zeile.groesse_pt || grund_pt;
  z.style.fontSize = (pt * MM_JE_PUNKT * mm) + "px";
  z.style.lineHeight = "1.25";
  if (zeile.fett) z.style.fontWeight = "600";
  if (zeile.ausrichtung === "mitte") z.style.textAlign = "center";
  else if (zeile.ausrichtung === "rechts") z.style.textAlign = "right";
  return z;
}

/** Das Blatt bauen: Briefkopf aus der Vorlage, darunter der Entwurf. */
function blattBauen(b, text) {
  const mm = BLATT_PX_JE_MM;
  const grund = (b.grundschrift && b.grundschrift.groesse_pt) || 10;
  const buehne = document.createElement("div"); buehne.className = "blatt-buehne";
  const blatt = document.createElement("div"); blatt.className = "blatt";
  blatt.style.width = (b.seite_mm.breite * mm) + "px";
  blatt.style.height = (b.seite_mm.hoehe * mm) + "px";
  blatt.style.fontFamily = blattSchrift(b);

  for (const stueck of (b.stuecke || [])) {
    const el = document.createElement("div");
    if (stueck.art === "fluss") {
      // Der Fluss steht im Satzspiegel; die Fusszeile haengt unten.
      el.className = "blatt-fluss";
      el.style.left = (b.raender_mm.links * mm) + "px";
      el.style.width = ((b.seite_mm.breite - b.raender_mm.links - b.raender_mm.rechts) * mm) + "px";
      if (stueck.fuss) el.style.bottom = (8 * mm) + "px";
      else el.style.top = (b.raender_mm.kopf * mm) + "px";
      for (const zeile of stueck.zeilen) el.appendChild(blattZeile(zeile, grund, mm));
      blatt.appendChild(el);
      continue;
    }
    el.style.left = (stueck.x_mm * mm) + "px";
    el.style.top = (stueck.y_mm * mm) + "px";
    el.style.width = (stueck.breite_mm * mm) + "px";
    if (stueck.art === "bild") {
      const bild = document.createElement("img");
      bild.className = "blatt-bild";
      bild.alt = "";
      blattBildQuelle(stueck.bild).then((adresse) => { bild.src = adresse; })
        .catch(() => { /* ein Bild weniger; das Blatt steht trotzdem */ });
      bild.style.width = "100%";
      bild.style.height = (stueck.hoehe_mm * mm) + "px";
      el.className = "blatt-stueck";
      el.appendChild(bild);
    } else if (stueck.art === "linie") {
      el.className = "blatt-linie";
    } else {
      el.className = "blatt-stueck";
      el.style.height = (stueck.hoehe_mm * mm) + "px";
      for (const zeile of stueck.zeilen) el.appendChild(blattZeile(zeile, grund, mm));
    }
    blatt.appendChild(el);
  }

  // Der Entwurf selbst - an derselben Stelle, an der ihn auch die Word-Datei
  // beginnt: `vorlauf_mm` kommt aus demselben Aufruf.
  const koerper = document.createElement("div"); koerper.className = "blatt-koerper";
  // Auf dem Blatt steht, was hinausgeht - und das sind die Belegmarken
  // nicht. Im Fliesstext bleiben sie: Dort wird geprueft.
  koerper.style.left = (b.raender_mm.links * mm) + "px";
  koerper.style.top = ((b.raender_mm.oben + (b.vorlauf_mm || 0)) * mm) + "px";
  koerper.style.width = ((b.seite_mm.breite - b.raender_mm.links - b.raender_mm.rechts) * mm) + "px";
  koerper.style.fontSize = (grund * MM_JE_PUNKT * mm) + "px";
  koerper.style.lineHeight = String(1.15 * ((b.grundschrift && b.grundschrift.zeilenabstand) || 1));
  // Zeile fuer Zeile, genau wie `_absatz` in services/briefbogen.py die
  // Word-Datei baut. NICHT ueber `antworttext`: Der setzt zwei Zeilen
  // hintereinander zu einem Absatz zusammen, Word macht daraus zwei. Dann
  // saehe die Ansicht anders aus als das Blatt - und das ist der eine
  // Fehler, den eine Ansicht nicht machen darf.
  for (const zeile of ohneBelege(text).replace(/\r\n/g, "\n").split("\n")) {
    const z = briefZeileZeichnen(zeile);
    if (z) koerper.appendChild(z);
  }
  blatt.appendChild(koerper);

  buehne.appendChild(blatt);
  // Auf die Fensterbreite rechnen. Ein Blatt, das man nicht ganz sieht, sagt
  // ueber die Laenge nichts aus - und die Laenge ist der Grund, warum es
  // dasteht.
  const anpassen = () => {
    const breite = buehne.clientWidth || buehne.parentElement?.clientWidth || 0;
    if (!breite) return;
    const faktor = breite / (b.seite_mm.breite * mm);
    blatt.style.transform = `scale(${faktor})`;
    buehne.style.height = (b.seite_mm.hoehe * mm * faktor) + "px";
  };
  requestAnimationFrame(anpassen);
  if (typeof ResizeObserver === "function") {
    const beobachter = new ResizeObserver(anpassen);
    beobachter.observe(buehne);
  } else {
    window.addEventListener("resize", anpassen);
  }
  return buehne;
}

function entwurfFensterOeffnen() {
  if (!fensterStand.entwurf) fensterOeffnen("entwurf");
}

/** Der Umschalter ueber dem Eingabefeld - sichtbar, nie stillschweigend. */
function entwurfModusZeigen() {
  const leiste = $("entwurf-modus");
  if (!leiste) return;
  const an = entwurfAendernAn && !!entwurfStand;
  leiste.hidden = !an;
  if (!an) return;
  $("entwurf-modus-text").textContent =
    `Änderung am Entwurf „${entwurfStand.betreff}“ – was hier steht, ändert den Entwurf, es ist keine Frage an die Akte.`;
  const feld = $("frage");
  if (feld) feld.placeholder = "Was soll am Entwurf anders werden? (Eingabetaste ändert)";
  // Auch der Knopf sagt es. Er stand auf "Fragen", waehrend darueber stand,
  // dass hier nicht gefragt wird - und der Knopf ist das Letzte, was man
  // vor dem Abschicken ansieht.
  const senden = $("senden");
  if (senden) senden.textContent = "Ändern";
}

function entwurfModusAus() {
  entwurfAendernAn = false;
  const feld = $("frage");
  if (feld) feld.placeholder = "Frage an die Akte … (Eingabetaste fragt, Umschalt+Eingabe macht eine neue Zeile)";
  const senden = $("senden");
  if (senden) senden.textContent = "Fragen";
  entwurfModusZeigen();
  entwurfFensterZeichnen();
}

/** Das Vorschaufenster zeichnen - aus `entwurfStand` und sonst nichts. */
function entwurfFensterZeichnen() {
  const ziel = $("entwurf-vorschau");
  if (!ziel) return;
  ziel.replaceChildren();
  const marke = $("entwurf-fassung");
  if (marke) {
    marke.textContent = entwurfStand
      ? (entwurfStand.fassung > 1 ? `Fassung ${entwurfStand.fassung}` : "Fassung 1")
      : "";
  }

  if (entwurfLaeuft) {
    const zeile = document.createElement("p"); zeile.className = "entwurf-laeuft";
    zeile.textContent = entwurfLaeuft === "aendert"
      ? "Der Entwurf wird geändert …"
      : "Der Entwurf entsteht …";
    ziel.appendChild(zeile);
    const erklaerung = document.createElement("p"); erklaerung.className = "entwurf-leer";
    erklaerung.textContent = "Es erscheint nur, was schon geprüft ist: Eine Aussage wird "
      + "sichtbar, sobald sie abgeschlossen ist und ihr Beleg steht.";
    ziel.appendChild(erklaerung);
    if (entwurfVorschautext) ziel.appendChild(entwurfInhalt(entwurfVorschautext));
    return;
  }

  if (!entwurfStand) {
    const leer = document.createElement("p"); leer.className = "entwurf-leer";
    leer.textContent = "Noch kein Entwurf. Oben rechts auf „Entwurf“ – er entsteht dann hier, "
      + "Stück für Stück, und lässt sich von hier aus über den Chat ändern.";
    ziel.appendChild(leer);
    return;
  }

  const e = entwurfStand;
  const kopf = document.createElement("div"); kopf.className = "entwurf-betreff";
  kopf.textContent = e.betreff;
  ziel.appendChild(kopf);

  if (!nebenfenster) ziel.appendChild(entwurfAnsichtWahl());

  const hb = hinweiseBlock((e.hinweise || []).concat(["Entwurf – anwaltliche Prüfung erforderlich."]));
  if (hb) ziel.appendChild(hb);

  ziel.appendChild(entwurfInhalt(e.text));

  // Im Nebenfenster keine Knoepfe: Es ist ein Spiegel, keine zweite
  // Arbeitsflaeche. In einer Mandatsakte muss klar sein, WO gearbeitet wird.
  if (!nebenfenster) ziel.appendChild(entwurfKnoepfe(e));
  ziel.appendChild(fusszeile(e));
}

/** Fliesstext oder Blatt - die Wahl steht oben im Fenster. */
function entwurfAnsichtWahl() {
  const leiste = document.createElement("div"); leiste.className = "entwurf-ansicht";
  for (const [wert, wort, erklaerung] of [
      ["text", "Text", "Nur der Wortlaut – gut zum Lesen und Ändern"],
      ["blatt", "Blatt", "Auf dem Briefbogen der Kanzlei – so lang wird das Schreiben"]]) {
    const knopf = document.createElement("button");
    knopf.type = "button";
    knopf.className = "mini leise" + (entwurfAnsicht === wert ? " an" : "");
    knopf.textContent = wort;
    knopf.title = erklaerung;
    knopf.setAttribute("aria-pressed", String(entwurfAnsicht === wert));
    knopf.addEventListener("click", () => mitKnopf(null, async () => {
      entwurfAnsicht = wert;
      if (wert === "blatt") await blattBildHolen();
      entwurfFensterZeichnen();
    }));
    leiste.appendChild(knopf);
  }
  return leiste;
}

/** Der Entwurfstext - als Fliesstext oder auf dem Blatt. */
function entwurfInhalt(text) {
  if (entwurfAnsicht === "blatt" && blattBild) {
    const rahmen = document.createElement("div"); rahmen.className = "blatt-rahmen";
    rahmen.appendChild(blattBauen(blattBild, text));
    const fuss = document.createElement("div"); fuss.className = "blatt-fuss";
    const satz = document.createElement("p"); satz.className = "blatt-fuss-hinweis";
    satz.textContent = blattHinweis(blattBild);
    fuss.appendChild(satz);
    if (!nebenfenster) {
      const stellen = document.createElement("button");
      stellen.type = "button"; stellen.className = "mini leise";
      stellen.textContent = "Blatt einstellen";
      stellen.title = "Textbeginn, Schrift, Größe und Zeilenabstand";
      stellen.addEventListener("click", blattEinstellenOeffnen);
      fuss.appendChild(stellen);
    }
    rahmen.appendChild(fuss);
    return rahmen;
  }
  const block = document.createElement("div"); block.className = "entwurf-text";
  if (entwurfAnsicht === "blatt" && blattBild === false) {
    const satz = document.createElement("p"); satz.className = "entwurf-leer";
    satz.textContent = blattFehler || "Es ist kein Briefbogen hinterlegt.";
    block.appendChild(satz);
  }
  // OHNE Belegmarken. Aus der Kanzlei am 15.10.2026: „Die Quellen gehoeren
  // nicht mehr in den Fliesstext des Entwurfs, da der Entwurf ansonsten nicht
  // brauchbar ist." Der Entwurf ist das Schriftstueck, das das Haus verlaesst
  // - auf dem Blatt und in der Word-Datei standen die Marken laengst nicht
  // mehr, nur in dieser einen Ansicht noch. Jetzt nirgends.
  //
  // Verloren ist nichts: Gespeichert bleibt der Text mit Marken, und jede
  // Fundstelle steht im Fenster „Belege“ - dort mit Dokument, Seite und
  // Wortlaut, also mehr als eine Kennung im Satz je sagen koennte.
  antworttext(block, ohneBelege(text));
  return block;
}

/** Was unter dem Blatt steht - und ob die Schrift ueberhaupt da ist.
 *
 * Eine Ansicht in einer Ersatzschrift sagt ueber die Laenge wenig: Franklin
 * Gothic Book und Times New Roman brauchen fuer denselben Satz
 * unterschiedlich viel Platz. Fehlt die Schrift auf diesem Rechner, steht
 * das hier - und nicht erst in Word.
 */
function blattHinweis(b) {
  const name = (b.grundschrift && b.grundschrift.name) || "";
  let satz = "Ansicht, gesetzt aus Ihrer Word-Vorlage (" + (b.datei || "")
           + "). Das Blatt baut Word; Zeilenumbruch und Schriftschnitt können geringfügig abweichen.";
  if (name && !schriftVorhanden(name)) {
    satz += " Die Schrift „" + name + "“ ist auf diesem Rechner nicht vorhanden – "
          + "die Ansicht zeigt eine Ersatzschrift, die Länge kann deshalb abweichen.";
  }
  return satz;
}

/** Hat dieser Rechner die Schrift?
 *
 * Gemessen und nicht geraten: Derselbe Satz wird einmal in der gesuchten
 * Schrift mit Rueckfall auf eine Standardschrift gezeichnet und einmal nur
 * in der Standardschrift. Sind beide gleich breit, hat der Browser auf die
 * Standardschrift zurueckgegriffen - die gesuchte gibt es also nicht.
 */
const schriftGemessen = new Map();
function schriftVorhanden(name) {
  if (schriftGemessen.has(name)) return schriftGemessen.get(name);
  let da = true;
  try {
    const flaeche = document.createElement("canvas").getContext("2d");
    const probe = "ABCDEFGHIJKLMnopqrstuvwxyz 0123456789";
    da = ["monospace", "serif", "sans-serif"].some((ersatz) => {
      flaeche.font = `16px ${ersatz}`;
      const ohne = flaeche.measureText(probe).width;
      flaeche.font = `16px "${name}", ${ersatz}`;
      return flaeche.measureText(probe).width !== ohne;
    });
  } catch (e) { /* kein Canvas: dann lieber nichts behaupten */ }
  schriftGemessen.set(name, da);
  return da;
}

function blattEinstellenOeffnen() {
  const b = blattBild;
  if (!b) return;
  const gesetzt = b.einstellungen || {};
  const vorlage = b.aus_vorlage || {};
  const setzen = (id, wert, hinweis) => {
    const feld = $(id);
    feld.value = (wert === null || wert === undefined || wert === "") ? "" : wert;
    feld.placeholder = "wie in der Vorlage: " + hinweis;
  };
  setzen("blatt-beginn", gesetzt.textbeginn_mm, (vorlage.textbeginn_mm || 0) + " mm");
  setzen("blatt-schrift", gesetzt.schrift, vorlage.name || "—");
  setzen("blatt-groesse", gesetzt.groesse_pt, (vorlage.groesse_pt || 0) + " pt");
  setzen("blatt-abstand", gesetzt.zeilenabstand, "einfach (1,0)");
  $("blatt-dialog").showModal();
}

async function blattEinstellen(zuruecksetzen) {
  const zahl = (id) => {
    const roh = ($(id).value || "").trim().replace(",", ".");
    const wert = Number(roh);
    return roh && Number.isFinite(wert) ? wert : null;
  };
  const daten = zuruecksetzen
    ? { textbeginn_mm: null, schrift: "", groesse_pt: null, zeilenabstand: null }
    : { textbeginn_mm: zahl("blatt-beginn"), schrift: ($("blatt-schrift").value || "").trim(),
        groesse_pt: zahl("blatt-groesse"), zeilenabstand: zahl("blatt-abstand") };
  blattBild = await api("PUT", "/api/briefbogen/einstellungen", daten);
  entwurfFensterZeichnen();
  nebenfensterGleichziehen();
  melden(zuruecksetzen ? "Zurückgesetzt – es gilt wieder die Vorlage." : "Übernommen.");
}

function entwurfKnoepfe(e) {
  const leiste = document.createElement("div"); leiste.className = "entwurf-knoepfe";
  const fertig = e.status && e.status !== "entwurf";

  if (!fertig) {
    const aendern = document.createElement("button");
    aendern.className = "mini" + (entwurfAendernAn ? " an" : "");
    aendern.textContent = entwurfAendernAn ? "Ändern: an" : "Über den Chat ändern";
    aendern.title = entwurfAendernAn
      ? "Zurück zu Fragen an die Akte"
      : "Was Sie unten tippen, ändert dann den Entwurf statt die Akte zu befragen";
    aendern.addEventListener("click", () => {
      entwurfAendernAn = !entwurfAendernAn;
      entwurfModusZeigen();
      entwurfFensterZeichnen();
      if (entwurfAendernAn) $("frage").focus();
    });
    leiste.appendChild(aendern);

    if ((e.vorfassungen || []).length) {
      const zurueck = document.createElement("button"); zurueck.className = "mini leise";
      zurueck.textContent = `Zurück zu Fassung ${e.vorfassungen[e.vorfassungen.length - 1].nummer}`;
      zurueck.title = "Die Änderung zurücknehmen – der Text von vorhin steht wieder da";
      zurueck.addEventListener("click", () => mitKnopf(zurueck, entwurfZuruecknehmen));
      leiste.appendChild(zurueck);
    }

    const frei = document.createElement("button"); frei.className = "mini";
    frei.textContent = "Freigeben und in jurnodes ablegen";
    frei.addEventListener("click", () => mitKnopf(frei, () => entwurfFreigeben(e)));
    leiste.appendChild(frei);
  }

  leiste.appendChild(briefbogenKnopf(e.id));
  return leiste;
}

async function entwurfFreigeben(e) {
  if (!confirm("Diesen von der KI vorbereiteten Entwurf als Vermerk in die jurnodes-Akte schreiben?")) return;
  // Die Pruefsumme deckt seit dem 05.10.2026 Akte, Art, Betreff UND Text ab.
  // Vorher nur den Text - ein in einem anderen Fenster geaenderter Betreff
  // ging damit ungesehen in den Vermerk (Befund F06 der Zweitpruefung).
  const f = await api("POST", `/api/entwuerfe/${e.id}/freigabe`,
                      { bestaetigung: true, freigabe_pruefsumme: e.freigabe_pruefsumme });
  entwurfStand = f;
  entwurfModusAus();
  nebenfensterGleichziehen();
  melden(`In jurnodes abgelegt (${f.jurnodes_referenz || ""}).`);
}

async function entwurfZuruecknehmen() {
  entwurfStand = await api("POST", `/api/entwuerfe/${entwurfStand.id}/zuruecknehmen`);
  belegeMerken(entwurfStand.quellen);
  entwurfFensterZeichnen();
  nebenfensterGleichziehen();
  melden(`Zurück bei Fassung ${entwurfStand.fassung}.`);
}

/** Der gemeinsame Leser fuer beide Stroeme - Entstehen und Aendern. */
async function entwurfStromLesen(pfad, rumpf, was) {
  entwurfLaeuft = was;
  entwurfVorschautext = "";
  entwurfFensterOeffnen();
  entwurfFensterZeichnen();
  nebenfensterGleichziehen();
  try {
    const resp = await fetch(K.apiBasis + pfad, {
      method: "POST", headers: kopfzeilen(), body: JSON.stringify(rumpf),
    });
    if (!resp.ok || !resp.body) {
      let f = null; try { f = await resp.json(); } catch (e) { /* kein JSON */ }
      throw new Error((f && f.fehler) || `Fehler ${resp.status}`);
    }
    const leser = resp.body.getReader();
    const entschluessler = new TextDecoder();
    let puffer = "", fertig = null, fehler = null;
    for (;;) {
      const { value, done } = await leser.read();
      if (done) break;
      puffer += entschluessler.decode(value, { stream: true });
      const zeilen = puffer.split("\n");
      puffer = zeilen.pop();
      for (const zeile of zeilen) {
        if (!zeile.trim()) continue;
        let ereignis = null;
        try { ereignis = JSON.parse(zeile); } catch (e) { continue; }
        if (ereignis.type === "geprueft") {
          entwurfVorschautext = ereignis.text;
          entwurfFensterZeichnen();
          nebenfensterGleichziehen();
        } else if (ereignis.type === "fertig") {
          fertig = ereignis.entwurf;
        } else if (ereignis.type === "fehler") {
          fehler = ereignis.detail;
        }
      }
    }
    if (fehler) throw new Error(fehler);
    if (!fertig) throw new Error("Der Entwurf kam nicht vollständig an.");
    entwurfStand = fertig;
    belegeMerken(fertig.quellen);
    return fertig;
  } finally {
    // Auch wenn es schiefging: Das Fenster darf nicht in "entsteht …"
    // stehenbleiben. Was dasteht, ist dann die letzte gute Fassung.
    entwurfLaeuft = "";
    entwurfVorschautext = "";
    entwurfFensterZeichnen();
    nebenfensterGleichziehen();
    ladeStatus();
  }
}

async function entwurfStarten(art, anweisung, empfaenger, auftrag) {
  const e = await entwurfStromLesen(
    `/api/sitzungen/${sitzung.sitzung.id}/entwuerfe/stream`,
    { art, anweisung, empfaenger, auftrag: auftrag || "" }, "entsteht");
  // Eine Zeile im Chat, damit der Verlauf weiss, dass hier etwas geschah -
  // der Entwurf selbst steht im Vorschaufenster und nicht zweimal.
  const karte = threadKarte("ai");
  const titel = document.createElement("div"); titel.className = "titelzeile";
  titel.textContent = "Entwurf: " + e.betreff; karte.appendChild(titel);
  const inhalt = document.createElement("div"); inhalt.className = "inhalt";
  const p = document.createElement("p");
  p.textContent = "Der Entwurf steht im Vorschaufenster rechts. Dort lässt er sich "
    + "über den Chat ändern, auf den Briefbogen setzen und freigeben.";
  inhalt.appendChild(p);
  karte.appendChild(inhalt);
  const fuss = document.createElement("div"); fuss.className = "fuss";
  const hin = document.createElement("button"); hin.className = "mini";
  hin.textContent = "Zum Entwurf";
  hin.addEventListener("click", () => { entwurfFensterOeffnen(); entwurfFensterZeichnen(); });
  fuss.appendChild(hin);
  // Aus der Kanzlei: "Ich denke auch einen Wissenstempel bauen, dass sich KI
  // gleiche Vorgaenge merkt." Der Weg dorthin faengt hier an - bei der
  // Anweisung, die gerade getippt wurde. Ohne Anweisung gibt es nichts zu
  // verallgemeinern, dann bleibt der Knopf weg.
  if (K.auftraegeAktiv && anweisung) {
    const merk = document.createElement("button"); merk.className = "mini";
    merk.textContent = "Als eigenen Auftrag vormerken";
    merk.addEventListener("click", () => mitKnopf(merk, () => auftragVormerken(e.id, anweisung)));
    fuss.appendChild(merk);
  }
  karte.appendChild(fuss);
}

/** Der Chat aendert den Entwurf. Die vorige Fassung bleibt erhalten. */
async function entwurfAendern(anweisung) {
  const vorher = entwurfStand;
  nutzerkarte(anweisung);
  const e = await entwurfStromLesen(
    `/api/sitzungen/${sitzung.sitzung.id}/entwuerfe/${vorher.id}/aendern/stream`,
    { anweisung }, "aendert");
  const karte = threadKarte("ai");
  const inhalt = document.createElement("div"); inhalt.className = "inhalt";
  const p = document.createElement("p");
  p.textContent = `Entwurf geändert – Fassung ${e.fassung}. Er steht im Vorschaufenster; `
    + `„Zurück zu Fassung ${e.fassung - 1}“ nimmt die Änderung zurück.`;
  inhalt.appendChild(p);
  karte.appendChild(inhalt);
}

// ── Was noch nicht fertig ist, sagt es selbst ──────────────────────────────
//
// Aus der Kanzlei am 14.10.2026: "Briefbogen funktioniert noch nicht. Bitte
// noch als Button kennzeichnen - rot und ‚noch nicht fertig' beim Anklicken."
//
// Zu Recht, und es ist mehr als eine Farbe: In einer Kanzlei arbeiten zwei
// Anwaelte mit demselben Programm. Was der eine als unfertig kennt, sieht
// der andere als fertigen Knopf - und verlaesst sich darauf. Deshalb steht
// es am Knopf und nicht in einem Merkzettel.
//
// Der Weg bleibt offen: Der Hinweis fragt, ob es trotzdem versucht werden
// soll. Ein gesperrter Knopf sagt nicht, WAS fehlt - und solange niemand
// ihn drueckt, erfaehrt es auch niemand.

const BRIEFBOGEN_UNFERTIG =
  "Der Weg auf den Briefbogen ist noch nicht fertig.\n\n"
  + "Was schon steht: Ihre Word-Vorlage wird geöffnet, der Entwurf kommt in "
  + "ihren leeren Rumpf, Kopf- und Fußzeile bleiben unverändert.\n\n"
  + "Was noch fehlt: die Anschrift des Empfängers und die Betreffzeile an "
  + "ihrem Platz. Und die Vorlage muss einmal hinterlegt sein — mit "
  + "BRIEFBOGEN-HINTERLEGEN.bat.\n\n"
  + "Trotzdem versuchen?";

/** Der Knopf mit der roten Kennzeichnung. */
function briefbogenKnopf(entwurfId) {
  const knopf = document.createElement("button");
  knopf.className = "mini unfertig";
  knopf.textContent = "Auf Briefbogen (Word) – noch nicht fertig";
  knopf.title = "Diese Funktion ist noch in Arbeit.";
  knopf.addEventListener("click", () => {
    if (!confirm(BRIEFBOGEN_UNFERTIG)) return;
    mitKnopf(knopf, () => briefbogenHolen(entwurfId));
  });
  return knopf;
}

/** Den Entwurf als Word-Datei auf dem Briefbogen holen.
 *
 * Nicht ueber `api`: Was zurueckkommt, ist kein JSON, sondern eine Datei.
 * Gespeichert wird sie nicht vom Programm - der Browser fragt, wohin.
 */
async function briefbogenHolen(entwurfId) {
  const antwort = await fetch(K.apiBasis + `/api/entwuerfe/${entwurfId}/briefbogen`,
                              { headers: kopfzeilen() });
  if (!antwort.ok) {
    let f = null; try { f = await antwort.json(); } catch (e) { /* keine JSON-Antwort */ }
    throw new Error((f && f.fehler) || `Fehler ${antwort.status}`);
  }
  const blob = await antwort.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = `Entwurf-${entwurfId}.docx`;
  document.body.appendChild(a); a.click(); a.remove();
  // Aufraeumen: Ohne das bleibt der ganze Entwurf im Speicher des Browsers
  // liegen, bis die Seite neu geladen wird.
  setTimeout(() => URL.revokeObjectURL(url), 10000);
  // Die Hinweise der Belegpruefung stehen seit dem 14.10.2026 nicht mehr IM
  // Schreiben - ein Brief, an dem vor dem Versand noch etwas zu loeschen
  // ist, ist kein fertiger Brief. Dafuer stehen sie hier, im Augenblick des
  // Herunterladens, und im Vorschaufenster daneben.
  const offen = ((entwurfStand && entwurfStand.hinweise) || []).length;
  melden("Der Entwurf liegt als Word-Datei im Download-Ordner."
    + (offen ? ` ${offen} Hinweis(e) der Belegprüfung stehen im Vorschaufenster – `
             + "sie sind nicht im Schreiben." : ""));
}

// ── Aus einer Anweisung ein Muster machen ──────────────────────────────────
// Angelegt wird hier nichts. Der Dienst holt den Vorschlag, der Dialog zeigt
// ihn - die Datei entsteht erst durch den Klick auf "Auftrag anlegen".

async function auftragVormerken(entwurfId, anweisung) {
  const d = await api("POST", `/api/sitzungen/${sitzung.sitzung.id}/auftragsvorschlag`,
                      { entwurf_id: entwurfId, anweisung });
  const v = d.vorschlag || {};
  $("vorschlag-name").value = v.dateiname || "";
  $("vorschlag-text").value = v.anweisung || "";
  const h = $("vorschlag-hinweis");
  h.textContent = v.hinweis ? "Hinweis aus dem Vorschlag: " + v.hinweis : "";
  h.hidden = !v.hinweis;
  $("vorschlag-dialog").showModal();
}

async function auftragAnlegen() {
  const name = $("vorschlag-name").value.trim(), text = $("vorschlag-text").value.trim();
  const a = await api("POST", "/api/auftraege", { name, text });
  $("vorschlag-dialog").close();
  melden(`Auftrag „${a.label}“ angelegt – er steht ab jetzt bei jedem Entwurf zur Auswahl.`);
}

async function packStarten() {
  const e = await api("POST", `/api/sitzungen/${sitzung.sitzung.id}/pack`, {});
  for (const b of e.befunde) belegeMerken(b.belege);
  const karte = threadKarte("ai");
  const titel = document.createElement("div"); titel.className = "titelzeile";
  titel.textContent = "Prüfliste: " + e.titel; karte.appendChild(titel);
  const inhalt = document.createElement("div"); inhalt.className = "inhalt";
  const summe = document.createElement("p"); summe.className = "pack-summe";
  summe.textContent = `${e.vorhanden} von ${e.befunde.length} belegt · ${e.fehlt_pflicht} Pflichtpunkt(e) offen`;
  inhalt.appendChild(summe);
  const liste = document.createElement("div"); liste.className = "pack-liste";
  for (const b of e.befunde) {
    const zeile = document.createElement("div"); zeile.className = "pack-zeile " + b.status;
    const dot = document.createElement("span"); dot.className = "pack-dot " + (b.status === "vorhanden" ? "g" : (b.pflicht ? "r" : "a"));
    const haupt = document.createElement("div"); haupt.className = "pack-haupt";
    const t = document.createElement("div"); t.className = "pack-titel";
    t.textContent = b.titel + (b.pflicht ? "" : " (optional)");
    haupt.appendChild(t);
    if (b.status === "vorhanden") {
      const bz = document.createElement("div"); bz.className = "pack-belege"; belegChips(bz, b.belege); haupt.appendChild(bz);
    } else if (b.hinweis) {
      const h = document.createElement("div"); h.className = "pack-hinweis"; h.textContent = b.hinweis; haupt.appendChild(h);
    }
    zeile.append(dot, haupt); liste.appendChild(zeile);
  }
  inhalt.appendChild(liste);
  if (e.offene_schritte.length) {
    const h = document.createElement("div"); h.className = "titelzeile"; h.style.fontSize = "13px"; h.textContent = "Nächste Schritte"; inhalt.appendChild(h);
    const ul = document.createElement("ul"); for (const s of e.offene_schritte) { const li = document.createElement("li"); li.textContent = s; ul.appendChild(li); } inhalt.appendChild(ul);
  }
  karte.appendChild(inhalt);
}

// Der Weg zurueck zur Aktenliste.
//
// Aus der Kanzlei: "es gibt anscheinend keinen Button wo man die Akte auf der
// Website aendern kann". Stimmte - der einzige Weg hiess "Sitzung schliessen"
// und steckte im Menue "Mehr". Wer eine Akte geoeffnet hatte, sass fest.
//
// Gewechselt wird ueber dasselbe Schliessen, nicht daran vorbei: Die Texte der
// einen Akte duerfen nicht in der naechsten stehenbleiben. Deshalb kostet der
// Wechsel das begonnene Gespraech - und deshalb wird vorher gefragt, sobald
// eines da ist.
async function akteWechseln() {
  // Zweiter Riegel, unabhaengig von der Sperre am Knopf. Ein gesperrter Knopf
  // ist eine Bitte; das hier ist die Zusage.
  if (liestGerade) {
    melden("Es werden gerade Dokumente gelesen. Bitte abwarten oder unten rechts anhalten.", true);
    return;
  }
  if ($("thread").querySelector(".karte-c") && !confirm(schlussfrage())) return;
  await sitzungSchliessen();
}

// Die Rückfrage vor dem Schließen. Sie sagt nicht mehr nur, was gelöscht wird,
// sondern zuerst, was bleibt – und mit welchen Zahlen. "Was im Gedächtnis
// steht, bleibt erhalten" ist eine Zusage; "50 Dokumente, 68 Zeilen Chronologie,
// 4 Antworten" ist eine Auskunft.
function schlussfrage() {
  const g = (sitzung && sitzung.gedaechtnis) || {};
  const bleibt = K.gedaechtnisAktiv && g.vorhanden
    ? "Im Gedächtnis bleiben: der Lebenssachverhalt, "
      + `${(g.eintraege || []).length} Dokument(e), `
      + `${(g.chronologie || []).length} Zeile(n) Chronologie und `
      + `${g.fragen || 0} geprüfte Antwort(en).`
    : "Zu dieser Akte besteht kein Gedächtnis – gespeichert wird deshalb nichts.";
  return "Akte schließen?\n\n" + bleibt
    + "\n\nNicht gespeichert werden Entwürfe und Eingangsprüfungen aus diesem Gespräch. "
    + "Wer einen Entwurf noch braucht, kopiert ihn vorher heraus.";
}

async function sitzungSchliessen() {
  // Aus der Kanzlei: "beim schließen sollte das bearbeitete gespeichert werden
  // und anhand einer meldung kenntlich gemacht werden."
  //
  // Erst sichern, dann schließen. Andersherum wäre die Sitzung schon weg, bevor
  // feststeht, ob das Dauerhafte wirklich im Speicher liegt – und ein
  // Schreibfehler fiele erst am nächsten Morgen auf.
  let bericht = null, fehler = null;
  if (sitzung) {
    try { bericht = await api("POST", `/api/sitzungen/${sitzung.sitzung.id}/gedaechtnis/sichern`); }
    catch (e) { fehler = e.message; }
    try { await api("DELETE", `/api/sitzungen/${sitzung.sitzung.id}`); } catch (e) { /* abgelaufen */ }
  }
  sitzung = null; passagenIndex = {}; belegKennungen = new Set(); belegQuellen = {}; chronoAusAnalyse = [];
  // Der Entwurf gehoert zu dieser Akte. Bliebe er stehen, waere beim
  // naechsten Oeffnen ein Entwurf im Fenster, der zu einer anderen Akte
  // gehoert - bei Mandatsakten die gefaehrlichste Art von Anzeige.
  entwurfStand = null; entwurfLaeuft = ""; entwurfVorschautext = "";
  entwurfModusAus();
  // Die Wahl gehoert zur Akte, die gerade offen war.
  bibGebietswahl = "";
  // Den Nebenfenstern sagen, dass hier nichts mehr offen ist. Sonst
  // zeigten sie weiter eine Akte, die geschlossen wurde - und das waere
  // bei Mandatsakten die gefaehrlichste Art von Anzeige.
  if (kanal) { try { kanal.postMessage({ was: "zu" }); } catch (e) {} }
  // Ein Rückgängig zeigt auf die geschlossene Sitzung und würde ins Leere
  // greifen. Es stehen zu lassen wäre ein Versprechen, das nicht mehr gilt.
  rueckgaengigVerbergen();
  $("akte-leiste").hidden = true;
  einstiegZeigen();
  // Nur eine Meldung, nicht zwei: Die kurze Einblendung unten rechts sagte
  // dasselbe wie der Kasten auf der Startseite und war nach drei Sekunden weg.
  // Der Kasten bleibt stehen, bis die naechste Akte geoeffnet wird.
  schlussHinweisZeigen(schlussmeldung(bericht, fehler), !!fehler);
}

// Was gesichert wurde – benannt, nicht behauptet. Die Zahlen stammen aus dem,
// was der Speicher zurückgibt, nicht aus dem, was die Oberfläche zu wissen
// glaubte.
function schlussmeldung(bericht, fehler) {
  if (fehler)
    return "Nicht gespeichert: " + fehler
      + " Die Sitzung ist geschlossen; das Gedächtnis kann unvollständig sein.";
  if (!bericht || !bericht.gesichert)
    return (bericht && bericht.aktiv)
      ? "Zu dieser Akte besteht noch kein Gedächtnis, gespeichert wurde deshalb nichts. "
        + "Die Sitzung ist geschlossen und die temporären Texte sind gelöscht."
      : "Sitzung geschlossen, temporäre Texte gelöscht. Gespeichert wurde nichts – "
        + "das Gedächtnis ist nicht aktiviert.";
  const teile = [];
  if ((bericht.lebenssachverhalt || "").length)
    teile.push(`Lebenssachverhalt (${umfangKurz(bericht.lebenssachverhalt.length)})`);
  if ((bericht.eintraege || []).length) teile.push(`${bericht.eintraege.length} Dokument(e)`);
  if ((bericht.chronologie || []).length) teile.push(`${bericht.chronologie.length} Zeile(n) Chronologie`);
  if (bericht.fragen) teile.push(`${bericht.fragen} geprüfte Antwort(en)`);
  const wo = bericht.aktenzeichen ? " zu " + bericht.aktenzeichen : "";
  return `Gespeichert im Gedächtnis${wo}: ` + (teile.length ? teile.join(", ") : "nichts Belegtes")
    + ". Entwürfe und Eingangsprüfungen werden nicht gespeichert.";
}

function schlussHinweisZeigen(text, fehler) {
  const el = $("schluss-hinweis");
  if (!el) return;
  el.textContent = text || "";
  el.className = "schluss-hinweis" + (fehler ? " fehler" : "");
  el.hidden = !text;
}

// ── Start ────────────────────────────────────────────────────────────────────

document.addEventListener("DOMContentLoaded", () => {
  $("nutzer-wechseln").addEventListener("click", (ev) => mitKnopf(ev.target, benutzerWechseln));
  $("verlauf-leeren").addEventListener("click", verlaufLeeren);
  for (const knopf of document.querySelectorAll("[data-fenster]"))
    knopf.addEventListener("click", () => fensterUmschalten(knopf.dataset.fenster));
  $("ged-einlesen").addEventListener("click", (ev) => mitKnopf(ev.target, gedaechtnisEinlesen));
  $("ged-abbrechen").addEventListener("click", (ev) => {
    // Die laufende Portion wird zu Ende gelesen - sie ist bezahlt, und ihr
    // Ergebnis wegzuwerfen waere die teuerste Art anzuhalten.
    einlesenAbbrechen = true;
    ev.target.disabled = true;
    $("ged-fortschritt-dauer").textContent = "hält nach dieser Portion an …";
  });
  $("lese-anhalten").addEventListener("click", (ev) => {
    // Wie beim Einlesen: Die laufende Portion wird zu Ende gelesen. Sie ist
    // bezahlt - bei einem Scan sogar mit Texterkennung -, und ihr Ergebnis
    // wegzuwerfen waere die teuerste Art anzuhalten.
    lesenAbbrechen = true;
    ev.target.disabled = true;
    $("lese-dauer").textContent = "hält nach dieser Portion an …";
  });
  for (const los of document.querySelectorAll("[data-fenster-los]"))
    los.addEventListener("click", () => nebenfensterOeffnen(los.dataset.fensterLos));
  for (const pfeil of document.querySelectorAll("[data-fenster-zu]"))
    pfeil.addEventListener("click", () => fensterSchliessen(pfeil.dataset.fensterZu));
  // Der Nachweis stand im Menue "Mehr" der Arbeitsflaeche, zwischen
  // Eingangspruefung und Aktenabschluss. Er gehoert aber nicht zur Arbeit an
  // einer Akte, sondern zur Rechenschaft ueber alle - deshalb steht er jetzt
  // bei der Verwaltung und nicht mehr im Weg.
  $("nachweis-oeffnen").addEventListener("click", (ev) => mitKnopf(ev.target, nachweisZeigen));
  // Die beiden Kreuze gehören NICHT zur Anmeldung.
  //
  // Aus der Kanzlei am 13.10.2026: „Fehlermeldung nimmt viel Platz weg und
  // läßt sich nicht schließen. Auch nicht mit dem Kreuz."
  //
  // Sie standen beide innerhalb von `if (AWS_MODUS)`. Die Kanzlei läuft mit
  // JUSPERFECT_BETRIEBSART=lokal, also ist AWS_MODUS falsch - und die
  // Kreuze bekamen nie einen Anschluss. Ein Knopf, der dasteht und nichts
  // tut, ist schlimmer als keiner: Man klickt ihn und zweifelt an sich.
  //
  // Warum sie dort landeten: Der Block begann mit der Anmeldung, und was
  // danach dazukam, wurde darunter geschrieben. Eine Einrückung ist kein
  // Zusammenhang.
  const astZu = $("arbeitsstand-zu");
  if (astZu) astZu.addEventListener("click", arbeitsstandSchliessen);
  const ubZu = $("uebernahme-zu");
  if (ubZu) ubZu.addEventListener("click", () => { $("uebernahme").hidden = true; });
  if (AWS_MODUS) {
    $("anmelden-aws").hidden = false;
    $("anmeldung").addEventListener("click", () => (angemeldet() ? abmelden() : anmeldungStarten()));
    anmeldungAbschliessen()
      .catch(() => anmeldeFehler("Die Anmeldung ist fehlgeschlagen."))
      .finally(async () => {
        anmeldungAnzeigen();
        if (await ladeStatus()) einstiegZeigen(); else anmeldenZeigen();
      });
  } else {
    $("anmelden-lokal").hidden = false;
    $("nutzer-eigen").addEventListener("keydown", (ev) => {
      if (ev.key !== "Enter") return;
      ev.preventDefault();
      mitKnopf(null, () => benutzerWaehlen($("nutzer-eigen").value));
    });
    // Wer gestern hier gearbeitet hat, soll nicht jeden Morgen neu waehlen -
    // aber nur, wenn die Kennung noch gilt. Sonst steht die Auswahl.
    (async () => {
      await nutzerlisteLaden();
      let zuletzt = "";
      try { zuletzt = localStorage.getItem("jusperfect.nutzer") || ""; } catch (e) {}
      if (zuletzt) {
        $("nutzer").value = zuletzt;
        if (await ladeStatus()) { einstiegZeigen(); return; }
        $("nutzer").value = "";
      }
      anmeldenZeigen();
    })();
  }
  $("suchen").addEventListener("click", (ev) => mitKnopf(ev.target, aktenSuchen));
  $("posteingang-oeffnen").addEventListener("click", (ev) => mitKnopf(ev.target, posteingangOeffnen));
  $("posteingang-pruefen").addEventListener("click", (ev) => mitKnopf(ev.target, posteingangPruefen));
  $("suche").addEventListener("keydown", (ev) => { if (ev.key === "Enter") mitKnopf($("suchen"), aktenSuchen); });
  // "alle anhaken" laesst die Ausgeschlossenen aus - genau dafuer gibt es die
  // Liste. Wer sie trotzdem will, hakt sie einzeln an oder sucht nach ihnen
  // und nimmt sie dann mit; ein zweiter Klick auf denselben Knopf holt sie
  // ebenfalls, wenn sonst schon alles drin ist.
  $("alle-rein").addEventListener("click", () => {
    const sichtbar = explorerSichtbar();
    const offen = sichtbar.filter((d) => !nichtVorwaehlenGrund(d));
    // Ist schon alles Unverdaechtige drin, meint der Klick die Uebrigen.
    const ziel = offen.every((d) => explorer.gewaehlt.has(d.id)) ? sichtbar : offen;
    for (const d of ziel) explorer.gewaehlt.add(d.id);
    if (ziel !== sichtbar && ziel.length < sichtbar.length)
      melden(`${sichtbar.length - ziel.length} nicht vorgewählt (Rechnung, RSV …) – `
             + "noch einmal klicken holt sie dazu.");
    explorerRendern();
  });
  $("alle-raus").addEventListener("click", () => { for (const d of explorerSichtbar()) explorer.gewaehlt.delete(d.id); explorerRendern(); });
  $("explorer-suche").addEventListener("input", explorerRendern);
  $("ged-suche").addEventListener("input", gedExplorerZeichnen);
  // Der Knopf schliesst den Dialog NICHT mehr: Waehrend gelesen wird, bleibt
  // die Gegenueberstellung stehen und haekelt Datei fuer Datei ab. Geschlossen
  // wird erst, wenn alles gelesen ist - oder auf einen zweiten Klick, wenn
  // etwas nicht ging.
  $("explorer-uebernehmen").addEventListener("click", (ev) => {
    ev.preventDefault();
    mitKnopf(null, explorerUebernehmen);
  });
  $("explorer-anhalten").addEventListener("click", () => {
    lesenAbbrechen = true;
    $("explorer-anhalten").disabled = true;
    explorerLesenZeigen("Wird angehalten \u2026 die laufende Portion l\u00e4uft noch zu Ende.");
  });
  $("frage-form").addEventListener("submit", (ev) => { ev.preventDefault(); mitKnopf($("senden"), frageStellen); });
  bibLadeHerstellen();
  kopfzeileHerstellen();
  $("bib-neu").addEventListener("click", bibNeu);
  $("bib-gebietswahl").addEventListener("change", (ev) => mitKnopf(null, async () => {
    bibGebietswahl = ev.target.value || "";
    await bibliothekLaden();
  }));
  $("entwurf-modus-aus").addEventListener("click", entwurfModusAus);
  $("blatt-dialog").addEventListener("close", () => {
    const wahl = $("blatt-dialog").returnValue;
    if (wahl === "setzen" || wahl === "zuruecksetzen")
      mitKnopf(null, () => blattEinstellen(wahl === "zuruecksetzen"));
  });
  $("prompt-dialog").addEventListener("close", () => {
    if ($("prompt-dialog").returnValue === "ablegen") mitKnopf(null, bibAblegen);
  });
  // Die Eingabetaste fragt.
  //
  // Aus der Kanzlei am 13.10.2026: "Fragen mit Returntaste ausloesen." Bisher
  // brauchte es Strg+Eingabe - eine Abkuerzung, die man kennen muss. In einem
  // Chat erwartet jeder, dass die Eingabetaste abschickt.
  //
  // Umschalt+Eingabe macht weiterhin einen Zeilenumbruch, fuer die seltene
  // mehrzeilige Frage. Strg+Eingabe bleibt ebenfalls: Wer es sich angewoehnt
  // hat, soll nicht ins Leere greifen.
  //
  // Waehrend eine Frage laeuft, tut die Taste nichts: `mitKnopf` sperrt den
  // Knopf, und zwei Fragen zugleich waeren zwei Modellaufrufe fuer eine
  // Absicht.
  $("frage").addEventListener("keydown", (ev) => {
    if (ev.key !== "Enter" || ev.isComposing) return;
    if (ev.shiftKey) return;
    ev.preventDefault();
    if ($("senden").disabled) return;
    mitKnopf($("senden"), frageStellen);
  });
  // Die Knoepfe des Trefferlaufs - in beiden Spalten dieselben.
  for (const knopf of document.querySelectorAll("[data-lauf]")) {
    knopf.addEventListener("click", () =>
      laufSpringen(knopf.dataset.lauf, Number(knopf.dataset.richtung)));
  }

  const chatSuche = $("chat-suche");
  if (chatSuche) {
    chatSuche.addEventListener("input", chatSuchen);
    // Eingabetaste im Suchfeld heisst ueberall "zur naechsten Fundstelle".
    // Wer sucht, tippt das Wort und drueckt Eingabe - das darf nicht ins
    // Leere gehen.
    chatSuche.addEventListener("keydown", (e) => {
      if (e.key === "Enter") { e.preventDefault(); laufSpringen("chat", 1); }
    });
    // Fluchtweg: Esc schliesst die Suche und stellt den ganzen Verlauf wieder
    // her. Ohne ihn muesste man das Feld von Hand leeren, um weiterzulesen.
    chatSuche.addEventListener("keydown", (e) => {
      if (e.key === "Escape") { e.stopPropagation(); chatSucheZeigen(false); }
    });
  }
  const chatFundstellen = $("chat-fundstellen");
  if (chatFundstellen) chatFundstellen.addEventListener("click", fundstellenUmschalten);
  fundstellenZeichnen();
  const chatLupe = $("chat-lupe");
  if (chatLupe) chatLupe.addEventListener("click", () => chatSucheZeigen($("chat-suche-zeile").hidden));
  const chatSucheZu = $("chat-suche-zu");
  if (chatSucheZu) chatSucheZu.addEventListener("click", () => chatSucheZeigen(false));

  const dokSucheFeld = $("dok-suche");
  if (dokSucheFeld) dokSucheFeld.addEventListener("keydown", (e) => {
    if (e.key === "Enter") { e.preventDefault(); laufSpringen("dok", 1); }
  });

  const dokSuche = $("dok-suche");
  if (dokSuche) dokSuche.addEventListener("input", () => {
    const filter = $("dok-filter");
    zeigeDokument(filter ? filter.value : "");
  });
  $("chrono-aktualisieren").addEventListener("click", (ev) =>
    mitKnopf(ev.currentTarget, chronologieAktualisieren));
  $("ged-oeffnen").addEventListener("click", () => gedaechtnisExplorerOeffnen());
  const ganzWeg = $("ged-ganz-loeschen");
  if (ganzWeg) ganzWeg.addEventListener(
    "click", (ev) => mitKnopf(ev.currentTarget, gedaechtnisGanzVerwerfen));
  $("ged-inhalt").addEventListener("toggle", gedInhaltSchalterMerken);
  $("ged-alle-fehlenden").addEventListener("click", () => {
    // Nur die sichtbaren. Wer nach "Gegner" filtert und dann hier klickt,
    // will den Gegner im Gedaechtnis - nicht die ganze Akte. Im
    // Dokumentfenster gilt dasselbe seit dem 29.09.2026.
    for (const d of gedSichtbarFehlende()) gedAuswahl.add(d.id);
    gedExplorerZeichnen();
  });
  $("ged-dialog").addEventListener("close", (ev) => {
    if (ev.target.returnValue === "uebernehmen") gedaechtnisAufnehmen();
  });
  // Die Funktionsknoepfe sind am 13.10.2026 in die rechte Spalte gewandert
  // (siehe index.html). Gelauscht wird deshalb am Dokument und nicht mehr an
  // einer Leiste: Wer Knoepfe verschiebt, soll nicht zugleich daran denken
  // muessen, den Lauscher mitzunehmen.
  document.addEventListener("click", (ev) => {
    const b = ev.target.closest("[data-aktion]"); if (!b) return;
    if (b.dataset.aktion === "pack") mitKnopf(b, packStarten);
    else if (b.dataset.aktion === "analyse") mitKnopf(b, analyseStarten);
    else if (b.dataset.aktion === "gedaechtnis") mitKnopf(b, gedaechtnisAktualisieren);
    else if (b.dataset.aktion === "triage") mitKnopf(b, triageStarten);
    else if (b.dataset.aktion === "dokumente") mitKnopf(b, dokumenteVerwalten);
    else if (b.dataset.aktion === "neu-einlesen") mitKnopf(b, dokumenteNeuEinlesen);
    else if (b.dataset.aktion === "entwurf") mitKnopf(b, entwurfDialogOeffnen);
    else if (b.dataset.aktion === "nachweis") mitKnopf(b, nachweisZeigen);
    else if (b.dataset.aktion === "referenzen") mitKnopf(b, referenzenOeffnen);
    else if (b.dataset.aktion === "abschluss") mitKnopf(b, abschlussOeffnen);
    else if (b.dataset.aktion === "haufe") haufeRecherche();
    else if (b.dataset.aktion === "gesetze") gesetzNachschlagen();
  });
  $("rueckgaengig-tun").addEventListener("click", (ev) => mitKnopf(ev.target, rueckgaengigMachen));
  $("rueckgaengig-zu").addEventListener("click", rueckgaengigVerbergen);
  document.addEventListener("keydown", (ev) => {
    if (!(ev.ctrlKey || ev.metaKey) || ev.key.toLowerCase() !== "z" || ev.shiftKey) return;
    // In einem Eingabefeld gehört Strg+Z dem Text, nicht der Akte. Wer eine
    // Frage tippt und sich vertut, will das Wort zurück, nicht das Dokument.
    const z = ev.target;
    if (z && (z.tagName === "INPUT" || z.tagName === "TEXTAREA" || z.isContentEditable)) return;
    if (!rueckgaengig) return;
    ev.preventDefault();
    mitKnopf($("rueckgaengig-tun"), rueckgaengigMachen);
  });

  // Beide Knoepfe tun dasselbe, und das ist keine Doppelung, sondern die
  // Wahrheit: Die Akte zu wechseln heisst, die Sitzung zu schliessen.
  // Beide gehen deshalb ueber dieselbe Rueckfrage.
  $("sitzung-schliessen").addEventListener("click", (ev) => mitKnopf(ev.target, akteWechseln));
  $("akte-wechseln").addEventListener("click", (ev) => mitKnopf(ev.target, akteWechseln));
  $("aufsicht-oeffnen").addEventListener("click", (ev) => mitKnopf(ev.target, aufsichtOeffnen));
  const mehrKnopf = $("mehr-knopf"), mehrMenue = $("mehr-menue");
  const mehrSchliessen = () => { mehrMenue.hidden = true; mehrKnopf.setAttribute("aria-expanded", "false"); };
  mehrKnopf.addEventListener("click", (ev) => {
    ev.stopPropagation();
    mehrMenue.hidden = !mehrMenue.hidden;
    mehrKnopf.setAttribute("aria-expanded", String(!mehrMenue.hidden));
  });
  // Ein Klick daneben oder Escape schliesst das Menue wieder.
  document.addEventListener("click", (ev) => { if (!ev.target.closest(".mehr")) mehrSchliessen(); });
  document.addEventListener("keydown", (ev) => { if (ev.key === "Escape") mehrSchliessen(); });
  mehrMenue.addEventListener("click", mehrSchliessen);
  $("abschluss-bestaetigt").addEventListener("change", abschlussKnopfPruefen);
  $("abschluss-vormerken").addEventListener("click", (ev) => mitKnopf(ev.target, abschlussVormerken));
  $("abschluss-ausfuehren").addEventListener("click", (ev) => mitKnopf(ev.target, abschlussAusfuehren));
  $("referenzen-dialog").addEventListener("close", () => {
    if ($("referenzen-dialog").returnValue === "speichern") mitKnopf(null, referenzenSpeichern);
  });
  $("entwurf-auftrag").addEventListener("change", (ev) => mitKnopf(null, () => auftragVorbelegen(ev.target.value)));
  // Der Dialog darf nicht zugehen, bevor die Datei wirklich liegt: Sonst waere
  // bei "Diesen Auftrag gibt es bereits" der geaenderte Text verloren.
  $("selbsttest-oeffnen").addEventListener("click", (ev) =>
    mitKnopf(ev.currentTarget, selbsttestOeffnen));
  $("selbsttest-anprobieren").addEventListener("click", (ev) => {
    ev.preventDefault();  // der Dialog bleibt offen, das Ergebnis erscheint darin
    mitKnopf(ev.currentTarget, modellTestlauf);
  });
  $("vorschlag-anlegen").addEventListener("click", (ev) => {
    ev.preventDefault();
    mitKnopf($("vorschlag-anlegen"), auftragAnlegen);
  });
  const klammer = $("dok-einfuegen");
  if (klammer) klammer.addEventListener("click", () => einfuegenDialogOeffnen(null));
  const einfuegenDialog = $("einfuegen-dialog");
  if (einfuegenDialog) {
    einfuegenDialog.addEventListener("close", () => {
      if (einfuegenDialog.returnValue !== "einfuegen") { einfuegenDatei = null; return; }
      mitKnopf($("senden"), dokumentEinfuegen);
    });
  }
  einfuegenPerAblegen();
  $("entwurf-dialog").addEventListener("close", () => {
    if ($("entwurf-dialog").returnValue !== "start") return;
    const auftrag = $("entwurf-auftrag").value;
    mitKnopf($("senden"), () => entwurfStarten($("entwurf-art").value, $("entwurf-anweisung").value.trim(), $("entwurf-empfaenger").value.trim(), auftrag));
    $("entwurf-anweisung").value = ""; $("entwurf-empfaenger").value = ""; $("entwurf-auftrag").value = "";
  });
  if (nebenfenster) { alsNebenfensterEinrichten(); return; }
  // Hauptfenster: auf Nachfragen der Nebenfenster antworten.
  kanal = nebenkanal();
  if (kanal) {
    kanal.onmessage = (nachricht) => {
      const inhalt = nachricht.data || {};
      if (inhalt.was === "bitte-stand") nebenfensterGleichziehen();
      // Ein geschlossenes Nebenfenster bringt seine Ansicht zurueck.
      else if (inhalt.was === "ende" && inhalt.name) fensterOeffnen(inhalt.name);
    };
    // Sich melden: Ein Nebenfenster, das offen stand, als dieses Fenster neu
    // geladen wurde, fragt von sich aus nicht noch einmal nach.
    try { kanal.postMessage({ was: "hallo" }); } catch (e) {}
  }
  ladeStatus();
});
