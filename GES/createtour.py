#!/usr/local/bin/python3.6

# more ABOVE is good because #1 higher vertical distance (footage quality) and #2 no weird/abrupt rotations (less ground distance)
#./createtour.py -split 10000 -n 3 -skip 1 -tilt 30 -sh AUT.kmz # nice view, this one has lots of source watermarks for some reason
#./createtour.py -split 10000 -n 3 -skip 1 -tilt 70 -sh AUT.kmz # STEEP, loss of 3D

# MOVIE REELS
#./createtour.py -skip 11 -tilt 35 -vd 650 -m 13 CHN.kmz
#./createtour.py -skip 1 -tilt 35 -vd 350 -m 13 AUT.kmz

import argparse
import re
from itertools import accumulate
from more_itertools import pairwise, windowed
from math import acos, asin, atan, atan2, ceil, cos, degrees, floor, log10, pi, radians, sin, sqrt, tan

import os
from os.path import basename, splitext
from pathlib import Path

import json
import geojson
#from osgeo import ogr
from shapely.geometry import asLineString, LineString, Point, Polygon
from shapely.ops import nearest_points
from countryname import countryname

import percache
cache = percache.Cache("/tmp/my-cache")

from pyproj import CRS, Transformer
proj = CRS.from_epsg(31287)
proj = Transformer.from_crs(proj.geodetic_crs, proj)

argparser = argparse.ArgumentParser(description='Generate Google Earth Studio tour(s) from boundary polygons.')
argparser.add_argument('file', nargs='+', help='boundary polygon .kmz file(s) to generate tour(s) for')

animation = argparser.add_argument_group('tour animation properties')
# first render with 75/500 means 130above, 482 behind
# second render with 65/500 means 211 above, 453 behind
animation.add_argument('-kmh', '-speed', type=int, default=50, help='animation ground speed (in km/h)')
animation.add_argument('-tilt', type=float, default=40, help='downwards camera angle (0 = parallel to horizon, 90 = vertically above). angles around 45 feel dislocated, so best < 40 (for panorama) or 60-70 (for satellite view with some 3d)')
animation.add_argument('-distance', type=float, default=400, help='diagonal distance from the camera to the targeted point on the ground (in m)')
animation.add_argument('-verticaldistance', '-vd', type=float, help='vertical distance between ground and camera, in m (overrides distance)')
animation.add_argument('-grounddistance', '-gd', type=float, help='ground distance between targeted point and camera, in m (overrides distance)')
animation.add_argument('-altitudeevery', type=float, default=.2, help='how often altitude should be sampled (in km)')
#animation.add_argument('--easein', type=float, default=1, help='in seconds (per 90 degrees maybe?)')

video = argparser.add_argument_group('video rendering properties')
video.add_argument('-width', type=int, default=1280, help='rendered image width (aspect ratio is fixed at 16:9)')
video.add_argument('-framerate', '-r', type=int, default=25, help='render export framerate (one of 24, 25 or 60)')
video.add_argument('-videoframerate', '-vr', type=int, default=25, help='output video framerate (if this differs from the export frame rate the video will appear sped up/slowed down accordingly)')
video.add_argument('-fade', type=float, default=1.2, help='ffmpeg fade duration (in s')
# recommended upload encoding settings: https://support.google.com/youtube/answer/1722171
#argparser.add_argument('--audio', default='-c:a aac/libfdk_aac -profile:a aac_low -b:a 384k')
# recommended keyframe interval (-g) is half the framerate (i.e. every two seconds)
# increasing further above 50 doesn't affect the bitrate much: https://forum.videohelp.com/threads/382698-keyframe-interval-recommended-for-h264-video-at-50-fps#post2478931
# GOP format is (IBBPBBPBBP....)I, so multiples of 3 all end on a P before the next IDR, which makes sense as ending on a B is pointless since looking forward to the following IDR is not possible with closed GOPS.
# so 'best' (if at all relevant) keyframe interval is a multiple of 3! (50 makes the GOP IBBP...BBPP and 3% smaller than with -g 30, just leave it...)
# (actually x264 appears to automatically pick a B/P alternation pattern that's smart)
# see also http://www.chaneru.com/Roku/HLS/X264_Settings.htm#bframes
# also says recommended HDR bitrates for 720p is 6.5MBps tops, -crf 18 has 13-16MBps @ 0.3x so turn up to 20+ maybe...
video.add_argument('-video', default='-pix_fmt yuv420p -c:v libx264 -profile:v high -preset slow -crf 20 -g 50 -bf 2', help='ffmpeg video encoding properties')
video.add_argument('-container', default=' -movflags faststart', help='ffmpeg container properties')

shape = argparser.add_argument_group('shape properties and extent')

#argparser.add_argument('-nkeyframes', type=int, help='only include the first points of the polygon')
#argparser.add_argument('-nframes', type=int, help='only include points that make up to this number of video frames')
shape.add_argument('-split', '-s', type=int, help='split tour into chunks of up to this many video frames')
shape.add_argument('-frompart', type=int, default=1, help='first part to write (counting starts at 1) TODO this isnt actually implemented yet')
shape.add_argument('-nparts', type=int, help='write this many parts')
shape.add_argument('-simplify', type=float, default=.0001, help='polygon simplification tolerance') # , default=.00025
shape.add_argument('-skip', type=int, default=0, help='move starting point of the tour forward by this many points from the beginning of the input polygon')
shape.add_argument('-startpoint', type=float, nargs=2, help='start tour at the polygon point at the given longitude/latitude (takes precedence over -skip)')
shape.add_argument('-ccw', '-left', action='store_true', help='whether the surrounded polygon should be to the left of the tour (default is clockwise, polygon to the right)')

group = argparser.add_mutually_exclusive_group(required=True)
group.add_argument('-esp', action='store_true', help='write esp files')
group.add_argument('-sh', action='store_true', help='write shell script for invoking the encoder')
group.add_argument('-all', action='store_true', help='write both esp and shell files')
group.add_argument('-moviereel', type=int, help='write a movie-reel runthrough of the entire border with the given number of (key)frames')

args = argparser.parse_args()

if args.all:
  args.esp = True
  args.sh = True
elif args.moviereel:
  args.esp = True

if args.esp:
  # environment variable name needs to be lower case for GDAL (https://trac.osgeo.org/gdal/wiki/ConfigOptions)
  os.environ['http_proxy'] = 'http://192.168.2.2:3128'
  os.environ['https_proxy'] = 'http://192.168.2.2:3128'
  import urllib3
  urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

  import gpsinfo

  layer = gpsinfo.Layer(gpsinfo.Service('http://gpsinfo.org/service_wmts/gpsinfoWMTSCapabilities.xml'), 'AT_OGD_DHM_LAMB_10M_ELEVATION_COMPRESSED')

  # projection coordinates
  @cache
  def getaltitude(lon, lat):
    # force to float here so that string error messages are not cached
    return float(layer.value('interpolate', lon, lat))

  import mapbox
  import mercantile
  altitudeprovider = mapbox.Maps(access_token="pk.eyJ1Ijoia2V2aW5zdGFkbGVyIiwiYSI6ImNqNGs4OXhqZjB2em8zMnBnNXhpemk4aDAifQ.iyPq8GPuxu18Eju7Q5ONlA")
  from io import BytesIO
  from PIL import Image

  @cache
  def getmapboxaltitude(lon, lat):
    # through the raster API:
    # https://docs.mapbox.com/help/troubleshooting/access-elevation-data/
    tile = mercantile.tile(lon, lat, 14)
    response = altitudeprovider.tile('mapbox.terrain-rgb', *tile)
    if response.status_code != 200:
      return 0
    bbox = mercantile.xy_bounds(*tile)
    ul = mercantile.lnglat(bbox.left, bbox.top)
    br = mercantile.lnglat(bbox.right, bbox.bottom)
    x = round(255 * (lon - ul[0]) / (br[0] - ul[0]))
    y = round(255 * (lat - ul[1]) / (br[1] - ul[1]))
    image = Image.open(BytesIO(response.content))
    px = image.load()[x,y]
    return -10000 + ((px[0] * 256 * 256 + px[1] * 256 + px[2]) * 0.1)

def getcoords(coordstring):
  return list(map(lambda coord: list(map(float, coord.split(','))), coordstring.split(' ')))

def takelonger(currentcoords, coordbytearray):
  coords = getcoords(coordbytearray.decode())
  return coords if currentcoords == None or len(coords) > len(currentcoords) else currentcoords

# lon/lat to km
def greatcircledistance(p1, p2):
  lon1, lat1, lon2, lat2 = map(radians, [p1[0], p1[1], p2[0], p2[1]])
  # min for overflow of approximation
  return 6371 * acos(min(1, sin(lat1) * sin(lat2) + cos(lat1) * cos(lat2) * cos(lon1 - lon2)))

# lon/lat to radians: outcome 0 = north, going clockwise!
def getbearing(fr, to):
  # longitude becomes less at higher latitudes, need to account for that both when calculating the heading and when adding the distance...
  # https://www.igismap.com/formula-to-find-bearing-or-heading-angle-between-two-points-latitude-longitude/
  dL = radians(to[0] - fr[0])
  x = cos(radians(to[1])) * sin(dL)
  y = cos(radians(fr[1])) * sin(radians(to[1])) - sin(radians(fr[1])) * cos(radians(to[1])) * cos(dL)
  return atan2(x, y)

# 0 latitude = -90deg, +.1 = +18deg, .5 latitude = 0
def gelatitude(deg, relative = False):
  return (deg / 180) + (0 if relative else .5)
def gelongitude(deg, relative = False):
  return .2442333785617368 + deg * .1221167/90
def gealtitude(m):
  return m * 1.535686e-08
def gecamlongitude(deg, relative = False):
  return .5780096 + deg * .02603647/90

last = None
# geodesic coordinates
def getreliablealtitude(lon, lat):
  if args.file[0] != 'AUT.kmz':
    altitude = getmapboxaltitude(lon, lat)
  else:
    t = proj.transform(lat, lon)
    lon = round(t[1])
    lat = round(t[0])
    cell = 0 # in case we need to search ~nearby
    altitude = getaltitude(lon, lat)
#  print((altitude, mbaltitude))
  if altitude > 0:
    global last
    last = altitude
    return altitude
  else:
    print(f'WARNING: interpolated altitude at {lon},{lat} is {altitude}')
    return last

def cumulativedistances(coords):
  return [0] + list(accumulate([greatcircledistance(prv, nxt) for prv, nxt in pairwise(coords)]))

# quantize distances to frames
def distancetoframe(distance):
  # from m and km/h to seconds, then multiply by framerate
  return round(60 * 60 * distance * args.framerate / args.kmh)

# returns a tuple of nframes and the distance offsets
def distancestoframe(distances):
  frameoffsets = [distancetoframe(distance) for distance in distances]
  return (frameoffsets[-1] + 1, frameoffsets)

def formatruntime(seconds):
  return (f'{floor(seconds / 3600)}h ' if seconds >= 3600 else '') + f'{floor(seconds % 3600 / 60)}m {round(seconds % 60)}s'

def partboundarykeyframeindices(frameoffsets, nparts = None):
  totalframes = frameoffsets[-1]
  # for nparts part, take *up to* nparts+1 boundaries
  splitboundaries = list(range(0, totalframes if nparts == None else min(totalframes, (nparts + 1) * args.split), args.split))
  keyframeindices = [ next((i for i, keyframeoffset in enumerate(frameoffsets) if keyframeoffset >= frameno)) for frameno in splitboundaries ]
  # if necessary, add the final boundary (end of video) manually
  if keyframeindices[-1] != len(frameoffsets) - 1:
    # add the index of the final keyframe iff:
    # * we can have an arbitrary number of parts
    # * we hve limited parts, and we haven't reached the number of parts yet
    if nparts == None or len(keyframeindices) < nparts:
      keyframeindices.append(len(frameoffsets) - 1)
  return keyframeindices

def keyframe(time, value, easein = None, easeout = None):
  return {
    'time': time,
    'value': value,
    'transitionIn': easein if easein else { 'type': 'linear' },
    'transitionOut': easeout if easeout else { 'type': 'linear' },
    'transitionLinked': True
  }

#@cache
def readlongestjson(filename):
  with open(filename, 'r') as f:
    fc = geojson.load(f)
    feature = fc['features'][0]
    if len(fc['features']) != 1:
      print(f'WARNING: {filename} contains {len(fc["features"])} features?')
#    for part in fc['features']:

    coords = []
    if feature['geometry']['type'] == 'Polygon':
      # TODO
      print(TODOwhatifitsapolygon)
      coords = None
    else:
      # multipolygon
      for part in feature['geometry']['coordinates']:
        partcoords = list(geojson.utils.coords(part))
        if len(partcoords) > len(coords):
          coords = partcoords
      print(f"Selected ring of length {len(coords)} from a total of {len(feature['geometry']['coordinates'])} parts")
    return (countryname(feature), coords)

tilt = radians(args.tilt)

# this will be the camera altitude (constant above ground)
verticaldistance = args.distance * sin(tilt) if args.verticaldistance == None else args.verticaldistance
# next: the heading-specific distance of the camera on the ground
grounddistance = args.distance * cos(tilt) if args.grounddistance == None else args.grounddistance

# maintain tilt (at the expense of distance) if only one of the two was specified
if args.verticaldistance == None and args.grounddistance != None:
  # we know the adjacent and angle, get opposite
  oppositeoveradjacent = tan(tilt)
  verticaldistance = grounddistance * oppositeoveradjacent
elif args.grounddistance == None and args.verticaldistance != None:
  # we know the opposite and angle, get adjacent
  oppositeoveradjacent = tan(tilt)
  grounddistance = verticaldistance / oppositeoveradjacent

effectivetilt = round(degrees(atan( verticaldistance / grounddistance )))
print(f'''At a viewer distance of {round(args.distance)}m and tilt of {args.tilt}, the camera is:
  * {round(verticaldistance)}m above the ground
  * {round(grounddistance)}m behind the target
  * effective tilt: {effectivetilt} degrees
  * total camera distance: {round(sqrt(grounddistance**2 + verticaldistance**2))}m
''')

print('Generating ' + str(len(args.file)) + ' tour(s)')
totaltotalseconds = 0
for filename in args.file:
  fullname, coords = readlongestjson(filename)
  print(fullname)

  filename, ext = splitext(basename(filename))
  if not args.moviereel:
    name = f'{filename}-t{effectivetilt}-vd{round(verticaldistance)}-gd{round(grounddistance)}-{args.kmh}kmh'
    # more stuff is appended later

  print(f'Full border outline consists of {len(coords)} points')

  if (args.ccw):
    coords.reverse()

  if args.startpoint:
    args.skip = coords.index(args.startpoint)
    print(f'Moving starting point of tour forward to {args.startpoint} (polygon point #{args.skip})')

  if args.skip != 0:
    if args.skip < 0:
      # reverse
      args.skip = len(coords) + args.skip
    print(f'Moving tour starting point forward to {args.skip} point(s) into the original polygon')
    coords = coords[args.skip:] + coords[:args.skip]
    if not args.moviereel:
      name = name + f'-skip{args.skip}'

  if args.simplify != None:
    origcount = len(coords)
    # TODO make simplify dynamic based on distance
    coords = asLineString(coords).simplify(args.simplify, False).coords
    print(f'Smoothed tour from {origcount} down to {len(coords)} points')

  # calculate total runtime before trimming anything
  distanceoffsets = cumulativedistances(coords)
  totaldistance = distanceoffsets[-1]
  totalframes = distancetoframe(totaldistance) + 1 # plus one because distance 0 frame was not counted

  totalseconds = totalframes / args.framerate
  # these should be the same
  totaltotalseconds = totaltotalseconds + totalseconds
  print()
  print(f'Total runtime of the COMPLETE {round(totaldistance)}km tour at {args.kmh} km/h would be {formatruntime(totalseconds)} ({totalframes} video frames)')
  print()

  if args.split != None:
    # calculate frame offsets for the entire tour...
    frameoffsets = [ distancetoframe(distance) for distance in distanceoffsets ]
    # ...to get the indices of the first keyframes after the boundaries
    partboundarykeyframes = partboundarykeyframeindices(frameoffsets, args.nparts)
    print(f'Split tour into {len(partboundarykeyframes)-1} parts, each of length ~{args.split} video frames')
    print('Preliminary split frames:')
    print([frameoffsets[i] for i in partboundarykeyframes])

    # now cut down the coords array appropriately
    coords = coords[:partboundarykeyframes[-1] + 1]

  # return a new array containing the point itself, as well as any interleaved ones
  def interleave(prv, nxt):
    distance = greatcircledistance(prv, nxt)
    n = ceil(distance / args.altitudeevery)
    return [(prv[0] + i * (nxt[0] - prv[0]) / n, prv[1] + i * (nxt[1] - prv[1]) / n) for i in range(n)]

  interleavedcoordparts = [interleave(prv, nxt) for prv, nxt in pairwise(coords)]
  # extract the frame numbers of non-interleaved keyframes, because those will get transitions
  turningpoints = [0] + list(accumulate([len(pointsperpoint) for pointsperpoint in interleavedcoordparts]))
  # flatten, and re-add final point
  coords = [coord for part in interleavedcoordparts for coord in part] + coords[-1:]
  print(f'Tour consists of {len(coords)} keyframes after interleaving')

  distanceoffsets = cumulativedistances(coords)
  nframes, frameoffsets = distancestoframe(distanceoffsets)

  # calculate bearings based on interleaved points in case we throw them away for the moviereel
  if args.moviereel:
    print(f'Creating movie reel of {args.moviereel} (key)frames')
    reelkeyframes = [round(len(coords) * i / args.moviereel) for i in range(args.moviereel)]
    # calculate reverse bearing into the frames (that's the one we want to move towards anyway)
    bearings = [ getbearing(coords[i+1], coords[i]) for i in reelkeyframes ]
    # truncate and mock the offsets
    coords = [ coords[k] for k in reelkeyframes ]
    nframes = args.moviereel
    frameoffsets = list(range(args.moviereel))
  elif args.esp:
    # anticipate bearing of future points by moving off the line
    # to be facing the point, the camera needs to be offset AGAINST the bearing (add pi)
    bearings = [ pi + getbearing(cur, nxt) for cur, nxt in pairwise(coords) ]
    # duplicate first bearing
    bearings = bearings[:1] + bearings

  # store the quantized information in some formats
#  framesbefore = [0] + [ nxt - prv for prv, nxt in pairwise(frameoffsets) ]
#  framesafter = framesbefore[1:] + [0]
#  relativeoffsets = [ offset / nframes for offset in frameoffsets ]
#  timebefore = [0] + [ nxt - prv for prv, nxt in pairwise(relativeoffsets) ]
#  timeafter = timebefore[1:] + [0]

  print(f'~{round(distanceoffsets[-1])} km at {args.kmh} km/h: total runtime of {nframes} frames ({formatruntime(nframes / args.framerate)}), 1 keyframe every ~{round(nframes/len(coords))} frames ({round(nframes/(len(coords)*args.framerate))} seconds)')

  if args.esp:
    print(f'Querying {len(coords)} ground altitudes')
    altitudes = [ getreliablealtitude(lon, lat) for (lon, lat) in coords ]
  # TODO actually should window over the thing...
#  slopes = [ (nxt - prv) / (1000*distance) for (prv, nxt), distance in zip(pairwise(altitudes), distances) ]

    longitudes = [ el[0] for el in coords ]
    latitudes = [ el[1] for el in coords ]

    longitudePOI = [ .2442333785617368 + longitude * .1221167/90 for longitude in longitudes ]
    latitudePOI = [ gelatitude(latitude) for latitude in latitudes ]
    altitudePOI = [ gealtitude(altitude) for altitude in altitudes ]

  # lon/lat to degrees: outcome 0 = north, going clockwise!
#  def getheading(fr, to):
#    return (degrees(atan2(to[0] - fr[0], to[1] - fr[1])) + 360) % 360
  # watch out: 0 degrees is NORTH!
#  headings = [ radians((90 - getheading(cur, nxt)) % 360) for cur, nxt in pairwise(coords) ]
#  headings = headings + headings[-1:]
  # FIXME also need to account for latitude here when adding the heading...
#  dxs = [ cos(heading) for heading in headings ]
#  dys = [ -sin(heading) for heading in headings ]
#  onedegree = 40075000 / 360 # equator in meters
  # camlongitudes = [ longitude + grounddistance * dx * cos(latitude) / onedegree for longitude, latitude, dx in zip(longitudes, latitudes, dxs) ]
  # camlatitudes = [ latitude + grounddistance * dy / onedegree for latitude, dy in zip(latitudes, dys) ]

    # equivalent angular distance of the ground distance (in m)
    Ad = grounddistance / 6371000

    if False:
      # stay on border line (together with easing this will lead to corner cuts) at grounddistance away
      # TODO add a straight-bearing line backwards!
      initialbearing = getbearing([longitudes[0], latitudes[0]], [longitudes[1], latitudes[1]])
      # 0 is north
      backprojection = [ longitudes[0] - sin(initialbearing), latitudes[0] - cos(initialbearing) ]
#      print(initialbearing)
#      print(getbearing(backprojection, [longitudes[0], latitudes[0]]))
      withprepoint = [backprojection] + list(zip(longitudes, latitudes))
      def backpoint(i):
        # https://shapely.readthedocs.io/en/stable/manual.html#shapely.ops.nearest_points on circle + line (circles will be highly inaccurate closer to the poles!)
#        return nearest_points(Point(longitudes[i], latitudes[i]).buffer(Ad).exterior, LineString(withprepoint[max(0, i-10):(i+2)]))[0]
        return Point(longitudes[i], latitudes[i]).buffer(20*Ad).exterior.intersection(LineString(withprepoint[max(0, i-10):(i+2)]))
        # alternatively: object.intersection(other) but make sure the other is a line, not a polygon!

      camlongitudes, camlatitudes = zip(*[ backpoint(i).coords[0] for i in range(len(longitudes)) ])
      print(greatcircledistance([longitudes[0], latitudes[0]], [camlongitudes[0], camlatitudes[0]]))
    else:
      # second part of https://www.igismap.com/formula-to-find-bearing-or-heading-angle-between-two-points-latitude-longitude/
      camlatitudes = [ degrees(asin(sin(radians(lat)) * cos(Ad) + cos(radians(lat)) * sin(Ad) * cos(b))) for lon, lat, b in zip(longitudes, latitudes, bearings) ]
      camlongitudes = [ lon + degrees(atan2(sin(b) * sin(Ad) * cos(radians(lat)), cos(Ad) - sin(radians(lat)) * sin(radians(lat2)))) for lon, lat, lat2, b in zip(longitudes, latitudes, camlatitudes, bearings) ]

    longitude = [ gecamlongitude(longitude) for longitude in camlongitudes ]
    # , easeout = { 'type': 'easeOut', 'influence': .4 } if time == 0 else None
    latitude = [ gelatitude(latitude) for latitude in camlatitudes ]
    print(f'Querying {len(camlongitudes)} camera altitudes')
    camaltitudes = [ getreliablealtitude(longitude, latitude) for longitude, latitude in zip(camlongitudes, camlatitudes) ] 
    if not args.moviereel:
      # smooth that shit
      camaltitudes = camaltitudes[:1] + [ (one + two + three ) / 3 for one, two, three in windowed(camaltitudes, 3) ] + camaltitudes[-1:]

    # instead of getting altitude information about the camera position to avoid going into the ground, just rotate according to the slope
    # and perform some smoothing
    altitudeeasein = { 'x': -1, 'y': 0, 'influence': .4, 'type': 'auto' }
    altitudeeaseout = { 'x': 1, 'y': 0, 'influence': .4, 'type': 'auto' }
  #  altitude = [ keyframe(time, (altitude + grounddistance * -slope + verticaldistance) * 1.535686e-08, altitudeeasein, altitudeeaseout) for time, altitude, slope in zip(relativeoffsets, altitudes, slopes) ]
    # TODO add , altitudeeasein, altitudeeaseout)
    altitude = [ gealtitude(altitude + verticaldistance) for altitude in camaltitudes ]
    cache.close()

    # add POI
    # 0 longitude = 4x18.69deg, +.1 = ??
    # exported:
    # 0x0deg = .2442333785617368
    # 0x90deg = .3663500678426052
    # 0x180deg = .4884667571234736
    # => +.1221167 = +90deg
#    points['attributes'][0]['attributes'][0]['attributes'][0]['keyframes'].append(keyframe(time, .2442333785617368 + longitude * .1221167/90))
#    points['attributes'][0]['attributes'][0]['attributes'][1]['keyframes'].append(keyframe(time, gelatitude(latitude)))
    # redundant altitude information
#    points['attributes'][0]['attributes'][0]['attributes'][2]['keyframes'].append(keyframe(time, 1, 'linear'))
    # camera heading is in degrees, with 0 = north, going clockwise


    # cameraheading 0 means north, going clockwise
#    heading = radians((90 - cameraheading) % 360)
#    dx = cos(heading)
#    dy = -sin(heading)
#    onedegree = 40075000 / 360 # equator in meters
#    longitude = longitude + grounddistance * dx * cos(latitude) / onedegree
#    latitude = latitude + grounddistance * dy / onedegree
#    print(f'translating heading {cameraheading} to {(90 - cameraheading) % 360}: put camera {grounddistance*dx} ({grounddistance * dx * cos(latitude) / onedegree} deg) east, {grounddistance * dy} ({-grounddistance * dy / onedegree} deg) north')

    # 0 longitude = -180deg, +.1 = +73.7deg
    # NO, rather:
    # 0x-1deg = 0.5777203046845393
    # 0x89deg = 0.6037567730979636
    # 0x179deg = 0.6297932414922371
    # => .5780096 = 0x0deg longitude, +.02603647 = +90deg
#    points['attributes'][1]['attributes'][0]['keyframes'].append(keyframe(time, .5780096 + longitude * .02603647/90, easeinfluence))
#    points['attributes'][1]['attributes'][1]['keyframes'].append(keyframe(time, gelatitude(latitude), easeinfluence))
    # redundant
#    points['attributes'][1]['attributes'][2]['keyframes'].append(keyframe(time, i/1000)) # just for testing
    # altitude: verticaldistance = 0 = 1m, +1.535686e-08 = +1m
    #1m: 0
    #10m: 1.3821173669497038E-7
    #100m: 0.0000015203291036446741
    #1000m: 0.00001534157092662743
    #10000m: 0.0001535532394681121

#  for i in range(len(coords)-1):
#    cur = coords[i]
#    nxt = coords[i+1]
#    heading = getheading(cur, nxt)
#    print(f'degree diff is ({nxt[0]-cur[0]},{nxt[1]-cur[1]})')
    # TODO calculate easing based on distance to neighbouring points -- transition out should be LONG, transition in short/low coverage
    # easing now does INFLUENCE (proportion of time between keyframes)
#    easeinfluence = None if i == 0 else -args.easein / (secondoffsets[i] - secondoffsets[i-1])
    # TODO calculate x and y of the next shift along that particular dimension....
    #x=1
    #y=diff of the next thing
#    addpoint(frameoffsets[i], cur[0], cur[1], heading, easeinfluence)

  # TODO update first point to have auto transitionOut on latitude and longitude

  def attribute(name, attributesOrKeyframes = None, mn = None, mx = None, rel = None, keyframes = False):
    a = {
      'type': name,
      'visible': True
    }
    if mn != None:
#      a['visible'] = True
      a['value'] = {
        'maxValueRange': mx,
        'minValueRange': mn
      }
      if rel != None:
        a['value']['relative'] = rel

    if attributesOrKeyframes != None:
      if keyframes:
        a['keyframes'] = attributesOrKeyframes
      else:
        a['attributes'] = attributesOrKeyframes

      if mn != None:
        a['attributesLocked'] = True
    return a

  # rejiggle split boundaries
  if args.split == None:
    splitboundaries = [0, len(frameoffsets)-1]
    npartsmagnitude = 1
  else:
    npartsmagnitude = ceil(log10(totalframes / args.split))
    name = name + f'by{args.split}'

    # FIXME check where the turningpoints are, DON'T split there (because it makes the easing through those points messy if they are at the end/beginning of videos)
    splitboundaries = partboundarykeyframeindices(frameoffsets, args.nparts) # this might shave off a couple more frames
    print(f'Split {nframes} frames into {len(splitboundaries) - 1} parts of length ~{args.split} each')

  splitboundaryframes = [ frameoffsets[keyframe] for keyframe in splitboundaries ]

  partstarts = splitboundaryframes[:-1]
  partends = splitboundaryframes[1:]
  partdurations = [ end - start for start, end in zip(partstarts, partends) ]

  size = [ args.width, round(args.width * 9 / 16) ]

  # zfill does same as {args.frompart + n:0{npartsmagnitude}d}#
#  partnames = [f'{name}pt{args.frompart + n+1}' for n, (startkeyframe, endkeyframe) in enumerate(pairwise(splitboundaries))]
  if args.moviereel:
    partnames = [ f'{name}-reel{args.moviereel}' ]
    script = Path('reel.sh').read_text(encoding='utf-8')
    with open(f'{name}reel.sh', 'w') as f:
      os.fchmod(f.fileno(), 0o744)
      f.write(script.format(fullname=fullname, name=name, runtime=formatruntime(totalseconds), size=size))

  else:
    # args.frompart is at least 1 so counting starts at 1
    partnames = [ f'{name}pt{str(args.frompart + n).zfill(npartsmagnitude)}' for n in range(len(splitboundaries) - 1) ]

  if args.esp:
    for partname, partduration, (startkeyframe, endkeyframe) in zip(partnames, partdurations, pairwise(splitboundaries)):
      start = frameoffsets[startkeyframe]
      end = frameoffsets[endkeyframe]
      print(f'Writing {partname}.esp (keyframe interval [{startkeyframe},{endkeyframe}], frame interval [{start},{end}]):')

      relativeoffsets = [ (offset - start) / partduration for offset in frameoffsets[startkeyframe:(endkeyframe + 1)] ]
      with open(f'data/{partname}.esp', 'w') as esp:
        json.dump({
          'modelVersion': 16,
          'settings': {
            'name': partname,
            'frameRate': args.framerate,
            'dimensions': {
              'width': size[0],
              'height': size[1]
            },
            'timeFormat': 'frames',
            'duration': partduration
          },
          'scenes': [
            {
              'animationModel': {
                'roving': False,
                'logarithmic': False,
                'groupedPosition': True
              },
              'duration': partduration,
              'attributes': [
                attribute('cameraGroup', [ # root element: has 3 attributes
                  attribute('cameraPositionGroup', [ # [0] has 3 keyframed attributes: longitude, latitude, altitude
                    attribute('longitude', list(map(keyframe, relativeoffsets, longitude[startkeyframe:(endkeyframe + 1)])), -1998, 1458.69, 0.6297932414922371, True),
                    attribute('latitude', list(map(keyframe, relativeoffsets, latitude[startkeyframe:(endkeyframe + 1)])), -89.9999, 89.9999, 0.4999999999401562, True),
                    # set constant altitude 300 is apparently 65117km, .000005484633 is 358m (logarithmic??) TODO put verticaldistance in here
                    # altitude: 1.535686e-08 = 1m
                    attribute('altitude', list(map(keyframe, relativeoffsets, altitude[startkeyframe:(endkeyframe + 1)])), 1, 65117481, 0.00001534157092662743, True),
                  ], 0, 71488366.22893658, 0),
                  attribute('cameraRotationGroup', [ # [1] has 2 attributes: rotationX, rotationY -- which will be ignored because of POI tracking
                    attribute('rotationX', [], 360, 0, 0.2499999987854837, True),
                    attribute('rotationY', [], 180, 0, 0.49436059161033025, True)
                  ]), # those are not truely keyframed
                  attribute('cameraTargetEffect', [ # [2] has has 2 attributes: poi and influence
                    attribute('poi', [ # [0][0] has 3 keyframed attributes: longitudePOI, latitudePOI, altitudePOI
                      attribute('longitudePOI', list(map(keyframe, relativeoffsets, longitudePOI[startkeyframe:(endkeyframe + 1)])), -180, 556.9999999999999, 0.4884667571234736, True),
                      attribute('latitudePOI', list(map(keyframe, relativeoffsets, latitudePOI[startkeyframe:(endkeyframe + 1)])), -89.9999, 89.9999, keyframes=True),
                      attribute('altitudePOI', list(map(keyframe, relativeoffsets, altitudePOI[startkeyframe:(endkeyframe + 1)])), 0, 65117481, 0, True),
                    ], -6371022.11950216, 71488366.22893658, 0),
                    attribute('influence', None, 0, 1)
                  ]),
                ]),
                {
                  "type": "environmentGroup",
                  "attributes": [
                    {
                      "type": "planet",
                      "value": {
                        "world": "earth"
                      },
                      "visible": True
                    } # TODO add "clouddate" type?
                  ]
                }
              ]
            }
          ],
          'playbackManager': {
            'range': {
              'start': 0,
              'end': partduration
            }
          }
        }, esp)

  if args.sh:
    print(f'Writing {filename}.sh')

    intro = [
      # format: filename duration (None is replaced by black screen, args.fade duration is added on either side)
      [None, .5], # be-a: 2
      ['0', 1], # be-a: 3
      [None, .5], # be-a: 1.5
      ['1', 0], # be-a: 2
      ['2', 2], # be-a: 2
      [None, .5] # be-a: 1.5
    ]

    def intropart(file, duration):
      if file == None:
        return f'-f lavfi -i "color=c=black:size={"x".join(map(str, size))}:duration={duration + 2 * args.fade}:r={args.videoframerate},format=yuv420p"'
      else:
        return f'-loop 1 -t {duration + 2*args.fade} -i "frontmatter/{name}{file}.$EXT"'

    introframes = " ".join([ intropart(file, duration) for (file, duration) in intro ])

    def crossfade(i, offset):
      return f'[o{i}][{i+1}]xfade=offset={offset}:duration={args.fade},format=yuv420p[o{i+1}]'

    offsets = list(accumulate([el[1] for el in intro ]))
    # complete file fades to black (for 1 full second)
    filters = [f'[0]format=yuv420p[o0]'] + [crossfade(i, offsets[i] + i * args.fade) for i in range(len(intro)-1)]
    filters = ";".join(filters + [f'[o{len(intro)-1}]format=yuv420p']) # append final out so that the logofilter can consume it as an input

    # no need to deal with magnitudes if we use a quoted '*' (all in-file now)
    # https://en.wikibooks.org/wiki/FFMPEG_An_Intermediate_Guide/image_sequence#Quote_the_glob_pattern

    # TODO the partduration (and thus magnitude) IS actually possibly different for different parts, so encode this somehow?
#    magnitude = ceil(log10(partduration))
#    frameinputpattern = f'/Volumes/Films/border/{partname}/footage/{partname}_%0{magnitude}d.jpeg'
    # http://ffmpeg.org/ffmpeg-all.html#blend-1
    # TODO figure out watermark opacity first: https://im.snibgo.com/watermark.htm#deriv

    script = Path('tour.sh').read_text(encoding='utf-8')
    with open(filename + '.sh', 'w') as f:
      os.fchmod(f.fileno(), 0o744)
      f.write(script.format(fullname=fullname, kmh=args.kmh, name=name, framerate=args.framerate, videoframerate=args.videoframerate, introframes=introframes, introfilter=filters, runtime=formatruntime(totalseconds), size=size, args=args.video + args.container, firstpart=args.frompart))

