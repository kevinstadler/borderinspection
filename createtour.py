#!/usr/local/bin/python3.6

import argparse

import mmap
from functools import reduce
from math import radians, degrees, sin, cos, asin, acos, sqrt, atan2

import simplekml

# good combinations: tilt 0 with distance 500, tilt 55 with distance 100

argparser = argparse.ArgumentParser(description='Generate Google Earth tour(s) from boundary polygons.')
argparser.add_argument('file', nargs='*', default=['gadm36_AUT_0.kml'], help='boundary polygon .kml file(s) or list filename (.txt) to generate tour(s) for')
argparser.add_argument('--tilt', type=float, default=45, help='camera angle (0 = vertically above, 90 = parallel to horizon)')
argparser.add_argument('--distance', type=float, default=500, help='distance from the camera to the point on the ground (in m)')
argparser.add_argument('--kmh', type=float, default=20, help='animation ground speed (in km/h)')
args = argparser.parse_args()

if len(args.file) == 1 and args.file[0].endswith('.txt'):
  with open(args.file[0]) as f:
    args.file = f.read().split('\n')

print('Generating ' + str(len(args.file)) + ' tour(s)')

def greatcircledistance(p1, p2):
  lon1, lat1, lon2, lat2 = map(radians, [p1[0], p1[1], p2[0], p2[1]])
  return 6371 * acos(sin(lat1) * sin(lat2) + cos(lat1) * cos(lat2) * cos(lon1 - lon2))

def getcoords(coordstring):
  return list(map(lambda coord: list(map(float, coord.split(','))), coordstring.split(' ')))

def takelonger(currentcoords, coordbytearray):
  coords = getcoords(coordbytearray.decode())
  return coords if currentcoords == None or len(coords) > len(currentcoords) else currentcoords

coordinatestartmarker = b'<Polygon><outerBoundaryIs><LinearRing><coordinates>'
coordinateendmarker = b'</coordinates></LinearRing></outerBoundaryIs></Polygon>'

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
        print('Read polygon spec of ' + str(len(coordinatebytearray)) + ' bytes from file')
        coords = takelonger(coords, coordinatebytearray)

  print('Generating ' + str(len(coords)) + ' point tour from ' + filename + ' (longest of ' + str(npolys) + ' polygon(s))')

  # Create an instance of kml
  kml = simplekml.Kml(name='border line tour', open=1)

  # Create a tour and attach a playlist to it
  tour = kml.newgxtour(name='click here to start the tour!')
  playlist = tour.newgxplaylist()

  # Attach a gx:AnimatedUpdate to the playlist
  #animatedupdate = playlist.newgxanimatedupdate(gxduration=6.5)
  #animatedupdate.update.change = '<IconStyle targetId="{0}"><scale>10.0</scale></IconStyle>'.format(pnt.style.iconstyle.id)

  setup = playlist.newgxflyto(gxduration=3, gxflytomode='bounce')
  setup.camera.longitude = coords[0][0]
  setup.camera.latitude = coords[1][0]
  setup.camera.altitude = 5000
  setup.camera.heading = degrees(atan2(coords[1][0] - coords[0][0], coords[1][1] - coords[0][1]))
  #setup.camera.tilt = 0
  playlist.newgxwait(gxduration=2)

  def addpointtoplaylist(prev, cur):
    duration = args.kmh * greatcircledistance(prev, cur)
    if args.tilt == 0.0:
      playlist.newgxflyto(gxduration=duration, gxflytomode='smooth',
        camera=simplekml.Camera(longitude = cur[0], latitude = cur[1], altitude = args.distance, heading = degrees(atan2(cur[0] - prev[0], cur[1] - prev[1])), tilt = 0))
    else:
      playlist.newgxflyto(gxduration=duration, gxflytomode='smooth',
        lookat=simplekml.LookAt(longitude = cur[0], latitude = cur[1], range = args.distance, heading = degrees(atan2(cur[0] - prev[0], cur[1] - prev[1])), tilt = args.tilt))

    return cur
  reduce(addpointtoplaylist, coords)

  # Save to file
  kml.save(filename + '-tour.kml')
