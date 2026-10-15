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
// WENN DIE BILDER VERSCHWUNDEN SIND - und das ist am 15.10.2026 passiert:
// Sie stecken in der zuletzt gebauten Word-Datei und lassen sich daraus
// zurueckholen. Eine .docx ist ein Zip-Archiv; die Bilder liegen unter
// word/media/ mit unleserlichen Namen. Die ZUORDNUNG steht woanders:
//
//   1. word/_rels/document.xml.rels nennt zu jeder rId die Mediendatei.
//   2. word/document.xml nennt die rIds in der Reihenfolge der Blaetter.
//   3. Diese Reihenfolge ist die der Liste unten - also laesst sich jedem
//      Bild sein Name aus `datei` wieder zuweisen.
//
// Nach der Reihenfolge im Zip zu gehen fuehrt in die Irre; die ist eine
// andere. Nachgerechnet wird ueber die Anzahl: Sie muss stimmen.

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
      "Wortlaut liegt deshalb zus\u00E4tzlich als vollst\u00E4ndiger Ausdruck \u00FCber die Schaltfl\u00E4che \u201EBedingungen ausdrucken\u201C bei.",
  },
  {
    datei: "druck-1.png",
    masse: [1239, 1740],
    anlage: "Anlage 14",
    titel: "Vertraulichkeitsbedingungen — vollständiger Ausdruck (Blatt 2 von 2)",
    fuss:
      "Derselbe Text als Ausdruck über die Schaltfläche „Bedingungen ausdrucken“. Maßgeblich ist diese englische Fassung. Tragend sind vier Stellen: keine Auszüge ohne schriftliche Zustimmung; Weitergabe an einen Regulator nur vollständig und mit dem Antrag auf vertrauliche Behandlung; Weitergabe an einen Endnutzer nur mit eigener Vertraulichkeitsvereinbarung, die Amazon als begünstigten Dritten benennt; und die Pflicht, über jede Weitergabe Buch zu führen.",
    quelle: "Ausdruck vom 15.10.2026, Kanzlei Dortschy & Thunert — Anlage zum Aktenvermerk vom 14.10.2026.",
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
  {
    datei: "druck-2.png",
    masse: [1237, 1744],
    anlage: "Anlage 15",
    titel: "Abschnitte 50.10.3 bis 50.12.3 — Ausdruck (Blatt 1 von 3)",
    fuss:
      "Deutsche Fassung. Hier stehen die beiden tragenden Stellen im Wortlaut: 50.12.1 — Drittanbieter-Modelle sind „Inhalte von Drittanbietern“, und ihre Nutzung heißt Zustimmung zu deren eigenen Bedingungen; 50.12.2 — die Speicherung von Ein- und Ausgaben bis zu 30 Tage für die auf der Missbrauchserkennungsseite namentlich genannten Modelle.",
    quelle: "Ausdruck vom 15.10.2026, Kanzlei Dortschy & Thunert — Anlage zum Aktenvermerk vom 14.10.2026.",
  },
  {
    datei: "druck-3.png",
    masse: [1237, 1748],
    anlage: "Anlage 15",
    titel: "Abschnitte 50.12.4 bis 50.13.3 — Ausdruck (Blatt 2 von 3)",
    fuss:
      "Die Gegenprobe im Wortlaut: 50.13 (Amazon Q) räumt AWS ausdrücklich ein, was 50.12 für Amazon Bedrock gerade nicht einräumt — die Nutzung zur Entwicklung und Verbesserung einschließlich des Trainierens von Modellen. Wo AWS solche Rechte will, schreibt es sie hin.",
    quelle: "Ausdruck vom 15.10.2026, Kanzlei Dortschy & Thunert — Anlage zum Aktenvermerk vom 14.10.2026.",
  },
  {
    datei: "druck-4.png",
    masse: [1239, 1749],
    anlage: "Anlage 15",
    titel: "Abschnitte 50.14 bis 50.15.4 — Ausdruck (Blatt 3 von 3)",
    fuss:
      "Anschluss des vorigen Blattes, mit 50.14.2 (Kiro) und dem dortigen Verweis auf Abschnitt 1.24. Mitgedruckt, weil ein Ausdruck, der mitten im Satz endet, als Beleg wenig taugt.",
    quelle: "Ausdruck vom 15.10.2026, Kanzlei Dortschy & Thunert — Anlage zum Aktenvermerk vom 14.10.2026.",
  },
  {
    datei: "24.png",
    masse: [590, 550],
    anlage: "Anlage 16",
    titel: "AWS Service Terms, Abschnitt 1.24",
    fuss:
      "Abschnitt 1.24 regelt AWS-Dienste mit eingebauter, von Amazon Bedrock betriebener KI-Funktion "
      + "(CloudWatch, CodeCatalyst, Connect, Q, SageMaker, Kiro, GuardDuty und weitere). 1.24.1 erkl\u00E4rt "
      + "die Missbrauchserkennungsmechanismen von Bedrock f\u00FCr diese Dienste f\u00FCr anwendbar, 1.24.2 "
      + "nennt die regions\u00FCbergreifende Inferenz. jusperfect nutzt keinen dieser Dienste, sondern ruft "
      + "die Bedrock-Schnittstelle unmittelbar auf.",
  },
  {
    datei: "druck-5.png",
    masse: [1239, 1743],
    anlage: "Anlage 16",
    titel: "Abschnitte 1.20 bis 1.23 — Ausdruck (Blatt 1 von 2)",
    fuss:
      "Der Anlauf zu Abschnitt 1.24, mitgedruckt um der Vollständigkeit willen.",
    quelle: "Ausdruck vom 15.10.2026, Kanzlei Dortschy & Thunert — Anlage zum Aktenvermerk vom 14.10.2026.",
  },
  {
    datei: "druck-6.png",
    masse: [1237, 1748],
    anlage: "Anlage 16",
    titel: "Abschnitte 1.24.1 bis 1.32 — Ausdruck (Blatt 2 von 2)",
    fuss:
      "Abschnitt 1.24 im Wortlaut. Er regelt AWS-Dienste mit eingebauter, von Amazon Bedrock betriebener KI-Funktion. jusperfect nutzt keinen dieser Dienste, sondern ruft die Bedrock-Schnittstelle unmittelbar auf — 1.24 betrifft die Kanzlei damit nicht.",
    quelle: "Ausdruck vom 15.10.2026, Kanzlei Dortschy & Thunert — Anlage zum Aktenvermerk vom 14.10.2026.",
  },
  {
    wortlaut: [
      { h: "Amazon Bedrock abuse detection" },
      "You are responsible for your (and your end users') data input into, and content generated using, Amazon Bedrock. As part of providing the Service, Amazon Bedrock may use automated abuse detection mechanisms to detect activity that violates our, or third-party model providers', terms of service or use policies. In certain limited circumstances described below, we may also store or review model inputs or outputs. Amazon Bedrock uses a zero operator access (ZOA) data security model, subject to the model-specific abuse and CSAM detection detailed below.",
      { h: "Model-specific abuse detection" },
      "For abuse detection purposes related to the following models, we will store inputs and outputs as follows:",
      { b: "For all OpenAI models other than GPT OSS Safeguard 120B, GPT OSS Safeguard 20B, gpt-oss-120b, and gpt-oss-20b, classifier-flagged traffic will be retained for up to 30 days for automated offline abuse detection. Eligible customers may request full ZDR through their AWS account team." },
      { b: "For Anthropic Claude Fable 5 and Claude Fable 5.1, all traffic will be retained for up to 30 days for automated offline abuse detection. Classifier-flagged traffic will be subject to potential human review performed by AWS." },
      { b: "Customers that are eligible for the Enterprise Frontier Safeguards program will receive ZDR through December 31, 2026. After ZDR ends, all traffic will be retained for up to 30 days for automated offline abuse detection. The Enterprise Frontier Safeguards program plans to enable customer-managed encryption keys and bring your own bucket for storage for automated offline abuse detection." },
      "Retained inputs and outputs are stored and processed by AWS and are not shared with third-party model providers. For more information on data retention and related controls, see Data retention.",
      "If cross-region inference is enabled for these models, retained inputs and outputs are stored in destination regions (i.e., the region where your inference request is processed).",
      { h: "Child sexual abuse material (\u201CCSAM\u201D)" },
      "To help stop the dissemination of child sexual abuse material (\u201CCSAM\u201D), Amazon Bedrock uses automated abuse detection mechanisms to detect apparent CSAM. If Amazon Bedrock detects apparent CSAM in your image inputs or outputs, Amazon Bedrock may block the request and return a ValidationException (HTTP 400) error in the API response. Amazon Bedrock may store and review the flagged input or output exclusively to determine if it is CSAM and may also file a report with the National Center for Missing and Exploited Children (NCMEC) or a relevant authority. You might be required by applicable laws to take additional actions, and you are responsible for those actions.",
      { h: "General information" },
      "If an abuse detection mechanism identifies potential violations, we may request information about your use of Amazon Bedrock and compliance with relevant terms and policies. These requests are sent to the email address associated with your AWS account, so ensure that your account contact information is current and monitored. AWS may suspend your access to any model or Amazon Bedrock if you fail to comply with applicable terms or policies or are non-responsive.",
      "Contact your AWS account team or AWS Support if you have additional questions.",
    ],
    anlage: "Anlage 17",
    titel: "Amazon Bedrock abuse detection \u2014 Wortlaut der Seite",
    fuss:
      "DIES IST EINE ABSCHRIFT UND KEIN BILDSCHIRMAUSDRUCK. Der Wortlaut ist unver\u00E4ndert \u00FCbernommen; "
      + "Hervorhebungen, Verweise und die Gliederung der Urfassung sind nicht wiedergegeben. Ein Ausdruck der "
      + "Seite selbst liegt bei. \u2014 Das von der Kanzlei genutzte Modell "
      + "anthropic.claude-opus-4-6-v1 ist in keiner der drei Aufz\u00E4hlungen genannt; f\u00FCr es gilt damit "
      + "das Zero-Operator-Access-Modell.",
    quelle:
      "Amazon Bedrock User Guide, Abschnitt \u201EAbuse detection\u201C (Seiten 2152 f.), abgerufen am "
      + "14.10.2026, Kanzlei Dortschy & Thunert \u2014 Anlage zum Aktenvermerk gleichen Datums. Der User Guide "
      + "ist Dokumentation und kein Vertrag; AWS kann ihn ohne Ank\u00FCndigung \u00E4ndern.",
  },
  {
    datei: "druck-7.png",
    quer: true,
    masse: [1740, 1237],
    anlage: "Anlage 17",
    titel: "Amazon Bedrock abuse detection — Ausdruck (Blatt 1 von 3)",
    fuss:
      "Der Ausdruck der Seite selbst, zu der die Abschrift auf dem vorigen Blatt gehört. Kopf der Seite und Beginn des Abschnitts. Abschrift und Ausdruck liegen beide bei, weil die Abschrift lesbar und der Ausdruck der Beleg ist.",
    quelle: "Ausdruck der Seite vom 15.10.2026, 12:04 Uhr, Kanzlei Dortschy & Thunert — Anlage zum Aktenvermerk vom 14.10.2026. Der User Guide ist Dokumentation und kein Vertrag; AWS kann ihn ohne Ankündigung ändern.",
  },
  {
    datei: "druck-8.png",
    quer: true,
    masse: [1749, 1238],
    anlage: "Anlage 17",
    titel: "Model-specific abuse detection — Ausdruck (Blatt 2 von 3)",
    fuss:
      "Das tragende Blatt: Hier stehen die Modelle, bei denen Ein- und Ausgaben aufbewahrt werden, namentlich. Das von der Kanzlei eingesetzte Modell anthropic.claude-opus-4-6-v1 ist in keiner der drei Aufzählungen genannt.",
    quelle: "Ausdruck der Seite vom 15.10.2026, 12:04 Uhr, Kanzlei Dortschy & Thunert — Anlage zum Aktenvermerk vom 14.10.2026. Der User Guide ist Dokumentation und kein Vertrag; AWS kann ihn ohne Ankündigung ändern.",
  },
  {
    datei: "druck-9.png",
    quer: true,
    masse: [1746, 1239],
    anlage: "Anlage 17",
    titel: "General information — Ausdruck (Blatt 3 von 3)",
    fuss:
      "Der Abschnitt, aus dem Regel 2 der Einweisung folgt: Bei Verdacht fragt AWS an der E-Mail-Adresse des Kontos nach und kann den Zugang sperren, wenn niemand antwortet.",
    quelle: "Ausdruck der Seite vom 15.10.2026, 12:04 Uhr, Kanzlei Dortschy & Thunert — Anlage zum Aktenvermerk vom 14.10.2026. Der User Guide ist Dokumentation und kein Vertrag; AWS kann ihn ohne Ankündigung ändern.",
  },
];

const t = (text, opt = {}) => new TextRun({ text, ...opt });

function blatt(s, erstes) {
  const kopf = (fussText) => [
    ...(erstes ? [] : [new Paragraph({ children: [new PageBreak()] })]),
    new Paragraph({
      children: [t(s.anlage, { bold: true, size: 28 })],
      spacing: { after: 80 },
    }),
    new Paragraph({
      children: [t(s.titel, { size: 24 })],
      spacing: { after: 240 },
      border: { bottom: { style: BorderStyle.SINGLE, size: 6, space: 8, color: "999999" } },
    }),
  ];

  // Ein Blatt kann statt einer Aufnahme auch WORTLAUT tragen. Dann ist es
  // eine Abschrift und kein Bildschirmausdruck - und sagt das auch.
  if (s.wortlaut) {
    const kinder = kopf();
    // Der Vorbehalt steht VOR dem Wortlaut: Wer liest, soll vorher wissen,
    // was er vor sich hat.
    kinder.push(new Paragraph({
      children: [t(s.fuss, { size: 20, italics: true })],
      spacing: { after: 280 },
      border: { bottom: { style: BorderStyle.SINGLE, size: 6, space: 10, color: "999999" } },
    }));
    s.wortlaut.forEach((z) => {
      if (typeof z === "string") {
        kinder.push(new Paragraph({ children: [t(z, { size: 18 })], spacing: { after: 100 } }));
      } else if (z.h) {
        kinder.push(new Paragraph({
          children: [t(z.h, { size: 21, bold: true })],
          spacing: { before: 200, after: 100 },
        }));
      } else if (z.b) {
        kinder.push(new Paragraph({
          children: [t("\u2022  " + z.b, { size: 18 })],
          indent: { left: 340, hanging: 220 },
          spacing: { after: 100 },
        }));
      }
    });
    kinder.push(new Paragraph({
      children: [t(s.quelle, { size: 18, color: "666666" })],
      spacing: { before: 240 },
      border: { top: { style: BorderStyle.SINGLE, size: 6, space: 10, color: "999999" } },
    }));
    return kinder;
  }

  const [bw, bh] = s.masse;
  const maxB = s.quer ? BREITE_QUER_PX : BREITE_PX;
  const maxH = s.quer ? HOEHE_QUER_PX : HOEHE_PX;
  let w = maxB;
  let h = (bh / bw) * w;
  if (h > maxH) {
    h = maxH;
    w = (bw / bh) * h;
  }

  const kinder = kopf();

  kinder.push(
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
      // Je Blatt verschieden, seit Ausdrucke dazugekommen sind: Ein Ausdruck
      // vom 15.10.2026 ist kein Bildschirmausdruck vom 14.10.2026, und in
      // einer Akte ist das der Unterschied zwischen Beleg und Behauptung.
      children: [
        t(
          s.quelle ||
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
