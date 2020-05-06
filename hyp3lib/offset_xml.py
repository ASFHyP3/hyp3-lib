"""Extracts offset information from ISO XML files"""

from __future__ import print_function, absolute_import, division, unicode_literals

import argparse
import os

from lxml import etree as et

ns_gmd = {'gmd': 'http://www.isotc211.org/2005/gmd'}
ns_gmd_new = {'ns': 'http://www.isotc211.org/2005/gmd'}
ns_gmi = {'gmi': 'http://www.isotc211.org/2005/gmi'}
ns_gco = {'gco': 'http://www.isotc211.org/2005/gco'}
ns_xs = {'xs': 'http://www.isotc211.org/2005/gmx'}
ns_eos = {'eos': 'http://earthdata.nasa.gov/schema/eos'}
ns_xlink = {'xlink': 'http://www.w3.org/1999/xlink'}
ns_gml = {'gml': 'http://www.opengis.net/gml/3.2'}
ns_gmx = {'gmx': 'http://www.isotc211.org/2005/gmx'}
ns = dict(
    list(ns_gmd.items()) +
    list(ns_gmi.items()) +
    list(ns_gco.items()) +
    list(ns_xs.items()) +
    list(ns_eos.items()) +
    list(ns_xlink.items()) +
    list(ns_gml.items()) +
    list(ns_gmx.items())
)


def offset_xml(listFile, csvFile):
    parser = et.XMLParser(remove_blank_text=True)

    lines = [line.rstrip() for line in open(listFile)]
    with open(csvFile, 'w') as fp:
        fp.write('rtc,granule,west,east,north,south,coregistration,rangeOffset,'
                 'azimuthOffset\n')
        for line in lines:
            print('Reading {0} ...'.format(line))
            meta = et.parse(line, parser)
            param = ('/gmd:DS_Series/gmd:composedOf/gmd:DS_DataSet/gmd:has[1]/'
                     'gmi:MI_Metadata/gmd:fileIdentifier/gco:CharacterString')
            granule = meta.xpath(param, namespaces=ns)[0].text

            param = ('/gmd:DS_Series/gmd:composedOf/gmd:DS_DataSet/gmd:has[1]/'
                     'gmi:MI_Metadata/gmd:identificationInfo/gmd:MD_DataIdentification/'
                     'gmd:extent/gmd:EX_Extent/gmd:geographicElement/'
                     'gmd:EX_GeographicBoundingBox/gmd:westBoundLongitude/gco:Decimal')
            westBound = float(meta.xpath(param, namespaces=ns)[0].text)

            param = ('/gmd:DS_Series/gmd:composedOf/gmd:DS_DataSet/gmd:has[1]/'
                     'gmi:MI_Metadata/gmd:identificationInfo/gmd:MD_DataIdentification/'
                     'gmd:extent/gmd:EX_Extent/gmd:geographicElement/'
                     'gmd:EX_GeographicBoundingBox/gmd:eastBoundLongitude/gco:Decimal')
            eastBound = float(meta.xpath(param, namespaces=ns)[0].text)

            param = ('/gmd:DS_Series/gmd:composedOf/gmd:DS_DataSet/gmd:has[1]/'
                     'gmi:MI_Metadata/gmd:identificationInfo/gmd:MD_DataIdentification/'
                     'gmd:extent/gmd:EX_Extent/gmd:geographicElement/'
                     'gmd:EX_GeographicBoundingBox/gmd:southBoundLatitude/gco:Decimal')
            southBound = float(meta.xpath(param, namespaces=ns)[0].text)

            param = ('/gmd:DS_Series/gmd:composedOf/gmd:DS_DataSet/gmd:has[1]/'
                     'gmi:MI_Metadata/gmd:identificationInfo/gmd:MD_DataIdentification/'
                     'gmd:extent/gmd:EX_Extent/gmd:geographicElement/'
                     'gmd:EX_GeographicBoundingBox/gmd:northBoundLatitude/gco:Decimal')
            northBound = float(meta.xpath(param, namespaces=ns)[0].text)

            param = ('/gmd:DS_Series/gmd:composedOf/gmd:DS_DataSet/gmd:has[1]/'
                     'gmi:MI_Metadata/gmd:dataQualityInfo/gmd:DQ_DataQuality/gmd:report[3]/'
                     'gmd:DQ_QuantitativeAttributeAccuracy/gmd:result/'
                     'gmd:DQ_QuantitativeResult/gmd:value/gco:Record/gco:CharacterString')
            coregistration = meta.xpath(param, namespaces=ns)[0].text

            param = ('/gmd:DS_Series/gmd:composedOf/gmd:DS_DataSet/gmd:has[1]/'
                     'gmi:MI_Metadata/gmd:dataQualityInfo/gmd:DQ_DataQuality/gmd:report[4]/'
                     'gmd:DQ_QuantitativeAttributeAccuracy/gmd:result/'
                     'gmd:DQ_QuantitativeResult/gmd:value/gco:Record/gco:Real')
            rangeOffset = float(meta.xpath(param, namespaces=ns)[0].text)

            param = ('/gmd:DS_Series/gmd:composedOf/gmd:DS_DataSet/gmd:has[1]/'
                     'gmi:MI_Metadata/gmd:dataQualityInfo/gmd:DQ_DataQuality/gmd:report[5]/'
                     'gmd:DQ_QuantitativeAttributeAccuracy/gmd:result/'
                     'gmd:DQ_QuantitativeResult/gmd:value/gco:Record/gco:Real')
            azimuthOffset = float(meta.xpath(param, namespaces=ns)[0].text)

            fp.write(
                '{0},{1},{2},{3},{4},{5},{6},{7},{8}\n'.format(
                    line[:-8], granule[:-8], westBound, eastBound, southBound, northBound, coregistration, rangeOffset,
                    azimuthOffset)
            )


def main():
    """Main entrypoint"""

    parser = argparse.ArgumentParser(
        prog=os.path.basename(__file__),
        description=__doc__,
    )
    parser.add_argument('list', help='XML list')
    parser.add_argument('csv', help='CSV output file')
    args = parser.parse_args()

    offset_xml(args.list, args.csv)


if __name__ == '__main__':
    main()
