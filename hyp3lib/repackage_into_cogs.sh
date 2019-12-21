#!/bin/bash

for file in *.zip
  do
    echo "**************** Working on file $file ****************"
    unzip $file
    cd ${file%.zip}
    echo "Making cogs" 
    make_cogs.py *.tif
    echo "Moving cogs" 
    for tif in *_cog.tif
      do 
        mv $tif ${tif%_cog.tif}.tif
      done
    cd ..
    rm $file
    echo "Making new zip file"
    zip $file ${file%.zip}/*
    /bin/rm -rf ${file%.zip}
  done
