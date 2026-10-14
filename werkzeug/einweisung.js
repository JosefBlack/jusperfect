// Setzt EINWEISUNG.md als Word-Datei. Aufruf:
//   node werkzeug/einweisung.js <ausgabe.docx>

const fs = require("fs");
const d = require("docx");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType,
  Table, TableRow, TableCell, WidthType, ShadingType, BorderStyle, LevelFormat,
} = d;

const SCHRIFT = "Franklin Gothic Book";

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

const inhalt = [];

inhalt.push(
  new Paragraph({ text: "Einweisung zur Arbeit mit jusperfect", heading: HeadingLevel.TITLE, spacing: { after: 200 } }),
  p([t("Kanzlei Dortschy & Thunert", { bold: true })], { spacing: { after: 200 } }),
  p([t("Stand: 14. Oktober 2026. ", { bold: true }), t("Gilt für alle, die mit jusperfect arbeiten.")], { spacing: { after: 160 } }),
  p("Dieses Blatt sammelt die Regeln, die sich nicht aus der Bedienung ergeben und die das Programm auch nicht erzwingen kann. Wer sie nicht kennt, macht nichts falsch im Sinne der Bedienung — und verletzt doch eine Pflicht aus der Datenschutz-Folgenabschätzung.", { spacing: { after: 120 } }),
  linie()
);

// ------------------------------------------------------------- Regel 1
inhalt.push(
  h1("Regel 1 — Das Modell wird nicht ohne Prüfung gewechselt"),
  p([
    t("Eingestellt ist ", { bold: true }),
    t("claude-opus-4-6-v1", { bold: true, font: "Consolas" }),
    t(". Dabei bleibt es, bis jemand die Prüfung unten gemacht hat.", { bold: true }),
  ], { spacing: { after: 160 } }),

  h2("Warum"),
  p("AWS führt eine Seite, auf der Modelle namentlich genannt sind, bei denen Eingaben und Ausgaben bis zu 30 Tage aufbewahrt werden — bei einigen der gesamte Verkehr, mit der Möglichkeit einer Durchsicht durch Mitarbeiter von AWS. Das betrifft dann den Akteninhalt, der an das Modell geht.", { spacing: { after: 120 } }),
  p([
    t("Unser Modell steht nicht darauf.", { bold: true }),
    t(" Für es gilt das Zero-Operator-Access-Modell: nichts wird aufbewahrt, nichts wird mitgelesen. Das ist der Grund, warum die Folgenabschätzung an dieser Stelle keine Aufbewahrung ausweisen muss."),
  ], { spacing: { after: 120 } }),
  p("Ein anderes Modell kann das ändern — ohne dass sich an der Bedienung etwas ändert und ohne dass eine Meldung erscheint.", { spacing: { after: 120 } }),

  h2("Was zu tun ist, bevor ein Modell gewechselt wird"),
  ((aktuelleListe = neueListe()), leer()),
  nr([
    t("Die Seite "),
    t("„Amazon Bedrock abuse detection“", { bold: true }),
    t(" im Amazon Bedrock User Guide aufrufen und nachsehen, ob das neue Modell dort genannt ist. Der Wortlaut vom 14.10.2026 liegt als Anlage 17 zum Aktenvermerk gleichen Datums in der Datenschutzakte."),
  ]),
  nr([t("Steht es darauf: nicht verwenden", { bold: true }), t(", jedenfalls nicht für Mandatsakten.")]),
  nr("Steht es nicht darauf: wechseln, den Tag der Prüfung notieren und den Ausdruck der Seite zur Datenschutzakte nehmen."),
  p([
    t("Dasselbe gilt für Modelle fremder Anbieter aus dem AWS-Marktplatz", { bold: true }),
    t(" — die bringen eigene Vertragsbedingungen mit, die wir nicht geprüft haben."),
  ], { spacing: { before: 120, after: 120 } }),

  h2("Wo das Modell steht"),
  punkt([t("In START-JURNODES.bat, Eintrag "), t("JUSPERFECT_MODELL_ID", { font: "Consolas" }), t(".")]),
  punkt([t("Zum Nachsehen genügt die Oberfläche: ", { bold: true }), t("Unter jeder Antwort steht, welches Modell sie erzeugt hat.")]),

  h2("Einmal im Jahr"),
  p([
    t("Die Seite wird bei der jährlichen Durchsicht der Folgenabschätzung erneut angesehen. Sie ist "),
    t("Dokumentation und kein Vertrag", { bold: true }),
    t(" — AWS kann sie ohne Ankündigung ändern und ein Modell aufnehmen, auch unseres."),
  ], { spacing: { after: 120 } }),
  linie()
);

// ------------------------------------------------------------- Regel 2
inhalt.push(
  h1("Regel 2 — Die E-Mail-Adresse des AWS-Kontos wird gelesen"),
  p([t("Benannt ist: ", { bold: true }), t("........................................  "), t("(Adresse eintragen)", { italics: true })], { spacing: { after: 160 } }),
  p([t("Dafür verantwortlich ist: ", { bold: true }), t("........................................")], { spacing: { after: 160 } }),
  p([t("Vertretung: ", { bold: true }), t("........................................")], { spacing: { after: 200 } }),

  h2("Warum"),
  p([
    t("Erkennt AWS einen möglichen Verstoß gegen seine Nutzungsbedingungen, fragt es "),
    t("per E-Mail an die Kontoadresse", { bold: true }),
    t(" nach. Erfolgt keine Antwort, "),
    t("kann AWS den Zugang zu Amazon Bedrock oder zu einzelnen Modellen sperren.", { bold: true }),
  ], { spacing: { after: 120 } }),
  p([
    t("Eine Sperre bedeutet: "),
    t("jusperfect steht still.", { bold: true }),
    t(" Keine Analyse, kein Entwurf, keine Texterkennung — mitten in der Arbeit und ohne Vorwarnung, weil die Vorwarnung in einem Postfach lag, das niemand liest."),
  ], { spacing: { after: 120 } }),
  p("An dieselbe Adresse gehen auch die übrigen Nachrichten von AWS: Rechnungen, Hinweise auf Änderungen an Diensten, Fristen.", { spacing: { after: 120 } }),

  h2("Was zu tun ist"),
  ((aktuelleListe = neueListe()), leer()),
  nr([t("Eine Adresse benennen, die "), t("tatsächlich gelesen wird", { bold: true }), t(" — kein Sammelkorb, der einmal im Quartal geöffnet wird.")]),
  nr("Eine Person benennen, die dafür zuständig ist, und eine Vertretung für Urlaub und Krankheit."),
  nr([
    t("Feststellen, welche Adresse AWS heute wirklich verwendet — nicht annehmen. ", { bold: true }),
    t("Daf\u00FCr gen\u00FCgt ein Blick in die Postf\u00E4cher: Nachrichten mit dem Absender "),
    t("Amazon Web Services", { bold: true }),
    t(" liegen in genau dieser Adresse. Es gibt sie regelm\u00E4\u00DFig — die monatliche Rechnung, Hinweise auf \u00C4nderungen, und die Best\u00E4tigung, die AWS beim Anlegen der Organisation am 14.10.2026 geschickt hat."),
  ]),
  kasten([
    t("Die Anmeldung beweist es nur in einem Fall. ", { bold: true }),
    t("Wer sich mit einer "),
    t("E-Mail-Adresse", { bold: true }),
    t(" anmeldet, ist als Root-Benutzer unterwegs — dann ist das die Kontoadresse. Wer sich mit "),
    t("Kontonummer oder Kontoalias und einem Benutzernamen", { bold: true }),
    t(" anmeldet, benutzt einen IAM-Benutzer; dann sagt die Anmeldung \u00FCber die Kontoadresse "),
    t("nichts", { bold: true }),
    t("."),
  ]),
  nr([
    t("In der AWS-Konsole nachsehen, dass "),
    t("diese", { bold: true }),
    t(" Adresse hinterlegt ist, und nicht eine aus der Einrichtungszeit. Der Weg: oben rechts auf den "),
    t("Kontonamen", { bold: true }),
    t(", dann "),
    t("Konto", { bold: true }),
    t(" (Account). Oben steht die "),
    t("E-Mail-Adresse des Root-Benutzers", { bold: true }),
    t(", weiter unten stehen die "),
    t("alternativen Kontakte", { bold: true }),
    t(" für Abrechnung, Betrieb und Sicherheit."),
  ]),
  kasten([
    t("Verlassen Sie sich nicht auf die Root-Adresse. ", { bold: true }),
    t("Sie ist zugleich die Adresse für das Zurücksetzen des Passworts, wird deshalb gern abgeschottet und selten geöffnet — und dort läge dann die Rückfrage. "),
    t("Unter \u201EBetrieb\u201C und \u201ESicherheit\u201C geh\u00F6rt eine Adresse, die wirklich gelesen wird.", { bold: true }),
    t(" Die trägt man oben ein."),
  ]),
  nr([t("Bei einer Nachfrage von AWS "), t("nicht abwarten.", { bold: true }), t(" Wer nicht weiß, was zu antworten ist, fragt zurück — aber antwortet.")]),
  kasten([
    t("Was in eine solche Antwort nicht gehört: ", { bold: true }),
    t("Akteninhalt. Kein Ausschnitt, kein anonymisiertes Beispiel, kein Bildschirmfoto mit Text. Nach Ziffer 6.5 der AWS-Kundenvereinbarung überträgt ein Vorschlag an AWS diesem unwiderruflich sämtliche Rechte daran."),
  ]),
  linie()
);

// ------------------------------------------------------------- Herkunft
const zelle = (text, breite, fett, grau) =>
  new TableCell({
    width: { size: breite, type: WidthType.DXA },
    shading: grau ? { type: ShadingType.CLEAR, fill: "EFEFEF", color: "auto" } : undefined,
    margins: { top: 60, bottom: 60, left: 100, right: 100 },
    children: [new Paragraph({ children: [t(text, fett ? { bold: true } : {})], spacing: { after: 0 } })],
  });

inhalt.push(
  h1("Woher diese Regeln kommen"),
  new Table({
    columnWidths: [1200, 8154],
    width: { size: 9354, type: WidthType.DXA },
    rows: [
      new TableRow({ tableHeader: true, children: [zelle("Regel", 1200, true, true), zelle("Fundstelle", 8154, true, true)] }),
      new TableRow({ children: [zelle("1", 1200), zelle("DSFA-ENTWURF.md, Abschnitt 4, R4, [KANZLEI 22]; AWS Service Terms 50.12.1 und 50.12.2 (Stand 15.09.2026); Amazon Bedrock User Guide, „Abuse detection“", 8154)] }),
      new TableRow({ children: [zelle("2", 1200), zelle("ebenda, letzter Absatz zu [KANZLEI 22]; Amazon Bedrock User Guide, „General information“", 8154)] }),
    ],
  }),
  leer()
);

// ------------------------------------------------------------- Ausblick
inhalt.push(
  h1("Was hier noch hinzukommt"),
  p([
    t("Dieses Blatt ist "),
    t("nicht vollständig.", { bold: true }),
    t(" Die Folgenabschätzung nennt noch mindestens einen weiteren Punkt, der in die Einweisung gehört und hier noch nicht steht:"),
  ], { spacing: { after: 120 } }),
  punkt([
    t("Die Auswahl im Dokumentfenster ist die wirksamste Maßnahme in der Hand des Bearbeiters ", { bold: true }),
    t("(DSFA-ENTWURF.md, Abschnitt 2.4). Zum Modell gehen nur die angehakten Passagen — was nicht angehakt ist, sieht das Modell nie. Das ist keine Bequemlichkeitsfrage, sondern Datenminimierung nach Art. 5 Abs. 1 lit. c DSGVO."),
  ]),
  p("Weitere Punkte ergeben sich aus den noch offenen Stellen der Folgenabschätzung. Dieses Blatt wächst mit ihnen.", { spacing: { before: 120, after: 120 } })
);

// ------------------------------------------------------------- Unterschriften
inhalt.push(
  linie({ before: 400 }),
  p("Zur Kenntnis genommen:", { spacing: { after: 320 } }),
  p("Name ........................   Ort, Datum ........................   Unterschrift ........................", { spacing: { after: 320 } }),
  p("Name ........................   Ort, Datum ........................   Unterschrift ........................", { spacing: { after: 120 } })
);

const doc = new Document({
  creator: "Kanzlei Dortschy & Thunert",
  title: "Einweisung zur Arbeit mit jusperfect",
  description: "Regeln, die sich nicht aus der Bedienung ergeben",
  numbering: {
    config: [
      ...[1, 2, 3, 4].map((i) => ({
        reference: "liste" + i,
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
