## mask images

* `whiteonblack.png`: white watermark on black background
* `blackonwhite.png`: black antialiased watermark dropshadow on white background

thresholded variants of both (can overlap!)
* `textmask.png`: thresholded whiteonblack text pixels
  * `convert whiteonblack.png -colorspace Gray -white-threshold .5% textmask.png`
* `shadowmask.png`: thresholded blackonwhite dropshadow pixels
  * `convert blackonwhite.png -negate -colorspace Gray -white-threshold .5% shadowmask.png`

* `mask.png`: all affected pixels
  * `convert blackonwhite.png -negate whiteonblack.png -compose Plus -composite -colorspace Gray -white-threshold .5% mask.png`
  * identical way: `convert textmask.png shadowmask.png -compose Plus -composite mask2.png`
  * identity check: `convert mask.png mask2.png -compose Minus -composite maskdiff.png`

<!-- * `dilated.bmp`: heuristically enlarged mask that also covers all of the dropshadow pixels (see below)
  * `convert earthlogo.bmp -white-threshold 1% -morphology Dilate Disk:2.0 dilated.bmp # can do Disk:2.5 for some extra` -->

## blur approaches (ok for stills, obvious for animations)

### `delogo` rectangular blur filter for imagery source logo removal

Not so pretty but o.k. for removing the dynamic text watermark on stills.

 `delogo=x=867:y=630:w=279:h=13`

### `removelogo` pixelmask blur filter

*For still images only* it can be acceptable to just use ffmpeg's `removelogo` blur filter, which blurs all non-black pixels from the mask:

`ffmpeg -i "$1" -vf "removelogo=/Users/kevin/borderline/whiteonblack.bmp" "$1-cleared-dark.jpg"`

Because masked pixels are interpolated based on those directly surrounding them (which actually have black dropshadow antialiasing in them) these stills actually end up with a slightly dark shaded 'Google Earth' text. This can be countered by extending the masked area to the shadow pixels as well.

`ffmpeg -i "$1" -vf "removelogo=/Users/kevin/borderline/mask.bmp" "$1-cleared.jpg"`

## pixel recovery

### recover *white* only

Based on https://im.snibgo.com/watermark.htm#dewm, to get from watermarked image (`R`) + watermark (`S`) to original (`D`) we need to calculate:

> `D = (R - S*Sa) / (1 - Sa)`

If we ignore the drop shadow and only address the opaque white and transparent whites we can assume that `S=1` and the RGB value of each pixel is `Sa`, so:

> `D = (R - S) / (1 - S)`

#### Imagemagick testing

The following command works reasonably well for some pixels:

`convert "whiteonblack.png" "../CHNreel/CHN-t35-vd650-gd928-50kmh-skip11-reel13_00.jpeg" -compose Minus -composite \( "whiteonblack.png" -negate \) -compose DivideSrc -composite out.png && open out.png`

Recovery quality based on pixel opacity:

* 52: perfect
* 77, 78, 91, 95: slightly too dark
* up to 135, 160, 174, 193, 201, 208, 213: sometimes decent
* 218, 233, 240: dodgy
* 246, 250: unusable
* 255: white

so create second step (`removelogo`) mask by accepting all pixels below 82% (\~210/255) and only interpolating the remaining ones

* `writeoff.png`: only hopelessly unrecoverable pixels (> 82% white)
  * `convert whiteonblack.png -colorspace Gray -black-threshold 82% -white-threshold .5% writeoff.png`

#### ffmpeg execution

The watermark mask (`S`, `[1]`) is used twice: once original to subtract, once negated for division. `ffmpeg` filter: `FRAMES -loop 0 -i earthlogo.bmp -filter_complex "[0]format=rgba[x0];[1]split[m1][m2];[m1]format=rgba[x1];[m2]negate[nm];[x0][x1]blend=all_mode=subtract[xx];[xx][nm]blend=all_mode=divide,format=rgba"`

Perform the calculation above to recover the semi-covered pixels, then apply `removelogo=writeoff.png` to interpolate/blur the hopeless pixels. Test on single frame (writing to jpg/png messes up the colorspace so just render one frame to mp4):

`ffmpeg -i "../CHNreel/CHN-t35-vd650-gd928-50kmh-skip11-reel13_00.jpeg" -i whiteonblack.png -filter_complex "[0]format=rgba[x0];[1]split[m1][m2];[m1]format=rgba[x1];[m2]negate[nm];[x0][x1]blend=all_mode=subtract[xx];[xx][nm]blend=all_mode=divide,format=rgba,removelogo=writeoff.png" -pix_fmt yuv420p -c:v libx264 -profile:v high -preset slow -crf 18 -g 30 -bf 2 -movflags faststart "filtertest.mp4" && open filtertest.mp4`

#### inverse compose + removelogo empirical result

conservative 10% threshold on the watermark pixels (i.e. letting removelogo do a lot) is much better, because removelogo does not fill in with slightly darker than should be reconstructed pixels.


### white *and* black watermark recovery

First we need to recover the full (text+dropshadow) watermark `S, Sa`

Composite over is calculated as `R = S*Sa + D * (1 - Sa)`

* for `whiteonblack` (`D=0`): `R = S*Sa`
* for `blackonwhite` (`D=1`): `R = S*Sa + (1 - Sa)`
* => `blackonwhite - whiteonblack = 1 - Sa`
  * `convert whiteonblack.png blackonwhite.png -compose Minus -composite -negate png24:alpha.png && open alpha.png`
* => `S = whiteonblack / Sa`
  * `convert alpha.png whiteonblack.png -compose Divide -composite png24:color.png && open color.png`
  * (has some artefacty/division by zero pixels scattered around, but those should be fully transparent pixels anyway)
* => fully reconstructed watermarks (according to different colors)
  * `convert color.png alpha.png -alpha off -compose CopyOpacity -composite watermark.png && open watermark.png`

Reconstruct the original according to `D = (R - S*Sa) / (1 - Sa)`

Try out on the masks firsts: `blackonwhite` is perfectly reconstructed except for 4 pixels:

`ffmpeg -i blackonwhite.png -i alpha.png -i color.png -filter_complex "[0]format=rgba[r];[1]split[a1][a2];[a1]format=rgba[aa1];[2]format=rgba,[aa1]blend=all_mode=multiply[ssa];[r][ssa]blend=all_mode=subtract[rssa];[a2]negate[na];[rssa][na]blend=all_mode=divide" -pix_fmt yuv420p -c:v libx264 -profile:v high -preset slow -crf 18 -g 30 -bf 2 -movflags faststart -y tmp.mp4 && convert tmp.mp4 -black-threshold 99.5% blackonwhitereconstructed.png && open blackonwhitereconstructed.png`

`whiteonblack` is messier:

`ffmpeg -i whiteonblack.png -i alpha.png -i color.png -filter_complex "[0]format=rgba[r];[1]split[a1][a2];[a1]format=rgba[aa1];[2]format=rgba,[aa1]blend=all_mode=multiply[ssa];[r][ssa]blend=all_mode=subtract[rssa];[a2]negate[na];[rssa][na]blend=all_mode=divide" -pix_fmt yuv420p -c:v libx264 -profile:v high -preset slow -crf 18 -g 30 -bf 2 -movflags faststart -y tmp.mp4 && convert tmp.mp4 whiteonblackreconstructed.png && open whiteonblackreconstructed.png`

Try reconstructing pixels, then `removelogo` of those pixels we know are not reconstructed well -- this one is perfect, but that doesn't seem to transfer to real world files...

`ffmpeg -i whiteonblack.png -i alpha.png -i color.png -filter_complex "[0]format=rgba[r];[1]split[a1][a2];[a1]format=rgba[aa1];[2][aa1]blend=all_mode=multiply[ssa];[r][ssa]blend=all_mode=subtract[rssa];[a2]negate[na];[rssa][na]blend=all_mode=divide,removelogo=whiteonblackreconstructed.png" -pix_fmt yuv420p -c:v libx264 -profile:v high -preset slow -crf 18 -g 30 -bf 2 -movflags faststart -y tmp.mp4 && convert tmp.mp4 whiteonblackreconstructedthenremoved.png && open whiteonblackreconstructedthenremoved.png`

With both `removelogo=writeoff.png` and `removelogo=whiteonblackreconstructed.png` at the end there's much whiteness left, even down to `convert whiteonblack.png -colorspace Gray -black-threshold 82% writeoff.png` it's not good. With `removelogo=whiteonblack.png` it looks great on stills tho.

`ffmpeg -i "../CHNreel/CHN-t35-vd650-gd928-50kmh-skip11-reel13_00.jpeg" -i alpha.png -i color.png -filter_complex "[0]format=rgba[r];[1]split[a1][a2];[a1]format=rgba[aa1];[2][aa1]blend=all_mode=multiply[ssa];[r][ssa]blend=all_mode=subtract[rssa];[a2]negate[na];[rssa][na]blend=all_mode=divide,removelogo=whiteonblack.png" -pix_fmt yuv420p -c:v libx264 -profile:v high -preset slow -crf 18 -g 30 -bf 2 -movflags faststart -y "filtertest.mp4" && open filtertest.mp4`

Test on video (again with `whiteonblack.png` for better results)

`ffmpeg -pattern_type glob -i "../GES/data/CHN45-8-10000pt1/footage/*.jpeg" -i alpha.png -i color.png -filter_complex "[1]format=rgba,split[sa],[2]blend=all_mode=multiply[ssa];[0][ssa]blend=all_mode=subtract[rssa];[sa]negate[nsa];[rssa][nsa]blend=all_mode=divide,removelogo=whiteonblack.png" -pix_fmt yuv420p -c:v libx264 -profile:v high -preset slow -crf 18 -g 30 -bf 2 -movflags faststart -y "filtertest.mp4"`


## testing

`convert filtertest.mp4 test.png`
`convert writeoff.png test.png -compose Minus -composite foo.png && open foo.png`

<!-- ### possible alternative: *between-frame* recovery

the main problem in the recovery quality is that the up-and-around jumble of pixels in the logo area does not match the strict forward-movement of the camera pan. so a better solution might be to figure out how many pixels forward (which means in most cases strictly downward) the camera advances per frame, and then copy the untainted pixels from the slightly higher up area in previous frames over the watermarked area.
-->