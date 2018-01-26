#!/usr/bin/env python
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
###############################################################################
# execute.py
#
# Project:  APD 
# Purpose:  Execute a commnand 
#  
# Author:   Tom Logan
#
# Issues/Caveats:
#
###############################################################################
# Copyright (c) 2017, Alaska Satellite Facility
# 
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Library General Public
# License as published by the Free Software Foundation; either
# version 2 of the License, or (at your option) any later version.
# 
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Library General Public License for more details.
# 
# You should have received a copy of the GNU Library General Public
# License along with this library; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.
###############################################################################
import subprocess

def execute(cmd, expected=None, logfile=None):
    print('Running command: ' + cmd)
    rcmd = cmd + ' 2>&1'

    pipe = subprocess.Popen(rcmd, shell=True, stdout=subprocess.PIPE)
    output = pipe.communicate()[0]
    return_val = pipe.returncode
    print('subprocess return value was ' + str(return_val))

    for line in output.split('\n'):
        if len(line.rstrip()) > 0:
            print('Proc: ' + line)
            if logfile is not None:
                logfile.write("%s\n" % line)
                
    print('Finished: ' + cmd)

    if return_val != 0:
        print('Nonzero return value!')
        tool = cmd.split(' ')[0]
        last = 'Nonzero return value: ' + str(return_val)
        next_line = False
        for line in output.split('\n'):
            last = line
            if next_line:
                raise Exception(tool + ': ' + line)
            elif '** Error: *****' in line: # MapReady style error
                next_line = True
            elif 'Error per GCP' in line: # MapReady message that is NOT an error
                pass
            elif 'ERROR' in line.upper():
                raise Exception(tool + ': ' + line)
        # No error line found, die with last line
        raise Exception(tool + ': ' + last)

    if expected is not None:
        print('Checking for expected output: ' + expected)
        if os.path.isfile(expected):
            print('Found: ' + expected)
        else:
            print('Expected output file not found: ' + expected)
            raise Exception("Expected output file not found: " + expected)

    return output
 
