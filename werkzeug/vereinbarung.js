// Setzt Fassung 1 aus Teil B von DATENSCHUTZHINWEISE-ENTWURF.md als Word-Datei:
// die Klausel fuer den Mandatsvertrag, zum Uebernehmen.
//
//   node werkzeug/vereinbarung.js <ausgabe.docx>

const fs = require("fs");
const d = require("docx");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel,
  BorderStyle, LevelFormat, AlignmentType,
} = d;

const SCHRIFT = "Franklin Gothic Book";

const t = (text, opt = {}) => new TextRun({ text, ...opt });
const p = (text, opt = {}) =>
  new Paragraph({ children: Array.isArray(text) ? text : [t(text)], ...opt });
const h1 = (text) =>
  new Paragraph({ text, heading: HeadingLevel.HEADING_1, spacing: { before: 400, after: 160 } });
const leer = () => new Paragraph({ children: [], spacing: { after: 120 } });

// Der Klauseltext steht in einem Rahmen: Er ist das, was uebernommen wird,
// und muss sich auf einen Blick vom Umliegenden abheben.
const klausel = (kinder, opt = {}) =>
  new Paragraph({
    children: Array.isArray(kinder) ? kinder : [t(kinder)],
    indent: { left: 280, right: 280 },
    spacing: { before: 160, after: 160, line: 300 },
    border: {
      left: { style: BorderStyle.SINGLE, size: 18, space: 14, color: "000000" },
    },
    ...opt,
  });

const punkt = (kinder) =>
  new Paragraph({
    children: Array.isArray(kinder) ? kinder : [t(kinder)],
    numbering: { reference: "punkte", level: 0 },
    spacing: { after: 120 },
  });

const inhalt = [
  new Paragraph({
    text: "Einsatz KI-gestützter Hilfsmittel",
    heading: HeadingLevel.TITLE,
    spacing: { after: 160 },
  }),
  p([t("Klausel für den Mandatsvertrag — Fassung 1 (Vereinbarung)", { bold: true })], { spacing: { after: 160 } }),
  p([
    t("Kanzlei Dortschy & Thunert · Stand 14. Oktober 2026 · "),
    t("Entwurf zur Übernahme, keine Rechtsberatung.", { italics: true }),
  ], { spacing: { after: 200 } }),
  new Paragraph({
    children: [],
    border: { bottom: { style: BorderStyle.SINGLE, size: 6, space: 8, color: "999999" } },
    spacing: { after: 240 },
  }),

  // ------------------------------------------------------------- Klausel
  p([t("Der Text", { bold: true })], { spacing: { after: 160 } }),

  klausel([
    t("Einsatz KI-gestützter Hilfsmittel. ", { bold: true }),
    t("Die Kanzlei setzt bei der Bearbeitung des Mandats ein KI-gestütztes Programm zur Auswertung der Akte ein. Dazu werden einzelne, von der Bearbeiterin oder dem Bearbeiter ausgewählte Abschnitte der Akte an einen Auftragsverarbeiter in Rechenzentren innerhalb der Europäischen Union übermittelt. Der Auftragsverarbeiter ist zur Verschwiegenheit verpflichtet; eine Nutzung der Inhalte über die Erbringung des Dienstes hinaus, insbesondere zum Training von KI-Modellen, ist vertraglich ausgeschlossen. Die anwaltliche Prüfung und jede Entscheidung bleiben bei der Kanzlei."),
  ]),
  klausel([
    t("Die Mandantschaft kann jederzeit verlangen, dass die Kanzlei das Programm in ihrem Mandat nicht einsetzt. ", { bold: true }),
    t("Die Bearbeitung erfolgt dann ohne dieses Hilfsmittel; Nachteile entstehen daraus nicht. Einzelheiten zur Verarbeitung stehen in unseren Datenschutzhinweisen."),
  ], { spacing: { before: 160, after: 320 } }),

  // ------------------------------------------------------------- Begruendung
  h1("Warum das keine Einwilligung ist"),
  p([
    t("Dieser Absatz "),
    t("beschreibt, wie das Mandat bearbeitet wird.", { bold: true }),
    t(" Er ist Bestandteil des Mandatsvertrags und damit Teil dessen, was nach "),
    t("Art. 6 Abs. 1 lit. b DSGVO", { bold: true }),
    t(" zu erfüllen ist — er trägt die Rechtsgrundlage, statt sie durch eine zweite zu ersetzen."),
  ], { spacing: { after: 140 } }),
  p([
    t("Das Verlangen, das Programm nicht einzusetzen, ist bewusst "),
    t("kein Widerruf nach Art. 7 Abs. 3.", { bold: true }),
    t(" Der Unterschied ist nicht sprachlich: Ein Widerruf ließe die Rechtsgrundlage entfallen. Hier bleibt sie bestehen, und die Kanzlei schuldet nur, auf das Hilfsmittel zu verzichten."),
  ], { spacing: { after: 140 } }),
  p([
    t("Was der Absatz nicht leistet und nicht leisten kann: ", { bold: true }),
    t("Für Daten von Gegnern, Zeugen und Dritten gilt ohnehin Art. 6 Abs. 1 lit. f. Deren Einverständnis ist weder zu erlangen noch nötig."),
  ], { spacing: { after: 200 } }),

  h1("Von einer zusätzlichen Einwilligung wird abgeraten"),
  p("Fünf Gründe, in der Reihenfolge ihres Gewichts:", { spacing: { after: 140 } }),
  punkt([t("Widerruf. ", { bold: true }), t("Eine Einwilligung ist jederzeit widerruflich (Art. 7 Abs. 3) — mitten im Mandat.")]),
  punkt([t("Freiwilligkeit. ", { bold: true }), t("Wer das Mandat faktisch nur mit Einwilligung bekommt, willigt nicht freiwillig ein (Art. 7 Abs. 4, ErwG 43). Eine unfreiwillige Einwilligung ist unwirksam.")]),
  punkt([t("Kein Nachrücken. ", { bold: true }), t("Fällt die Einwilligung weg, darf nach verbreiteter Auffassung nicht nachträglich auf lit. b oder lit. f umgestellt werden.")]),
  punkt([t("Dritte. ", { bold: true }), t("Gegner und Zeugen können nicht einwilligen; die Einwilligung des Mandanten deckt sie nicht.")]),
  punkt([t("Besondere Kategorien. ", { bold: true }), t("Art. 9 Abs. 2 lit. f (Rechtsansprüche) ist belastbarer als lit. a, weil er nicht widerruflich ist.")]),
  p([
    t("Diese Fassung gibt der Mandantschaft, was die Einwilligung geben soll — Offenheit über den Einsatz und die Möglichkeit, ihn abzulehnen —, "),
    t("ohne die Rechtsgrundlage daran zu hängen.", { bold: true }),
    t(" Der Unterschied zeigt sich erst im Streitfall, und dann ist er der ganze Unterschied."),
  ], { spacing: { before: 140, after: 200 } }),

  h1("Was dazugehört"),
  punkt([
    t("Die Ergänzung der Datenschutzhinweise nach Art. 13 DSGVO", { bold: true }),
    t(" — Teil A von DATENSCHUTZHINWEISE-ENTWURF.md. Die Klausel verweist darauf; ohne sie steht sie in der Luft."),
  ]),
  punkt([
    t("Die Entscheidung über die Rechtsgrundlage", { bold: true }),
    t(" ist dort ausformuliert und bleibt die der Kanzlei."),
  ]),
  punkt([
    t("Die Einweisung", { bold: true }),
    t(" (EINWEISUNG.md): Die Zusage \u201Ekein Training\u201C und die Zusage, dass nichts aufbewahrt wird, hängen am eingesetzten Modell. Regel 1 hält das."),
  ]),

  leer(),
  new Paragraph({
    children: [],
    border: { bottom: { style: BorderStyle.SINGLE, size: 6, space: 8, color: "999999" } },
    spacing: { before: 280, after: 280 },
  }),
  p("In die Mandatsbedingungen übernommen am ........................", { spacing: { after: 320 } }),
  p("Unterschrift ........................................", { spacing: { after: 120 } }),
];

const doc = new Document({
  creator: "Kanzlei Dortschy & Thunert",
  title: "Einsatz KI-gestützter Hilfsmittel — Klausel für den Mandatsvertrag",
  description: "Fassung 1: Vereinbarung statt Einwilligung",
  numbering: {
    config: [
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
