#!/usr/local/bin/python3

import argparse

import re
import mmap
from more_itertools import windowed
from math import radians, degrees, sin, cos, asin, acos, sqrt, atan2

from os.path import basename
import simplekml
import shapely
from shapely.geometry import asLineString, LineString
from pycountry import countries

# good combinations: tilt 0 with distance 500 at 20kmh for vertical trace, tilt 65 with distance 200 and 10-15kmh for 'walking' (but enters ground sometimes)

argparser = argparse.ArgumentParser(description='Generate Google Earth tour(s) from boundary polygons.')
argparser.add_argument('file', nargs='*', default=['data/AUT.kmz'], help='boundary polygon .kml file(s) or list filename (.txt) to generate tour(s) for')
argparser.add_argument('--tilt', type=float, default=90, help='camera angle (0 = vertically above, 90 = parallel to horizon)')
argparser.add_argument('--distance', type=float, default=3, help='distance from the camera to the point on the ground (in m)')
argparser.add_argument('--kmh', type=float, default=20, help='animation ground speed (in km/h)')
argparser.add_argument('--dps', type=float, default=30, help='degrees that the camera rotates per second')
argparser.add_argument('--ccw', '--left', action='store_true', help='whether the surrounded country should be to the left of the tour (default is clockwise, country to the right)')
args = argparser.parse_args()

if len(args.file) == 1 and args.file[0].endswith('.txt'):
  with open(args.file[0]) as f:
    args.file = f.read().split('\n')

print('Generating ' + str(len(args.file)) + ' tour(s)')

def greatcircledistance(p1, p2):
  lon1, lat1, lon2, lat2 = map(radians, [p1[0], p1[1], p2[0], p2[1]])
  # min for overflow of approximation
  return 6371 * acos(min(1, sin(lat1) * sin(lat2) + cos(lat1) * cos(lat2) * cos(lon1 - lon2)))

def getcoords(coordstring):
  return list(map(lambda coord: list(map(float, coord.split(','))), coordstring.split(' ')))

def takelonger(currentcoords, coordbytearray):
  coords = getcoords(coordbytearray.decode())
  return coords if currentcoords == None or len(coords) > len(currentcoords) else currentcoords

def getheading(fr, to):
  return degrees(atan2(to[0] - fr[0], to[1] - fr[1]))

def addflytopoint(point, heading, duration = None, distance = args.distance, tilt = args.tilt, mode = 'smooth'):
  playlist.newgxflyto(gxduration=duration, gxflytomode=mode,
#    camera=simplekml.Camera(longitude = nxt[0], latitude = nxt[1], altitude = distance, heading = heading, tilt = tilt))
    lookat=simplekml.LookAt(longitude = point[0], latitude = point[1], range = distance, heading = heading, tilt = tilt))

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
        print('Read polygon spec #' + str(npolys) + ': ' + str(len(coordinatebytearray)) + ' bytes')
        coords = takelonger(coords, coordinatebytearray)

  origcount = len(coords)
  ring = asLineString(coords)
  coords = ring.simplify(.00025, False).coords
  print('Smoothed longest tour from ' + str(origcount) + ' down to ' + str(len(coords)) + ' points')

  if (args.ccw):
    pass # TODO reverse array

  name = ''
  iso = re.search(r'[A-Z]{3}', basename(filename))
  if iso:
    name = countries.get(alpha_3=iso.group(0))
    name = (name.official_name or name.name) if name else ''

  kml = simplekml.Kml(name=name + ': a border tour', open=1)
  # Create a tour and attach a playlist to it
  tour = kml.newgxtour(name='click here to start the tour!')
  playlist = tour.newgxplaylist()

  # Attach a gx:AnimatedUpdate to the playlist
  #animatedupdate = playlist.newgxanimatedupdate(gxduration=6.5)
  #animatedupdate.update.change = '<IconStyle targetId="{0}"><scale>10.0</scale></IconStyle>'.format(pnt.style.iconstyle.id)

  # TODO use GxViewerOptions (streetview) for other projects: https://simplekml.readthedocs.io/en/latest/abstractviews.html#simplekml.GxViewerOptions

  prvheading = getheading(coords[0], coords[1])
  addflytopoint(coords[0], prvheading, 4, 5000, 0, 'bounce')
#  addflytopoint(coords[0], prvheading, 4)
#  playlist.newgxwait(gxduration=5)

  tourduration = 0
  for prv, cur, nxt in windowed(coords, 3):
    walktime = 60 * 60 * greatcircledistance(prv, cur) / args.kmh
    tourduration = tourduration + walktime

    heading = getheading(cur, nxt)
    rotationtime = abs(heading - prvheading) / args.dps
    if rotationtime > 0:
      rotationtime = walktime * min(1, rotationtime / walktime)
      walktime = walktime - rotationtime

    walktopoint = cur if rotationtime == 0 else LineString([prv, cur]).interpolate(walktime / (walktime + rotationtime), True).coords[0]
    # earth does NOT like 90 degree turns per second! but lower dps means having to leave the center line wayyy earlier...so might have to adjust speed along line?

    if walktime > 0:
      addflytopoint(walktopoint, prvheading, walktime)
    if rotationtime > 0:
      addflytopoint(cur, heading, rotationtime)

    prvheading = heading

  # TODO add marker point at the first polygon, label: 'the _ border (x km, tour will take y hours z minutes)'
  # TO your left: _, to your right: Austria
  duration = str(round(tourduration / 60)) + ' minutes'
  kml.newpoint(name=name + 'a border tour', description='a walk along the border, total duration ' + duration, coords=[coords[0]])
  line = kml.newlinestring(name='the border', coords=coords)
  print('Saving tour file, total duration ' + duration)

  # Save to file
  kml.save(basename(filename) + '-tour.kml')
