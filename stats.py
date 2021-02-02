#!/usr/local/bin/python3.6

from functools import reduce
from more_itertools import pairwise
from operator import itemgetter
from os.path import basename, splitext
import re
import csv

import argparse

import geojson
from great_circle_calculator.great_circle_calculator import distance_between_points as gcdistance
from area import area

from countryname import countryname

argparser = argparse.ArgumentParser(description='generate some information about (multi)polygons from geojson files')
argparser.add_argument('file', nargs='*', help='geojson file(s)')
argparser.add_argument('-parts', action='store_true', default=True, help='write one line per part, not just one line per administrative body')
argparser.add_argument('-summary', action='store_true', help='display aggregate information about each borders largest polygon')

import percache
cache = percache.Cache('stats.pycache')

# in km
def ringlength(coords):
  return sum([ gcdistance(pt1, pt2, 'kilometers') for pt1, pt2 in pairwise(coords + coords[:1]) ])

def sqkm(geometry):
  return area(geometry) / 1000000

# returns an array of tuples, where the first element is the length of a part and the second an array of holes in it (again respectively their length)
def getpartsandholes(geometry):
    # multipolygon
  outer, *holes = geometry['coordinates']
  return (ringlength(outer), sqkm(geometry), [ ringlength(hole) for hole in holes ])

@cache
def getpartsandholesfromfile(filename):
  with open(filename) as f:
    fts = geojson.load(f).features
#    name = fts[0]['properties']['geocoding']['name'] if 'geocoding' in fts[0]['properties'] else filename
    if len(fts) > 1:
      print(f'More than one feature in {filename}!?')
    # parts are sorted descending based on outer ring (perimeter) length
    return { 'iso': fts[0]['properties']['tags']['ISO3166-1:alpha2'], 'name': countryname(fts[0]), 'parts': sorted([ getpartsandholes({ 'type': 'Polygon', 'coordinates': pt }) for pt in fts[0].geometry.coordinates ], key=itemgetter(0), reverse=True) }

#@cache
#def getpartsandholesfromcountry(filename):
#  name = splitext(basename(filename))[0]
#  fullname = name
#  iso = re.search(r'[A-Z]{3}', name)
#  if iso:
#    fullname = countries.get(alpha_3=iso.group(0))
#    fullname = (fullname.name or fullname.official_name).replace("'", "\\'") if fullname else filename
#  return (fullname, getpartsandholesfromfile(filename))

args = argparser.parse_args()

allstats = [ getpartsandholesfromfile(filename) for filename in args.file]

if args.summary:
  longestouterring = [ max([ part[0] for part in country['parts'] ]) for country in allstats ]
  print(f'{len(allstats)} borders, total length of each parts longest outer ring is {round(sum(longestouterring), 2)}, ranging from {round(min(longestouterring), 2)} to {round(max(longestouterring), 2)}')

else:
  if args.parts:
    print('iso;name;videos;holes;perimeter;area')
    with open('videos.csv') as f:
      videos = { iso: ids for (iso, ids) in csv.reader(f) }
  else:
    print('name;nparts;holes;totalperimeter;longestperimeter;totalarea;largestarea')

  for country in allstats:
    if args.parts:
      nameprinted = False
      try:
        video = videos[country['iso']]
      except KeyError:
        video = ''
      for part in country['parts']:
        print(f"{country['iso']};{'' if nameprinted else country['name']};{'' if nameprinted else video};{len(part[2])};{round(part[0], 4)};{round(part[1], 4)}")
        nameprinted = True
    else:
      print(f"{country['name']};{len(parts)};{sum([ len(part[2]) for part in parts ])};{round(sum(part[0] for part in parts), 4)};{round(max([ part[0] for part in parts ]), 4)};{round(sum(part[1] for part in parts), 2)};{round(max([ part[1] for part in parts ]), 2)}")
