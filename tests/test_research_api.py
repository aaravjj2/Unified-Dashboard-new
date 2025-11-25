import json
import os

import pytest


def test_research_health_and_demo(client):
    # Health endpoint
    rv = client.get('/api/research/health')
    assert rv.status_code == 200
    data = rv.get_json()
    assert isinstance(data, dict)
    assert data.get('ok') is True

    # Demo brief fixture
    rv2 = client.get('/api/research/demo_brief')
    assert rv2.status_code == 200
    demo = rv2.get_json()
    assert isinstance(demo, dict)
    # minimal expected keys in demo fixture
    assert 'title' in demo or 'id' in demo


def test_create_update_delete_brief(client):
    # Create without title -> should 400
    rv = client.post('/api/research/briefs', json={})
    assert rv.status_code == 400

    # Create valid brief
    payload = {
        'title': 'pytest brief',
        'summary': 'created by pytest',
        'body': 'body text',
        'tags': ['test']
    }
    rv2 = client.post('/api/research/briefs', json=payload)
    assert rv2.status_code == 200
    created = rv2.get_json()
    assert created.get('title') == 'pytest brief'
    brief_id = created.get('id')
    assert brief_id

    # Get the brief
    rv3 = client.get(f'/api/research/briefs/{brief_id}')
    assert rv3.status_code == 200
    got = rv3.get_json()
    assert got.get('id') == brief_id

    # Update brief - also ensure azure block works
    rv4 = client.put(f'/api/research/briefs/{brief_id}', json={'body': 'updated'})
    assert rv4.status_code == 200

    # Block azure usage
    rv5 = client.post('/api/research/briefs', json={'title': 'x', 'body': 'uses Azure in text'})
    assert rv5.status_code == 403

    # Delete brief
    rv6 = client.delete(f'/api/research/briefs/{brief_id}')
    assert rv6.status_code == 200


@pytest.fixture(scope='module')
def client():
    # Import here so env vars can be set by callers if needed
    os.environ.setdefault('RESEARCH_DETERMINISTIC', '1')
    from financial_dashboard.app import server

    with server.test_client() as c:
        yield c
