#!/bin/bash

# generate using
#./createtour.py -tilt 35 -vd 350 -m 14 ../data/2/AUT.geojson && ./AUTreel.sh
#./createtour.py -tilt 35 -vd 650 -m 14 ../data/2/CHN.geojson && ./CHNreel.sh

INFILES=`ls {name}reel/*-cleared.png 2> /dev/null`
if [ $? -ne 0 ]; then
  # jpEg is the originals
  ./filter/removemark `ls {name}reel/*.jpeg`
  INFILES=`ls {name}reel/*-cleared.png`
fi
set -- "$@" $INFILES

# from 60/40 to 
convert -size {size[0]}x{size[1]} xc:black -fill white -gravity center -pointsize 72 -draw "text 0,-80% '{fullname}'" -pointsize 42 -draw "text 0,50% '(runtime: {runtime})'" "{name}title.png"
GAP=20
#2x+halfgap needs to be same as resize*4*x + 3*gap
#convert -background transparent \( {name}title.png $1 +smush $((GAP/2)) \) \( $2 $3 $4 $5 +smush $GAP -resize 49.6% \) \( $6 $7 $8 $9 +smush $GAP -resize 49.65% \) \( ${{10}} ${{11}} ${{12}} ${{13}} +smush $GAP -resize 49.65% \) -smush $((GAP/2)) -resize 50% {name}reel24.png
#convert -background transparent \( {name}title.png $1 +smush $((GAP/2)) \) \( $2 $3 $4 +smush $GAP -resize 66.25% \) \( $6 $7 $8 +smush $GAP -resize 66.25% \) \( ${{10}} ${{11}} ${{12}} +smush $GAP -resize 66.25% \) -smush $((GAP/2)) -resize 50% {name}reel23.png
convert -background transparent \( {name}title.png $2 $3 +smush $((GAP/2)) -resize 88.8% \) \( $3 $4 $5 $6 +smush $GAP -resize 66.25% \) \( $8 $9 ${{10}} ${{11}} +smush $GAP -resize 66.25% \) \( ${{12}} ${{13}} $1 $2 +smush $GAP -resize 66.25% \) -smush $((GAP/2)) -resize 50% {name}reel34.png
#convert -background transparent \( {name}title.png $2 $3 +smush $((GAP/2)) -resize 50% \) \( $4 $5 $6 +smush $((GAP/2)) -resize 50% \) \( $8 $9 ${{10}} +smush $((GAP/2)) -resize 50% \) -smush $((GAP/4)) {name}reel33.png
#open {name}reel33.png
