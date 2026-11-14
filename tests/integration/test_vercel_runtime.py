"""Deployment-sensitive regressions: visitor boundaries, queue retries and cross-instance SSE."""
from contextlib import nullcontext
import asyncio
import importlib

from fastapi.testclient import TestClient
import pytest

from recovery.config import settings
from recovery.runtime.context import visitor_id
from recovery.runtime.jobs import DurableJobs


@pytest.fixture
def public_api(svc, monkeypatch):
    module = importlib.import_module('recovery.api.app')
    old = settings.public_demo
    object.__setattr__(settings, 'public_demo', True)
    monkeypatch.setattr(module, 'SERVICES', svc)
    yield module
    object.__setattr__(settings, 'public_demo', old)


def test_anonymous_visitors_have_separate_runs_uploads_and_replay_authority(public_api, svc):
    with TestClient(public_api.app) as a, TestClient(public_api.app) as b:
        ra = a.get('/api/v1/engines/engine-demo-001').json()['scenario_run_id']
        rb = b.get('/api/v1/engines/engine-demo-001').json()['scenario_run_id']
        assert ra != rb
        assert a.cookies.get('resource_visitor') != b.cookies.get('resource_visitor')
        assert b.get(f'/api/v1/scenario-runs/{ra}').status_code == 404
        assert b.get(f'/api/v1/cases/case-primary?run_id={ra}').status_code == 404
        assert a.get('/api/v1/scenario-runs/current').json()['previous_run_ids'] == []
        assert b.post('/api/v1/scenario-runs', json={'mode':'replay','replay_source_run_id':ra}).status_code == 404
        upload = a.post('/api/v1/intake/uploads', data={'kind':'blueprint'}, files={'file':('test.txt',b'PART 7: fixture','text/plain')})
        assert upload.status_code == 201
        uid = upload.json()['upload_id']
        assert a.get(f'/api/v1/intake/uploads/{uid}/content').status_code == 200
        assert b.get(f'/api/v1/intake/uploads/{uid}/content').status_code == 404
        assert a.post('/api/v1/scenario-runs', json={'mode':'seeded'}, headers={'Origin':'https://untrusted.example'}).status_code == 403


def test_activated_manifest_and_reset_are_private_to_each_run(public_api):
    from test_intake import GOOD, make_glb
    with TestClient(public_api.app) as a, TestClient(public_api.app) as b:
        a.get('/api/v1/engines/engine-demo-001')
        b.get('/api/v1/engines/engine-demo-001')
        upload = a.post('/api/v1/intake/uploads', data={'kind':'mesh_glb'},
                        files={'file':('synthetic.glb',make_glb(GOOD),'model/gltf-binary')}).json()
        job = a.post('/api/v1/intake/mesh-jobs', json={'upload_id':upload['upload_id'], 'engine_id':'engine-demo-001'}).json()
        activated = a.post(f"/api/v1/intake/mesh-jobs/{job['job_id']}/activate").json()
        assert activated['kind'] == 'generated'
        assert a.get('/api/v1/engines/engine-demo-001').json()['engine']['asset']['kind'] == 'generated'
        assert b.get('/api/v1/intake/manifest').json()['kind'] == 'procedural'
        assert b.get('/api/v1/engines/engine-demo-001').json()['engine']['asset']['kind'] == 'procedural'
        assert b.post('/api/v1/intake/manifest/reset').json()['kind'] == 'procedural'
        assert a.get('/api/v1/intake/manifest').json()['manifest_version'] == activated['manifest_version']
        a.post('/api/v1/scenario-runs', json={'mode':'seeded'})
        assert a.get('/api/v1/intake/manifest').json()['kind'] == 'procedural'


def test_queue_duplicate_is_noop_and_retry_preserves_job_and_owner(svc, monkeypatch):
    module = importlib.import_module('recovery.runtime.jobs')
    deliveries = []
    monkeypatch.setattr(module, 'send', lambda topic, msg, **kwargs: deliveries.append(msg.job_id))
    jobs = DurableJobs(svc)
    monkeypatch.setattr(jobs, 'lock', lambda key: nullcontext())
    owner = visitor_id.set('owner-a')
    try:
        jobs.enqueue('extract', 'run-a', {'draft_id':'draft-a'}, key='job-a')
    finally:
        visitor_id.reset(owner)
    calls = []
    def fail_once(job):
        calls.append(visitor_id.get())
        if len(calls) == 1:
            raise RuntimeError('temporary failure')
    monkeypatch.setattr(jobs, '_perform', fail_once)
    with pytest.raises(RuntimeError):
        jobs.execute('job-a')
    assert svc.store.kv_get('job:job-a')['status'] == 'pending'
    jobs.execute('job-a')
    jobs.execute('job-a')
    assert calls == ['owner-a','owner-a']
    assert svc.store.kv_get('job:job-a')['status'] == 'done'
    assert visitor_id.get() is None


@pytest.mark.asyncio
async def test_sse_reads_committed_events_from_a_second_bus(svc, monkeypatch):
    module = importlib.import_module('recovery.api.app')
    from recovery.runtime.events import EventBus
    monkeypatch.setattr(module, 'SERVICES', svc)
    run = svc.scenario.create_run()['scenario_run_id']
    cursor = svc.store.max_sequence(run, 'case-primary')
    class Request:
        async def is_disconnected(self): return False
    stream = module._sse(run, 'case-primary', cursor, Request())
    assert 'retry:' in await anext(stream)
    # Publishing through another bus cannot notify this process-local subscriber.
    other = EventBus(svc.store)
    other.publish(run, 'case-primary', 'run.progress', 'Another worker committed this')
    item = await asyncio.wait_for(anext(stream), timeout=3)
    assert 'Another worker committed this' in item
    await stream.aclose()


def test_serverless_rejects_local_sqlite_fallback(tmp_path, monkeypatch):
    from recovery.services.container import Services
    before = settings.serverless
    object.__setattr__(settings, 'serverless', True)
    try:
        with pytest.raises(RuntimeError, match='durable Postgres'):
            Services(db_url=f'sqlite:///{tmp_path}/ephemeral.sqlite', start_worker=False)
    finally:
        object.__setattr__(settings, 'serverless', before)


def test_generation_and_undispatched_job_commit_together_and_retry_publication(svc, monkeypatch):
    from recovery.runtime import jobs as module
    before = settings.job_backend
    run = svc.scenario.create_run()['scenario_run_id']
    object.__setattr__(settings, 'job_backend', 'vercel')
    calls = []
    def flaky_send(topic, msg, **kwargs):
        calls.append(msg.job_id)
        if len(calls) == 1:
            raise RuntimeError('queue temporarily unavailable')
    monkeypatch.setattr(module, 'send', flaky_send)
    try:
        with pytest.raises(RuntimeError, match='queue temporarily'):
            svc.coordinator.start_investigation(run, 'case-primary', 'seeded', 1)
        gen = svc.store.get_case(run, 'case-primary')['active_generation_id']
        assert svc.store.kv_get(f'job:{gen}')['payload']['gen_id'] == gen
        assert not svc.store.kv_get(f'dispatched:{gen}')
        svc.jobs.recover_dispatches()
        svc.jobs.recover_dispatches()
        assert calls == [gen, gen]
        assert svc.store.kv_get(f'dispatched:{gen}') is True
    finally:
        object.__setattr__(settings, 'job_backend', before)


def test_serverless_http_startup_does_not_wait_for_remote_tracing(public_api, monkeypatch):
    before = settings.serverless
    object.__setattr__(settings, 'serverless', True)
    def forbidden():
        raise AssertionError('Remote tracing must not gate HTTP startup')
    monkeypatch.setattr(public_api, 'init_tracing', forbidden)
    try:
        with TestClient(public_api.app) as client:
            assert client.get('/api/v1/health').json()['status'] == 'ok'
    finally:
        object.__setattr__(settings, 'serverless', before)
