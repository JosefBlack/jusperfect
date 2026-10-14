const fs = require("fs");
const d = require("docx");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType,
  Table, TableRow, TableCell, WidthType, ShadingType, BorderStyle,
  LevelFormat, convertMillimetersToTwip,
} = d;

const SCHRIFT = "Franklin Gothic Book";
const BREITE = 9354; // Satzspiegel in DXA

const t = (text, opt = {}) => new TextRun({ text, ...opt });

const p = (text, opt = {}) =>
  new Paragraph({ children: Array.isArray(text) ? text : [t(text)], ...opt });

const h1 = (text) =>
  new Paragraph({ text, heading: HeadingLevel.HEADING_1, spacing: { before: 360, after: 160 } });

const h2 = (text) =>
  new Paragraph({ text, heading: HeadingLevel.HEADING_2, spacing: { before: 280, after: 120 } });

const leer = () => new Paragraph({ children: [], spacing: { after: 120 } });

// Aufzaehlung mit Zahlen
let listenNr = 0;
const neueListe = () => { listenNr += 1; return "liste" + listenNr; };
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

// Hervorgehobener Kasten: Absatz mit linkem Rand und Einzug
const kasten = (kinder) =>
  new Paragraph({
    children: Array.isArray(kinder) ? kinder : [t(kinder)],
    indent: { left: 340 },
    spacing: { before: 160, after: 200 },
    border: { left: { style: BorderStyle.SINGLE, size: 12, space: 12, color: "888888" } },
  });

function tabelle(kopf, zeilen, spalten) {
  const zelle = (kinder, breite, fett, grau) =>
    new TableCell({
      width: { size: breite, type: WidthType.DXA },
      shading: grau ? { type: ShadingType.CLEAR, fill: "EFEFEF", color: "auto" } : undefined,
      margins: { top: 60, bottom: 60, left: 100, right: 100 },
      children: [
        new Paragraph({
          children: Array.isArray(kinder) ? kinder : [t(kinder, fett ? { bold: true } : {})],
          spacing: { after: 0 },
        }),
      ],
    });

  return new Table({
    columnWidths: spalten,
    width: { size: spalten.reduce((a, b) => a + b, 0), type: WidthType.DXA },
    rows: [
      new TableRow({
        tableHeader: true,
        children: kopf.map((z, i) => zelle(z, spalten[i], true, true)),
      }),
      ...zeilen.map(
        (r) => new TableRow({ children: r.map((z, i) => zelle(z, spalten[i], false, false)) })
      ),
    ],
  });
}

const inhalt = [];

// ---------------------------------------------------------------- Kopf
inhalt.push(
  new Paragraph({
    text: "Aktenvermerk",
    heading: HeadingLevel.TITLE,
    spacing: { after: 240 },
  }),
  p([t("Kanzlei Dortschy & Thunert", { bold: true })], { spacing: { after: 240 } }),
  p([
    t("Gegenstand: ", { bold: true }),
    t("Nachweise zum Auftragsverarbeiter Amazon Web Services — AI-services-Opt-out-Richtlinie, Vertragslage, Zertifikate und Prüfberichte"),
  ], { spacing: { after: 120 } }),
  p([t("Datum: ", { bold: true }), t("14. Oktober 2026")], { spacing: { after: 120 } }),
  p([
    t("Zur Datenschutzakte. ", { bold: true }),
    t("Betrifft die Datenschutz-Folgenabschätzung nach Art. 35 DSGVO zum Programm jusperfect sowie die Dokumentation der Dienstleisterauswahl nach § 43e Abs. 2 BRAO."),
  ], { spacing: { after: 160 } }),
  new Paragraph({
    children: [],
    border: { bottom: { style: BorderStyle.SINGLE, size: 6, space: 8, color: "999999" } },
    spacing: { after: 160 },
  })
);

// ---------------------------------------------------------------- 1
inhalt.push(
  h1("1. Anlass"),
  p("Die Folgenabschätzung geht davon aus, dass bei der Verarbeitung durch die KI-Dienste von AWS keine Inhalte gespeichert und keine zur Verbesserung der Dienste verwendet werden. Eine Zweitprüfung hat am 5. Oktober 2026 festgestellt, dass dieser Schluss ohne eine wirksame AI-services-Opt-out-Richtlinie des Kontos nicht trägt. Bis zu deren Nachweis durfte keine Unterlage der Kanzlei eine Nicht-Speicherung behaupten.", { spacing: { after: 120 } }),
  p("Daneben war die Auswahl des Auftragsverarbeiters nach § 43e Abs. 2 BRAO zu dokumentieren.", { spacing: { after: 120 } }),
  p("Beides ist am heutigen Tage erledigt worden. Der Vorgang ist nachstehend festgehalten.", { spacing: { after: 120 } })
);

// ---------------------------------------------------------------- 2
inhalt.push(
  h1("2. Was festgestellt wurde"),
  h2("2.1 Die Opt-out-Richtlinie"),
  p([
    t("Betroffen ist das AWS-Konto "),
    t("579138738703", { bold: true }),
    t(", Region eu-central-1 (Frankfurt am Main)."),
  ], { spacing: { after: 120 } }),
  ((aktuelleListe = neueListe()), leer()),
  nr("Für das Konto wurde eine AWS-Organisation angelegt. Sie besteht aus diesem einen Konto; es ist zugleich das Verwaltungskonto. Eine Opt-out-Richtlinie ist nur innerhalb einer Organisation möglich."),
  nr([
    t("Die Richtlinienart "),
    t("\u201EAbmelderichtlinien f\u00FCr KI-Services\u201C", { bold: true }),
    t(" (AI services opt-out policies) wurde eingeschaltet."),
  ]),
  nr([
    t("Die Richtlinie "),
    t("jusperfect-keine-ki-nutzung", { bold: true }),
    t(" wurde angelegt und an die Stammorganisation gehängt."),
  ]),
  nr([
    t("Am Konto wurde die "),
    t("effektive", { bold: true }),
    t(" Richtlinie abgerufen. Sie lautet:"),
  ]),
  new Paragraph({
    children: [t('{ "services": { "default": { "opt_out_policy": "optOut" } } }', { font: "Consolas", size: 20 })],
    indent: { left: 700 },
    spacing: { before: 60, after: 120 },
  }),
  new Paragraph({
    children: [
      t("Zeitpunkt der Feststellung: ", {}),
      t("14.10.2026, 17:11 Uhr MESZ.", { bold: true }),
      t(" AWS meldet keine Validierungsprobleme. Als Quelle ist \u201EVerkn\u00FCpft mit Root\u201C ausgewiesen."),
    ],
    indent: { left: 700 },
    spacing: { after: 160 },
  }),
  kasten([
    t("Zum Unterschied zwischen erstellt und wirksam. ", { bold: true }),
    t("Eine angelegte, aber nicht angehängte Richtlinie bewirkt nichts und sieht in der Konsole fast genauso aus. Der Nachweis ist deshalb am Konto abgelesen worden und nicht an der Richtlinie. Damit ist zugleich geklärt, dass eine Richtlinie an der Stammorganisation auch das Verwaltungskonto erfasst — bei den Service-Kontrollrichtlinien ist das bekanntlich nicht so."),
  ])
);

inhalt.push(
  h2("2.2 Die Vereinbarungen"),
  p("In AWS Artifact wurden beide Reiter durchgesehen:", { spacing: { after: 100 } }),
  punkt([t("Kontovereinbarungen: ", { bold: true }), t("zehn Einträge, sämtlich inaktiv.")]),
  punkt([t("Organisationsvereinbarungen: ", { bold: true }), t("fünf Einträge, sämtlich inaktiv.")]),
  p([
    t("Es handelt sich durchweg um Zusatzvereinbarungen für besondere Lagen (Australien, Neuseeland, Japan, US-Gesundheitsdaten nach HIPAA, US-Wertpapieraufsicht nach SEC, kostenlose Beratungsleistungen). "),
    t("Keine davon ist für die Kanzlei einschlägig; keine wurde angenommen.", { bold: true }),
  ], { spacing: { before: 100, after: 120 } }),
  p("Ein gesonderter DSGVO-Zusatz steht dort nicht zur Annahme bereit. AWS hat ihn in die Kundenvereinbarung aufgenommen; er gilt ohne gesonderte Annahme.", { spacing: { after: 120 } })
);

inhalt.push(
  h2("2.3 Die Vertragslage"),
  p("Es liegen vor und sind geprüft:", { spacing: { after: 120 } }),
  tabelle(
    ["Unterlage", "Fassung"],
    [
      ["AWS Data Processing Addendum (Auftragsverarbeitungsvertrag)", "am 14.10.2026 abgerufen"],
      ["AWS-Kundenvereinbarung, deutsche Fassung", "Stand 01.06.2026"],
      ["AWS-Datenschutzhinweis", "Stand 18.05.2026"],
      ["AWS Service Terms, Abschnitt 50.12 (Amazon Bedrock)", "Stand 15.09.2026"],
    ],
    [6000, 3354]
  ),
  leer(),
  p([
    t("Das Data Processing Addendum ist Abschnitt für Abschnitt gegen Art. 28 Abs. 3 DSGVO gelesen worden; "),
    t("alle acht Punkte sind belegt.", { bold: true }),
  ], { spacing: { before: 120, after: 120 } }),
  p("Sechs Feststellungen daraus:", { spacing: { after: 100 } }),
  ((aktuelleListe = neueListe()), leer()),
  nr([
    t("Die Nutzungsschranke steht in der Kundenvereinbarung, nicht im Auftragsverarbeitungsvertrag. ", { bold: true }),
    t("Deren Ziffer 1.4 ist die tragende Stelle und reicht weiter, weil sie f\u00FCr \u201EIhre Inhalte\u201C gilt und nicht nur für personenbezogene Daten: AWS greift auf Inhalte nicht zu und nutzt sie nicht, außer soweit zur Wartung oder Erbringung der Services nötig oder gesetzlich gefordert. Ergänzend Ziffer 6.1."),
  ]),
  nr([
    t("Der Datenschutzhinweis gilt ausdrücklich nicht für Akteninhalt", { bold: true }),
    t(", sondern nur für Account-Informationen. Er nennt als Zweck unter anderem die Verbesserung der AWS-Angebote; dieser Zweck betrifft den Akteninhalt nicht."),
  ]),
  nr([
    t("Vertragspartei ist für Kunden mit Sitz in der EU die Amazon Web Services EMEA SARL, Luxemburg. ", { bold: true }),
    t("Ihr gegenüber ist die Haftung für grobe Fahrlässigkeit und Vorsatz nicht beschränkt."),
  ]),
  nr([
    t("Die Service Terms, Abschnitt 50.12, enthalten für Amazon Bedrock keine Erlaubnis, Inhalte zum Training oder zur Verbesserung der Dienste zu verwenden. ", { bold: true }),
    t("Das ist von Bedeutung, weil die Service Terms sowohl dem Auftragsverarbeitungsvertrag (Abschnitt 16) als auch der Kundenvereinbarung (Ziffer 11.2) vorgehen. Die Schranke aus Ziffer 1.4 bleibt damit unangetastet. Dass dieses Schweigen Absicht ist, zeigt der unmittelbar folgende Abschnitt 50.13 zu Amazon Q: Dort nimmt AWS sich das Gegenteil ausdrücklich heraus, einschließlich des Trainierens von Machine-Learning-Modellen, und verweist für den Widerspruch auf die Opt-out-Richtlinie."),
  ]),
  nr([
    t("Abschnitt 50.12.2 regelt jedoch eine Speicherung. ", { bold: true }),
    t("Für bestimmte, auf einer eigenen Seite von AWS genannte Modelle speichert Amazon Bedrock "),
    t("Ein- und Ausgaben bis zu 30 Tage", { bold: true }),
    t(" zum alleinigen Zweck der Erkennung von Verstößen gegen die Nutzungsbedingungen und "),
    t("überprüft sie im Verdachtsfall", { bold: true }),
    t(". Der Nachbarabschnitt zu Kiro (50.14.2) spricht dabei von \u201Em\u00F6glicher menschlicher \u00DCberpr\u00FCfung\u201C. Siehe Abschnitt 4 dieses Vermerks."),
  ]),
  nr([
    t("Nach Abschnitt 50.12.1 hängt die Rechtslage am gewählten Modell. ", { bold: true }),
    t("Ein Modell eines Drittanbieters aus dem AWS Marketplace brächte dessen eigene Bedingungen mit. Die Modellwahl in jusperfect ist deshalb keine rein technische Einstellung."),
  ]),
  p([
    t("Die Kundenvereinbarung, der Datenschutzhinweis und die Service Terms liegen in deutscher Übersetzung vor und tragen den Hinweis, dass bei Abweichungen die "),
    t("englische Fassung maßgeblich", { bold: true }),
    t(" ist."),
  ], { spacing: { before: 100, after: 120 } })
);

inhalt.push(
  h2("2.4 Die Nachweise der Prüfer"),
  p("Aus AWS Artifact wurden am 14.10.2026 abgerufen:", { spacing: { after: 120 } }),
  tabelle(
    ["Nachweis", "Gegenstand"],
    [
      ["ISO 27001:2022 Certification", "Informationssicherheit"],
      ["ISO 27017:2015 Certification", "Sicherheit in der Cloud"],
      ["ISO 27018:2019 Certification", "Schutz personenbezogener Daten in der Cloud"],
      ["ISO/IEC 27701:2019 Certification", "Datenschutz-Managementsystem"],
      [
        "System and Organization Controls (SOC) 2 Report, Typ 2",
        "Berichtszeitraum 1. April 2025 bis 31. März 2026; geprüfte Kriterien: Security, Availability, Confidentiality, Privacy",
      ],
      ["System and Organization Controls (SOC) 3 Report", "dasselbe Prüfurteil in weitergabefähiger Fassung"],
      ["SOC Continued Operations Letter", "Fortgeltung der geprüften Kontrollen über den Berichtszeitraum hinaus"],
    ],
    [4000, 5354]
  ),
  leer()
);

inhalt.push(
  h2("2.5 Die Missbrauchserkennung bei Amazon Bedrock"),
  p("Gelesen am 14.10.2026: der Abschnitt \u201EAbuse detection\u201C des Amazon Bedrock User Guide \u2014 die Seite, auf die Abschnitt 50.12.2 der Service Terms verweist \u2014 sowie Abschnitt 1.24 der Service Terms. Der User Guide ist Dokumentation und kein Vertrag; AWS kann ihn ohne Ank\u00FCndigung \u00E4ndern.", { spacing: { after: 140 } }),
  p([
    t("Abschnitt 1.24 betrifft die Kanzlei nicht. ", { bold: true }),
    t("Er regelt andere AWS-Dienste mit eingebauter, von Bedrock betriebener KI-Funktion (genannt werden unter anderem CloudWatch, CodeCatalyst, Connect, Q, SageMaker, Kiro und GuardDuty). jusperfect ruft die Bedrock-Schnittstelle unmittelbar auf und nutzt keinen dieser Dienste."),
  ], { spacing: { after: 140 } }),
  p([t("Die Seite nennt die betroffenen Modelle namentlich:", { bold: true })], { spacing: { after: 120 } }),
  tabelle(
    ["Modell", "Was aufbewahrt wird"],
    [
      ["OpenAI-Modelle, bis auf vier genannte", "vom Klassifikator aufgefallener Verkehr, bis zu 30 Tage"],
      ["Anthropic Claude Fable 5 und Claude Fable 5.1", "der gesamte Verkehr, bis zu 30 Tage; aufgefallener Verkehr zus\u00E4tzlich mit m\u00F6glicher menschlicher \u00DCberpr\u00FCfung durch AWS"],
      ["alle \u00FCbrigen", "nichts; es gilt das Zero-Operator-Access-Modell"],
    ],
    [4000, 5354]
  ),
  leer(),
  p([
    t("Das von jusperfect genutzte Modell anthropic.claude-opus-4-6-v1 steht nicht auf dieser Liste. ", { bold: true }),
    t("F\u00FCr die Verarbeitung der Kanzlei gilt damit nach dem Stand vom 14.10.2026: "),
    t("keine Aufbewahrung und keine \u00DCberpr\u00FCfung.", { bold: true }),
    t(" Die Kanzlei hat am 14.10.2026 best\u00E4tigt, dass dieses Modell im Betrieb eingestellt ist."),
  ], { spacing: { before: 120, after: 120 } }),
  p("Drei Angaben derselben Seite geh\u00F6ren dazu:", { spacing: { after: 100 } }),
  ((aktuelleListe = neueListe()), leer()),
  nr("W\u00FCrde ein gelistetes Modell genutzt, l\u00E4gen die aufbewahrten Daten bei regions\u00FCbergreifender Inferenz in der jeweiligen Verarbeitungsregion."),
  nr("Die Erkennung von Darstellungen des Kindesmissbrauchs arbeitet auf Bild-Ein- und -Ausgaben. jusperfect sendet an Bedrock ausschlie\u00DFlich Text."),
  nr("Aufbewahrtes wird nicht an die Modellanbieter weitergegeben."),
  kasten([
    t("Eine Betriebspflicht, die daraus folgt: ", { bold: true }),
    t("Erkennt AWS einen m\u00F6glichen Versto\u00DF, richtet es R\u00FCckfragen an die E-Mail-Adresse des AWS-Kontos und kann den Zugang sperren, wenn keine Antwort erfolgt. Diese Adresse ist zu pflegen und zu lesen."),
  ])
);

// ---------------------------------------------------------------- 3
inhalt.push(
  h1("3. Was daraus folgt"),
  ((aktuelleListe = neueListe()), leer()),
  nr([
    t("Für Amazon Textract", { bold: true }),
    t(" — die Texterkennung gescannter Seiten — ist damit belegt, dass Inhalte weder gespeichert noch zur Entwicklung und Verbesserung der AWS-KI-Dienste verwendet werden. Der Vorbehalt vom 5. Oktober 2026 ist gegenstandslos; die Unterlagen der Kanzlei sind entsprechend berichtigt worden."),
  ]),
  nr([
    t("Für Amazon Bedrock", { bold: true }),
    t(" — die Verarbeitung im Sprachmodell — gilt das "),
    t("nicht aus dieser Richtlinie.", { bold: true }),
    t(" Die Abmelderichtlinie erfasst Bedrock nicht. Dort trägt die vertragliche Schranke aus Ziffer 1.4 der Kundenvereinbarung, die durch die Service Terms bestätigt und nicht eingeschränkt wird. Die Aufbewahrung nach Abschnitt 50.12.2 greift für das "),
    t("genutzte Modell nicht", { bold: true }),
    t(" (Abschnitt 2.5); für die dort gelisteten Modelle gälte sie."),
  ]),
  nr([
    t("Die Auswahl des Auftragsverarbeiters", { bold: true }),
    t(" ist mit den unter 2.4 genannten Nachweisen belegbar. Die Bewertung, ob sie die Anforderungen des § 43e Abs. 2 BRAO tragen, bleibt der Kanzlei vorbehalten."),
  ]),
  nr([
    t("Nicht belegt und auch nicht behauptet", { bold: true }),
    t(" ist, dass AWS die Inhalte nicht lesen könne. Bedrock und Textract verarbeiten im Klartext; das ist technisch nicht anders möglich. Es handelt sich um Auftragsverarbeitung nach Art. 28 DSGVO und nicht um einen Vorgang, dem durch Verschlüsselung der Personenbezug genommen wäre."),
  ])
);

// ---------------------------------------------------------------- 4
inhalt.push(
  h1("4. Was offen bleibt"),
  p([
    t("Drei Punkte zur Missbrauchserkennung", { bold: true }),
    t(", nachdem die beiden Sachfragen geklärt sind (Abschnitt 2.5):"),
  ], { spacing: { after: 100 } }),
  ((aktuelleListe = neueListe()), leer()),
  nr([
    t("Die Liste gehört in die jährliche Durchsicht. ", { bold: true }),
    t("Sie ist Dokumentation und kein Vertrag; AWS kann ein Modell aufnehmen, auch das genutzte. Dann änderte sich die Bewertung."),
  ]),
  nr([
    t("Zwei Hausregeln in die Einweisung: ", { bold: true }),
    t("Für Mandatsakten wird kein Modell verwendet, das auf der Missbrauchserkennungsseite steht, und vor jedem Modellwechsel wird sie angesehen. Die E-Mail-Adresse des AWS-Kontos wird gelesen."),
  ]),
  nr([
    t("Die Hinweise nach Art. 13 DSGVO: ", { bold: true }),
    t("Nach heutigem Stand ist über eine Aufbewahrung bei Bedrock nichts zu sagen. Ändert sich die Liste, ändert sich das."),
  ]),
  p("Ferner zur Vervollständigung der Ablage: die englischen Fassungen der übersetzten Stücke, die Standardvertragsklauseln und die Liste der Unterauftragsverarbeiter.", { spacing: { before: 100, after: 120 } })
);

// ---------------------------------------------------------------- 5
inhalt.push(
  h1("5. Umgang mit den Anlagen"),
  p([
    t("Der SOC-2-Bericht ist vertrauliche Information von AWS. ", { bold: true }),
    t("Beim Abruf wurde die zugehörige Vertraulichkeitsvereinbarung angenommen. Daraus folgt:"),
  ], { spacing: { after: 100 } }),
  ((aktuelleListe = neueListe()), leer()),
  nr([
    t("Keine Auszüge. ", { bold: true }),
    t("Aus dem Bericht darf ohne ausdrückliche schriftliche Zustimmung von AWS nicht zitiert werden — auch nicht in der Folgenabschätzung oder in einem Schriftsatz."),
  ]),
  nr([
    t("Weitergabe an eine Aufsichtsbehörde ist zulässig", { bold: true }),
    t(", jedoch nur vollständig und unter ausdrücklichem Antrag auf vertrauliche Behandlung."),
  ]),
  nr([t("An Mandanten ist stattdessen der SOC-3-Bericht zu verwenden.", { bold: true })]),
  nr([
    t("Über jede Weitergabe ist Buch zu führen", { bold: true }),
    t(" (Datum, Empfänger, Anlass); AWS kann Einsicht in diese Aufzeichnungen verlangen."),
  ]),
  p([
    t("Die Anlagen verbleiben in der Datenschutzakte und werden "),
    t("nicht", { bold: true }),
    t(" in den Programmordner von jusperfect übernommen, da dieser weitergegeben wird."),
  ], { spacing: { before: 100, after: 120 } })
);

// ---------------------------------------------------------------- 6
inhalt.push(
  h1("6. Wiedervorlage"),
  p([
    t("Die Prüfberichte decken einen Zeitraum ab und veralten. Sie sind im Rahmen der "),
    t("jährlichen Durchsicht der Datenschutz-Folgenabschätzung", { bold: true }),
    t(" neu abzurufen. Eine gesonderte Frist wird nicht notiert."),
  ], { spacing: { after: 120 } })
);

// ---------------------------------------------------------------- 7
inhalt.push(h1("7. Anlagen"));
[
  "Bildschirmausdruck: effektive AI-Richtlinie für Konto 579138738703, 14.10.2026, 17:11 Uhr MESZ",
  "Bildschirmausdruck: angewendete Richtlinien am Konto, Quelle \u201EVerkn\u00FCpft mit Root\u201C",
  "Bildschirmausdruck: Konto- und Organisationsvereinbarungen in AWS Artifact",
  "AWS Data Processing Addendum",
  "AWS-Kundenvereinbarung, Fassung 01.06.2026",
  "AWS-Datenschutzhinweis, Fassung 18.05.2026",
  "ISO 27001:2022 Certification",
  "ISO 27017:2015 Certification",
  "ISO 27018:2019 Certification",
  "ISO/IEC 27701:2019 Certification",
  "SOC 2 Report, Typ 2, Berichtszeitraum 01.04.2025 – 31.03.2026",
  "SOC 3 Report",
  "SOC Continued Operations Letter",
  "Bildschirmausdruck der Vertraulichkeitsbedingungen f\u00FCr den Abruf der SOC-Berichte \u2014 vollst\u00E4ndiger Ausdruck \u00FCber die Schaltfl\u00E4che \u201EBedingungen ausdrucken\u201C nachzureichen",
  "Bildschirmausdruck: AWS Service Terms, Stand 15.09.2026, Abschnitt 50.12 (Amazon Bedrock) nebst Abschnitt 50.13 (Amazon Q) zum Vergleich",
  "Bildschirmausdruck: AWS Service Terms, Abschnitt 1.24",
  "Abschrift der Seite \u201EAmazon Bedrock abuse detection\u201C aus dem Amazon Bedrock User Guide, abgerufen am 14.10.2026 \u2014 ein Ausdruck der Seite selbst ist nachzureichen",
].forEach((z) =>
  inhalt.push(
    new Paragraph({
      children: [t(z)],
      numbering: { reference: "anlagen", level: 0 },
      spacing: { after: 60 },
    })
  )
);

// ---------------------------------------------------------------- Unterschrift
inhalt.push(
  new Paragraph({
    children: [],
    border: { bottom: { style: BorderStyle.SINGLE, size: 6, space: 8, color: "999999" } },
    spacing: { before: 200, after: 200 },
  }),
  p("Ort, Datum ........................................", { spacing: { after: 240 }, keepNext: true }),
  p("Unterschrift ........................................", { spacing: { after: 120 } })
);

const doc = new Document({
  creator: "Kanzlei Dortschy & Thunert",
  title: "Aktenvermerk AWS — 14.10.2026",
  description: "Nachweise zum Auftragsverarbeiter Amazon Web Services",
  numbering: {
    config: [
      ...[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map((i) => ({
        reference: "liste" + i,
        levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.START,
          style: { paragraph: { indent: { left: 700, hanging: 340 } } } }],
      })),
      {
        reference: "anlagen",
        levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.START,
          style: { paragraph: { indent: { left: 700, hanging: 340 } } } }],
      },
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
