"""Managed subprocessing for HyP3 externals"""

import logging
import os
import subprocess
from pathlib import Path
from typing import Optional, TextIO, Union

from hyp3lib import ExecuteError


def execute(cmd: str, expected: Optional[Union[str, Path]] = None, logfile: Optional[TextIO] = None,
            uselogging: bool = False) -> str:
    """
    Run a command in a subprocess and perform some post-process verification of
    the command's execution

    Args:
        cmd: The command to subprocess in a shell
        expected: Ensure an expected file created by the cmd exists
        logfile: A file to to write the cmd's stdout to
        uselogging: Instead of printing status messages of this function, log
            them with the logging module

    Returns:
        output: The stdout of cmd
    """
    if uselogging:
        logging.info('Running command: ' + cmd)
    else:
        print('Running command: ' + cmd)
    rcmd = cmd + ' 2>&1'

    pipe = subprocess.Popen(rcmd, shell=True, stdout=subprocess.PIPE, universal_newlines=True)
    output = pipe.communicate()[0]
    return_val = pipe.returncode
    if uselogging:
        logging.info('subprocess return value was ' + str(return_val))
    else:
        print('subprocess return value was ' + str(return_val))

    for line in output.split('\n'):
        if len(line.rstrip()) > 0:
            if uselogging:
                logging.info('Proc: ' + line)
            else:
                print('Proc: ' + line)
            if logfile is not None:
                logfile.write("%s\n" % line)

    if uselogging:
        logging.info('Finished: ' + cmd)
    else:
        print('Finished: ' + cmd)

    if return_val != 0:
        if uselogging:
            logging.error('Nonzero return value!')
        else:
            print('Nonzero return value!')
        tool = cmd.split(' ')[0]
        last = 'Nonzero return value: ' + str(return_val)
        next_line = False
        for line in output.split('\n'):
            last = line
            if next_line:
                raise ExecuteError(tool + ': ' + line)
            elif '** Error: *****' in line:  # MapReady style error
                next_line = True
            elif 'Error per GCP' in line:  # MapReady message that is NOT an error
                pass
            elif 'Setting maximum error to be' in line:  # RTC message that is NOT an error
                pass
            elif 'Root mean squared error' in line:  # RTC message that is NOT an error
                pass
            elif 'ERROR' in line.upper():
                raise ExecuteError(tool + ': ' + line)
        # No error line found, die with last line
        raise ExecuteError(tool + ': ' + last)

    if expected is not None:
        if uselogging:
            logging.info('Checking for expected output: ' + expected)
        else:
            print('Checking for expected output: ' + expected)
        if os.path.isfile(expected):
            if uselogging:
                logging.info('Found: ' + expected)
            else:
                print('Found: ' + expected)
        else:
            if uselogging:
                logging.info('Expected output file not found: ' + expected)
            else:
                print('Expected output file not found: ' + expected)
            raise ExecuteError("Expected output file not found: " + expected)

    return output
