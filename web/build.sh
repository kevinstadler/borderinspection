#!/bin/bash

if [ "$1" == 'landuse' ]; then
  ../landuse/site.py ../data/landuse/*.json > landuse/index.html
fi

if [ -z "$1" ]; then
  rsync -avv . kevin@sukzessiv.net:/var/www/thiswasyouridea.com/borderinspection/
fi
