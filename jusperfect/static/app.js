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

async function benutzerWaehlen(kennung) {
  kennung = (kennung || "").trim();
  if (!kennung) { anmeldeFehler("Bitte einen Benutzer wählen."); return; }
  $("nutzer").value = kennung;
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
  marke.title = "Diese Akte ist in jur|nodes archiviert.";
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

// ── Zwei-Fenster-Explorer: jur|nodes ⇄ Arbeitsakte ───────────────────────────

let explorer = null;  // { karte: Map(id->dok), gewaehlt: Set, geladen: Set, initial: bool }

async function akteOeffnen(akteId) {
  // Die Meldung der zuletzt geschlossenen Akte hat hier nichts mehr zu suchen.
  schlussHinweisZeigen("");
  sitzung = await api("POST", "/api/sitzungen", { akte_id: akteId });
  verlaufMerken(sitzung.sitzung.akte);
  explorerStarten(true);
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
  explorer = { karte, gewaehlt: new Set(geladen), geladen, initial };
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
    if (m.ohne_antwort) teile.push(`${m.ohne_antwort} von jur|nodes nicht herausgegeben`);
    if (teile.length) {
      eakteHinweis.hidden = false;
      const satz = `Bei ${teile.join(", ")} E-Mail(s) fehlt der Inhalt. `
        + `Sie stehen in der Liste mit Betreff und Datum; der Vermerk steht in der Zeile.`;
      eakteHinweis.textContent = eakteHinweis.textContent
        ? eakteHinweis.textContent + " — " + satz : satz;
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
  zahlZeigen("arbeit-zahl", angehakt, explorer.gewaehlt.size);
  explorerArtenZeichnen(sichtbar);
  explorerUmfangZeigen();
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

async function explorerUebernehmen() {
  if (!explorer.gewaehlt.size) { melden("Bitte mindestens ein Dokument in die Arbeitsakte legen.", true); return; }
  const dazu = [...explorer.gewaehlt].filter((id) => !explorer.geladen.has(id));
  const weg = [...explorer.geladen].filter((id) => !explorer.gewaehlt.has(id));
  if (dazu.length) await dokumenteInPortionenLesen(dazu);
  for (const id of weg)
    sitzung = await api("DELETE", `/api/sitzungen/${sitzung.sitzung.id}/dokumente/${id.split("/").map(encodeURIComponent).join("/")}`);
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

/** Die Dokumente in Portionen lesen und dabei zeigen, wie weit es ist. */
async function dokumenteInPortionenLesen(dazu) {
  const gesamt = dazu.length;
  // Fuer ein, zwei Dokumente lohnt der Aufbau nicht - da blitzt er nur auf.
  if (gesamt <= 2) {
    laeuft(gesamt === 1 ? "Ein Dokument wird gelesen …" : "Zwei Dokumente werden gelesen …");
    sitzung = await api("POST", `/api/sitzungen/${sitzung.sitzung.id}/dokumente`, { dokument_ids: dazu });
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
      const antwort = await api("POST", `/api/sitzungen/${meine}/dokumente`,
                                { dokument_ids: teil });
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
    }
  } finally {
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
 * Kostet nichts: Alles steht schon im Aktengedächtnis. Gezeigt werden die
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
  await gespeicherteAnalyseZeigen();
  zeigeBelege();
}

async function passagenLaden() {
  const daten = await api("GET", `/api/sitzungen/${sitzung.sitzung.id}/passagen`);
  passagenIndex = {};
  for (const p of daten.passagen) passagenIndex[p.kennung] = p;
  // Dokumentfilter
  const filter = $("dok-filter"); filter.replaceChildren();
  const alle = document.createElement("option"); alle.value = ""; alle.textContent = "Alle Dokumente"; filter.appendChild(alle);
  for (const g of sitzung.sitzung.geladen) {
    const o = document.createElement("option"); o.value = g.dokument_id; o.textContent = g.titel; filter.appendChild(o);
  }
  filter.onchange = () => zeigeDokument(filter.value);
  zeigeDokument("");
}

function zeigeDokument(nurDokument) {
  const ziel = $("dok-text"); ziel.replaceChildren();
  let letzterTitel = null;
  for (const kennung of Object.keys(passagenIndex)) {
    const p = passagenIndex[kennung];
    if (nurDokument && p.dokument_id !== nurDokument) continue;
    if (p.dokument_titel !== letzterTitel) {
      const t = document.createElement("div"); t.className = "dok-doktitel"; t.textContent = p.dokument_titel;
      ziel.appendChild(t); letzterTitel = p.dokument_titel;
    }
    const abs = document.createElement("div"); abs.className = "passage"; abs.id = `p-${p.kennung}`;
    const kz = document.createElement("span"); kz.className = "kennung"; kz.textContent = `${p.kennung} · Seite ${p.seite}`;
    const satz = document.createElement("div"); satz.className = "satz"; satz.textContent = p.text;
    abs.append(kz, satz); ziel.appendChild(abs);
  }
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
  belege: "fenster-belege",
};

// Voreinstellung: wie bisher, nur ohne das Gedaechtnisfenster - das ist neu
// und soll sich niemandem aufdraengen, der es nicht eingeschaltet hat.
let fensterStand = { dokument: true, chronologie: true, gedaechtnis: false, belege: true };

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
      nebenfensterZeichnen();
    } else if (inhalt.was === "hallo") {
      // Das Hauptfenster ist (wieder) da. Noch einmal um den Stand bitten -
      // sonst zeigte dieses Fenster weiter einen Stand von vorhin.
      try { kanal.postMessage({ was: "bitte-stand" }); } catch (e) {}
    } else if (inhalt.was === "zu") {
      sitzung = null;
      chronoAusAnalyse = []; passagenIndex = {};
      belegKennungen = new Set(); belegQuellen = {};
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
    const offen = ["chronologie", "gedaechtnis", "belege"].some(
      (n) => fensterStand[n] && (n !== "gedaechtnis" || K.gedaechtnisAktiv));
    rechts.hidden = !offen;
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
    const titel = document.createElement("div"); titel.className = "titelzeile"; titel.textContent = "Aktengedächtnis · Lebenssachverhalt";
    const inhalt = document.createElement("div"); inhalt.className = "inhalt";
    antworttext(inhalt, g.lebenssachverhalt);
    karte.append(titel, inhalt); t.appendChild(karte);
  }
  for (const qa of (g.fragen_antworten || []).slice(-5)) {
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
}

// ── Aktengedächtnis: was liegt drin, was fehlt, wie groß ist es ─────────────
// Ein dauerhafter Speicher, den niemand einsehen kann, ist eine Zusage ohne
// Nachweis. Das Fenster nennt den Umfang, der Explorer zeigt ihn neben der
// Akte aus jur|nodes – und hebt hervor, was noch fehlt.

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
  if (!offenAmAnfang) { melden("Es ist schon alles eingelesen."); return; }
  const zeichen = g.zeichen || 0;
  const grenze = K.maxPassagenZeichen || 160000;
  const portionen = Math.max(1, Math.ceil(zeichen / grenze));
  const nichtDrin = (sitzung.dokumente || []).length - gesamt;
  const teile = [
    "Die Akte wird Portion für Portion ins Aktengedächtnis gelesen.",
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
  titel.textContent = "Aktengedächtnis · Hinweis";
  const inhalt = document.createElement("div"); inhalt.className = "inhalt"; inhalt.textContent = text;
  karte.append(titel, inhalt);
  $("thread").appendChild(karte);
}

function gedaechtnisExplorerOeffnen() {
  gedAuswahl = new Set();
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
  let linksN = 0;
  for (const d of alle) {
    if (!dokumentPasst(d, begriffe)) continue;
    linksN++;
    const li = document.createElement("li");
    const fehlt = !drinNach.has(d.id);
    li.className = "explorer-zeile" + (fehlt ? " fehlt" : " drin schon-drin");
    // Ein Haekchen gibt es nur bei dem, was noch fehlt. Was schon drin ist,
    // steht ausgegraut da - sichtbar, damit man es sucht und findet, aber
    // nicht waehlbar, damit es nicht ein zweites Mal aufgenommen wird.
    const box = document.createElement("input");
    box.type = "checkbox";
    box.checked = fehlt ? gedAuswahl.has(d.id) : true;
    box.disabled = !fehlt;
    box.title = fehlt ? "In das Aktengedächtnis aufnehmen" : "Liegt bereits im Aktengedächtnis";
    if (fehlt) {
      box.addEventListener("change", () => {
        box.checked ? gedAuswahl.add(d.id) : gedAuswahl.delete(d.id);
        gedUmfangZeigen();
      });
    }
    li.appendChild(box);
    li.appendChild(feld(d.titel, "explorer-titelzeile"));
    li.appendChild(feld(fehlt ? "fehlt" : "schon im Gedächtnis", "explorer-marke"));
    links.appendChild(li);
  }
  zahlZeigen("ged-quelle-zahl", linksN, alle.length);

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
    weg.title = `„${e.titel}" aus dem Aktengedächtnis entfernen`;
    weg.addEventListener("click", (ev) => mitKnopf(ev.target, () => gedaechtnisDokumentVergessen(e)));
    li.appendChild(weg);
    rechts.appendChild(li);
  }
  zahlZeigen("ged-drin-zahl", rechtsN, eintraege.length);
  gedInhaltZeigen();
  gedUmfangZeigen();
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
    weg.title = "Diese Frage und ihre Antwort aus dem Aktengedächtnis entfernen";
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
    : "gespeichert wird bei jusperfect, nicht in jur|nodes");
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
    `„${e.titel}" aus dem Aktengedächtnis entfernen?`,
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
    "Die Akte in jur|nodes bleibt unberührt. Entfernt wird nur, was sich",
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
  melden(`„${e.titel}" ist nicht mehr im Aktengedächtnis.`
         + (nach.length ? ` Mit entfallen: ${nach.join(", ")}.` : ""));
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
    melden("Diese Frage liegt nicht mehr im Aktengedächtnis – jemand war schneller. "
           + "Die Ansicht steht jetzt auf dem neuen Stand.", true);
    return;
  }
  const kurz = (f.frage || "").length > 90 ? (f.frage || "").slice(0, 90) + "…" : (f.frage || "");
  const teile = [
    `„${kurz}"`,
    "",
    "Diese Frage und ihre Antwort aus dem Aktengedächtnis entfernen?",
    "",
    "Es fällt nur diese eine Runde heraus. Die Dokumentauszüge, der",
    "Lebenssachverhalt und der Zeitstrahl bleiben stehen.",
    "",
    "Die Akte in jur|nodes bleibt unberührt.",
    "",
    "Dieselbe Frage noch einmal zu stellen kostet einen neuen Modellaufruf.",
    "",
    "Entfernen?"];
  if (!confirm(teile.join("\n"))) return;
  const akte = encodeURIComponent(sitzung.sitzung.akte_id);
  sitzung.gedaechtnis = await api("DELETE", `/api/akten/${akte}/gedaechtnis/fragen/${stelle}`);
  gedExplorerZeichnen();
  gedaechtnisFensterZeigen();
  melden("Die Frage ist nicht mehr im Aktengedächtnis.");
}

async function gedaechtnisAufnehmen() {
  if (!gedAuswahl.size) { melden("Nichts ausgewählt."); return; }
  const ids = [...gedAuswahl];
  sitzung = await api("POST", `/api/sitzungen/${sitzung.sitzung.id}/dokumente`, { dokument_ids: ids });
  gedAuswahl = new Set();
  await passagenLaden();
  gedaechtnisFensterZeigen();
  chronologieZeigen();
  melden(`${ids.length} Dokument(e) ins Gedächtnis aufgenommen.`);
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
    melden("Das Aktengedächtnis ist ausgeschaltet. Es lässt sich in der "
           + "Startdatei wieder einschalten (JUSPERFECT_GEDAECHTNIS). "
           + "Ohne es wird jede Akte bei jeder Sitzung neu eingelesen.", true);
    return;
  }
  const g = await api("POST", `/api/sitzungen/${sitzung.sitzung.id}/gedaechtnis/aktualisieren`);
  sitzung.gedaechtnis = g;
  const karte = threadKarte("ai");
  const titel = document.createElement("div"); titel.className = "titelzeile"; titel.textContent = "Aktengedächtnis aktualisiert";
  const inhalt = document.createElement("div"); inhalt.className = "inhalt";
  if (g.lebenssachverhalt) antworttext(inhalt, g.lebenssachverhalt);
  else inhalt.textContent = "Noch kein belegter Lebenssachverhalt vorhanden.";
  karte.append(titel, inhalt);
  melden(g.offene_dokumente ? `${g.offene_dokumente} Dokument(e) warten noch auf Verarbeitung.` : "Alle neuen Dokumente sind verarbeitet.");
  ladeStatus();
}

function threadKarte(klasse) {
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
    if (m.index > letzte) angabenAnklickbar(ziel, aussage, erste);
    const kennungen = m[1].split(",");
    kennungen.forEach((roh, i) => {
      const kennung = roh.trim();
      const chip = document.createElement("span");
      const bekannt = !!passagenIndex[kennung];
      chip.className = "beleg" + (bekannt ? "" : " fehlt");
      chip.textContent = bekannt ? kennung : "ohne Beleg";
      if (bekannt) chip.addEventListener("click", () => passageMarkieren(kennung, chip, aussage));
      ziel.appendChild(chip);
      // Zwischen zwei Fundstellen ein Leerzeichen, hinter der letzten keines:
      // Sonst steht im Satz "… zu [Beleg] ." - der Punkt rutscht ab.
      if (i < kennungen.length - 1) ziel.appendChild(document.createTextNode(" "));
    });
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

async function frageStellen() {
  const frage = $("frage").value.trim();
  if (!frage) return;
  $("frage").value = "";
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
// Stammdaten aus jur|nodes. Eine Aktenanalyse reichert sie später an; bis
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
  // "Betriebsrats"). Dieselbe Regel wie beim Speichern im Aktengedächtnis –
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
  zeile("Status in jur|nodes", stand.aktenstatus);
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
    p.textContent = "Die Akte ist in jur|nodes nicht abgeschlossen. Der Arbeitsbereich bleibt "
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
  zeile("Nach jur|nodes gesichert", nachweis.jurnodes_referenz);
  zeile("Freigegeben von", nachweis.nutzer_id);
  zeile("Zeitpunkt", new Date(nachweis.zeitpunkt).toLocaleString("de-DE"));
  zeile("Gelöscht", `${g.dokumente} Dokumentauszug/-auszüge, ${g.fragen} Frage(n), `
                  + `${g.sitzungen} Sitzung(en), ${g.entwuerfe} Entwurf/Entwürfe`);
  const hinweis = document.createElement("p");
  hinweis.className = "abschluss-hinweis";
  hinweis.textContent = "Der Arbeitsbereich dieser Akte ist gelöscht. Die Akte selbst bleibt in "
    + "jur|nodes unberührt; dort steht jetzt der gesicherte Arbeitsstand als Vermerk.";
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
    p.textContent = "Nichts zu entscheiden. Alle Arbeitsbereiche folgen dem Stand in jur|nodes.";
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

async function entwurfStarten(art, anweisung, empfaenger, auftrag) {
  const e = await api("POST", `/api/sitzungen/${sitzung.sitzung.id}/entwuerfe`, { art, anweisung, empfaenger, auftrag: auftrag || "" });
  belegeMerken(e.quellen);
  const karte = threadKarte("ai");
  const titel = document.createElement("div"); titel.className = "titelzeile"; titel.textContent = "Entwurf: " + e.betreff; karte.appendChild(titel);
  const inhalt = document.createElement("div"); inhalt.className = "inhalt";
  const hb = hinweiseBlock((e.hinweise || []).concat(["Entwurf – anwaltliche Prüfung erforderlich."])); if (hb) inhalt.appendChild(hb);
  antworttext(inhalt, e.text);
  karte.appendChild(inhalt);
  const fuss = fusszeile(e);
  const frei = document.createElement("button"); frei.className = "mini"; frei.textContent = "Freigeben und in jur|nodes ablegen";
  frei.addEventListener("click", () => mitKnopf(frei, async () => {
    if (!confirm("Diesen von der KI vorbereiteten Entwurf als Vermerk in die jur|nodes-Akte schreiben?")) return;
    // Die Pruefsumme deckt seit dem 05.10.2026 Akte, Art, Betreff UND Text ab.
    // Vorher nur den Text - ein in einem anderen Fenster geaenderter Betreff
    // ging damit ungesehen in den Vermerk (Befund F06 der Zweitpruefung).
    const f = await api("POST", `/api/entwuerfe/${e.id}/freigabe`, { bestaetigung: true, freigabe_pruefsumme: e.freigabe_pruefsumme });
    frei.replaceWith(Object.assign(document.createElement("span"), { textContent: `In jur|nodes abgelegt (${f.jurnodes_referenz || ""})` }));
  }));
  fuss.appendChild(frei);
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
  ladeStatus();
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
// sondern zuerst, was bleibt – und mit welchen Zahlen. "Was im Aktengedächtnis
// steht, bleibt erhalten" ist eine Zusage; "50 Dokumente, 68 Zeilen Chronologie,
// 4 Antworten" ist eine Auskunft.
function schlussfrage() {
  const g = (sitzung && sitzung.gedaechtnis) || {};
  const bleibt = K.gedaechtnisAktiv && g.vorhanden
    ? "Im Aktengedächtnis bleiben: der Lebenssachverhalt, "
      + `${(g.eintraege || []).length} Dokument(e), `
      + `${(g.chronologie || []).length} Zeile(n) Chronologie und `
      + `${g.fragen || 0} geprüfte Antwort(en).`
    : "Zu dieser Akte besteht kein Aktengedächtnis – gespeichert wird deshalb nichts.";
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
      + " Die Sitzung ist geschlossen; das Aktengedächtnis kann unvollständig sein.";
  if (!bericht || !bericht.gesichert)
    return (bericht && bericht.aktiv)
      ? "Zu dieser Akte besteht noch kein Aktengedächtnis, gespeichert wurde deshalb nichts. "
        + "Die Sitzung ist geschlossen und die temporären Texte sind gelöscht."
      : "Sitzung geschlossen, temporäre Texte gelöscht. Gespeichert wurde nichts – "
        + "das Aktengedächtnis ist nicht aktiviert.";
  const teile = [];
  if ((bericht.lebenssachverhalt || "").length)
    teile.push(`Lebenssachverhalt (${umfangKurz(bericht.lebenssachverhalt.length)})`);
  if ((bericht.eintraege || []).length) teile.push(`${bericht.eintraege.length} Dokument(e)`);
  if ((bericht.chronologie || []).length) teile.push(`${bericht.chronologie.length} Zeile(n) Chronologie`);
  if (bericht.fragen) teile.push(`${bericht.fragen} geprüfte Antwort(en)`);
  const wo = bericht.aktenzeichen ? " zu " + bericht.aktenzeichen : "";
  return `Gespeichert im Aktengedächtnis${wo}: ` + (teile.length ? teile.join(", ") : "nichts Belegtes")
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
  if (AWS_MODUS) {
    $("anmelden-aws").hidden = false;
    $("anmeldung").addEventListener("click", () => (angemeldet() ? abmelden() : anmeldungStarten()));
    const astZu = $("arbeitsstand-zu");
    if (astZu) astZu.addEventListener("click", arbeitsstandSchliessen);
    const ubZu = $("uebernahme-zu");
    if (ubZu) ubZu.addEventListener("click", () => { $("uebernahme").hidden = true; });
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
  $("explorer-dialog").addEventListener("close", () => {
    if ($("explorer-dialog").returnValue === "uebernehmen") mitKnopf(null, explorerUebernehmen);
  });
  $("frage-form").addEventListener("submit", (ev) => { ev.preventDefault(); mitKnopf($("senden"), frageStellen); });
  $("frage").addEventListener("keydown", (ev) => {
    if (ev.key === "Enter" && (ev.ctrlKey || ev.metaKey)) { ev.preventDefault(); mitKnopf($("senden"), frageStellen); }
  });
  $("chrono-aktualisieren").addEventListener("click", (ev) =>
    mitKnopf(ev.currentTarget, chronologieAktualisieren));
  $("ged-oeffnen").addEventListener("click", () => gedaechtnisExplorerOeffnen());
  $("ged-inhalt").addEventListener("toggle", gedInhaltSchalterMerken);
  $("ged-alle-fehlenden").addEventListener("click", () => {
    for (const d of gedFehlende()) gedAuswahl.add(d.id);
    gedExplorerZeichnen();
  });
  $("ged-dialog").addEventListener("close", (ev) => {
    if (ev.target.returnValue === "uebernehmen") gedaechtnisAufnehmen();
  });
  document.querySelector(".aktionen").addEventListener("click", (ev) => {
    const b = ev.target.closest("[data-aktion]"); if (!b) return;
    if (b.dataset.aktion === "pack") mitKnopf(b, packStarten);
    else if (b.dataset.aktion === "analyse") mitKnopf(b, analyseStarten);
    else if (b.dataset.aktion === "gedaechtnis") mitKnopf(b, gedaechtnisAktualisieren);
    else if (b.dataset.aktion === "triage") mitKnopf(b, triageStarten);
    else if (b.dataset.aktion === "dokumente") mitKnopf(b, dokumenteVerwalten);
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
