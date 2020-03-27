from __future__ import print_function, absolute_import, division, unicode_literals

import os
from lxml import etree
import logging

def getBursts(mydir,make_tab_flag=True):
    logging.info("Determining number of bursts")
    back = os.getcwd()
    burst_tab = "%s_burst_tab" % mydir[17:25]
    if make_tab_flag:
        f1 = open(burst_tab,"w")
        os.chdir(os.path.join(mydir,"annotation"))
        for name in ['001.xml','002.xml','003.xml']:
            for myfile in os.listdir("."):
                if name in myfile:
                    root = etree.parse(myfile)
                    for count in root.iter('burstList'):
                        total_bursts=int(count.attrib['count'])
                    f1.write("1 {}\n".format(total_bursts))
        f1.close()
        os.chdir(back)
    return burst_tab 


