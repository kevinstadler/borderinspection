#!/bin/bash

# requires -i alpha.png -i color.png as [1] and [2] respectively, video input ([0] or [o_] or whatever) needs to be prepended up front!
LOGOFILTER="[ssa]blend=all_mode=subtract[rssa];[1]split[sa],[2]blend=all_mode=multiply[ssa];[sa]negate[nsa];[rssa][nsa]blend=all_mode=divide,removelogo=../filter/whiteonblack.png" # TODO readd ../filter/ for removelogo
# -filter_complex "[0]format=rgba[r];[1]split[a1][a2];[a1]format=rgba[aa1];[2]format=rgba,[aa1]blend=all_mode=multiply[ssa];[r][ssa]blend=all_mode=subtract[rssa];[a2]negate[na];[rssa][na]blend=all_mode=divide,removelogo=whiteonblack.png"

# improve logofilter performance by only applying the blend on small part
X=1015
Y=598
W=136
H=32
convert filter/alpha.png -crop ${{W}}x${{H}}+${{X}}+${{Y}} png24:data/alpha.png
convert filter/color.png -crop ${{W}}x${{H}}+${{X}}+${{Y}} png24:data/color.png
convert filter/whiteonblack.png -crop ${{W}}x${{H}}+${{X}}+${{Y}} png24:data/whiteonblack.png
# 1. [0]split[in],crop=$W:$H:$X:$Y[watermark]
# ...
# [in][processed]overlay=x=$X:y=$Y:eval=init
# this one is not more than 1/3 faster but need to stop it from being jpegged or whatever green! (add format= somewhere?)
#LOGOFILTER="split[in],crop=$W:$H:$X:$Y,$LOGOFILTER[recovered];[in][recovered]overlay=x=$X:y=$Y:eval=init"

# low verbosity, but keep showing stats
#FFMPEG="ffmpeg -v 24 -stats"
cd data

FRAMEDIR="/Volumes/Films/border"
if [ -d "$FRAMEDIR" ]; then
  # check every directory
  SAVEIFS=$IFS
  IFS=$(echo -en "\n\b")
  # reverse order with -r to get " (x)" directories first
  for PARTDIR in `ls -dr $FRAMEDIR/{name}pt* 2> /dev/null`; do
    if [[ "$PARTDIR" == *" ("* ]]; then
      IFS=' ' read -ra BASENAME <<< "$PARTDIR"
      echo "Moving files from $PARTDIR to $BASENAME"
      # FIXME make sure that were not interrupting a current render by checking filesize/timestamp or something
      # https://stackoverflow.com/questions/11942422/moving-large-number-of-files (double the brackets because of python.format())
      find "$PARTDIR/footage/" -name '*.jpeg' -exec mv {{}} "$BASENAME/footage/" \; || exit 1
      rm -rf "$PARTDIR"
    else
      PARTNAME=`basename $PARTDIR`
      # render
      if [ -f "$PARTNAME.mp4" ]; then
        echo "Already rendered: $PARTNAME.mp4"
        continue
      else
        NFRAMES=$((`ls -l "$PARTDIR/footage/" | wc -l`))
        FADEOUTKEYFRAME=`echo "2 k $((NFRAMES-{framerate})) {framerate} p" | dc`
        echo "Rendering $PARTNAME.mp4 ($NFRAMES input frames)"
        INPUTFRAMES="$PARTDIR/footage/$PARTNAME_*.jpeg"
        # force keyframes at 1s into and 1s before the end since that's where we might want to apply a fade in/out
        time ffmpeg -v 24 -stats -r {videoframerate} -pattern_type glob -i "$INPUTFRAMES" -i ../filter/alpha.png -i ../filter/color.png -filter_complex "[0]$LOGOFILTER" {args} -force_key_frames 1,$FADEOUTKEYFRAME "$PARTNAME.mp4" || exit 1
      fi
    fi
  done
  IFS=$SAVEIFS
fi

# concatting also ok if we don't have original footage
ls {name}pt*.mp4 &> /dev/null
if [ $? -eq 0 ]; then
  # there are parts, so write concat demuxer for all parts, starting with intro
  echo "file frontmatter/{name}.mp4" > tmp.txt

  # hard-coded fade duration of 1s!
  FADEDURATION=1
  truncateandfade () {{
    # args: 1=infile, 2='in' or 'out', 3=truncatedfile, 4=fadedfile
    if [ ! -f "$4" ]; then
      # cut into two segments https://superuser.com/questions/883108/avoid-ffmpeg-re-encode-using-complex-filter
      local NFRAMES=`ffprobe -v error -select_streams v:0 -show_entries stream=nb_frames -of default=nokey=1:noprint_wrappers=1 "$1"`
      local TRUNCDURATION=$((NFRAMES - {framerate})) # errr * fadeduration or whatever
      local TRUNCDURATIONS=`echo "2 k $TRUNCDURATION {framerate} p" | dc`
      echo "minus 1s of fade, the TRUNCDURATION is $TRUNCDURATION frames ($TRUNCDURATIONS seconds)"
      if [ "$2" == "in" ]; then
        local TRUNCSTART=$FADEDURATION
        local FADESTART=0
      else
        local TRUNCSTART=0
        local FADESTART=$TRUNCDURATIONS
      fi
      echo "Splitting $1 into raw (starting at $TRUNCSTART) + fade-$2 part (starting at $FADESTART)"
      # according to https://superuser.com/questions/459313/how-to-cut-at-exact-frames-using-ffmpeg
      # cutting on exact frames with bitstream copy (-c:v copy) is not possible, since not all frames are intra-coded ("keyframes")
      # we therefore force a keyframe at 1s in during concatenation (above)
      # only -ss before -i does accurate input seeking to the forced keyframe (-ss after skipped the whole keyframe for some reason)
      # accurate input seeking is especially crucial on the truncated video which comes right after the fade-in:
      ffmpeg -v 24 -stats -ss $TRUNCSTART -i "$1" -frames:v $TRUNCDURATION -c copy "$3" || exit 1
      # FIXME the latter is still not working nicely on thingamingie. need to find the second-to last keyframe instead to seek from??
      ffmpeg -v 24 -ss $FADESTART -i "$1" -frames:v {framerate} -vf "fade=$2:0:{framerate}" "$4" || exit 1
    fi
  }}

  read -r -a FILES <<< `ls {name}pt*.mp4`

  # add a nice fadein to the first file
  TRUNCATED="frontmatter/intro-truncated-${{FILES[0]}}"
  INTRO="frontmatter/intro-fadein-${{FILES[0]}}"
  truncateandfade ${{FILES[0]}} "in" $TRUNCATED $INTRO
  echo "file $INTRO" >> tmp.txt
  echo "file $TRUNCATED" >> tmp.txt

  N=$((${{#FILES[@]}}-1))
  # only write from the second until the second-to-last file
  for (( i=1; i < $N; i++ )); do
    echo "file ${{FILES[$i]}}" >> tmp.txt
  done
  # add a nice fadeout to the last file
  # FIXME how to handle when it's only one file!??
  LAST=${{FILES[$N]}}
  TRUNCATED="frontmatter/outro-truncated-$LAST"
  OUTRO="frontmatter/outro-fadeout-$LAST"
  truncateandfade $LAST "out" $TRUNCATED $OUTRO
  echo "file $TRUNCATED" >> tmp.txt
  echo "file $OUTRO" >> tmp.txt

  EXT='png'
  if [ ! -f "frontmatter/{name}.mp4" ]; then
    echo "Generating intro"
    # 72/32/16 too small, go for 90/40/20
    convert -size {size[0]}x{size[1]} xc:black -fill white -font /Library/Fonts/AmericanTypewriter.ttc -pointsize 90 -gravity center -draw "text 0,-30% 'border inspection'" "frontmatter/{name}0.$EXT"
    convert -size {size[0]}x{size[1]} xc:black -fill white -pointsize 40 -gravity center -draw "text 0,-20% '{fullname}'" "frontmatter/{name}1.$EXT"
    convert "{name}1.$EXT" -fill white -pointsize 20 -gravity center -draw "text 0,20% '(runtime: {runtime})'" "frontmatter/{name}2.$EXT"
    ffmpeg -v 24 {introframes} -filter_complex "{introfilter}" {args} "frontmatter/{name}.mp4"
  fi

  echo "Merging $((N+1)) parts into {name}.mp4"
  # very fast with stream copy but doesn't allow for filtering
  time ffmpeg -v 24 -stats -f concat -i tmp.txt -c copy "{name}.mp4"
  rm tmp.txt
  echo "border inspection: {fullname}"
  echo
  echo "{fullname} @ {kmh}km/h"
  echo "Imagery (c) Google Earth and its providers"
fi

cd ..
