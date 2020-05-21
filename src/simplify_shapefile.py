#!/usr/bin/python

import glob
import shutil
import requests
import json
import argparse
import logging
import os
import ogr
import osr
import sys
import shapefile
 
def getFeatureCount(lyrfile):
    result = arcpy.GetCount_management(lyrfile)
    count = int(result.getOutput(0))
    logging.info("Number of features in {} is {}".format(lyrfile,count))
    return count

def wkt2shape(wkt,output_file):

    layer_name  = os.path.splitext(os.path.basename(output_file))[0]

    spatialref = osr.SpatialReference()  # Set the spatial ref.
    spatialref.SetWellKnownGeogCS('WGS84')  # WGS84 aka ESPG:4326

    driver = ogr.GetDriverByName("ESRI Shapefile")
    dstfile = driver.CreateDataSource(output_file) # Your output file

    # Please note that it will fail if a file with the same name already exists
    dstlayer = dstfile.CreateLayer(layer_name, spatialref, geom_type=ogr.wkbMultiPolygon) 

    # Add the other attribute fields needed with the following schema :
    #fielddef = ogr.FieldDefn("ID", ogr.OFTInteger)
    #fielddef.SetWidth(10)
    #dstlayer.CreateField(fielddef)

    poly = ogr.CreateGeometryFromWkt(wkt)
    feature = ogr.Feature(dstlayer.GetLayerDefn())
    feature.SetGeometry(poly)
    #feature.SetField("ID", "shape") # A field with an unique id.
    dstlayer.CreateFeature(feature)
    feature.Destroy()
    dstfile.Destroy()


def simplify_shapefile(inshp,outshp):
    if not os.path.isfile(inshp):
        logging.error("ERROR: File {} does not exist".format(inshp))
        exit(1)
    sf = shapefile.Reader(inshp)
    shapes = sf.shapes() 
    scnt = len(shapes)
    print("Found {} shapes in input file".format(scnt))
    pcnt = 0
    for x in range(scnt):
        pcnt += len(shapes[x].points) 

    if pcnt > 300:
        logging.info("Shapefile is too large ({} points) - reducing to fewer than 300 points".format(pcnt))

        # read the shape file
        files = {'files': open('{}'.format(inshp), 'rb')}
 
        # post a request for simplification service
        try:
            response = requests.post('https://api.daac.asf.alaska.edu/services/utils/files_to_wkt', files=files)
        except:
            logging.error("ERROR: service unavaible - it may be that your shapefile is too large.  Reduce to under 300 points") 
          
        if not response.status_code == requests.codes.ok:
            response.raise_for_status("ERROR: Unable to simplify shapefile")
        
        results = json.loads(response.text)
#       logging.info(json.dumps(results, sort_keys=True, indent=4))
  
        if "error" in results.keys():
            logging.error("ERROR: {}".format(results['error']['report']))
            exit(1)
   
        if "repairs" in results.keys():
            logging.info("Repairs")
            for x in range(0,len(results['repairs'])):
                logging.info("        {}: {}".format(x,results['repairs'][x]['report']))
    
        if "wkt" in results.keys():
#            logging.info("{}".format(results['wkt']['wrapped']))
            wkt = ("{}".format(results['wkt']['wrapped']))
            logging.info("Creating new shape file {}".format(outshp))
            wkt2shape(wkt,outshp)
    else:
        logging.info("Shapefile has {} points; using as is".format(pcnt))
        inbase = os.path.splitext(inshp)[0]
        outbase = os.path.splitext(outshp)[0]
        for myfile in glob.glob("{}.*".format(inbase)):
            newExt = os.path.splitext(myfile)[1]
            newName = outbase + newExt
            shutil.copy(myfile,newName)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="simplify_shapefile.py",
            description="Simplify complicated shapefiles")
    parser.add_argument("infile",help="input shapefile")
    parser.add_argument("outfile",help="output shapefile")
    args = parser.parse_args()

    logFile = "simplify_shapefile.log".format(os.getpid())
    logging.basicConfig(filename=logFile,format='%(asctime)s - %(levelname)s - %(message)s',
                        datefmt='%m/%d/%Y %I:%M:%S %p',level=logging.DEBUG)
    logging.getLogger().addHandler(logging.StreamHandler())
    logging.info("Starting run")

    simplify_shapefile(args.infile, args.outfile)
