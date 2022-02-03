#!/bin/bash
cd `dirname "$0"`

if [ "$1" == 'landuse' ]; then
  cd landuse
  ./site.py ../data/landuse/*.json > ../web/landuse/index.html
fi

if [ "$1" == 'numeric' ]; then
  cd numeric
fi

if [ -z "$1" ]; then
  rsync -avv web/ kevin@sukzessiv.net:/var/www/thiswasyouridea.com/
fi
