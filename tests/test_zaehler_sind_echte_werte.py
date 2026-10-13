"""Der Abbruch vom 13.10.2026, gefunden: ein `field()` in keiner Dataclass.

Die Zeile aus dem schwarzen Fenster der Kanzlei:

    {"ereignis": "fehler_abgefangen", "verfahren": "POST",
     "nummer": "f732c458", "kette": "builtins.TypeError (web.py:956)"}

Dort steht::

    "mail_ausgelassen": dict(getattr(d.adapter, "letzte_mail_ausgelassen", {})),

`HttpJurNodesAdapter` ist **keine** Dataclass. Ein
``= field(default_factory=dict)`` legt dort deshalb keinen leeren
Verzeichniswert an, sondern ein ``dataclasses.Field``-**Objekt** als
Klassenattribut – und ``dict(Field)`` wirft
``TypeError: 'Field' object is not iterable``.

**Warum es so lange unsichtbar war:** `_mail_dokumente` setzt den Zähler am
Objekt, bevor irgendjemand ihn liest – solange es läuft, liegt über dem Field
ein echtes Verzeichnis. Fällt das Korrespondenzverzeichnis aus, kehrt
`_vermerke` vorher um, `_mail_dokumente` läuft nie, und das Field steht blank
da. Genau das war in der Kanzlei der Fall: vier Aufrufe des Servers wurden
abgewiesen, darunter die Korrespondenzsuche.

Zwei Lehren, und beide stehen hier als Prüfung:

1. **Kein Klassenattribut dieser Klassen darf ein `Field` sein.** Der Fehler
   ist nicht zu sehen – man liest `field(default_factory=dict)` und denkt
   „leeres Verzeichnis". Eine Maschine sieht es sofort.
2. **Die Zähler werden an einer Stelle zurückgesetzt, nicht je Zweig.** Ein
   Zähler, den nur sein eigener Zweig zurücksetzt, ist nicht gesetzt, sobald
   der Zweig ausfällt – und zählt den vorigen Lauf mit, wenn er es doch war.
"""

from __future__ import annotations

import dataclasses
import inspect
import unittest

import httpx

from jusperfect.jurnodes import base, fixture_adapter, http_adapter, webdav_adapter
from jusperfect.web import _sitzung_antwort
from tests.hilfen import client, dienste
from tests.test_eakte import AKTE, _Server, _adapter, _eintrag


class KeinFieldAusserInEinerDataclass(unittest.TestCase):
    MODULE = (http_adapter, fixture_adapter, webdav_adapter, base)

    def test_keine_klasse_traegt_ein_field_als_attribut(self):
        gefunden = []
        for modul in self.MODULE:
            for name, klasse in vars(modul).items():
                if not inspect.isclass(klasse) or klasse.__module__ != modul.__name__:
                    continue
                if dataclasses.is_dataclass(klasse):
                    continue
                for attribut, wert in vars(klasse).items():
                    if isinstance(wert, dataclasses.Field):
                        gefunden.append(f"{modul.__name__}.{name}.{attribut}")
        self.assertEqual(gefunden, [], "field() wirkt nur in einer Dataclass.")

    def test_die_beiden_zaehler_sind_am_objekt_echte_verzeichnisse(self):
        adapter = _adapter(_Server())
        for name in ("letzte_mail_ausgelassen", "letzte_eintraege_mit_fehler"):
            with self.subTest(zaehler=name):
                self.assertEqual(getattr(adapter, name), {})
                self.assertEqual(dict(getattr(adapter, name)), {})


class _ServerOhneKorrespondenz(_Server):
    """Die Korrespondenzsuche wird abgewiesen – wie in der Kanzlei."""

    def __call__(self, anfrage: httpx.Request) -> httpx.Response:
        if anfrage.url.path.endswith("/correspondence/search"):
            self.gefragt.append(f"{anfrage.method} {anfrage.url.path}")
            return httpx.Response(405, json={})
        if anfrage.url.path.endswith("/relation/search") or \
                anfrage.url.path.endswith("/todo/search"):
            return httpx.Response(200, json={"elements": [], "pagesTotal": 1})
        return super().__call__(anfrage)


class DerFallAusDerKanzlei(unittest.TestCase):
    def test_die_zaehler_stehen_auch_dann_wenn_die_e_akte_ausfaellt(self):
        """Das ist der Fall, in dem `_mail_dokumente` nie läuft."""
        adapter = _adapter(_ServerOhneKorrespondenz([_eintrag("mail", referenceMail="x")]))
        adapter.dokumente(AKTE)
        self.assertEqual(dict(adapter.letzte_mail_ausgelassen), {})
        self.assertEqual(adapter.letzte_korrespondenz_ohne_inhalt, -1)

    def test_die_sitzungsantwort_laesst_sich_bauen(self):
        """Genau hier brach es ab – und damit war die Akte nicht zu öffnen.

        **Ohne** vorherigen Listenaufbau: Das ist der Zustand, in dem die
        Zähler nie am Objekt gesetzt wurden. Ein `dokumente()` davor würde
        sie setzen und die Prüfung um ihren Gegenstand bringen.
        """
        d = dienste()
        d.adapter = _adapter(_ServerOhneKorrespondenz())
        c = client(d)
        antwort = c.post("/api/sitzungen", json={"akte_id": "MV-2026-0007"})
        self.assertEqual(antwort.status_code, 201, antwort.text)
        self.assertEqual(antwort.json()["mail_ausgelassen"], {})
        self.assertEqual(antwort.json()["eintraege_mit_fehler"], {})

    def test_ohne_jeden_aufruf_traegt_ein_frischer_adapter_schon_werte(self):
        """Vorher war der Zähler erst nach dem ersten Listenaufbau gesetzt."""
        adapter = _adapter(_Server())
        d = dienste()
        d.adapter = adapter
        # Kein dokumente() davor - genau so, wie es beim Oeffnen zuerst kommt.
        self.assertEqual(dict(adapter.letzte_mail_ausgelassen), {})


class AlleZaehlerAnEinerStelle(unittest.TestCase):
    def test_ein_zweiter_lauf_erbt_nichts_vom_ersten(self):
        """Ein Zähler, den nur sein Zweig zurücksetzt, zählt den vorigen mit."""
        server = _Server([_eintrag("beA")], mails={})
        adapter = _adapter(server)
        adapter.dokumente(AKTE)
        self.assertEqual(adapter.letzte_korrespondenz_ohne_inhalt, 1)

        adapter._client = httpx.Client(
            base_url="https://beispiel.invalid",
            transport=httpx.MockTransport(_ServerOhneKorrespondenz()))
        adapter._puffer_leeren()
        adapter.dokumente(AKTE)
        self.assertEqual(adapter.letzte_korrespondenz_ohne_inhalt, -1,
                         "Die 1 des vorigen Laufs stünde sonst noch da.")

    def test_das_zuruecksetzen_steht_an_einer_stelle(self):
        quelle = inspect.getsource(http_adapter.HttpJurNodesAdapter.dokumente)
        self.assertIn("_zaehler_zuruecksetzen()", quelle)


if __name__ == "__main__":
    unittest.main()
