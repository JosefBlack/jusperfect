// Setzt die Bildschirmausdrucke zum Aktenvermerk vom 14.10.2026 zu einem
// Anlagenkonvolut: je Aufnahme eine Seite, beschriftet nach dem
// Anlagenverzeichnis des Vermerks.
//
// Aufruf: node werkzeug/anlagen-aws.js <bilderordner> <ausgabe.docx>
//
// Die Dateinamen unten sind die der Aufnahmen vom 14.10.2026. Fuer einen
// neuen Satz Bildschirmausdrucke wird die Liste `seiten` angepasst: je
// Eintrag Dateiname, Masse in Bildpunkten, Anlagennummer, Ueberschrift und
// Fussnote. `quer: true` legt das Blatt quer - noetig bei den breiten
// Listenansichten der Konsole, deren Schrift hochkant unleserlich wird.

const fs = require("fs");
const path = require("path");
const d = require("docx");
const {
  Document, Packer, Paragraph, TextRun, ImageRun,
  BorderStyle, PageBreak, PageOrientation,
} = d;

const SCHRIFT = "Franklin Gothic Book";
const ordner = process.argv[2];
const ausgabe = process.argv[3];

// docx rechnet Bildmasse in BILDPUNKTEN zu 96 je Zoll, nicht in Punkt zu 72.
// Mit Punkt gerechnet kommt das Bild auf drei Viertel der Breite heraus.
const JE_MM = 96 / 25.4;
const BREITE_PX = 170 * JE_MM; // Satzspiegel A4 hoch bei 2 cm Rand: 17 cm
const HOEHE_PX = 190 * JE_MM; // was unter der Beschriftung noch auf die Seite geht
// Die Listenansichten der Konsole sind sehr breit. Auf 17 cm gesetzt wird ihre
// Schrift auf dem Papier unleserlich; quer stehen 25,7 cm zur Verfuegung.
const BREITE_QUER_PX = 257 * JE_MM;
const HOEHE_QUER_PX = 120 * JE_MM;

const seiten = [
  {
    datei: "18.png",
    masse: [1061, 754],
    anlage: "Anlage 1",
    titel: "Effektive AI-Richtlinie für das Konto 579138738703",
    fuss:
      "AWS Organizations, Reiter \u201ERichtlinien\u201C des Kontos, Ansicht \u201EEffektive AI-Richtlinie\u201C. " +
      "Stand der Richtlinie laut Anzeige: 14.10.2026, 17:11:54 Uhr MESZ. Keine Validierungsprobleme.",
  },
  {
    datei: "3.png",
    masse: [924, 492],
    anlage: "Anlage 2",
    titel: "Angewendete Richtlinien am Konto \u2014 Quelle \u201EVerkn\u00FCpft mit Root\u201C",
    fuss:
      "AWS Organizations, Konto 579138738703, Abschnitt \u201EAbmelderichtlinien f\u00FCr KI-Services\u201C. " +
      "Die Richtlinie jusperfect-keine-ki-nutzung ist dem Konto über die Stammorganisation zugeordnet.",
  },
  {
    datei: "2.png",
    masse: [993, 765],
    anlage: "Anlage 2a",
    titel: "Die Richtlinie jusperfect-keine-ki-nutzung und ihr Inhalt",
    fuss:
      "Bestätigung der Zuordnung an das Stammverzeichnis sowie der Richtlinieninhalt " +
      "(services/default/opt_out_policy = optOut).",
  },
  {
    datei: "4.png",
    quer: true,
    masse: [1851, 734],
    anlage: "Anlage 3",
    titel: "Kontovereinbarungen in AWS Artifact (Blatt 1 von 3)",
    fuss:
      "Zehn Einträge, sämtlich inaktiv. Der Hinweis oben betrifft die am 14.10.2026 angelegte Organisation. " +
      "Keine der Vereinbarungen ist für die Kanzlei einschlägig; keine wurde angenommen.",
  },
  {
    datei: "5.png",
    quer: true,
    masse: [1499, 608],
    anlage: "Anlage 3",
    titel: "Kontovereinbarungen in AWS Artifact (Blatt 2 von 3)",
    fuss: "Fortsetzung der Liste.",
  },
  {
    datei: "6.png",
    quer: true,
    masse: [1516, 632],
    anlage: "Anlage 3",
    titel: "Kontovereinbarungen in AWS Artifact (Blatt 3 von 3)",
    fuss: "Fortsetzung der Liste.",
  },
  {
    datei: "7.png",
    quer: true,
    masse: [1555, 508],
    anlage: "Anlage 3",
    titel: "Organisationsvereinbarungen in AWS Artifact (Blatt 1 von 3)",
    fuss: "Fünf Einträge, sämtlich inaktiv. Auch hier ist keine Vereinbarung einschlägig oder angenommen.",
  },
  {
    datei: "8.png",
    quer: true,
    masse: [1560, 467],
    anlage: "Anlage 3",
    titel: "Organisationsvereinbarungen in AWS Artifact (Blatt 2 von 3)",
    fuss: "Fortsetzung der Liste.",
  },
  {
    datei: "9.png",
    quer: true,
    masse: [1495, 757],
    anlage: "Anlage 3",
    titel: "Organisationsvereinbarungen in AWS Artifact (Blatt 3 von 3)",
    fuss: "Fortsetzung der Liste.",
  },
];

const t = (text, opt = {}) => new TextRun({ text, ...opt });

function blatt(s, erstes) {
  const [bw, bh] = s.masse;
  const maxB = s.quer ? BREITE_QUER_PX : BREITE_PX;
  const maxH = s.quer ? HOEHE_QUER_PX : HOEHE_PX;
  let w = maxB;
  let h = (bh / bw) * w;
  if (h > maxH) {
    h = maxH;
    w = (bw / bh) * h;
  }

  const kinder = [];
  if (!erstes) {
    kinder.push(new Paragraph({ children: [new PageBreak()] }));
  }

  kinder.push(
    new Paragraph({
      children: [t(s.anlage, { bold: true, size: 28 })],
      spacing: { after: 80 },
    }),
    new Paragraph({
      children: [t(s.titel, { size: 24 })],
      spacing: { after: 240 },
      border: { bottom: { style: BorderStyle.SINGLE, size: 6, space: 8, color: "999999" } },
    }),
    new Paragraph({
      children: [
        new ImageRun({
          type: "png",
          data: fs.readFileSync(path.join(ordner, s.datei)),
          transformation: { width: Math.round(w), height: Math.round(h) },
        }),
      ],
      // Ohne lineRule "auto" klemmt Word das Bild auf die Zeilenhoehe des
      // Absatzes und zeigt nur einen Streifen davon.
      spacing: { before: 200, after: 240, line: 240, lineRule: "auto" },
    }),
    new Paragraph({
      children: [t(s.fuss, { size: 20, italics: true })],
      spacing: { before: 120 },
    }),
    new Paragraph({
      children: [
        t(
          "Bildschirmausdruck vom 14.10.2026, Kanzlei Dortschy & Thunert — Anlage zum Aktenvermerk gleichen Datums.",
          { size: 18, color: "666666" }
        ),
      ],
      spacing: { before: 80 },
    })
  );
  return kinder;
}

const hoch = seiten.filter((s) => !s.quer);
const quer = seiten.filter((s) => s.quer);

const doc = new Document({
  creator: "Kanzlei Dortschy & Thunert",
  title: "Anlagen zum Aktenvermerk AWS vom 14.10.2026",
  description: "Bildschirmausdrucke zu den Anlagen 1 bis 3",
  styles: {
    default: {
      document: { run: { font: SCHRIFT, size: 22 }, paragraph: { spacing: { line: 276 } } },
    },
  },
  sections: [
    {
      properties: {
        page: {
          size: { width: 11906, height: 16838 },
          margin: { top: 1134, right: 1134, bottom: 1134, left: 1134 },
        },
      },
      children: hoch.flatMap((s, i) => blatt(s, i === 0)),
    },
    {
      properties: {
        page: {
          // Hoch-Masse angeben; die Kennzeichnung dreht das Blatt.
          size: { width: 11906, height: 16838, orientation: PageOrientation.LANDSCAPE },
          margin: { top: 1134, right: 1134, bottom: 1134, left: 1134 },
        },
      },
      children: quer.flatMap((s, i) => blatt(s, i === 0)),
    },
  ],
});

Packer.toBuffer(doc).then((buf) => {
  fs.writeFileSync(ausgabe, buf);
  console.log("geschrieben:", ausgabe, "-", hoch.length, "hoch,", quer.length, "quer");
});
