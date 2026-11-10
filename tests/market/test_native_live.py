"""Versioned live execution, all tests use the same private fake engine."""
import importlib
import pytest

pytestmark = pytest.mark.usefixtures("native_software_paths")
from test_native_worker import FakeEngine, TickClock
from test_native_protocol import header_fixture, envelope, INCARNATION, SESSION, DIGEST


def test_live_worker_more_than_forty_same_engine_and_v1_rejects():
    from market.native_protocol import NativeProfile, scope
    from market.native_worker import _Worker
    profile = NativeProfile('live-pilot/v1', 480, 48)
    header, clock, sent = header_fixture(), TickClock(), []
    engine = FakeEngine(header)
    commands = []
    with scope(profile):
        from market.native_protocol import schema
        for index in range(48):
            command = envelope('release' if index == 0 else 'ack', last_observation_index=index-1 if index else None,
                next_observation_index=index, action='black', permit=None, dispatch_id=None, exposure_ordinal=None)
            command['schema'] = schema('ipc')
            commands.append((command, b''))
        command = envelope('ack', last_observation_index=47, next_observation_index=None, action='end',
            permit=None, dispatch_id=None, exposure_ordinal=None)
        command['schema'] = schema('ipc')
        commands.append((command,b''))
    incoming = iter(commands)
    worker = _Worker(engine, header, clock, lambda kind, fields, binary=b'', **kw: sent.append((kind, fields)),
        lambda **kw: next(incoming), wall_deadline_ns=1000000000000, profile=profile)
    worker.run()
    assert len(engine.frames) == 48 and engine.brain.sim_ms == 24000
    assert sent[-1][1]['reason'] == 'model_limit'
    assert worker.ring.stats['valid_length'] == 1000
    from market.native_protocol import validate_message
    with pytest.raises(ValueError):
        validate_message(commands[-1][0], 'parent')


def test_live_profile_bounds_and_declaration_only(tmp_path):
    from market.native_session import NativeConfig, NativeSession
    from market.native_protocol import NativeProfile
    for minutes, count in [(0,1),(721,1),(1,0),(1,86401),(True,1)]:
        with pytest.raises(ValueError):
            NativeProfile('live-pilot/v1', minutes, count)
    value = NativeSession(NativeConfig(INCARNATION, SESSION, DIGEST, tmp_path / 'native',
        profile='live-pilot/v1', duration_minutes=480, max_observations=86400), importlib.import_module('market.price_service').SystemClock())
    assert value.snapshot().schema == 'market-native-session/v2'
    assert value.snapshot().free_observations == 86400
    value.enable_readout()
    assert value.readout_identity() is None and value.poll_readouts() == ()
    assert not (tmp_path / 'native').exists()

def test_live_worker_wall_expiry_discards_inflight_observation():
    from market.native_protocol import NativeProfile, scope, schema
    from market.native_worker import _Worker
    header, clock, sent = header_fixture(), TickClock(), []
    class Slow(FakeEngine):
        def observe(self, *args, **kwargs):
            result = super().observe(*args, **kwargs)
            clock.ns = 1000
            return result
    engine = Slow(header)
    with scope(NativeProfile('live-pilot/v1', 1, 48)):
        command = envelope('release', last_observation_index=None,next_observation_index=0,
            action='black',permit=None,dispatch_id=None,exposure_ordinal=None)
        command['schema'] = schema('ipc')
    worker = _Worker(engine, header, clock, lambda kind, fields, binary=b'', **kw: sent.append((kind,fields)),
        lambda **kw:(command,b''), wall_deadline_ns=1000, profile=NativeProfile('live-pilot/v1',1,48))
    worker.run()
    assert worker.completed == 0 and len(engine.frames) == 1
    assert [kind for kind,_ in sent] == ['ended']
    assert sent[0][1]['reason'] == 'wall_limit'


def test_live_readouts_validated_detached_bounded_and_disabled(tmp_path):
    from market.native_session import NativeConfig, NativeSession
    from market import native_protocol as p
    from test_native_protocol import observation_fixture
    from market.price_service import SystemClock
    value = NativeSession(NativeConfig(INCARNATION,SESSION,DIGEST,tmp_path/'native',profile='live-pilot/v1'),SystemClock())
    value._header = p.validate_header(header_fixture())
    identity = value.readout_identity()
    expected = dict(protocol_sha256=DIGEST,engine_identity_sha256=value._header.engine_identity.sha256,
        header_sha256=p.canonical_sha256(value._header))
    assert identity.source_sha256 == p.canonical_sha256(expected)
    observation, binary = observation_fixture(header_fixture())
    value._publish_readout(p.FrozenRecord(observation))
    assert value.poll_readouts() == ()
    value.enable_readout()
    for _ in range(8):
        value._publish_readout(p.FrozenRecord(observation))
    with pytest.raises(ValueError,match='resource'):
        value._publish_readout(p.FrozenRecord(observation))
    records=value.poll_readouts()
    assert len(records)==8 and value.poll_readouts()==()
    assert records[0].wall_start_ns==observation['wall_start_ns']
    assert records[0].group_bin_counts==tuple(tuple(row) for row in observation['group_bin_counts'])
    with pytest.raises(TypeError):
        records[0].group_bin_counts[0][0]=0


def test_profile_scope_isolated_between_owners_and_threads(tmp_path):
    import threading
    from market.native_session import NativeConfig, NativeSession
    from market.native_protocol import NativeProfile, scope, limits, schema
    from market.price_service import SystemClock
    live=NativeSession(NativeConfig(INCARNATION,SESSION,DIGEST,tmp_path/'live',profile='live-pilot/v1',max_observations=48),SystemClock())
    proof=NativeSession(NativeConfig(INCARNATION,SESSION,DIGEST,tmp_path/'proof'),SystemClock())
    snapshots=[]
    threads=[threading.Thread(target=lambda owner=owner:snapshots.append(owner.snapshot())) for owner in (live,proof)]
    with scope(NativeProfile('live-pilot/v1',1,75)):
        for thread in threads: thread.start()
        for thread in threads: thread.join()
        assert limits()['model_observations']==75
        assert proof.snapshot().free_observations==40 and live.snapshot().free_observations==48
    assert limits()['model_observations']==40 and schema('ipc')=='market-native-ipc/v1'
    assert sorted(s.free_observations for s in snapshots)==[40,48]

@pytest.mark.parametrize('image_at',[None,40])
def test_live_session_forty_eight_streams_seal_and_inspects(tmp_path, monkeypatch,image_at):
    import time
    from market import native_protocol as p
    from test_native_session import software_session, drive_software
    profile=p.NativeProfile('live-pilot/v1',480,48)
    with p.scope(profile):
        value=software_session(tmp_path,profile=profile)
        # No full-journal collection may be called by finalization or inspection.
        monkeypatch.setattr(p,'read_events',lambda *a,**kw:pytest.fail('whole event history'))
        monkeypatch.setattr(p,'read_monitors',lambda *a,**kw:pytest.fail('whole monitor history'))
        receipt=drive_software(value,image_at)
        assert value.snapshot().fault is None
        assert len(value._transport.engine.frames)==48
        if image_at is not None:
            assert receipt['status']=='processed'
            assert value._transport.engine.frames[40:48]==[bytes([9])*12288]*8
        value.finish_receipts()
        monkeypatch.setattr(value,'_final_source_check',lambda:p.FrozenRecord(dict(
            scope='prepared-source-lock-tool-cache/v1', started_ns=value._stop_ns,
            finished_ns=value._stop_ns,file_count=p.source_subset(value._protocol,value._bindings,
                value._prepared.protocol_sha256,value._prepared.bindings_sha256).file_count,
            bindings_subset_sha256=p.source_subset(value._protocol,value._bindings,
                value._prepared.protocol_sha256,value._prepared.bindings_sha256).bindings_subset_sha256, all_match=True)))
        value.finish_close()
    final=p.inspect_evidence(value.config.work_root)
    assert final.schema=='market-native-final/v2' and final.observations==48
    assert final.status=='complete' and final.terminal_reason=='model_limit'
    with pytest.raises(ValueError):
        p.validate_final(final)

def test_live_hello_binds_absolute_wall_deadline_and_rejects_unbound():
    from market import native_protocol as p
    from market.price_service import SystemClock
    profile=p.NativeProfile('live-pilot/v1',1,48)
    with p.scope(profile):
        message=envelope('hello',bindings_sha256=DIGEST,parent_clock=SystemClock().describe())
        message['schema']=p.schema('ipc')
        with pytest.raises(ValueError):
            p.validate_message(message,'parent')
        message['wall_deadline_ns']=60000001000
        assert p.validate_message(message,'parent').wall_deadline_ns==60000001000

def test_live_session_normal_wall_end_seals_partial_without_counting_inflight(tmp_path,monkeypatch):
    import time
    from market import native_protocol as p
    from test_native_session import software_session,drive_software
    from test_native_worker import FakeEngine
    real_observe=FakeEngine.observe
    def delayed(self,*args,**kwargs):
        result=real_observe(self,*args,**kwargs)
        time.sleep(.15)
        return result
    monkeypatch.setattr(FakeEngine,'observe',delayed)
    with p.scope(p.NativeProfile('live-pilot/v1',1,48)) as unused:
        value=software_session(tmp_path,profile=p.current_profile(),wall_ns=650000000)
        drive_software(value)
        assert value.snapshot().fault is None
        assert value.snapshot().state=='ended'
        assert value._terminal_reason=='wall_limit'
        completed=value.snapshot().completed_observations
        assert 0<completed<48 and len(value._transport.engine.frames)==completed+1
        value.finish_receipts()
        subset=p.source_subset(value._protocol,value._bindings,value._prepared.protocol_sha256,value._prepared.bindings_sha256)
        monkeypatch.setattr(value,'_final_source_check',lambda:p.FrozenRecord(dict(scope='prepared-source-lock-tool-cache/v1',
            started_ns=value._stop_ns,finished_ns=value._stop_ns,file_count=subset.file_count,
            bindings_subset_sha256=subset.bindings_subset_sha256,all_match=True)))
        value.finish_close()
    final=p.inspect_evidence(value.config.work_root)
    assert final.status=='partial' and final.terminal_reason=='wall_limit' and final.observations==completed

def test_live_protocol_event_monitor_caps_are_versioned_and_strict():
    from market import native_protocol as p
    from test_native_evidence import monitor_fixture
    with p.scope(p.NativeProfile('live-pilot/v1',720,86400)):
        row=p.make_event(4096,p.ZERO_SHA256,1,'binding',dict(protocol_sha256=DIGEST,bindings_sha256=DIGEST))
        assert row.schema=='market-native-event/v2'
        monitor=monitor_fixture()
        monitor.update(schema=p.schema('monitor'),sequence=12000)
        monitor.pop('sha256')
        measured=p.make_monitor(monitor)
        assert measured.schema=='market-native-monitor/v2'
        assert p.limits()['monitor_records']>=432000
        assert p.limits()['combined_output_bytes']==8*1024**3
        with pytest.raises(ValueError):
            p.make_event(p.limits()['event_records'],p.ZERO_SHA256,1,'binding',dict(protocol_sha256=DIGEST,bindings_sha256=DIGEST))
    with pytest.raises(ValueError): p.validate_event(row)
    with pytest.raises(ValueError): p.validate_monitor(measured)


def test_live_cli_prepare_binds_duration_and_count_no_launch(monkeypatch,tmp_path,capsys):
    import json
    from test_native_cli import cli
    from market import native_protocol as p,native_session as n
    module=cli()
    declaration={}
    recorded=[]
    def current(profile,minutes,count):
        recorded.append((profile,minutes,count))
        return declaration
    class Session:
        def __init__(self,config,clock):
            self.config=config
        def prepare(self):
            with p.scope(p.NativeProfile(self.config.profile,self.config.duration_minutes,self.config.max_observations)):
                return n.PreparedNative(dict(schema=p.schema('prepared'),protocol_sha256=self.config.protocol_sha256,
                    bindings_sha256=DIGEST,incarnation=self.config.incarnation,worker_session=self.config.worker_session))
    monkeypatch.setattr(module,'_check_platform',lambda:None)
    monkeypatch.setattr(module,'_decoder_root',lambda root:None)
    monkeypatch.setattr(n,'current_protocol',current)
    monkeypatch.setattr(n,'NativeSession',Session)
    assert module.main(['prepare','--work-root',str(tmp_path/'native'),'--profile','live-pilot/v1',
        '--duration-minutes','60','--max-observations','120'])==0
    result=json.loads(capsys.readouterr().out)
    assert recorded==[('live-pilot/v1',60,120)]
    assert result['wall_seconds']==3600 and result['model_observations']==120
    assert result['native_released'] is False and result['prepared']['schema']=='market-native-prepared/v2'

def test_live_load_prepared_restores_exact_limits_and_rejects_override(tmp_path,monkeypatch):
    from pathlib import Path
    from dataclasses import replace
    from market import native_protocol as p,native_session as n
    from market.price_service import SystemClock
    from test_native_cli import cli,ROOT
    from test_native_evidence import prepared_fixtures
    declaration,bindings=prepared_fixtures()
    def relocate(value):
        if type(value) is str:return value.replace('C:\\project',str(ROOT))
        if type(value) is dict:return {key:relocate(item) for key,item in value.items()}
        if type(value) is list:return [relocate(item) for item in value]
        return value
    bindings=relocate(bindings)
    root=tmp_path/'prepared'
    root.mkdir();(root/'scratch').mkdir()
    profile=p.NativeProfile('live-pilot/v1',60,48)
    with p.scope(profile):
        declaration.update(schema=p.schema('protocol'),proof=profile.name,constants=p.limits())
        declaration['application_sources']['market/native_price.py']=DIGEST
        bindings['files']['market/native_price.py']=dict(bindings['files']['market/native_worker.py'],
            path=bindings['files']['market/native_worker.py']['path'].replace('native_worker.py','native_price.py'))
        bindings.update(schema=p.schema('bindings'),protocol_sha256=p.canonical_sha256(declaration),
            work_root=str(root),decoder_work_root=str(root.parent/'prepared-decoder'))
        bindings['environment'].update(TMP=str(root/'scratch'),TEMP=str(root/'scratch'))
        bindings['compiler_probe']['environment_sha256']=p.canonical_sha256(bindings['environment'])
        prepared=n.PreparedNative(dict(schema=p.schema('prepared'),incarnation=INCARNATION,worker_session=SESSION,
            protocol_sha256=p.canonical_sha256(declaration),bindings_sha256=p.canonical_sha256(bindings)))
    (root/'protocol.json').write_bytes(p.canonical_bytes(declaration))
    (root/'bindings.json').write_bytes(p.canonical_bytes(bindings))
    config=cli()._read_prepared_config(root)
    assert config.profile=='live-pilot/v1' and config.duration_minutes==60 and config.max_observations==48
    monkeypatch.setattr(n,'current_protocol',lambda *a:p.FrozenRecord(declaration))
    assert n.NativeSession(config,SystemClock()).load_prepared(p.canonical_sha256(prepared))==prepared
    with pytest.raises(ValueError):
        n.NativeSession(replace(config,max_observations=49),SystemClock()).load_prepared(p.canonical_sha256(prepared))
    with pytest.raises(ValueError):
        n.NativeSession(replace(config,profile='bounded-image20s/v1'),SystemClock()).load_prepared(p.canonical_sha256(prepared))

@pytest.mark.parametrize('wall_offset',[3600000000000,5000000000])
def test_live_receive_keeps_original_issue_plus_thirty_five_second_budget(tmp_path,monkeypatch,wall_offset):
    from market import native_protocol as p,native_session as n
    from market.price_service import SystemClock
    value=n.NativeSession(n.NativeConfig(INCARNATION,SESSION,DIGEST,tmp_path/'native',profile='live-pilot/v1'),SystemClock())
    issued=value._now()
    value._wall_deadline=issued+wall_offset
    def startup():
        value._authorize(dict(action='black'))
    captured=[]
    def receive(**kwargs):
        captured.append(kwargs['deadline'])
        raise p.ProtocolError('deadline')
    monkeypatch.setattr(value,'_startup',startup)
    monkeypatch.setattr(value,'_receive',receive)
    value._run()
    assert len(captured)==1
    assert issued+35000000000<=captured[0]<=issued+35050000000


def test_synchronous_start_failure_shares_first_stop_epoch_and_closes(tmp_path,monkeypatch):
    import time
    from market import native_protocol as p,native_session as n,native_windows as w
    from market.price_service import SystemClock
    from test_native_evidence import cleanup_fixture
    value=n.NativeSession(n.NativeConfig(INCARNATION,SESSION,DIGEST,tmp_path/'native',profile='live-pilot/v1'),SystemClock())
    value.config.work_root.mkdir()
    value._bindings=p.FrozenRecord(dict(work_root=str(value.config.work_root),decoder_work_root=str(tmp_path/'decoder')))
    value._prepared=p.FrozenRecord(dict(bindings_sha256=DIGEST))
    monkeypatch.setattr(value,'_compare_controls',lambda deadline:None)
    monkeypatch.setattr(w,'compare_bound_files',lambda *args,**kwargs:None)
    instances=[]
    class FailedChild(w.OwnedNativeChild):
        def __init__(self,*args):
            super().__init__(*args)
            self.confirmed=False
            instances.append(self)
        def start(self):
            raise w.NativeTransportError('source')
        def confirm_exit(self):
            self.confirmed=True
            return p.FrozenRecord(dict(worker_exit_confirmed=True,worker_exit_code=0,job_empty_confirmed=True))
        def finish_close(self,**kwargs):
            result=cleanup_fixture()
            result.update(requested_ns=self._cleanup_requested_ns,finished_ns=self._now())
            return p.validate_cleanup(result)
    monkeypatch.setattr(w,'OwnedNativeChild',FailedChild)
    try:
        with pytest.raises(w.NativeTransportError,match='source'):
            value.start(value._prepared,True)
        child=instances[0]
        assert value._final_deadline is not None and value._stop_ns is not None
        assert child._cleanup_real_deadline==value._final_deadline
        first_epoch=child._cleanup_real_deadline
        time.sleep(.002)
        value.finish_receipts()
        cleanup=value.finish_close()
        assert child.confirmed and cleanup.outcome=='confirmed'
        assert child._cleanup_real_deadline==first_epoch and cleanup.requested_ns==value._stop_ns
        assert (value.config.work_root/'failure.json').is_file()
        assert not (value.config.work_root/'final.json').exists()
    finally:
        if value._events is not None:
            value.finish_receipts()
            value._close_test_evidence()


@pytest.mark.parametrize('profile_name',['bounded-image20s/v1','live-pilot/v1'])
def test_online_seal_refuses_nonterminal_durable_receipt(tmp_path,monkeypatch,profile_name):
    from market import native_protocol as p
    from test_native_session import software_session,drive_software,entry
    from test_native_evidence import receipt_fixture
    profile=p.NativeProfile(profile_name,480,48)
    with p.scope(profile):
        value=software_session(tmp_path,profile=profile if profile.live else None)
    drive_software(value)
    ticket=value.reserve_receipts()
    value.publish_receipts(ticket,(entry(receipt_fixture()),))
    value.finish_receipts()
    checked=[]
    subset=p.source_subset(value._protocol,value._bindings,value._prepared.protocol_sha256,value._prepared.bindings_sha256)
    def source_check():
        checked.append(True)
        return p.FrozenRecord(dict(scope='prepared-source-lock-tool-cache/v1',started_ns=value._stop_ns,
            finished_ns=value._stop_ns,file_count=subset.file_count,bindings_subset_sha256=subset.bindings_subset_sha256,all_match=True))
    monkeypatch.setattr(value,'_final_source_check',source_check)
    cleanup=value.finish_close()
    assert cleanup.outcome=='confirmed' and cleanup.first_fault=='journal_gap'
    assert not checked
    assert not (value.config.work_root/'final.json').exists()
    assert (value.config.work_root/'failure.json').is_file()
    assert value.receipt_progress().durable_ticket==ticket.ticket
    with pytest.raises(ValueError,match='journal_gap'):
        value._seal(cleanup,None)
    if value._events is not None:
        value._events.close()
        value._events=None
    value._watchdog_stop.set()
    if value._watchdog is not None:value._watchdog.join(1)
