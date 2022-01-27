#!/bin/bash


# ../landuse/site.py ../data/landuse/*.json > landuse/index.html

rsync -a . kevin@sukzessiv.net:/var/www/thiswasyouridea.com/borderinspection/
