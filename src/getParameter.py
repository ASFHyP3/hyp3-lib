#!/usr/bin/python

import re, os
import logging
#
# Read a value from a par file
#
def getParameter(parFile,parameter,uselogging=False):

    try:
        myfile = open(parFile,"r")
    except IOError: 
        if (uselogging):
            logging.error("Unable to find file {}".format(parFile))
        raise Exception("ERROR: Unable to find file {}".format(parFile))

    parameter = parameter.lower()
    for line in myfile:
        if parameter in line.lower():
            t = re.split(":",line)
            value = t[1].strip()
    myfile.close()

    try:
        if value:
            return value
    except:    
        if uselogging:
            logging.error("Unable to find parameter {} in file {}".format(parameter,parFile))
        raise Exception ("ERROR: Unable to find parameter {} in file {}".format(parameter, parFile))
