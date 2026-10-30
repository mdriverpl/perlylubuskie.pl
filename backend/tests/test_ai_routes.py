import json
from pathlib import Path
import httpx
import pytest
from fastapi import HTTPException
from app import ai_routes as ai

CATALOG=[{'id':1,'name':'Łagów','lat':52.3347,'lng':15.2922,'location':'Łagów','category':'heritage'},{'id':5,'name':'Jezioro','lat':52.35,'lng':15.29,'location':'Łagów','category':'nature'}]


@pytest.fixture(autouse=True)
def settings(monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY','test-only-api-key')
    monkeypatch.setenv('OPENAI_MODEL','gpt-6-astra')
    ai._requests.clear();ai._daily.clear()


def intent(**patch):
    return ai.Intent(**{'title':'Spacer','description':'Krótki spacer','transport':'walk','circuit':'none','place_ids':[1,5],'loop':False,'supported':True,'message':'',**patch})


def test_missing_configuration(monkeypatch):
    monkeypatch.delenv('OPENAI_API_KEY')
    with pytest.raises(HTTPException) as caught:ai.propose('Spacer w Łagowie',CATALOG,'qa')
    assert caught.value.status_code==503


def test_structured_request_and_secret_boundary(monkeypatch):
    def post(url,**kwargs):
        assert url=='https://api.openai.com/v1/responses'
        assert kwargs['headers']['Authorization']=='Bearer test-only-api-key'
        payload=kwargs['json']
        assert payload['store'] is False
        assert payload['model']=='gpt-6-astra'
        assert payload['reasoning']=={'effort':'medium'}
        assert payload['max_output_tokens']==4000
        assert 'test-only-api-key' not in json.dumps(payload)
        assert payload['text']['format']['strict'] is True
        assert payload['text']['format']['schema']['properties']['place_ids']['items']['enum']==[1,5]
        return httpx.Response(200,json={'status':'completed','output':[{'content':[{'type':'output_text','text':intent().model_dump_json()}]}]})
    monkeypatch.setattr(ai.httpx,'post',post)
    assert ai.interpret('Spacer w Łagowie',CATALOG).place_ids==[1,5]


@pytest.mark.parametrize('status',[401,429,500])
def test_provider_errors_do_not_expose_secrets(monkeypatch,status):
    monkeypatch.setattr(ai.httpx,'post',lambda *a,**kw:httpx.Response(status,json={'error':{'message':'test-only-api-key'}}))
    with pytest.raises(HTTPException) as caught:ai.interpret('Spacer w Łagowie',CATALOG)
    assert 'test-only-api-key' not in caught.value.detail


def test_refusal_invalid_ids_and_rate_limit(monkeypatch):
    monkeypatch.setattr(ai,'interpret',lambda *a:intent(supported=False,message='Doprecyzuj miejscowość.'))
    with pytest.raises(HTTPException) as caught:ai.propose('Coś innego',CATALOG,'qa')
    assert caught.value.status_code==422
    monkeypatch.setattr(ai,'interpret',lambda *a:intent(place_ids=[1,999]))
    with pytest.raises(HTTPException) as caught:ai.propose('Spacer w Łagowie',CATALOG,'qa')
    assert caught.value.status_code==422
    for _ in range(4):ai.limit_requests('qa')
    with pytest.raises(HTTPException) as caught:ai.limit_requests('qa')
    assert caught.value.status_code==429


def test_catalog_loop_and_lake_circuit(monkeypatch):
    captured=[]
    monkeypatch.setattr(ai,'interpret',lambda *a:intent(loop=True))
    def routing(points,transport):
        captured.append(points)
        return {'geometry':{'type':'LineString','coordinates':[[p['lng'],p['lat']] for p in points]},'distance_m':9285,'duration_s':7200}
    monkeypatch.setattr(ai,'calculate_route',routing)
    proposal=ai.propose('Spacer z powrotem',CATALOG,'qa')
    assert proposal['place_ids']==[1,5,-810099]
    assert captured[-1][0]['lat']==captured[-1][-1]['lat']
    monkeypatch.setattr(ai,'interpret',lambda *a:intent(circuit='lagowskie',place_ids=[]))
    monkeypatch.setattr(ai,'calculate_route',lambda *a:json.loads((Path(__file__).parent/'fixtures/lagowskie-route.json').read_text()))
    proposal=ai.propose('Dookoła jeziora Łagowskiego',CATALOG,'qa')
    assert len(proposal['place_ids'])==9
    assert all(i<0 for i in proposal['place_ids'])
    assert proposal['distance_m']==9285
    assert len(proposal['sources'])>=1
    source=json.loads((Path(ai.__file__).parent/'data/lagowskie-circuit.json').read_text(encoding='utf8'))
    assert source['points'][0]['lat']==source['points'][-1]['lat']


@pytest.mark.parametrize('prompt',['Zaplanuj trasę dookoła jeziora Ciecz','zaplanuj trasę doodkoła jeziora Ciecz','Spacer wokół Jeziora Trześniowskiego','Pętla dookoła jeziora Trzesniowskiego'])
def test_ciecz_alias_cannot_use_distant_catalog_places(monkeypatch,prompt):
    monkeypatch.setattr(ai,'interpret',lambda *a:intent(circuit='none',place_ids=[1,5]))
    actual=json.loads((Path(__file__).parent/'fixtures/ciecz-route.json').read_text())
    captured=[]
    def routing(points,transport):
        captured.extend(points)
        return actual
    monkeypatch.setattr(ai,'calculate_route',routing)
    proposal=ai.propose(prompt,CATALOG,'qa')
    assert proposal['place_ids']==[p['id'] for p in captured]
    assert len(captured)==13 and all(p['id']<0 for p in captured)
    assert all(15.27<p['lng']<15.34 and 52.33<p['lat']<52.4 for p in captured)
    assert proposal['distance_m']==12859
    assert proposal['warnings']
    assert 'Ciecz' in proposal['name']


def test_unknown_lake_and_wrong_circuit_are_rejected(monkeypatch):
    monkeypatch.setattr(ai,'interpret',lambda *a:pytest.fail('Unknown lake must not call OpenAI'))
    with pytest.raises(HTTPException) as caught:ai.propose('Zaplanuj trasę dookoła jeziora Niezidentyfikowanego',CATALOG,'qa')
    assert caught.value.status_code==422
    circuit=json.loads((Path(ai.__file__).parent/'data/ciecz-circuit.json').read_text(encoding='utf8'))
    wrong=json.loads((Path(__file__).parent/'fixtures/lagowskie-route.json').read_text())
    with pytest.raises(HTTPException) as caught:ai.validate_lake_loop(wrong,circuit)
    assert caught.value.status_code==422
    correct=json.loads((Path(__file__).parent/'fixtures/ciecz-route.json').read_text())
    ai.validate_lake_loop(correct,circuit)
    with pytest.raises(HTTPException):ai.validate_lake_loop({**correct,'distance_m':70000},circuit)
    with pytest.raises(HTTPException):ai.validate_lake_loop({**correct,'geometry':{'coordinates':correct['geometry']['coordinates'][:10]}},circuit)
