#!/usr/local/bin/python3.6

import argparse

import re
import mmap
from itertools import accumulate
from more_itertools import pairwise, windowed
from math import acos, atan, atan2, ceil, cos, degrees, floor, log10, radians, sin

from os.path import basename, splitext
from os import fchmod
import json
import shapely
from shapely.geometry import asLineString, LineString
from pycountry import countries

from pyproj import CRS, Transformer
proj = CRS.from_epsg(31287)
proj = Transformer.from_crs(proj.geodetic_crs, proj)

import percache
cache = percache.Cache("/tmp/my-cache")

import os
os.environ['HTTP_PROXY'] = 'http://192.168.2.2:3128'
os.environ['HTTPS_PROXY'] = 'http://192.168.2.2:3128'
import gpsinfo
layer = gpsinfo.Layer(gpsinfo.Service('http://gpsinfo.org/service_wmts/gpsinfoWMTSCapabilities.xml'), 'AT_OGD_DHM_LAMB_10M_ELEVATION_COMPRESSED')

# projection coordinates
@cache
def getaltitude(lon, lat):
  return layer.value('interpolate', lon, lat)

import mapbox
import mercantile
altitudeprovider = mapbox.Maps(access_token="")
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

# cellmoves = [
#   [-30, 0],
#   [0, 30],
#   [30, 0],
#   [30, 0],
#   [-30, 0],
#   [-30, 0],
#   [0, -30],
#   [0, -30],
#   [30, 0],
#   # repeat, but MORE of each!
# ]
last = None
# geodesic coordinates
def getreliablealtitude(lon, lat):
#  mbaltitude = getmapboxaltitude(lon, lat)
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
#  while True:
    # incrementally walk:
    # 1. up one
    # 2. right one
    # 3. down one
    # 4. down one
    # 5. left one
    # 6. left one
    # 7. up one
    # 8. up one
    # then iterate...outwards??
#    lon = lon + 1#cellmoves[cell % 8][0]
#    lat = lat + cellmoves[cell % 8][1]
#    cell = cell + 1

# good combinations: tilt 0 with distance 500 at 20kmh for vertical trace, tilt 65 with distance 200 and 10-15kmh for 'walking' (but enters ground sometimes)

argparser = argparse.ArgumentParser(description='Generate Google Earth tour(s) from boundary polygons.')
argparser.add_argument('file', nargs='*', default=['AUT.kmz'], help='boundary polygon .kml file(s) or list filename (.txt) to generate tour(s) for')

argparser.add_argument('--width', type=int, default=1280, help='rendered image width (aspect ratio is fixed at 16:9)')
argparser.add_argument('--framerate', type=int, default=25, help='framerate (one of 24, 25 or 60)')

# first render with 75/500 means 130above, 482 behind
# second render with 65/500 means 211 above, 453 behind
argparser.add_argument('--tilt', type=float, default=50, help='camera angle (0 = vertically above, 90 = parallel to horizon)')
argparser.add_argument('--distance', type=float, default=700, help='distance from the camera to the targeted point on the ground (in m)')
argparser.add_argument('--kmh', type=float, default=70, help='animation ground speed (in km/h)')
argparser.add_argument('--simplify', type=float, default=.00025, help='polygon simplification tolerance')
argparser.add_argument('--ccw', '--left', action='store_true', help='whether the surrounded polygon should be to the left of the tour (default is clockwise, polygon to the right)')
argparser.add_argument('--altitudeevery', type=float, default=.2, help='how often altitude should be sampled (in km)')

argparser.add_argument('--nkeyframes', type=int, help='only include the first points of the polygon')
argparser.add_argument('--nframes', type=int, help='only include points that make up to this number of video frames')
argparser.add_argument('--chunks', type=int, help='split tour into chunks of up to this many video frames')
#argparser.add_argument('--easein', type=float, default=1, help='in seconds (per 90 degrees maybe?)')

argparser.add_argument('--scripts', action='store_true', help='generate a ffmpeg concat demuxer playlist file and bash script for invoking the encoder')
argparser.add_argument('--fade', type=float, default=1.2)
#argparser.add_argument('--audio', default='-c:a aac/libfdk_aac -profile:a aac_low -b:a 384k')
argparser.add_argument('--video', default='-pix_fmt yuv420p -c:v libx264 -profile:v high -preset slow -crf 18 -g 30 -bf 2')
argparser.add_argument('--container', default='-movflags faststart')
args = argparser.parse_args()

size = [ args.width, round(args.width * 9 / 16) ]

if len(args.file) == 1 and args.file[0].endswith('.txt'):
  with open(args.file[0]) as f:
    args.file = f.read().split('\n')

print('Generating ' + str(len(args.file)) + ' tour(s)')

def getcoords(coordstring):
  return list(map(lambda coord: list(map(float, coord.split(','))), coordstring.split(' ')))

def takelonger(currentcoords, coordbytearray):
  coords = getcoords(coordbytearray.decode())
  return coords if currentcoords == None or len(coords) > len(currentcoords) else currentcoords

coordinatestartmarker = b'<Polygon><outerBoundaryIs><LinearRing><coordinates>'
coordinateendmarker = b'</coordinates></LinearRing></outerBoundaryIs>'

for filename in args.file:
  coords = None
  with open(filename, 'r+b') as f:
    mappedfile = mmap.mmap(f.fileno(), 0)
    npolys = 0
    offset = 0
    while True:
      offset = mappedfile.find(coordinatestartmarker, offset + 1)
      if offset == -1:
        break
      else:
        npolys += 1
        end = mappedfile.find(coordinateendmarker, offset)
        mappedfile.seek(offset + len(coordinatestartmarker))
        coordinatebytearray = mappedfile.read(end - mappedfile.tell())
        print(f'Read polygon spec #{npolys}: {len(coordinatebytearray)} bytes')
        coords = takelonger(coords, coordinatebytearray)

  origcount = len(coords)
  ring = asLineString(coords)
  # TODO make simplify dynamic based on distance
  coords = ring.simplify(args.simplify, False).coords
  print(f'Smoothed longest polygon from {origcount} down to {len(coords)} points')

  # lon/lat to km
  def greatcircledistance(p1, p2):
    lon1, lat1, lon2, lat2 = map(radians, [p1[0], p1[1], p2[0], p2[1]])
    # min for overflow of approximation
    return 6371 * acos(min(1, sin(lat1) * sin(lat2) + cos(lat1) * cos(lat2) * cos(lon1 - lon2)))

  # calculate total runtime before trimming anything
  totaldistance = sum([greatcircledistance(prv, nxt) for prv, nxt in pairwise(coords)])
  # from m and km/h to seconds
  totalseconds = 60 * 60 * totaldistance / args.kmh
  totalruntime = f'{floor(totalseconds / 3600)}h {floor(totalseconds % 3600 / 60)}m {floor(totalseconds % 60)}s'
  print('Total runtime of the COMPLETE tour: ' + totalruntime)
  print()

  if args.nkeyframes != None:
    coords = coords[0:args.nkeyframes]
    print(f'Cutting tour down to the first {args.nkeyframes} points')
  # FIXME undo skipping the first (for austria)
  coords = coords[1:]

  if (args.ccw):
    coords.reverse()

  name = splitext(basename(filename))[0]
  fullname = ''
  iso = re.search(r'[A-Z]{3}', name)
  if iso:
    fullname = countries.get(alpha_3=iso.group(0))
    fullname = (fullname.official_name or fullname.name) if fullname else ''

  # return a new array containing the point itself, as well as any interleaved ones
  def interleave(prv, nxt):
    distance = greatcircledistance(prv, nxt)
    n = ceil(distance / args.altitudeevery)
    return [prv] + [(prv[0] + (nxt[0] - prv[0]) * (i+1) / n, prv[1] + (nxt[1] - prv[1]) * (i+1) / n) for i in range(n - 1)]

  coords = [interleave(prv, nxt) for prv, nxt in pairwise(coords)]
  # extract the frame numbers of non-interleaved keyframes, because those will get transitions
  turningpoints = [0] + list(accumulate([len(pointsperpoint) for pointsperpoint in coords]))
  # flatten
  coords = [coord for part in coords for coord in part]
  print(f'{len(coords)} keyframes after interleaving')

  # make some lists to be comprehended
  distances = [greatcircledistance(prv, nxt) for prv, nxt in pairwise(coords)]
  distancefromprev = [0] + distances
  distanceoffsets = list(accumulate(distancefromprev))

  # quantize distances to frames
  frameoffsets = [ round(60 * 60 * distance * args.framerate / args.kmh) for distance in distanceoffsets ]

  # truncate
  if args.nframes != None and frameoffsets[-1] > args.nframes:
    firsttoexclude = next((i for i, offset in enumerate(frameoffsets) if offset > args.nframes))
    print(f'Limiting tour to {frameoffsets[firsttoexclude-1]} frames ({firsttoexclude} interleaved keyframes)')
    coords = coords[:firsttoexclude]
    distances = distances[:firsttoexclude - 1]
    distancefromprev = distancefromprev[:firsttoexclude]
    distanceoffsets = distanceoffsets[:firsttoexclude]
    frameoffsets = frameoffsets[:firsttoexclude]
    # TODO cut turningpoints
    turningpoints = turningpoints[:next((i for i, offset in enumerate(turningpoints) if offset > args.nframes))]
#  print(turningpoints)
  nframes = frameoffsets[-1]

  # store the quantized information in some formats
  framesbefore = [0] + [ nxt - prv for prv, nxt in pairwise(frameoffsets) ]
  framesafter = framesbefore[1:] + [0]

  relativeoffsets = [ offset / nframes for offset in frameoffsets ]
  timebefore = [0] + [ nxt - prv for prv, nxt in pairwise(relativeoffsets) ]
  timeafter = timebefore[1:] + [0]

  longitudes = [ el[0] for el in coords ]
  latitudes = [ el[1] for el in coords ]
  altitudes = [ getreliablealtitude(lon, lat) + 10 for (lon, lat) in coords ]
  # TODO actually should window over the thing...
#  slopes = [ (nxt - prv) / (1000*distance) for (prv, nxt), distance in zip(pairwise(altitudes), distances) ]

  print(f'~{round(distanceoffsets[-1])} km at {args.kmh} km/h: total runtime of ~{round(nframes / (args.framerate*60*60))} hours = {nframes} frames, 1 keyframe every ~{round(nframes/len(coords))} frames ({round(nframes/(len(coords)*args.framerate))} seconds)')

  tilt = radians(90 - args.tilt)
  # this will be the camera altitude (constant above ground)
  verticaldistance = args.distance * sin(tilt)
  # this is the heading-specific distance of the camera on the ground
  grounddistance = args.distance * cos(tilt)
  print(f'at a viewer distance of {args.distance}m and tilt of {args.tilt}, the camera is {verticaldistance}m above the ground, {grounddistance}m behind the target')

  def keyframe(time, value, easein = None, easeout = None):
    return {
      'time': time,
      'value': value,
      'transitionIn': easein if easein else { 'type': 'linear' },
      'transitionOut': easeout if easeout else { 'type': 'linear' },
      'transitionLinked': True
    }

  # 0 latitude = -90deg, +.1 = +18deg, .5 latitude = 0
  def gelatitude(deg, relative = False):
    return (deg / 180) + (0 if relative else .5)

  longitudePOI = [ keyframe(time, .2442333785617368 + longitude * .1221167/90) for time, longitude in zip(relativeoffsets, longitudes) ]
  latitudePOI = [ keyframe(time, gelatitude(latitude)) for time, latitude in zip(relativeoffsets, latitudes) ]
  altitudePOI = [ keyframe(time, altitude * 1.535686e-08) for time, altitude in zip(relativeoffsets, altitudes) ]

  # lon/lat to degrees: outcome 0 = north, going clockwise!
  def getheading(fr, to):
    return (degrees(atan2(to[0] - fr[0], to[1] - fr[1])) + 360) % 360

  headings = [ radians((90 - getheading(cur, nxt)) % 360) for cur, nxt in pairwise(coords) ]
  dxs = [ cos(heading) for heading in headings ]
  dys = [ -sin(heading) for heading in headings ]
  onedegree = 40075000 / 360 # equator in meters

  camlongitudes = [ longitude + grounddistance * dx * cos(latitude) / onedegree for longitude, latitude, dx in zip(longitudes, latitudes, dxs) ]
  camlatitudes = [ latitude + grounddistance * dy / onedegree for latitude, dy in zip(latitudes, dys) ]
    # easing now does INFLUENCE (proportion of time between keyframes)
#    easeinfluence = None if i == 0 else -args.easein / (secondoffsets[i] - secondoffsets[i-1])
    # TODO calculate x and y of the next shift along that particular dimension....
  dlong = [ s - f for f, s in pairwise(longitudes) ]
  dlat = [ s - f for f, s in pairwise(latitudes) ]
  # take average delta of the two adjacent keyframes as the slope (that's the tangent of the two)

#  longslope = [ dlong[0] ] + [ (dy1/dt1 + dy2/dt2) / 2 for (dy1, dy2), (dt1, dt2) in zip(pairwise(dlong), pairwise(timeafter)) ]
#  latslope = [ dlat[0] ] + [ (dy1/dt1 + dy2/dt2) / 2 for (dy1, dy2), (dt1, dt2) in zip(pairwise(dlat), pairwise(timeafter)) ]

#  def easing(dt, dy, influence):
#    return {
#      'type': 'auto',#'easeIn',
#      'x': dt,
#      'y': dy,
#      'influence': influence
#    }

  # influence is relative to the distance to the PREVIOUS (doesn't matter what scale, unitless)
  # influences = [ 0 if approachframes == 0 else min(1, args.easein * args.framerate / approachframes) for approachframes in framesbefore ]
  # outfluences = [ 0 if approachframes == 0 else min(1, args.easein * args.framerate / approachframes) for approachframes in framesafter ]
  # # dt is about the slope of the NEXT segment
  # longeasein = [ easing(-dt, -dy*.02603647/(90*dt), influence) for dt, dy, influence in zip(timeafter, dlong, influences) ]
  # longeaseout = [ easing(dt, dy*.02603647/(90*dt), influence) for dt, dy, influence in zip(timeafter, dlong, outfluences) ]
  # lateasein = [ easing(-dt, -gelatitude(dy, True)/dt, influence) for dt, dy, influence in zip(timeafter, dlat, influences) ]
  # lateaseout = [ easing(dt, gelatitude(dy, True)/dt, influence) for dt, dy, influence in zip(timeafter, dlat, outfluences) ]

  # longitude = [ keyframe(time, .5780096 + longitude * .02603647/90) for time, longitude, easein, easeout in zip(relativeoffsets, camlongitudes, longeasein, longeaseout) ]
  # latitude = [ keyframe(time, gelatitude(latitude)) for time, latitude, easein, easeout in zip(relativeoffsets, camlatitudes, lateasein, lateaseout) ]
  # altitude = [ keyframe(time, (altitude + verticaldistance) * 1.535686e-08) for time, altitude in zip(relativeoffsets, altitudes) ]
  longitude = [ keyframe(time, .5780096 + longitude * .02603647/90) for time, longitude in zip(relativeoffsets, camlongitudes) ]
  # , easeout = { 'type': 'easeOut', 'influence': .4 } if time == 0 else None
  latitude = [ keyframe(time, gelatitude(latitude)) for time, latitude in zip(relativeoffsets, camlatitudes) ]

  camaltitudes = [ getreliablealtitude(longitude, latitude) for longitude, latitude in zip(camlongitudes, camlatitudes) ] 
  # smooth that shit
  camaltitudes = camaltitudes[:1] + [ (one + two + three ) / 3 for one, two, three in windowed(camaltitudes, 3) ] + camaltitudes[-1:]

  # instead of getting altitude information about the camera position to avoid going into the ground, just rotate according to the slope
  # and perform some smoothing
  altitudeeasein = { 'x': -1, 'y': 0, 'influence': .4, 'type': 'auto' }
  altitudeeaseout = { 'x': 1, 'y': 0, 'influence': .4, 'type': 'auto' }
#  altitude = [ keyframe(time, (altitude + grounddistance * -slope + verticaldistance) * 1.535686e-08, altitudeeasein, altitudeeaseout) for time, altitude, slope in zip(relativeoffsets, altitudes, slopes) ]
  altitude = [ keyframe(time, (altitude + verticaldistance) * 1.535686e-08, altitudeeasein, altitudeeaseout) for time, longitude, latitude, altitude in zip(relativeoffsets, camlongitudes, camlatitudes, camaltitudes) ]
  cache.close()

#  def addpoint(frameno, longitude, latitude, cameraheading, easeinfluence):
    # TODO need to look up GROUND LEVEL information!

#    time = frameno / nframes
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



  # addpoint(0, 0, 0, 0, 0)
  # addpoint(nframes/4, .1, .1, 90, 1)
  # addpoint(nframes/2, 0, .2, 180, 2)
  # addpoint(nframes*3/4, .2, .3, 270, 3)
  # addpoint(nframes, .1, .4, 0, 4)
#  addflytopoint(coords[0], prvheading, 4, 5000, 0, 'bounce')

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

#  duration = str(round(tourduration / 360, 1)) + ' hours'
#  print('Writing tour file with ' + str(npoints) + ' points, total duration ' + duration)

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

  if args.chunks != None:
    # TODO split up

  tour = {
    'modelVersion': 16,
    'settings': {
      'name': name,
      'frameRate': args.framerate,
      'dimensions': {
        'width': size[0],
        'height': size[1]
      },
      'timeFormat': 'frames',
      'duration': nframes
    },
    'scenes': [
      {
        'animationModel': {
          'roving': False,
          'logarithmic': False,
          'groupedPosition': True
        },
        'duration': nframes,
        'attributes': [
          attribute('cameraGroup', [ # root element: has 3 attributes
            attribute('cameraPositionGroup', [ # [0] has 3 keyframed attributes: longitude, latitude, altitude
              attribute('longitude', longitude, -1998, 1458.69, 0.6297932414922371, True),
              attribute('latitude', latitude, -89.9999, 89.9999, 0.4999999999401562, True),
              # set constant altitude 300 is apparently 65117km, .000005484633 is 358m (logarithmic??) TODO put verticaldistance in here
              # altitude: 1.535686e-08 = 1m
              attribute('altitude', altitude, 1, 65117481, 0.00001534157092662743, True),
            ], 0, 71488366.22893658, 0),
            attribute('cameraRotationGroup', [ # [1] has 2 attributes: rotationX, rotationY -- which will be ignored because of POI tracking
              attribute('rotationX', [], 360, 0, 0.2499999987854837, True),
              attribute('rotationY', [], 180, 0, 0.49436059161033025, True)
            ]), # those are not truely keyframed
            attribute('cameraTargetEffect', [ # [2] has has 2 attributes: poi and influence
              attribute('poi', [ # [0][0] has 3 keyframed attributes: longitudePOI, latitudePOI, altitudePOI
                attribute('longitudePOI', longitudePOI, -180, 556.9999999999999, 0.4884667571234736, True),
                attribute('latitudePOI', latitudePOI, -89.9999, 89.9999, keyframes=True),
                attribute('altitudePOI', altitudePOI, 0, 65117481, 0, True),
        #        attribute('altitudePOI', [{ 'time': 0, 'value': max(0, (verticaldistance*9/10-1)) * 1.535686e-08 }], 0, 65117481, 0),
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
        'end': nframes
      }
    }
  }

  with open('data/' + name + '.esp', 'w') as f:
    json.dump(tour, f)

  # write playlist for concat demuxer: https://trac.ffmpeg.org/wiki/Slideshow
  if args.scripts:
    print('Writing playlist...')

    intro = [
      # format: filename duration (None is replaced by black screen, args.fade duration is added on either side)
      [None, 2],
      ['0', 3],
      [None, 1.5],
      ['1', 2],
      ['2', 2],
      [None, 1.5]
    ]

    def inputfile(file, duration):
      if file == None:
        return f'-f lavfi -i "color=c=black:size={"x".join(map(str, size))}:duration={duration + 2 * args.fade}:r={args.framerate},format=yuv420p"'
      else:
        return f'-loop 1 -t {duration + 2*args.fade} -i "{name}{file}.jpeg"'

    # enumerate(intro) is not reversible my ass (alternatively: https://pypi.org/project/enumerate-reversible/)
    introframes =  [ inputfile(file, duration) for (file, duration) in intro ]

#    vfilter = ','.join([f'[{i}]xfade=offset={args.fade + intro[i][1]},duration={args.fade}' for i in reversed(range(len(intro)))])
    # insert first video and final fadeout
#    vfilter = vfilter[:3] + f'[{len(intro)}]' + vfilter[3:] + f',fade=out:{nintroframes + nframes - args.framerate}:{args.framerate}'
#    fadeframes = args.fade * args.framerate
#    def fadeinout(i, instartframe, outstartframe, length = args.fade * args.framerate):
#      return f'[{i}]fade=in:{instartframe}:{length},fade=out:{outstartframe}:{length}[o{i}]'
#    filters = [fadeinout(i, pre * args.framerate, (pre + args.fade + duration) * args.framerate) for i, (pre, file, duration) in enumerate(intro)]
    # concat the actual footage video at the end
#    filters = filters + [fadeinout(len(intro), 0, nframes - args.framerate), ''.join([f'[o{i}]' for i in range(len(intro) + 1)]) + 'concat=n=' + str(len(intro)+1)]

    # 'o' outputs are written from back to front
    def crossfade(i, offset):
#      return f'[{i}][o{i+1}]xfade=offset={intro[i][1] + args.fade}:duration={args.fade}[o{i}]'
      return f'[o{i}][{i+1}]xfade=offset={offset}:duration={args.fade}[o{i+1}]'
    offsets = list(accumulate([el[1] for el in intro ]))
    # complete file fades to black (for 1 full second)
    filters = [f'[0]format=yuv420p[o0]'] + [crossfade(i, offsets[i] + i * args.fade) for i in range(len(intro))] + [f'[o{len(intro)}]fade=out:{nframes + args.framerate * (sum([frame[1] for frame in intro]) + args.fade * len(intro))}:{args.framerate}']

#ffmpeg -loop 1 -t 6.0 -i "AUT0.jpeg" -loop 1 -t 4.0 -i "AUT1.jpeg" -loop 1 -t 4.0 -i "AUT2.jpeg" -filter_complex "[0]fade=in:25:12.5,fade=out:437.5:12.5[o0];[1]fade=in:25:12.5,fade=out:387.5:12.5[o1];[2]fade=in:25:12.5,fade=out:387.5:12.5[o2];[o0][o1][o2]concat=n=3" -r 25 -pix_fmt yuv420p -c:v libx264 -profile:v high -preset slow -crf 18 -g 30 -bf 2 out.mp4

#    with open(f'data/{name}-intro.txt', 'w') as f:
#      def writefile(filename, duration = None): # 1 / args.framerate
#        f.write(f"file '{name}{filename}.{ext}'\n")
#        if duration != None:
#          f.write('duration ' + str(duration) + '\n')
#      for frame in intro:
#        writefile(frame[0], frame[1])
#      f.write(f"file '{name}black.jpeg'")

    magnitude = ceil(log10(nframes))
    with open(f'data/{name}.txt', 'w') as f:
      for i in range(nframes):
        f.write(f"file '{name}/{name}_{str(i).zfill(magnitude)}.jpeg'\n")
      f.write(f"file '{name}/{name}_{nframes-1}.jpeg'\n")

    print('Writing shell script...')
    ext = 'jpeg' # png (even PNG24:) is somehow not recognized by ffmpeg, so do jpeg instead
    with open(name + '.sh', 'w') as f:
#      fchmod(f, 755)
      f.write('#!/bin/sh\n')
      f.write('cd data\n')
      f.write(f'convert -size {size[0]}x{size[1]} xc:black "{name}black.{ext}"\n')
      f.write(f'convert -size {size[0]}x{size[1]} xc:black -fill white -font /Library/Fonts/AmericanTypewriter.ttc -pointsize 72 -gravity center -draw "text 0,-30% \'border inspection\'" "{name}0.{ext}"\n')
      f.write(f'convert -size {size[0]}x{size[1]} xc:black -fill white -font ps:helvetica -pointsize 32 -gravity center -draw "text 0,-20% \'The {fullname}\'" "{name}1.{ext}"\n')
      f.write(f'convert "{name}1.{ext}" -fill white -font ps:helvetica -pointsize 16 -gravity center -draw "text 0,20% \'(runtime: {totalruntime})\'" "{name}2.{ext}"\n')
      f.write(f'if [ ! -d "{name}" ]; then\n')
      f.write(f'  mkdir "{name}"\n')
      f.write(f'  sshfs shared@shared.local:/Users/shared/Downloads/{name}/footage {name} || exit 1\n')
      f.write(f'fi\n')
      # xfade=fade:1:{sum([frame[1] for frame in intro]) - 1}
      f.write(f'time ffmpeg {" ".join(introframes)} -f concat -i {name}.txt -r {args.framerate} -filter_complex "{";".join(filters)}" {args.video} {args.container} "../{name}.mp4"\n')
      # encoding times for 925 frames (37 seconds of footage) = 42 second video
      # with -framerate:

    # https://www.mathpages.com/home/kmath502/kmath502.htm
    # actually, fuck loxodromes. we're only dealing with tiny deltas anyway
#    if cos(heading) == 0.0:
#      # TODO: K=0 == purely westwards
#      dlat = 0
#      dlong = .01
#    else:
#      # K = dy/dx. K=0 == purely westwards, K=inf == purely northward
#      K = sin(heading) / cos(heading) # 
#      R = 6357000 # why not 6371?
#      k = K / (R * sqrt(1 + K**2))
#      dlat = degrees(k * grounddistance)
#      # 0 at north pole, pi/2 at equator, pi at south pole
#      metriclatitude = - radians(latitude - 90)
#      kspluslat = k * grounddistance + metriclatitude # TODO should this be in degrees or radians?
#      dlong = degrees(log( sin(metriclatitude) * (1 - cos(kspluslat)) / ( sin(kspluslat) * (1 - cos(metriclatitude)) ) ) / K)
#      print(f'distance of {round(grounddistance)} in direction {round(cameraheading)} (K={K}) leads to easting: {dlong} and northing: {dlat}')
#    longitude = longitude + dlong
#    latitude = latitude + dlat