#!/bin/bash

# requires -i alpha.png -i color.png as [1] and [2] respectively, video input ([0] or [o_] or whatever) needs to be prepended up front!
LOGOFILTER="[ssa]blend=all_mode=subtract[rssa];[1]split[sa],[2]blend=all_mode=multiply[ssa];[sa]negate[nsa];[rssa][nsa]blend=all_mode=divide,removelogo=../filter/whiteonblack.png" # TODO readd ../filter/ for removelogo
# -filter_complex "[0]format=rgba[r];[1]split[a1][a2];[a1]format=rgba[aa1];[2]format=rgba,[aa1]blend=all_mode=multiply[ssa];[r][ssa]blend=all_mode=subtract[rssa];[a2]negate[na];[rssa][na]blend=all_mode=divide,removelogo=whiteonblack.png"

# improve logofilter performance by only applying the blend on small part
#X=1015
#Y=598
#W=136
#H=32
#convert filter/alpha.png -crop ${{W}}x${{H}}+${{X}}+${{Y}} png24:data/alpha.png
#convert filter/color.png -crop ${{W}}x${{H}}+${{X}}+${{Y}} png24:data/color.png
#convert filter/whiteonblack.png -crop ${{W}}x${{H}}+${{X}}+${{Y}} png24:data/whiteonblack.png
# 1. [0]split[in],crop=$W:$H:$X:$Y[watermark]
# ...
# [in][processed]overlay=x=$X:y=$Y:eval=init
# this one is not more than 1/3 faster but need to stop it from being jpegged or whatever green! (add format= somewhere?)
#LOGOFILTER="split[in],crop=$W:$H:$X:$Y,$LOGOFILTER[recovered];[in][recovered]overlay=x=$X:y=$Y:eval=init"

# low verbosity, but keep showing stats
#FFMPEG="ffmpeg -v 24 -stats"
cd data

FADEINDURATION=1.5
FADEOUTDURATION=2

FRAMEDIR="/Volumes/Films/border"
if [ -d "$FRAMEDIR" ]; then
  # check every directory
  SAVEIFS=$IFS
  IFS=$(echo -en "\n\b")
  # reverse order with -r to get " (x)" directories first
  for PARTDIR in `ls -dr $FRAMEDIR/{name}pt* 2> /dev/null`; do
    if [ ! -d "$PARTDIR" ]; then
      # not a directory, pass
      continue
    elif [[ "$PARTDIR" == *" ("* ]]; then
      IFS=' ' read -ra BASENAME <<< "$PARTDIR"
      echo "Moving files from $PARTDIR to $BASENAME"
      # FIXME make sure that were not interrupting a current render by checking filesize/timestamp or something
      # https://stackoverflow.com/questions/11942422/moving-large-number-of-files (double the brackets because of python.format())
      find "$PARTDIR/footage/" -name '*.jpeg' -exec mv {{}} "$BASENAME/footage/" \; || exit 1
      rm -rf "$PARTDIR"
    else
      PARTNAME=`basename $PARTDIR`
      # render
      if [ -e "$PARTNAME.mp4" ]; then
        echo "Already rendered: $PARTNAME.mp4"
        continue
      else
        # force keyframes at 1s into and before the end since that's where we might want to apply a fade in/out
        NFRAMES=$((`ls -l "$PARTDIR/footage/" | wc -l`))
        FADEOUTOFFSETS=`echo "2 k $((NFRAMES-$FADEOUTDURATION*{framerate})) {framerate} / p" | dc`
        # according to https://superuser.com/questions/459313/how-to-cut-at-exact-frames-using-ffmpeg
        # cutting on exact frames with bitstream copy (-c:v copy) is not possible, since not all frames are intra-coded ("keyframes")
        # we therefore force a keyframe at 1s in during concatenation (above)
        KEYFRAMES="1,1.5,2,$FADEOUTOFFSETS"
        echo "Rendering $PARTNAME.mp4 ($NFRAMES input frames) with forced keyframes at $KEYFRAMES"
        INPUTFRAMES="$PARTDIR/footage/$PARTNAME_*.jpeg"
        time ffmpeg -v 24 -stats -r {videoframerate} -pattern_type glob -i "$INPUTFRAMES" -i ../filter/alpha.png -i ../filter/color.png -filter_complex "[0]$LOGOFILTER" {args} -force_key_frames "$KEYFRAMES" "$PARTNAME.mp4" || exit 1
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

  fade () {{
    echo
    # args: 1=infile, 2='in' or 'out', 3=truncatedfile, 4=fadedfile, 5=shorttruncate (when -eq 0 truncate intro as well as outro time)
    if [ ! -e "$4" ]; then
      # cut into two segments https://superuser.com/questions/883108/avoid-ffmpeg-re-encode-using-complex-filter
      local NFRAMES=`ffprobe -v error -select_streams v:0 -show_entries stream=nb_frames -of default=nokey=1:noprint_wrappers=1 "$1"`
      local TRUNCFRAMES=""
      if [ "$2" == "in" ]; then
        local FADESECONDS=$FADEINDURATION
        if [ "$5" -eq 0 ]; then
          echo "Truncating on both ends! this feature online works with fade-in atm..."
          printf -v TRUNCFRAMES "%d" $(bc -l <<< "$NFRAMES - $FADEINDURATION*{framerate} - $FADEOUTDURATION*{framerate}")
        fi
      else
        local FADESECONDS=$FADEOUTDURATION # without forced keyframes this will be fuzzy anyway
      fi
      # quantize that shit
      printf -v FADEFRAMES "%.0f" $(bc -l <<< "$FADESECONDS*{framerate}")
      FADESECONDS=`echo "2 k $FADEFRAMES {framerate} / p" | dc`

      # set if not set yet
      if [ -z "$TRUNCFRAMES" ]; then
        printf -v TRUNCFRAMES "%.0f" $(bc -l <<< "$NFRAMES - $FADESECONDS*{framerate}")
      fi
      echo $TRUNCFRAMES
      local TRUNCDURATION=`echo "2 k $TRUNCFRAMES {framerate} / p" | dc`

      # DEBUG that fucker:
      #doddy-2:GES kevin$ keyframes data/AUT-t40-vd500-gd596-50kmh-skip113873by10000pt004.mp4
      #Total number of frames: 10031 (frame indices go from 1 to 10031, TIMES from 0 to (10030)/25 = 6m41.2 (after last frame vid is 6m41.24 long))
      #9926:frame,I 9976:frame,I 9982:frame,I


      if [ "$2" == "in" ]; then
        local TRUNCSTART=$FADESECONDS
        local FADESTART=0
      else
        local TRUNCSTART=0
        # outro truncation duration when $5 is not 0 (i.e. double truncation) doesn't work!
        local FADESTART=$TRUNCDURATION
      fi

      echo "$1 has $NFRAMES frames (`echo "2 k $NFRAMES {framerate} / p" | dc` seconds)"
      STARTFRAME=`echo "2 k $FADESTART {framerate} * 1 + p" | dc` # add one because frame index
      echo "Fade $2 part is $FADEFRAMES frames, starting at ${{FADESTART}}s (frame $STARTFRAME)"

      if [ "$3" == 'skip' ]; then
        echo "Not producing truncated one"
      else
        echo "minus ${{FADESECONDS}}s of fade, the truncated (non re-encoded) part is $TRUNCFRAMES frames ($TRUNCDURATION seconds)"
        echo "Splitting $1 into raw (starting at $TRUNCSTART) + fade-$2 part (starting at ${{FADESTART}}s)"
      fi
      # only -ss before -i does accurate input seeking to the forced keyframe (-ss after skipped the whole keyframe for some reason)
      # accurate input seeking is especially crucial on the truncated video which comes right after the fade-in:
#        ffmpeg -v 24 -stats -ss $TRUNCSTART -i "$1" -frames:v $TRUNCFRAMES -c copy "$3"
      ffmpeg -v 24 -ss $FADESTART -i "$1" -frames:v $FADEFRAMES -vf "fade=$2:0:$FADEFRAMES" "$4" || exit 1
    fi
  }}

  read -r -a FILES <<< `ls {name}pt*.mp4`
  N=$((${{#FILES[@]}}-1))

  # add a nice fadein to the first file
  TRUNCATED="frontmatter/intro-truncated-${{FILES[0]}}"
  INTRO="frontmatter/intro-fadein-${{FILES[0]}}"
  fade ${{FILES[0]}} "in" $TRUNCATED $INTRO $N # pass N as last to possibly deduct fadeout time as well
  echo "file $INTRO" >> tmp.txt
  #echo "file $TRUNCATED" >> tmp.txt
  # https://ffmpeg.org/ffmpeg-formats.html#concat-1
  echo "file ${{FILES[0]}}" >> tmp.txt
  echo "inpoint $FADEINDURATION" >> tmp.txt

  # only write from the second until the second-to-last file
  for (( i=1; i < $N; i++ )); do
    echo "file ${{FILES[$i]}}" >> tmp.txt
  done
  # add a nice fadeout to the last file
  LAST=${{FILES[$N]}}
  TRUNCATED="frontmatter/outro-truncated-$LAST"
  # don't produce a truncated one when it's only one file
  if [ "$N" -eq 0 ]; then
    TRUNCATED="skip"
  else
#    echo "file $TRUNCATED" >> tmp.txt
    echo "file $LAST" >> tmp.txt
  fi
  NFRAMES=`ffprobe -v error -select_streams v:0 -show_entries stream=nb_frames -of default=nokey=1:noprint_wrappers=1 "$LAST"`
  # Out point is exclusive, which means that the demuxer will not output packets with a decoding timestamp greater or equal to Out point.
  FADEOUTOFFSET=`echo "2 k $((NFRAMES - 1 - $FADEOUTDURATION*{framerate})) {framerate} / p" | dc`
  echo $FADEOUTOFFSET
  echo "outpoint $FADEOUTOFFSET" >> tmp.txt

  OUTRO="frontmatter/outro-fadeout-$LAST"
  fade $LAST "out" $TRUNCATED $OUTRO $N
  echo "file $OUTRO" >> tmp.txt

  EXT='png'
  if [ ! -e "frontmatter/{name}.mp4" ]; then
    echo "Generating intro"
    # 72/32/16 too small, go for 72/48/24
    convert -size {size[0]}x{size[1]} xc:black -fill white -font /Library/Fonts/AmericanTypewriter.ttc -pointsize 72 -gravity center -draw "text 0,-30% 'border inspection'" "frontmatter/{name}0.$EXT"
    convert -size {size[0]}x{size[1]} xc:black -fill white -pointsize 48 -gravity center -draw "text 0,-50% '{fullname}'" "frontmatter/{name}1.$EXT"
    convert "frontmatter/{name}1.$EXT" -fill white -pointsize 24 -gravity center -draw "text 0,20% '(runtime: {runtime})'" "frontmatter/{name}2.$EXT"
    ffmpeg -v 24 {introframes} -filter_complex "{introfilter}" {args} "frontmatter/{name}.mp4" || exit 1
  fi

  echo "Merging $((N+1)) parts into {name}.mp4"
  # very fast with stream copy but doesn't allow for filtering
  time ffmpeg -v 24 -stats -f concat -i tmp.txt -c copy "$FRAMEDIR/{name}.mp4" || exit 1
#  rm tmp.txt
  echo "border inspection: {fullname}"
  echo
  echo "{fullname} @ {kmh}km/h"
  echo
  echo "Imagery (c) Google Earth and its providers"
fi

cd ..
