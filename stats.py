#!/usr/local/bin/python3

from math import ceil, floor
from fractions import Fraction

from functools import reduce
from more_itertools import pairwise
from operator import itemgetter
from os.path import basename, splitext
import re
import csv

import argparse
from os import path
import percache
cache = percache.Cache('stats.pycache')

import json
import geojson
from great_circle_calculator.great_circle_calculator import distance_between_points as gcdistance
from area import area, polygon__area, ring__area
from shapely.geometry import asShape, LinearRing, LineString, Point

from PIL import Image

from countryname import countryname

argparser = argparse.ArgumentParser(description='generate some information about (multi)polygons from geojson files')
argparser.add_argument('file', nargs='+', help='geojson file(s)')
argparser.add_argument('-parts', action='store_true', help='write one line per part, not just one line per administrative body')
argparser.add_argument('-summary', action='store_true', help='display aggregate information about each borders largest polygon')

argparser.add_argument('-landuse', action='store_true', help='look up landuse data from GLCC geotiff files')

args = argparser.parse_args()

# in km
def distance(pt1, pt2):
  return gcdistance(pt1, pt2, 'kilometers')

def ringlength(coords):
  return sum([ distance(pt1, pt2) for pt1, pt2 in pairwise(coords + coords[:1]) ])

def ringsqkm(coordinates):
  return ring__area(coordinates) / 1000000
  
def polygonsqkm(coordinates):
  return polygon__area(coordinates) / 1000000
  
def sqkm(geometry):
  return area(geometry) / 1000000

def getpolygonstats(geometry):
  outer, *holes = geometry['coordinates']
  # outer polygon (border) length
  # area in sqkm
  # array of (length, sqkm) tuples, for each hole of the polygon
  return { 'length': ringlength(outer), 'fullarea': ringsqkm(outer), 'effectivearea': sqkm(geometry), 'holes': [ { 'length': ringlength(hole), 'area': ringsqkm(hole) } for hole in holes ]}

#@cache
def getpartsandholesfromfile(filename):
  print(f'\nLoading {filename}...')
  with open(filename) as f:
    fts = geojson.load(f).features
#    name = fts[0]['properties']['geocoding']['name'] if 'geocoding' in fts[0]['properties'] else filename
    if len(fts) > 1:
      raise ValueError(f'More than one feature in {filename}!?')
    # parts are sorted descending based on outer ring (perimeter) length
    parts = [{ 'type': 'Polygon', 'coordinates': pt } for pt in fts[0].geometry.coordinates ]
    stats = [ getpolygonstats(pt) for pt in parts ]
    partorder = [ i for i, pt in sorted(enumerate([s['length'] for s in stats ]), key=itemgetter(1), reverse=True) ]
    if len(partorder) > 1:
      print(f"Part order: {partorder}")
      # TODO add other (shorter) names
    return { 'info': { 'iso2': fts[0]['properties']['tags']['ISO3166-1:alpha2'], 'iso3': fts[0]['properties']['tags']['ISO3166-1:alpha3'], 'name': countryname(fts[0]), 'id': fts[0]['properties']['id'] }, 'parts': [ parts[i] for i in partorder ], 'stats': [ stats[i] for i in partorder ] }

#@cache
#def getpartsandholesfromcountry(filename):
#  name = splitext(basename(filename))[0]
#  fullname = name
#  iso = re.search(r'[A-Z]{3}', name)
#  if iso:
#    fullname = countries.get(alpha_3=iso.group(0))
#    fullname = (fullname.name or fullname.official_name).replace("'", "\\'") if fullname else filename
#  return (fullname, getpartsandholesfromfile(filename))

if args.landuse:
    Image.MAX_IMAGE_PIXELS = None
    igbp18 = Image.open('data/glccgbe20_tif/gbigbpgeo20.tif')
    bats99 = Image.open('data/glccgbe20_tif/gbbatsgeo20.tif')
    dx = Fraction(360, igbp18.width)
    dy = Fraction(-180, igbp18.height)
    def lonlattoxy(lonlat): # return the (i, j) pixel coords that the given lonlat fall into
      return (floor((lonlat[0] + 180) / dx), floor((lonlat[1] - 90) / dy)) # to achieve the same result as floor() but in an inverted axis use ceil(val - 1)

    def gethook(xy, dirs): # get the two border segments of the xy cell in the given direction out of is
      x, y = xy
      xdir, ydir = dirs
      cornerpoint = (dx * (x + max(0, xdir)) - 180, dy * (y + max(0, ydir)) + 90)
      #pc = ((0.5 + xy[0])*dx - 180, (0.5 + xy[1])*dy + 90 ) # pixelcenter
      # return two line strings: the x-axis boundary of the pixel in the given direction (a vertical line)
      # the y-axis boundary of the pixel in that direction (a horizontal line)
      return (LineString([cornerpoint, (cornerpoint[0], dy * (y + max(0, ydir) - ydir) + 90)]), LineString([cornerpoint, ((dx * (x + max(0, xdir) - xdir)) - 180, cornerpoint[1])]))

    lastwater = 17
    igbpmap = { }
    def getlanduse(xy):
      # observe dateline wrapping
      xy = (xy[0] % igbp18.width, xy[1])
      # TODO prevent Pillow from loading the entire image by cropping it
      #crop = igbp18.crop((x, y, x+1, y+1))
      #print(crop)
      val = igbp18.getpixel(xy)
      if val != 17:
        return val
      # if it's igbp water (17), map bats inland (14) and sea (15) onto 18 and 17 respectively
      water = bats99.getpixel(xy)
      # if bats doesn't think the pixel is water at all, just return the last water value that we got from it before...
      global lastwater
      if water == 14 or water == 15:
        lastwater = 32 - water
      return lastwater
  
    def getpointinfo(lonlat, landuse = True):
      xy = lonlattoxy(lonlat)
      if landuse:
        return (xy, getlanduse(xy))
      else:
        return xy

    def getlanduses(ring, targetlength):
        totaldist = ringlength(ring)
        cumdist = 0
        lastxy, curlanduse = getpointinfo(ring[0])
        # prev can be either a vertex of the border, or a pixel cutting point we found somewhere?
        curlandusesegment = [ ring[0] ]
        landuse = []
        global lastwater
        lastwater = 17
        for vertex in ring:
          xy = lonlattoxy(vertex)
          if xy == lastxy:
            # vertex doesn't cross pixel boundary, just add to segment and move on to next
            cumdist += distance(curlandusesegment[-1], vertex)
            curlandusesegment.append(vertex)
            continue

          # else: find boundaries between prev and current vertex (might be multiple)
          segment = LineString([curlandusesegment[-1], vertex])
          longaxis = 0 if abs(xy[0] - lastxy[0]) >= abs(xy[1] - lastxy[1]) else 1 # 0 = x, 1 = y
          shortaxis = (longaxis + 1) % 2
          dirs = [ sign(xy[i] - lastxy[i]) for i in range(2) ] # -1, 0, 1
          mockdirs = [ 1 if dir == 0 else dir for dir in dirs ] # -1, 1
          for i in range(lastxy[longaxis], xy[longaxis] + mockdirs[longaxis], mockdirs[longaxis]):
            covered = False
            for j in range(lastxy[shortaxis], xy[shortaxis] + mockdirs[shortaxis], mockdirs[shortaxis]):
              # check intersect with a hook in the corner of where we're going
              hooks = gethook((i, j) if longaxis == 0 else (j, i), mockdirs)
              # FIXME gotta check TOUCHES first
              intersections = [ segment.intersection(hook) for hook in hooks ]
              try:
                point = next(( p for p in intersections if not p.is_empty ))
              except StopIteration:
                if segment.touches(hooks[0]) or segment.touches(hooks[1]):
                  raise ValueError("Two segments don't intersect, but they do touch?")
                if covered:
                  # last one intersected but this one didn't, so increment outer loop
                  break
                else:
                  # no intersection, just carry on...
                  continue

              covered = True
              point = point.coords[0]
              cumdist += distance(curlandusesegment[-1], point)
              curlandusesegment.append(point)
              # get landuse of next entered cell
              intdirs = [ 0 if intersection.is_empty else 1 for intersection in intersections ]
              if intdirs[0] == intdirs[1]: # FIXME check these here, if everything is correct...
                print(f"Intersects on both axes: {intersections[0]}, {intersections[1]}")
              lastxy = (lastxy[0] + dirs[0]*intdirs[0], lastxy[1] + dirs[1]*intdirs[1])
              nextlanduse = getlanduse(lastxy)
              if nextlanduse != curlanduse:
                landuse.append(segmentinfo(cumdist, curlanduse, curlandusesegment))
                curlanduse = nextlanduse
                curlandusesegment = curlandusesegment[-1:]
              if lastxy == xy:
                break # second loop will be broken just below
            if lastxy == xy:
              break
            if not covered:
              print(f'\n{lastxy} + {dirs} ({mockdirs}) -> {xy} (long axis={"x" if longaxis == 0 else "y"}), now at {lastxy} -> {xy}')
              print(list(segment.coords))
              print(list(hooks[0].coords))
              print(list(hooks[1].coords))
              raise ValueError("NOT COVERED??")

          cumdist += distance(curlandusesegment[-1], vertex)
          curlandusesegment.append(vertex)
        # just round it off at the end (final point)
        landuse.append(segmentinfo(cumdist, curlanduse, curlandusesegment))
        diff = round(1000 * (cumdist - targetlength), 2) # .01m = 1cm threshold
        if diff != 0:
          print(f"Ringlength along linearly computed landuse points is {diff} m longer than the exact great circle length of {round(targetlength, 3)} km")
        return landuse

def sign(a): # returns -1, 0 and 1
  return (a > 0) - (a < 0)

def roundall(xs, d = 3):
  return [ round(x, d) for x in xs ]

def segmentinfo(cumdist, curlanduse, curlandusesegment):
  return { 'dist': round(cumdist, 3), 'use': curlanduse, 'to': roundall(curlandusesegment[-1], 4), 'bbox': roundall(LineString(curlandusesegment).bounds) }

with open("data/summary.csv", 'w') as summary:
  for filename in args.file:

    country = getpartsandholesfromfile(filename)
    if args.summary:
      longestouterring = [ max([ part[0] for part in country['parts'] ]) for country in allstats ]
      print(f'{len(allstats)} borders, total length of each parts longest outer ring is {round(sum(longestouterring), 3)}, ranging from {round(min(longestouterring), 3)} to {round(max(longestouterring), 3)}')

    runlanduse = False
    if args.landuse:
      landusefile = f'data/landuse/{country["info"]["iso3"]}.json'
      if path.exists(landusefile):
        print("Landuse file already exists, skipping")
      else:
        runlanduse = True
        print("Computing landuse...")
        landuses = []

    if runlanduse or False: # ...
      try:
        for n, (part, stats) in enumerate(zip(country['parts'], country['stats'])):
          if len(country['parts']) > 1:
            print(f"Part {n+1}/{len(country['parts'])}...")
          #print(f"\n\n{len(part['holes'])};{round(part['length'], 4)};{round(part['effectivearea'], 4)}")
          if runlanduse:
            if len(part['coordinates']) > 1:
              print(f"Finding landuse of outer border and {len(part['coordinates'])-1} hole(s)")
            # add one (array) element for the whole part, containing landuse of outer ring AND holes (if any)
            landuses.append([ getlanduses(ring, stat['length']) for ring, stat in zip(part['coordinates'], [stats] + stats['holes']) ])

        with open(landusefile, 'w') as out:
          json.dump({ 'info': country['info'], 'stats': country['stats'], 'landuses': landuses }, out)
      except ValueError:
        print("Some point wasn't covered, continueing with next country...")
