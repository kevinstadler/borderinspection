#!/bin/sh
i=1
for ISO in `cat iso.txt`; do
  FILE="gadm36_${ISO}_0"
  if [ ! -f $FILE.kml ]; then
    if [ ! -f "$FILE.kmz" ]; then
      echo "Downloading border #$i ($ISO)"
      wget "https://biogeo.ucdavis.edu/data/gadm3.6/kmz/gadm36_${ISO}_0.kmz"
    fi
    unzip "$FILE.kmz" && rm "$FILE.kmz"
  fi
done
