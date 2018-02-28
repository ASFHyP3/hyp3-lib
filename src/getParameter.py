#!/usr/bin/python

import re

#
# Read a value from a par file
#
def getParameter(parFile,parameter):
    myfile = open(parFile,"r")
    value = None
    for line in myfile:
        if re.search(parameter,line):
            t = re.split(":",line)
            value = t[1].strip()
    myfile.close()
    if value is None:
        print "Unable to find parameter {} in file {}".format(parameter,parFile)
        exit(1)
    return value

