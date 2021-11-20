#!/bin/bash
if [ $? -eq 0 ]; then
  set -- "$@" `ls {name}reel/*-cleared.jpg`
fi

convert -size {size[0]}x{size[1]} xc:black -fill white -gravity center -pointsize 60 -draw "text 0,-50% \'The {fullname}\'" -pointsize 40 -draw "text 0,20% \'(runtime: {runtime})\'" "{name}title.png"
GAP=20
#2x+halfgap needs to be same as resize*4*x + 3*gap
# TODO hardcode add parameters?
convert -background transparent \\( {name}title.png $1 +smush $((GAP/2)) \\) \\( $2 $3 $4 $5 +smush $GAP -resize 49.6% \\) \\( $6 $7 $8 $9 +smush $GAP -resize 49.65% \\) \\( ${{10}} ${{11}} ${{12}} ${{13}} +smush $GAP -resize 49.65% \\) -smush $((GAP/2)) -resize 75% {name}reel4.jpg
convert -background transparent \\( {name}title.png $1 +smush $((GAP/2)) \\) \\( $2 $3 $4 +smush $GAP -resize 66.25% \\) \\( $6 $7 $8 +smush $GAP -resize 66.25% \\) \\( ${{10}} ${{11}} ${{12}} +smush $GAP -resize 66.25% \\) -smush $((GAP/2)) -resize 75% {name}reel3.jpg
