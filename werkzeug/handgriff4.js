// Setzt Handgriff 4 aus AWS-ZWEI-HANDGRIFFE.md als Word-Datei - die Pruefung
// vor einem Modellwechsel, mit einem Bogen zum Ausfuellen am Ende.
//
//   node werkzeug/handgriff4.js <ausgabe.docx>

const fs = require("fs");
const d = require("docx");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType,
  Table, TableRow, TableCell, WidthType, ShadingType, BorderStyle, LevelFormat,
} = d;

const SCHRIFT = "Franklin Gothic Book";
const FEST = "Consolas";

const t = (text, opt = {}) => new TextRun({ text, ...opt });
const p = (text, opt = {}) =>
  new Paragraph({ children: Array.isArray(text) ? text : [t(text)], ...opt });
const h1 = (text) =>
  new Paragraph({ text, heading: HeadingLevel.HEADING_1, spacing: { before: 400, after: 160 } });
const h2 = (text) =>
  new Paragraph({ text, heading: HeadingLevel.HEADING_2, spacing: { before: 280, after: 120 } });
const leer = () => new Paragraph({ children: [], spacing: { after: 120 } });
const linie = (opt = {}) =>
  new Paragraph({
    children: [],
    border: { bottom: { style: BorderStyle.SINGLE, size: 6, space: 8, color: "999999" } },
    spacing: { before: 200, after: 200, ...opt },
  });

// Jede Aufzaehlung braucht ihre eigene Kennung - sonst zaehlt die naechste
// dort weiter, wo die vorige aufgehoert hat.
let listenNr = 0;
const neueListe = () => "liste" + ++listenNr;
let aktuelleListe = "liste1";
const nr = (kinder) =>
  new Paragraph({
    children: Array.isArray(kinder) ? kinder : [t(kinder)],
    numbering: { reference: aktuelleListe, level: 0 },
    spacing: { after: 100 },
  });
const punkt = (kinder) =>
  new Paragraph({
    children: Array.isArray(kinder) ? kinder : [t(kinder)],
    numbering: { reference: "punkte", level: 0 },
    spacing: { after: 100 },
  });
const kasten = (kinder) =>
  new Paragraph({
    children: Array.isArray(kinder) ? kinder : [t(kinder)],
    indent: { left: 340 },
    spacing: { before: 180, after: 200 },
    border: { left: { style: BorderStyle.SINGLE, size: 12, space: 12, color: "888888" } },
  });

const zelle = (kinder, breite, kopf = false) =>
  new TableCell({
    width: { size: breite, type: WidthType.DXA },
    shading: kopf ? { type: ShadingType.CLEAR, fill: "EEF1F3" } : undefined,
    margins: { top: 70, bottom: 70, left: 110, right: 110 },
    children: [new Paragraph({
      children: Array.isArray(kinder) ? kinder : [t(kinder, kopf ? { bold: true } : {})],
      spacing: { after: 0 },
    })],
  });

const inhalt = [];

inhalt.push(
  new Paragraph({ text: "Handgriff 4 — vor dem Modellwechsel",
    heading: HeadingLevel.TITLE, spacing: { after: 200 } }),
  p([t("Kanzlei Dortschy & Thunert", { bold: true })], { spacing: { after: 200 } }),
  p([t("Stand: 15. Oktober 2026. ", { bold: true }),
     t("Aus AWS-ZWEI-HANDGRIFFE.md. Gilt für jeden Wechsel des Modells — nicht einmal, sondern jedes Mal.")],
    { spacing: { after: 160 } }),
  p("Dieser Handgriff ist kein Einstellen und kein Holen, sondern ein Nachsehen. Er steht auf einem eigenen Blatt, weil eine Prüfung, die nur im Gedächtnis steht, an dem Tag ausfällt, an dem es eilig ist.", { spacing: { after: 120 } }),
  linie()
);

// ------------------------------------------------- Worum es geht
inhalt.push(
  h1("Warum die Liste in der Konsole nicht genügt"),
  p("Die AWS-Konsole zeigt zu jedem Modell einen Satz zum Können: „frontier model for ambitious coding“, „most capable Opus model“, „much lower cost per task“. Zu der Frage, die für eine Kanzlei entscheidet, sagt sie nichts.", { spacing: { after: 120 } }),
  p("Entschieden wird an drei Stellen, und keine davon steht in der Modellliste:", { spacing: { after: 120 } }),
  ((aktuelleListe = neueListe()), leer()),
  nr([t("Wird bei diesem Modell der Akteninhalt aufbewahrt?", { bold: true }),
      t(" Das sagt allein die Seite „Amazon Bedrock abuse detection“.")]),
  nr([t("Läuft es in Frankfurt, über das EU-Inferenzprofil?", { bold: true }),
      t(" Darauf ruht die ganze Folgenabschätzung. Ein Modell, das es nur in den Vereinigten Staaten gibt, bricht sie.")]),
  nr([t("Wie lautet die Kennung genau?", { bold: true }),
      t(" Zusammensetzen führt zu einer Abweisung, und die kann Akteninhalt enthalten.")]),
  kasten([
    t("Und der Grund dahinter: ", { bold: true }),
    t("Nach Service Terms 50.12.1 sind Drittanbieter-Modelle „Inhalte von Drittanbietern“, und ihre Nutzung heißt Zustimmung zu deren Bedingungen. Die Rechtslage hängt damit am gewählten Modell. "),
    t("JUSPERFECT_MODELL_ID", { font: FEST }),
    t(" zu ändern ist eine Entscheidung mit Rechtsfolgen und keine Einstellung."),
  ])
);

// ------------------------------------------------- Was feststeht
inhalt.push(
  h1("Was heute schon feststeht"),
  p([t("Dafür braucht niemand die Prüfung. Die Seite ist am "),
     t("14.10.2026", { bold: true }),
     t(" gelesen worden; der Wortlaut liegt als Anlage 17 zum Aktenvermerk gleichen Datums in der Datenschutzakte.")],
    { spacing: { after: 160 } }),
  new Table({
    columnWidths: [3100, 6254],
    width: { size: 9354, type: WidthType.DXA },
    rows: [
      new TableRow({ tableHeader: true, children: [
        zelle("Modell", 3100, true), zelle("Stand 14.10.2026", 6254, true)] }),
      new TableRow({ cantSplit: true, children: [
        zelle([t("Claude Fable 5 und Claude Fable 5.1", { bold: true })], 3100),
        zelle([t("Nicht verwenden. ", { bold: true }),
               t("Namentlich genannt: aller Verkehr bis zu 30 Tage aufbewahrt, aufgefallener mit möglicher Durchsicht durch Menschen bei AWS")], 6254)] }),
      new TableRow({ cantSplit: true, children: [
        zelle([t("Die meisten OpenAI-Modelle")], 3100),
        zelle([t("Nicht verwenden. ", { bold: true }), t("Aufgefallener Verkehr bis zu 30 Tage")], 6254)] }),
      new TableRow({ cantSplit: true, children: [
        zelle([t("Claude Opus 4.6 — "), t("anthropic.claude-opus-4-6-v1", { font: FEST })], 3100),
        zelle([t("Eingesetzt. ", { bold: true }), t("Steht nicht darauf — Zero Operator Access")], 6254)] }),
      new TableRow({ cantSplit: true, children: [
        zelle([t("Claude Mythos 5 und Claude Mythos 5.1")], 3100),
        zelle([t("Unbekannt. ", { bold: true }), t("Neu gegenüber dem 14.10.2026; vor jeder Verwendung nachzusehen")], 6254)] }),
      new TableRow({ cantSplit: true, children: [
        zelle([t("Alle übrigen Claude-Modelle")], 3100),
        zelle([t("Standen am 14.10.2026 nicht darauf — "), t("aber die Seite ändert sich", { bold: true })], 6254)] }),
    ],
  }),
  kasten([
    t("Die Falle liegt genau andersherum, als man denkt. ", { bold: true }),
    t("Fable 5.1 wird in der Konsole als das stärkste Modell für „enterprise knowledge work“ beschrieben — also als das, was eine Kanzlei zu brauchen glaubt. Dass bei ihm der gesamte Verkehr dreißig Tage liegt, steht dort nicht. Wer nach der Modellliste auswählt, wählt das Falsche."),
  ])
);

// ------------------------------------------------- Die vier Schritte
inhalt.push(
  h1("Schritt 1 — Die Missbrauchserkennungsseite ansehen"),
  ((aktuelleListe = neueListe()), leer()),
  nr([t("Den "), t("Amazon Bedrock User Guide", { bold: true }),
      t(" aufrufen und den Abschnitt „Abuse detection“ öffnen.")]),
  nr([t("Den Abschnitt „Model-specific abuse detection“ lesen. Dort stehen die Aufzählungen mit den "),
      t("namentlich genannten", { bold: true }), t(" Modellen.")]),
  nr([t("Steht das gewünschte Modell darauf: nicht verwenden", { bold: true }),
      t(", jedenfalls nicht für Mandatsakten. Hier endet die Prüfung.")]),
  nr("Steht es nicht darauf, gilt für es das Zero-Operator-Access-Modell: nichts wird aufbewahrt, nichts wird mitgelesen. Weiter mit Schritt 2."),
  nr([t("Die Seite ausdrucken", { bold: true }),
      t(" — mit Datum. Sie ist Dokumentation und kein Vertrag; AWS kann sie ohne Ankündigung ändern.")]),
  kasten([
    t("Ein Satz auf derselben Seite, der leicht übersehen wird: ", { bold: true }),
    t("„If cross-region inference is enabled for these models, retained inputs and outputs are stored in destination regions.“", { italics: true }),
    t(" Bei einem gelisteten Modell landet das Aufbewahrte also dort, wo die Anfrage verarbeitet wurde. Beim EU-Inferenzprofil bliebe es in der EU — aufbewahrt wäre es trotzdem. "),
    t("Die Region rettet ein gelistetes Modell nicht.", { bold: true }),
  ]),

  h1("Schritt 2 — Die Region prüfen"),
  ((aktuelleListe = neueListe()), leer()),
  nr([t("In der AWS-Konsole oben rechts auf "), t("eu-central-1 (Frankfurt)", { bold: true }), t(" stellen.")]),
  nr([t("Amazon Bedrock", { bold: true }), t(" öffnen, links "), t("Modellzugriff", { bold: true }), t(" ("), t("Model access", { italics: true }), t(").")]),
  nr("Nachsehen, ob das gewünschte Modell dort aufgeführt ist. Was in Frankfurt nicht erscheint, gibt es für uns nicht — gleich wie gut es ist."),
  nr([t("Prüfen, ob es über das "), t("EU-Inferenzprofil", { bold: true }),
      t(" erreichbar ist (Kennungen mit dem Vorsatz "), t("eu.", { font: FEST }),
      t("). jusperfect ruft über dieses Profil auf.")]),
  kasten([
    t("Warum das kein Nebenpunkt ist: ", { bold: true }),
    t("Die Folgenabschätzung sagt zu, dass die Verarbeitung in Rechenzentren innerhalb der Europäischen Union stattfindet. Derselbe Satz steht in der Klausel für den Mandatsvertrag, die die Mandantschaft unterschreibt. Ein Modell außerhalb der EU macht beide unrichtig."),
  ]),

  h1("Schritt 3 — Die Kennung abschreiben, nicht bilden"),
  ((aktuelleListe = neueListe()), leer()),
  nr([t("Die Kennung in der Konsole "), t("anzeigen lassen und kopieren", { bold: true }), t(" — nicht aus dem Namen zusammensetzen.")]),
  nr([t("Sie beginnt mit "), t("anthropic.", { font: FEST }), t(" und endet auf "), t("-v1", { font: FEST }),
      t(". Ein bloßes "), t("claude-opus-4-6", { font: FEST }),
      t(" ist die Kennung der Anthropic-Schnittstelle und funktioniert bei AWS nicht; "),
      t("anthropic.claude-opus-4-6", { font: FEST }), t(" ohne das "), t("-v1", { font: FEST }), t(" ebenfalls nicht.")]),
  kasten([
    t("Warum das hier steht und nicht nur in der Einrichtung: ", { bold: true }),
    t("Eine falsche Kennung führt zu einer Abweisung von AWS — und eine Abweisung kann ein Stück der Anfrage enthalten, also Akteninhalt. jusperfect reicht den AWS-Wortlaut deshalb nie durch. Der Bearbeiter sieht dann einen Fehler ohne Grund, und niemand weiß, warum."),
  ]),

  h1("Schritt 4 — Umstellen und festhalten"),
  ((aktuelleListe = neueListe()), leer()),
  nr([t("In "), t("START-JURNODES.bat", { font: FEST }), t(" den Eintrag "), t("JUSPERFECT_MODELL_ID", { font: FEST, bold: true }), t(" ändern.")]),
  nr([t("jusperfect neu starten und "), t("unter einer Antwort nachsehen", { bold: true }), t(", welches Modell sie erzeugt hat. Dort steht es.")]),
  nr("Den Bogen auf der letzten Seite ausfüllen und mit dem Ausdruck der Seite in die Datenschutzakte nehmen."),
  nr("Bescheid geben — dann werden die Folgenabschätzung, die Einweisung und der Einrichtungsbogen nachgezogen."),

  h1("Was kein Grund für einen Wechsel ist"),
  punkt([t("Ein neueres Modell ist da. ", { bold: true }), t("Ein Modell, das läuft, geprüft und dokumentiert ist, ist mehr wert als ein halbes Prozent mehr Güte.")]),
  punkt([t("Es ist günstiger. ", { bold: true }), t("Die Kosten stehen in der Oberfläche und sind bisher kein Problem. Ein Wechsel kostet eine Prüfung, einen Vermerk und ein Risiko.")]),
  punkt([t("Es steht als „frontier“ oder „most capable“ in der Liste. ", { bold: true }), t("Genau das war am 14.10.2026 die Beschreibung des Modells, das die Akteninhalte dreißig Tage aufbewahrt.")])
);

// ------------------------------------------------- Der Bogen
const zeile = (beschriftung, breit = true) =>
  p([t(beschriftung + " ", { bold: true }),
     t(breit ? "..................................................................." : "..............................")],
    { spacing: { after: 200 } });

inhalt.push(
  new Paragraph({ children: [new d.PageBreak()] }),
  new Paragraph({ text: "Prüfbogen Modellwechsel", heading: HeadingLevel.TITLE, spacing: { after: 160 } }),
  p("Auszufüllen vor der Umstellung, danach mit dem Ausdruck der Missbrauchserkennungsseite in die Datenschutzakte.", { spacing: { after: 240 } }),
  linie(),

  zeile("Bisheriges Modell"),
  // Die Beschriftung bleibt kurz: Laenger brach die Zeile um, und die
  // Punktreihe stand allein darunter wie eine zweite, leere Frage.
  zeile("Neues Modell"),
  p([t("Kennung (Schritt 3, abgeschrieben) ", { bold: true }),
     t("............................................................", { font: FEST })],
    { spacing: { after: 240 } }),

  h2("Schritt 1 — Missbrauchserkennungsseite"),
  zeile("Seite aufgerufen am", false),
  p([t("Das neue Modell ist dort ", { bold: true }),
     t("□ nicht genannt — weiter    □ genannt — NICHT VERWENDEN, Prüfung endet hier")],
    { spacing: { after: 200 } }),
  zeile("Ausdruck der Seite liegt bei", false),
  leer(),

  h2("Schritt 2 — Region"),
  p([t("In eu-central-1 (Frankfurt) verfügbar:  ", { bold: true }), t("□ ja    □ nein — nicht verwenden")], { spacing: { after: 200 } }),
  p([t("Über das EU-Inferenzprofil erreichbar:  ", { bold: true }), t("□ ja    □ nein — nicht verwenden")], { spacing: { after: 200 } }),
  leer(),

  h2("Schritt 4 — Umgestellt"),
  zeile("Geändert in START-JURNODES.bat am", false),
  p([t("In der Oberfläche unter einer Antwort nachgesehen:  ", { bold: true }), t("□ ja")], { spacing: { after: 200 } }),
  leer(),
  linie(),
  p([t("Geprüft und umgestellt durch", { bold: true })], { spacing: { after: 200 } }),
  p("Name ........................   Ort, Datum ........................   Unterschrift ........................",
    { spacing: { after: 240 } }),
  kasten([
    t("Wird dieser Bogen nicht gebraucht, ist er auch nicht auszufüllen. ", { bold: true }),
    t("Solange das eingestellte Modell bleibt, ist an diesem Handgriff nichts zu tun. Er ist eine Prüfung vor einer Entscheidung — keine laufende Aufgabe."),
  ])
);

const doc = new Document({
  creator: "Kanzlei Dortschy & Thunert",
  title: "Handgriff 4 — vor dem Modellwechsel",
  description: "Die Prüfung vor einem Wechsel des Modells, mit Bogen zum Ausfüllen",
  numbering: {
    config: [
      ...Array.from({ length: 10 }, (_, i) => ({
        reference: "liste" + (i + 1),
        levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.START,
          style: { paragraph: { indent: { left: 700, hanging: 340 } } } }],
      })),
      {
        reference: "punkte",
        levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.START,
          style: { paragraph: { indent: { left: 700, hanging: 340 } } } }],
      },
    ],
  },
  styles: {
    default: {
      document: { run: { font: SCHRIFT, size: 24 }, paragraph: { spacing: { line: 276, after: 140 } } },
      title: { run: { font: SCHRIFT, size: 40, bold: true, color: "000000" }, paragraph: { spacing: { after: 200 } } },
      heading1: { run: { font: SCHRIFT, size: 28, bold: true, color: "000000" } },
      heading2: { run: { font: SCHRIFT, size: 24, bold: true, color: "000000" } },
    },
  },
  sections: [
    {
      properties: {
        page: {
          size: { width: 11906, height: 16838 },
          margin: { top: 1134, right: 1134, bottom: 1134, left: 1418 },
        },
      },
      children: inhalt,
    },
  ],
});

Packer.toBuffer(doc).then((buf) => {
  fs.writeFileSync(process.argv[2], buf);
  console.log("geschrieben:", process.argv[2]);
});
