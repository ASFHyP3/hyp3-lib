import logging

import pytest

from hyp3lib import ExecuteError, execute


def test_execute_cmd():
    cmd = 'echo "Hello world"'

    output = execute.execute(cmd)

    assert 'Hello world' in output


def test_excute_cmd_fail():
    with pytest.raises(ExecuteError):
        cmd = 'echo "Hello world"; exit 1'

        try:
            _ = execute.execute(cmd)
        except ExecuteError as err:
            assert 'echo' in str(err)
            raise


def test_execute_logfile(tmp_path):
    cmd = 'echo "Hello world"'
    log_path = tmp_path / 'echo.log'

    with log_path.open(mode='w') as log_file:
        output = execute.execute(cmd, logfile=log_file)

        assert 'Hello world' in output

    with log_path.open() as log_file:
        log_str = log_file.read()

        assert 'Hello world' in log_str


def test_execute_uselogging(caplog):
    with caplog.at_level(logging.INFO):
        cmd = 'echo "Hello world"'

        output = execute.execute(cmd, uselogging=True)

        assert 'Hello world' in output
        assert 'Proc: Hello world' in caplog.text
