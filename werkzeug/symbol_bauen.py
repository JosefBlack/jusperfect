"""Das Programmsymbol fuer jusperfect.

Gruener Grund, das j in Weiss, der Punkt darauf in Bernstein: die Fundstelle.
Das ist der Kern des Programms - jeder Satz traegt seinen Beleg - und zugleich
das eine Merkmal, an dem man es bei sechzehn Pixeln in der Taskleiste
wiedererkennt.

Eine helle Fassung war zwischenzeitlich eingebaut und wurde wieder verworfen;
das satte Gruen setzt sich auf jedem Schreibtisch durch und braucht dafuer
keinen Umriss.

Gezeichnet wird vierfach zu gross und heruntergerechnet - so werden Rundungen
und Kanten glatt. Sieben Groessen, damit Windows nicht selbst herunterrechnet
und aus dem Punkt Matsch wird.

Farben aus static/styles.css: --akzent #0d6e6b,
--amber (dunkles Thema) #d9ab53.

Nachziehen mit:  python3 werkzeug/symbol_bauen.py
"""
from PIL import Image, ImageDraw, ImageFont

AKZENT = (13, 110, 107)
AMBER = (217, 171, 83)
WEISS = (255, 255, 255)
SCHRIFT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

KANTE = 1024
GROESSEN = [256, 128, 64, 48, 32, 24, 16]


def symbol() -> Image.Image:
    bild = Image.new("RGBA", (KANTE, KANTE), (0, 0, 0, 0))
    z = ImageDraw.Draw(bild)
    rand = int(KANTE * 0.06)
    z.rounded_rectangle([rand, rand, KANTE - rand, KANTE - rand],
                        radius=int(KANTE * 0.22), fill=AKZENT)

    schrift = ImageFont.truetype(SCHRIFT, int(KANTE * 0.60))
    text = "j"
    kasten = z.textbbox((0, 0), text, font=schrift)
    x = (KANTE - (kasten[2] - kasten[0])) // 2 - kasten[0]
    # Etwas tiefer als die Mitte: Der Punkt braucht Luft nach oben, sonst
    # stoesst er bei 16 Pixeln an den Rand und wirkt abgeschnitten.
    y = (KANTE - (kasten[3] - kasten[1])) // 2 - kasten[1] + int(KANTE * 0.04)
    z.text((x, y), text, font=schrift, fill=WEISS)

    # Den Punkt des j ueberdecken und in Bernstein neu setzen. Seine Lage
    # ergibt sich aus dem Zeichenkasten, nicht aus geratenen Zahlen.
    punkt_r = int(KANTE * 0.062)
    punkt_x = x + kasten[0] + (kasten[2] - kasten[0]) // 2
    punkt_y = y + kasten[1] + int((kasten[3] - kasten[1]) * 0.085)
    z.ellipse([punkt_x - punkt_r * 1.4, punkt_y - punkt_r * 1.4,
               punkt_x + punkt_r * 1.4, punkt_y + punkt_r * 1.4], fill=AKZENT)
    z.ellipse([punkt_x - punkt_r, punkt_y - punkt_r,
               punkt_x + punkt_r, punkt_y + punkt_r], fill=AMBER)
    return bild


if __name__ == "__main__":
    gross = symbol()
    gross.resize((256, 256), Image.LANCZOS).save(
        "jp/jusperfect/static/jusperfect.ico", format="ICO",
        sizes=[(s, s) for s in GROESSEN])

    # Zum Ansehen: auf hellem UND dunklem Grund, denn beides kommt vor.
    zeile = [16, 24, 32, 48, 64]
    breite = 40 + sum(s * 4 + 40 for s in zeile)
    hoehe = 64 * 4 + 130
    probe = Image.new("RGB", (breite, 2 * hoehe), (238, 241, 243))
    z = ImageDraw.Draw(probe)
    klein = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 17)
    for reihe, (grund, name) in enumerate((((238, 241, 243), "auf hellem Grund"),
                                           ((26, 32, 33), "auf dunkler Taskleiste"))):
        oben = reihe * hoehe
        z.rectangle([0, oben, breite, oben + hoehe - 2], fill=grund)
        z.text((20, oben + 14), name, font=klein,
               fill=(90, 100, 102) if reihe == 0 else (170, 180, 182))
        x = 20
        for s in zeile:
            k = gross.resize((s, s), Image.LANCZOS)
            probe.paste(k, (x, oben + 48), k)
            lupe = k.resize((s * 4, s * 4), Image.NEAREST)
            probe.paste(lupe, (x, oben + 48 + 20 + s), lupe)
            x += s * 4 + 40
    probe.save("symbol-probe.png")
    print("geschrieben:", GROESSEN)
