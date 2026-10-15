// Setzt die Mandatsunterlagen aus ihren Markdown-Fassungen als Word-Datei.
//
//   node werkzeug/mandatsunterlagen.js <quelle.md> <ausgabe.docx>
//
// Gesetzt wird ein kleiner, fester Ausschnitt von Markdown - der, den diese
// Unterlagen benutzen. Absichtlich kein vollstaendiger Satz: Was hier nicht
// steht, soll in den Quellen auch nicht vorkommen, damit gedruckt dasselbe
// herauskommt wie gelesen.

const fs = require("fs");
const d = require("docx");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType,
  Table, TableRow, TableCell, WidthType, ShadingType, BorderStyle, LevelFormat,
} = d;

const SCHRIFT = "Franklin Gothic Book";
const FEST = "Consolas";
const BREITE = 9354;                       // Satzspiegel in DXA

const quelle = process.argv[2];
const ausgabe = process.argv[3];
const zeilen = fs.readFileSync(quelle, "utf-8").split("\n");

// ── Satz innerhalb einer Zeile ──────────────────────────────────────────────
// **fett**, `fest`, *kursiv*. In dieser Reihenfolge, sonst frisst der Stern
// der Kursivschrift die Haelfte des Fettdrucks.
function stuecke(text, grund = {}) {
  const aus = [];
  const re = /(\*\*[^*]+\*\*|`[^`]+`|\*[^*]+\*)/g;
  let zuletzt = 0, t;
  while ((t = re.exec(text)) !== null) {
    if (t.index > zuletzt) aus.push(new TextRun({ text: text.slice(zuletzt, t.index), ...grund }));
    const s = t[0];
    if (s.startsWith("**")) aus.push(new TextRun({ text: s.slice(2, -2), bold: true, ...grund }));
    else if (s.startsWith("`")) aus.push(new TextRun({ text: s.slice(1, -1), font: FEST, ...grund }));
    else aus.push(new TextRun({ text: s.slice(1, -1), italics: true, ...grund }));
    zuletzt = t.index + s.length;
  }
  if (zuletzt < text.length) aus.push(new TextRun({ text: text.slice(zuletzt), ...grund }));
  return aus.length ? aus : [new TextRun({ text: "", ...grund })];
}

// ── Bausteine ───────────────────────────────────────────────────────────────
let listenNr = 0;
const neueListe = () => "liste" + ++listenNr;

// Zwei Leerzeichen am Zeilenende sind ein harter Umbruch: dieselbe Zeile
// geht weiter, aber auf einer neuen. Ohne das liefe ein Anschriftenblock zu
// einer einzigen Zeile zusammen - Strasse, Ort, E-Mail und Telefon in einem
// Fluss, und niemand findet darin die Telefonnummer.
const UMBRUCH = "\u0001";

const mitUmbruechen = (text, grund = {}) => {
  const teile = text.split(UMBRUCH);
  const aus = [];
  teile.forEach((t, n) => {
    const laeufe = stuecke(t, grund);
    if (n > 0 && laeufe.length) aus.push(new TextRun({ text: "", break: 1 }));
    aus.push(...laeufe);
  });
  return aus;
};

const absatz = (text, opt = {}) =>
  new Paragraph({ children: mitUmbruechen(text), spacing: { after: 140 }, ...opt });

const kasten = (teile) =>
  teile.map((text, i) =>
    new Paragraph({
      children: stuecke(text),
      indent: { left: 340 },
      spacing: { before: i === 0 ? 180 : 60, after: i === teile.length - 1 ? 200 : 60 },
      border: { left: { style: BorderStyle.SINGLE, size: 12, space: 12, color: "888888" } },
    }));

const zelle = (text, breite, kopf = false) =>
  new TableCell({
    width: { size: breite, type: WidthType.DXA },
    shading: kopf ? { type: ShadingType.CLEAR, fill: "EEF1F3" } : undefined,
    margins: { top: 70, bottom: 70, left: 110, right: 110 },
    children: [new Paragraph({
      children: stuecke(text, kopf ? { bold: true } : {}),
      spacing: { after: 0 },
    })],
  });

// ── Durchlauf ───────────────────────────────────────────────────────────────
const inhalt = [];
let listenKennung = neueListe();
let i = 0;

const spalten = (z) => z.split("|").slice(1, -1).map((s) => s.trim());

while (i < zeilen.length) {
  const z = zeilen[i];
  const roh = z.trimEnd();

  if (!roh.trim()) { i++; continue; }

  // Tabelle
  if (roh.startsWith("|") && (zeilen[i + 1] || "").trim().startsWith("|---")) {
    const kopf = spalten(roh);
    i += 2;
    const reihen = [];
    while (i < zeilen.length && zeilen[i].trim().startsWith("|")) {
      reihen.push(spalten(zeilen[i].trim()));
      i++;
    }
    const anzahl = kopf.length;
    const breiten = anzahl === 2 ? [2400, BREITE - 2400]
      : Array(anzahl).fill(Math.floor(BREITE / anzahl));
    // Eine Kopfzeile aus lauter leeren Zellen ist keine - dann wird sie
    // weggelassen, statt einen grauen Streifen ohne Text zu setzen.
    const mitKopf = kopf.some((t) => t !== "");
    inhalt.push(new Table({
      columnWidths: breiten,
      width: { size: BREITE, type: WidthType.DXA },
      rows: [
        ...(mitKopf ? [new TableRow({ tableHeader: true,
          children: kopf.map((t, n) => zelle(t, breiten[n], true)) })] : []),
        ...reihen.map((r) => new TableRow({ cantSplit: true,
          children: r.map((t, n) => zelle(t, breiten[n] || breiten[0])) })),
      ],
    }));
    inhalt.push(new Paragraph({ children: [], spacing: { after: 160 } }));
    continue;
  }

  // Kasten (zusammenhaengende > Zeilen)
  if (roh.startsWith(">")) {
    const teile = [];
    let gerade = "";
    while (i < zeilen.length && zeilen[i].trimEnd().startsWith(">")) {
      const t = zeilen[i].trimEnd().replace(/^>\s?/, "");
      if (!t.trim()) { if (gerade) { teile.push(gerade); gerade = ""; } }
      else gerade = gerade ? gerade + " " + t.trim() : t.trim();
      i++;
    }
    if (gerade) teile.push(gerade);
    inhalt.push(...kasten(teile));
    continue;
  }

  // Trennlinie
  if (/^---+$/.test(roh)) {
    inhalt.push(new Paragraph({
      children: [],
      border: { bottom: { style: BorderStyle.SINGLE, size: 6, space: 8, color: "999999" } },
      spacing: { before: 200, after: 200 },
    }));
    i++;
    continue;
  }

  // Ueberschriften
  if (roh.startsWith("### ")) {
    inhalt.push(new Paragraph({ children: stuecke(roh.slice(4)),
      heading: HeadingLevel.HEADING_2, spacing: { before: 280, after: 120 } }));
    i++; continue;
  }
  if (roh.startsWith("## ")) {
    inhalt.push(new Paragraph({ children: stuecke(roh.slice(3)),
      heading: HeadingLevel.HEADING_1, spacing: { before: 380, after: 150 } }));
    i++; continue;
  }
  if (roh.startsWith("# ")) {
    inhalt.push(new Paragraph({ children: stuecke(roh.slice(2)),
      heading: HeadingLevel.TITLE, spacing: { after: 200 } }));
    i++; continue;
  }

  // Aufzaehlung - zusammenhaengende Punkte teilen sich eine Kennung,
  // damit eine neue Liste wieder bei eins anfaengt.
  if (/^[*-] /.test(roh)) {
    while (i < zeilen.length && (/^[*-] /.test(zeilen[i].trimEnd()) || /^\s{2,}\S/.test(zeilen[i]))) {
      let t = zeilen[i].trimEnd().replace(/^[*-] /, "");
      i++;
      while (i < zeilen.length && /^\s{2,}\S/.test(zeilen[i])) { t += " " + zeilen[i].trim(); i++; }
      inhalt.push(new Paragraph({
        children: stuecke(t),
        numbering: { reference: "punkte", level: 0 },
        spacing: { after: 100 },
      }));
    }
    continue;
  }
  if (/^\d+\. /.test(roh)) {
    listenKennung = neueListe();
    while (i < zeilen.length && (/^\d+\. /.test(zeilen[i].trimEnd()) || /^\s{2,}\S/.test(zeilen[i]))) {
      let t = zeilen[i].trimEnd().replace(/^\d+\. /, "");
      i++;
      while (i < zeilen.length && /^\s{2,}\S/.test(zeilen[i])) { t += " " + zeilen[i].trim(); i++; }
      inhalt.push(new Paragraph({
        children: stuecke(t),
        numbering: { reference: listenKennung, level: 0 },
        spacing: { after: 100 },
      }));
    }
    continue;
  }

  // Gewoehnlicher Absatz - Folgezeilen gehoeren dazu.
  let text = roh.trim();
  let hart = /  $/.test(zeilen[i]);
  i++;
  while (i < zeilen.length) {
    const n = zeilen[i].trimEnd();
    if (!n.trim() || n.startsWith("#") || n.startsWith(">") || n.startsWith("|")
        || /^---+$/.test(n) || /^[*-] /.test(n) || /^\d+\. /.test(n)) break;
    text += (hart ? UMBRUCH : " ") + n.trim();
    hart = /  $/.test(zeilen[i]);
    i++;
  }
  inhalt.push(absatz(text));
}

const doc = new Document({
  creator: "Dortschy, Thunert und Partner mbB",
  title: quelle.replace(/.*\//, "").replace(/\.md$/, ""),
  numbering: {
    config: [
      ...Array.from({ length: Math.max(listenNr, 1) }, (_, n) => ({
        reference: "liste" + (n + 1),
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
      document: { run: { font: SCHRIFT, size: 22 }, paragraph: { spacing: { line: 276, after: 140 } } },
      title: { run: { font: SCHRIFT, size: 36, bold: true, color: "000000" }, paragraph: { spacing: { after: 200 } } },
      heading1: { run: { font: SCHRIFT, size: 26, bold: true, color: "000000" } },
      heading2: { run: { font: SCHRIFT, size: 23, bold: true, color: "000000" } },
    },
  },
  sections: [{
    properties: {
      page: {
        size: { width: 11906, height: 16838 },
        margin: { top: 1134, right: 1134, bottom: 1134, left: 1418 },
      },
    },
    children: inhalt,
  }],
});

Packer.toBuffer(doc).then((buf) => {
  fs.writeFileSync(ausgabe, buf);
  console.log("geschrieben:", ausgabe);
});
