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
  {
    datei: "11.png",
    masse: [817, 828],
    anlage: "Anlage 14",
    titel: "Vertraulichkeitsbedingungen f\u00FCr den Abruf der SOC-Berichte",
    fuss:
      "Der Dialog \u201EBedingungen zum Herunterladen des Berichts akzeptieren\u201C, wie er beim Abruf des " +
      "ersten SOC-Berichts angezeigt wurde. Ob der sichtbare Text vollst\u00E4ndig ist, l\u00E4sst sich " +
      "an der Aufnahme nicht abschlie\u00DFend feststellen (Bildlaufleiste rechts). Der ma\u00DFgebliche " +
      "Wortlaut ist \u00FCber die Schaltfl\u00E4che \u201EBedingungen ausdrucken\u201C zu beziehen und " +
      "dieser Anlage nachzureichen.",
  },
  {
    datei: "19.png",
    masse: [373, 81],
    anlage: "Anlage 15",
    titel: "AWS Service Terms \u2014 Stand der Fassung",
    fuss:
      "Kopf der Seite mit dem Stand der Fassung: 15. September 2026. Die Service Terms gehen nach " +
      "Abschnitt 16 des Data Processing Addendum und Ziffer 11.2 der Kundenvereinbarung beiden vor.",
  },
  {
    datei: "20.png",
    masse: [799, 671],
    anlage: "Anlage 15",
    titel: "Abschnitt 50.12 Amazon Bedrock (Blatt 1 von 4)",
    fuss:
      "50.12.1 Modelle von Drittanbietern; 50.12.2 Erkennung von Missbrauch \u2014 Speicherung von Ein- und " +
      "Ausgaben bis zu 30 Tage f\u00FCr bestimmte Modelle, mit \u00DCberpr\u00FCfung im Verdachtsfall; " +
      "50.12.3 Durchsatzverpflichtungen.",
  },
  {
    datei: "21.png",
    masse: [678, 832],
    anlage: "Anlage 15",
    titel: "Abschnitt 50.12 Amazon Bedrock (Blatt 2 von 4)",
    fuss:
      "50.12.4 bis 50.12.6; anschlie\u00DFend 50.13 Amazon Q. Der Vergleich ist der Grund, warum dieses " +
      "Blatt dabei ist: F\u00FCr Amazon Q nimmt AWS sich die Nutzung zur Verbesserung ausdr\u00FCcklich " +
      "heraus \u2014 f\u00FCr Bedrock an keiner Stelle.",
  },
  {
    datei: "22.png",
    masse: [700, 370],
    anlage: "Anlage 15",
    titel: "Abschnitt 50.13 Amazon Q zum Vergleich (Blatt 3 von 4)",
    fuss:
      "50.13.1 bis 50.13.3: Nutzung zur Entwicklung und Verbesserung, ausdr\u00FCcklich einschlie\u00DFlich " +
      "des \u201ETrainieren[s] von Machine-Learning-Modellen\u201C, und Verweis auf die " +
      "Opt-out-Richtlinie f\u00FCr den Widerspruch. Das rechts eingeblendete Men\u00FC des " +
      "Anzeigeprogramms geh\u00F6rt nicht zum Vertragstext.",
  },
  {
    datei: "23.png",
    masse: [483, 356],
    anlage: "Anlage 15",
    titel: "Abschnitt 50.14.2 Kiro (Blatt 4 von 4)",
    fuss:
      "Die Bestimmung verweist auf Abschnitt 1.24 der Service Terms und spricht von der Speicherung und " +
      "\u201Em\u00F6glichen menschlichen \u00DCberpr\u00FCfung von Eingaben und Ausgaben\u201C durch die " +
      "Missbrauchserkennungsmechanismen von Amazon Bedrock. Abschnitt 1.24 liegt noch nicht vor.",
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

// Die Abschnitte folgen der Reihenfolge der Anlagen; ein neuer Abschnitt
// beginnt, sobald sich die Blattlage aendert. Sortiert man stattdessen nach
// Lage, stuenden die Anlagen in falscher Folge.
const gruppen = [];
seiten.forEach((s) => {
  const letzte = gruppen[gruppen.length - 1];
  if (letzte && !!letzte.quer === !!s.quer) letzte.seiten.push(s);
  else gruppen.push({ quer: !!s.quer, seiten: [s] });
});

const doc = new Document({
  creator: "Kanzlei Dortschy & Thunert",
  title: "Anlagen zum Aktenvermerk AWS vom 14.10.2026",
  description: "Bildschirmausdrucke zu den Anlagen 1 bis 3",
  styles: {
    default: {
      document: { run: { font: SCHRIFT, size: 22 }, paragraph: { spacing: { line: 276 } } },
    },
  },
  sections: gruppen.map((g) => ({
    properties: {
      page: {
        // Immer die Hoch-Masse angeben; die Kennzeichnung dreht das Blatt.
        size: g.quer
          ? { width: 11906, height: 16838, orientation: PageOrientation.LANDSCAPE }
          : { width: 11906, height: 16838 },
        margin: { top: 1134, right: 1134, bottom: 1134, left: 1134 },
      },
    },
    children: g.seiten.flatMap((s, i) => blatt(s, i === 0)),
  })),
});

Packer.toBuffer(doc).then((buf) => {
  fs.writeFileSync(ausgabe, buf);
  console.log("geschrieben:", ausgabe, "-", seiten.length, "Seiten in", gruppen.length, "Abschnitten");
});
