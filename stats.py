#!/usr/local/bin/python3.6

from functools import reduce
from more_itertools import pairwise
from os.path import basename, splitext
import re

import argparse

import geojson
from pycountry import countries
from great_circle_calculator.great_circle_calculator import distance_between_points as gcdistance

argparser = argparse.ArgumentParser(description='generate some information about (multi)polygons from geojson files')
argparser.add_argument('file', nargs='*', help='geojson file(s)')
argparser.add_argument('-parts', action='store_true', help='write one line per part, not just one line per administrative body')
argparser.add_argument('-summary', action='store_true', help='display aggregate information about each borders largest polygon')

import percache
cache = percache.Cache('borderstatscache')

# in km
def ringlength(coords):
  return sum([ gcdistance(pt1, pt2, 'kilometers') for pt1, pt2 in pairwise(coords + coords[:1]) ])

# returns an array of tuples, where the first element is the length of a part and the second an array of holes in it (again respectively their length)
def getpartsandholes(coords):
  if isinstance(coords[0][0], list):
    # multipolygon
    outer, *holes = coords
    return (ringlength(outer), [ ringlength(hole) for hole in holes ])
  else:
    return (ringlength(coords), [])

@cache
def getpartsandholesfromfile(filename):
  with open(filename) as f:
    fts = geojson.load(f).features
    name = fts[0]['properties']['geocoding']['name'] if 'geocoding' in fts[0]['properties'] else filename
    if len(fts) > 1:
      print(f"More than one feature in {name} result!?")
    return [ getpartsandholes(pt) for pt in fts[0].geometry.coordinates ]

def getpartsandholesfromcountry(filename):
  name = splitext(basename(filename))[0]
  fullname = name
  iso = re.search(r'[A-Z]{3}', name)
  if iso:
    fullname = countries.get(alpha_3=iso.group(0))
    fullname = (fullname.name or fullname.official_name).replace("'", "\\'") if fullname else filename
  return (fullname, getpartsandholesfromfile(filename))

args = argparser.parse_args()

allstats = { key:value for (key, value) in [ getpartsandholesfromcountry(filename) for filename in args.file] }
longestouterring = [ max([ part[0] for part in parts ]) for parts in allstats.values() ]
if args.summary:
  print(f'{len(allstats)} borders, total length of each parts longest outer ring is {round(sum(longestouterring), 2)}, ranging from {round(min(longestouterring), 2)} to {round(max(longestouterring), 2)}')
else:
  for (name, parts) in allstats.items():
    # 1. name 2. number of parts 3. number of holes 4. total length of all outer rings 5. length of longest outer ring
  #  print(f'{name}: {len(parts)} part(s) with a total length of {round(sum(part[0] for part in parts))}km (with {sum([len(part[1]) for part in parts])} holes in it), single longest part is {round(max([part[0] for part in parts]))}km long')
    print(f'{name};{len(parts)};{sum([ len(part[1]) for part in parts ])};{round(sum(part[0] for part in parts), 2)};{round(max([ part[0] for part in parts ]), 2)}')
