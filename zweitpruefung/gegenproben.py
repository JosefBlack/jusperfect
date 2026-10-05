"""Offline-Gegenproben: grün bedeutet, dass die dokumentierte Lücke reproduziert wurde.
Keine Regressionstests für den Sollzustand; ausschließlich erfundene Daten.
"""
import json
import traceback
from unittest.mock import Mock

import httpx
import pytest
from fastapi.testclient import TestClient

from jusperfect.domain.models import (Akte, Aktengedaechtnis, Aktenanalyse,
    ChronologieEintrag, GedaechtnisDokument, Seite, Passage)
from jusperfect.jurnodes.http_adapter import HttpJurNodesAdapter, dokument_aus_json
from jusperfect.providers.base import ProviderAntwort, Nutzung, ProviderFehler
from jusperfect.providers.bedrock import BedrockProvider
from jusperfect.security.approval import Freigabestelle, text_pruefsumme
from jusperfect.services.belegpflicht import aussage_fail_closed
from jusperfect.services.fristen import entschaerfen
from jusperfect.services.passagen import passagen_bilden
from jusperfect.services.prompts import material_bauen
from jusperfect.web import app_erstellen
from tests.hilfen import client, dienste, einstellungen
from tests.test_web_ablauf import SkriptProvider

AKTE = 'VU-2026-0042'
MARKER = 'PRUEFMARKER_ERFUNDENER_GEHEIMINHALT'

def vorbereitet(provider=None, **kwargs):
    d = dienste(provider=provider, **kwargs) if provider else dienste(**kwargs)
    c = client(d)
    r = c.post('/api/sitzungen', json={'akte_id': AKTE})
    assert r.status_code == 201, r.text
    sid = r.json()['sitzung']['id']
    assert c.post(f'/api/sitzungen/{sid}/dokumente', json={'dokument_ids':['D-001']}).status_code == 200
    return d, c, sid

def test_01_entwurf_ohne_beleg_bleibt():
    p = SkriptProvider([json.dumps({'betreff':'Test', 'text':MARKER})])
    d,c,sid = vorbereitet(p)
    r = c.post(f'/api/sitzungen/{sid}/entwuerfe', json={'art':'mandant'})
    assert r.status_code == 201, r.text
    assert r.json()['text'] == MARKER and r.json()['quellen'] == []

def test_02_triage_und_analyse_hinweise_ungeprueft():
    p = SkriptProvider([json.dumps({'kernaussage':MARKER, 'empfohlene_schritte':[MARKER]}),
                        json.dumps({'hinweise':[MARKER]})])
    d,c,sid = vorbereitet(p)
    r = c.post(f'/api/sitzungen/{sid}/triage', json={'dokument_id':'D-001'})
    assert r.status_code == 200, r.text
    assert r.json()['kernaussage'] == MARKER and not r.json()['quellen']
    r = c.post(f'/api/sitzungen/{sid}/analyse')
    assert r.status_code == 200, r.text
    assert MARKER in r.json()['hinweise']

def test_03_stream_liefert_unbelegten_rohtext():
    class P:
        modell_id = 'skript'
        def fragen_stream(self, *args, **kwargs):
            yield MARKER
            yield ProviderAntwort(text=MARKER, nutzung=Nutzung(), modell='skript')
    d,c,sid = vorbereitet(P())
    r = c.post(f'/api/sitzungen/{sid}/frage/stream', json={'frage':'Was steht hier?'})
    events = [json.loads(line) for line in r.text.splitlines()]
    assert events[0] == {'type':'text', 'text':MARKER}
    assert MARKER not in events[-1]['antwort']['text']

def test_04_vergessen_laesst_analyse_und_gemischten_sachverhalt(tmp_path):
    d,c,sid = vorbereitet(einstellungen=einstellungen(JUSPERFECT_GEDAECHTNIS='lokal',
        JUSPERFECT_GEDAECHTNIS_PFAD=str(tmp_path)))
    g = d.gedaechtnis.lesen(AKTE)
    g.dokumente.append(GedaechtnisDokument(dokument_id='D-ZWEI',titel='Zweite Quelle',nummer=2,
        seiten=[Seite(nummer=1,text='Ein anderer, unabhängiger Inhalt.')]))
    g.letzte_dokumentnummer = 2
    q = aussage_fail_closed('Unfall [Q: D1-S1-P1]',
        {p.kennung:p for p in d.gedaechtnis._passagen(g)}).quellen[0]
    g.analyse = Aktenanalyse(chronologie=[ChronologieEintrag(datum='2026-01-01',ereignis=MARKER,quellen=[q])])
    g.analyse_dokumente = ['D-001']
    g.lebenssachverhalt = MARKER + ' [Q: D1-S1-P1, D2-S1-P1]'
    d.gedaechtnis.ablegen(g)
    r = c.delete(f'/api/akten/{AKTE}/gedaechtnis/dokumente/D-001')
    assert r.status_code == 200, r.text
    assert MARKER in r.json()['analyse']['chronologie'][0]['ereignis']
    assert MARKER in r.json()['lebenssachverhalt']
    assert 'D1-S1-P1' not in r.json()['lebenssachverhalt']
    # Bereits geöffnete Sitzung behält den Originalauszug.
    assert d.sitzungen.passagen(d.speicher.sitzung_lesen(sid))
    d.analyse._ausgang._provider = SkriptProvider([MARKER+' [Q: D1-S1-P1]'])
    assert c.post(f'/api/sitzungen/{sid}/frage',json={'frage':'Unfall?'}).status_code == 200
    assert MARKER in d.gedaechtnis.lesen(AKTE).fragen_antworten[-1].antwort

def test_05_betreffwechsel_entgeht_freigabe():
    p = SkriptProvider([json.dumps({'betreff':'Gesehener Betreff','text':'Text [Q: D1-S1-P1]'})])
    d,c,sid = vorbereitet(p)
    draft = c.post(f'/api/sitzungen/{sid}/entwuerfe',json={'art':'mandant'}).json()
    assert c.put(f"/api/entwuerfe/{draft['id']}",json={'betreff':MARKER,'text':draft['text']}).status_code == 200
    r = c.post(f"/api/entwuerfe/{draft['id']}/freigabe",json={'bestaetigung':True,'text_pruefsumme':draft['text_pruefsumme']})
    assert r.status_code == 200, r.text
    assert MARKER in str(d.adapter.geschriebene_vermerke)

def test_06_rechteentzug_sperrt_entwurf_nicht():
    p = SkriptProvider([json.dumps({'betreff':'Test','text':'Text [Q: D1-S1-P1]'})])
    d,c,sid = vorbereitet(p)
    draft = c.post(f'/api/sitzungen/{sid}/entwuerfe',json={'art':'mandant'}).json()
    d.berechtigungen._nutzer['ra-weber'].akten = []
    assert c.get(f'/api/sitzungen/{sid}').status_code == 403
    assert c.get(f"/api/entwuerfe/{draft['id']}").status_code == 200
    r = c.post(f"/api/entwuerfe/{draft['id']}/freigabe",json={'bestaetigung':True,'text_pruefsumme':draft['text_pruefsumme']})
    assert r.status_code == 200, r.text
    assert d.adapter.geschriebene_vermerke

def test_07_fremde_record_antwort_wird_angenommen():
    def response(req):
        if req.url.path == '/record':
            return httpx.Response(200,json={'identifier':'FREMDE-AKTE','recordSign':'FREMD','shortRubrum':'Fremd','fileFolderId':42})
        if req.url.path == '/file-system/folder/content':
            return httpx.Response(200,json={'elements':[{'type':'file','file':{'identifier':'FREMDDOK','fileName':'fremd','fileExtension':'txt'}}]})
        if req.url.path == '/file-system/file/download':
            return httpx.Response(200,content=MARKER.encode())
        raise AssertionError(str(req.url))
    a = HttpJurNodesAdapter('https://jurnodes.invalid','test',Freigabestelle(),transport=httpx.MockTransport(response))
    assert a.akte('EIGENE-AKTE').id == 'FREMDE-AKTE'
    doc,data = a.dokument_laden('EIGENE-AKTE','FREMDDOK')
    assert doc.akte_id == 'EIGENE-AKTE' and data.decode() == MARKER
    a.schliessen()

def test_08_providerfehler_hinterlaesst_keinen_nachweis():
    class P:
        modell_id='skript'
        def fragen(self,*args,**kwargs):
            self.material = args[1]
            raise ProviderFehler('Simulierter Ausfall nach Übertragung')
    p=P()
    d,c,sid=vorbereitet(p)
    assert c.post(f'/api/sitzungen/{sid}/frage',json={'frage':'Unfall?'}).status_code == 502
    assert p.material
    assert d.kosten.nachweis('ra-weber') == []

def test_09_metadaten_gehen_als_material_hinaus():
    doc=dokument_aus_json('A',{'identifier':'INTERN','fileName':MARKER+'.pdf'})
    ps=passagen_bilden(1,doc,[Seite(nummer=1,text='Neutraler Text')])
    material=material_bauen(Akte(id='A',aktenzeichen='AZ-PRUEFMARKER',bezeichnung='Test'),[],[],ps)
    assert MARKER+'.pdf' in material
    assert 'AZ-PRUEFMARKER' in material

@pytest.mark.parametrize('satz',[
    'Die Klagefrist endet am 26.05.26 [Q: D1-S1-P1].',
    'Die Klagefrist endet am 26. Mai [Q: D1-S1-P1].',
    'Die Klage muss bis zum 26.05.2026 eingereicht werden [Q: D1-S1-P1].',
])
def test_10_fristensperre_laesst_berechnete_termine_durch(satz):
    p=Passage(kennung='D1-S1-P1',dokument_id='D1',dokument_titel='Test',seite=1,text='Zugang am 05.05.2026.')
    text,zahl=entschaerfen(satz,{p.kennung:p})
    assert text == satz and zahl == 0

def test_11_globales_profil_in_frankfurt_akzeptiert():
    e=einstellungen(JUSPERFECT_ANBIETER='bedrock',JUSPERFECT_JURNODES_ADAPTER='http',
        JUSPERFECT_JURNODES_URL='https://jurnodes.invalid',JUSPERFECT_GUARDRAIL_ID='realguard123',
        JUSPERFECT_MODELL_ID='global.anthropic.claude-opus-4-6-v1')
    assert e.aws_region == 'eu-central-1'
    assert e.modell_fuer('frage').startswith('global.')

def test_12_exception_chain_verlaesst_app_mit_inhalt():
    from botocore.exceptions import ClientError
    mock=Mock()
    mock.converse.side_effect=ClientError({'Error':{'Code':'ValidationException','Message':MARKER}},'Converse')
    p=BedrockProvider('test',client=mock,prompt_cache=False)
    d,c,sid=vorbereitet(p)
    # Normale HTTP-Antwort ist bereinigt.
    r=c.post(f'/api/sitzungen/{sid}/frage',json={'frage':'Unfall?'})
    assert r.status_code == 502 and MARKER not in r.text
    # Exception-Handler für Exception ist Starlette-ServerErrorMiddleware:
    # Nach der Antwort wird die Ausnahme samt Ursache erneut geworfen.
    raw=TestClient(app_erstellen(d.einstellungen,d),headers={'X-Jusperfect-Nutzer':'ra-weber'},raise_server_exceptions=True)
    with pytest.raises(ProviderFehler) as ex:
        raw.post(f'/api/sitzungen/{sid}/frage',json={'frage':'Unfall?'})
    assert MARKER in ''.join(traceback.format_exception(ex.value))

def test_13_uvicorn_errorlog_enthaelt_aws_rohfehler(caplog):
    import asyncio
    import logging
    from types import SimpleNamespace
    from botocore.exceptions import ClientError
    from uvicorn.protocols.http.h11_impl import RequestResponseCycle
    mock=Mock()
    mock.converse.side_effect=ClientError({'Error':{'Code':'ValidationException','Message':MARKER}},'Converse')
    d,c,sid=vorbereitet(BedrockProvider('test',client=mock,prompt_cache=False))
    body=json.dumps({'frage':'Unfall?'}).encode()
    scope={'type':'http','asgi':{'version':'3.0'},'http_version':'1.1',
        'method':'POST','scheme':'http','path':f'/api/sitzungen/{sid}/frage',
        'raw_path':f'/api/sitzungen/{sid}/frage'.encode(),'query_string':b'',
        'root_path':'','headers':[(b'x-jusperfect-nutzer',b'ra-weber'),(b'content-type',b'application/json')],
        'server':('127.0.0.1',8765),'client':('127.0.0.1',12345)}
    sent=[]
    async def receive():
        return {'type':'http.request','body':body,'more_body':False}
    async def send(message):
        sent.append(message)
    # Originale Uvicorn-Ausnahmebehandlung, nur Transport durch Speicher ersetzt.
    cycle=SimpleNamespace(scope=scope,receive=receive,send=send,
        logger=logging.getLogger('uvicorn.error'),response_started=True,
        transport=Mock(),on_response=lambda:None)
    with caplog.at_level(logging.ERROR,logger='uvicorn.error'):
        asyncio.run(RequestResponseCycle.run_asgi(cycle,app_erstellen(d.einstellungen,d)))
    assert sent[0]['status'] == 502
    assert MARKER not in str(sent)
    assert MARKER in caplog.text

def test_14_kennungspruefung_akzeptiert_unbelegten_absatz_vor_beleg():
    p=Passage(kennung='D1-S1-P1',dokument_id='D1',dokument_titel='Test',seite=1,text='Der Vertrag ist unterschrieben.')
    text=MARKER+'\n\nDer Vertrag ist unterschrieben [Q: D1-S1-P1].'
    result=aussage_fail_closed(text,{p.kennung:p})
    assert MARKER in result.text and result.verworfen == 0

def test_15_s3_etag_schuetzt_nicht_zwei_vorgaenge_derselben_instanz():
    import boto3
    from moto import mock_aws
    from jusperfect.gedaechtnis.aws import AwsGedaechtnisSpeicher
    with mock_aws():
        s3=boto3.client('s3',region_name='eu-central-1',aws_access_key_id='testing',aws_secret_access_key='testing')
        s3.create_bucket(Bucket='pruefung-test',CreateBucketConfiguration={'LocationConstraint':'eu-central-1'})
        store=AwsGedaechtnisSpeicher('pruefung-test','eu-central-1','test-kms',s3=s3)
        original=Aktengedaechtnis(akte_id='A',dokumente=[GedaechtnisDokument(dokument_id='D1',titel='Test',nummer=1,
            seiten=[Seite(nummer=1,text=MARKER)])])
        store.ablegen(original)
        alter_lauf=store.lesen('A')
        loesch_lauf=store.lesen('A')
        loesch_lauf.dokumente=[]
        store.ablegen(loesch_lauf)
        assert not store.lesen('A').dokumente
        # Das globale _etags-Dict trägt jetzt die neue ETag, auch für alter_lauf.
        alter_lauf.bezeichnung='Später fertige Analyse'
        store.ablegen(alter_lauf)
        assert MARKER in store.lesen('A').dokumente[0].seiten[0].text
