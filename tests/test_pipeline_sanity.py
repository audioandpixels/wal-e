import pytest

from wal_e import pipeline


def create_bogus_payload(dirname):
    payload = 'abcd' * 1048576
    payload_file = dirname.join('payload')
    payload_file.write(payload)
    return payload, payload_file


def test_rate_limit(tmpdir):
    payload, payload_file = create_bogus_payload(tmpdir)

    pl = pipeline.PipeViewerRateLimitFilter(1048576 * 100,
                                           stdin=payload_file.open())
    pl.start()
    round_trip = pl.stdout.read()
    pl.finish()
    assert round_trip == payload


def test_upload_download_pipeline(tmpdir, rate_limit):
    payload, payload_file = create_bogus_payload(tmpdir)

    # Upload section
    test_upload = tmpdir.join('upload')
    with open(unicode(test_upload), 'w') as upload:
        with open(unicode(payload_file)) as inp:
            with pipeline.get_upload_pipeline(
                    inp, upload, rate_limit=rate_limit):
                pass

    with open(unicode(test_upload)) as completed:
        round_trip = completed.read()

    # Download section
    test_download = tmpdir.join('download')
    with open(unicode(test_upload)) as upload:
        with open(unicode(test_download), 'w') as download:
            with pipeline.get_download_pipeline(upload, download):
                pass

    with open(unicode(test_download)) as completed:
        round_trip = completed.read()

    assert round_trip == payload


def test_close_process_when_normal():
    """Process leaks must not occur in successful cases"""
    with pipeline.get_cat_pipeline(pipeline.PIPE, pipeline.PIPE) as pl:
        assert len(pl.commands) == 1
        assert pl.commands[0]._process.poll() is None

    # Failure means a failure to terminate the process.
    pipeline_wait(pl)


def test_close_process_when_exception():
    """Process leaks must not occur when an exception is raised"""
    exc = Exception('boom')

    with pytest.raises(Exception) as e:
        with pipeline.get_cat_pipeline(pipeline.PIPE, pipeline.PIPE) as pl:
            assert len(pl.commands) == 1
            assert pl.commands[0]._process.poll() is None
            raise exc

    assert e.value is exc

    # Failure means a failure to terminate the process.
    pipeline_wait(pl)


def test_close_process_when_aborted():
    """Process leaks must not occur when the pipeline is aborted"""
    with pipeline.get_cat_pipeline(pipeline.PIPE, pipeline.PIPE) as pl:
        assert len(pl.commands) == 1
        assert pl.commands[0]._process.poll() is None
        pl.abort()

    # Failure means a failure to terminate the process.
    pipeline_wait(pl)


def pipeline_wait(pl):
    for command in pl.commands:
        # Failure means a failure to terminate the process.
        command.wait()


def pytest_generate_tests(metafunc):
    # Test both with and without rate limiting if there is rate_limit
    # parameter.
    if "rate_limit" in metafunc.funcargnames:
        metafunc.parametrize("rate_limit", [None, int(2 ** 25)])
