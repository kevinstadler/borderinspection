#!/usr/local/bin/python3.6

from functools import reduce
from itertools import zip_longest
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
argparser.add_argument('file', nargs='*', default=['data/2/AUT.geojson'], help='geojson file(s)')
argparser.add_argument('-summary', action='store_true', help="only display aggregate information about each borders largest polygon, don't write csv files")
argparser.add_argument('-parts', action='store_true', default=True, help='write all per-country parts into individual csv files')
argparser.add_argument('-out', default='web/public/data/', help='output directory (default: {default})')

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
  with open('videos.csv') as csvfile:
    videodata = list(csv.DictReader(csvfile))

  with open(f'{args.out}/data.csv', 'w') as f:
    f.write('iso;name;videos;nparts;holes;perimeter;area\n')
    for country in allstats:
      parts = country['parts'] # TODO if any of them have vids
      hasvideos = any((len(el['videos']) > 0 for el in filter(lambda row: row['iso'] == country['iso'], videodata)))
      f.write(f"{country['iso']};{country['name']};{'true' if hasvideos else ''};{len(parts)};{sum([ len(part[2]) for part in parts ])};{sum(part[0] for part in parts):.2f};{sum(part[1] for part in parts):.2f}\n")
      if args.parts:
        with open(f'{args.out}/{country["iso"]}.csv', 'w') as p:
          partinfos = filter(lambda row: row['iso'] == country['iso'], videodata)
          for (part, partinfo) in zip_longest(parts, partinfos, fillvalue={ key: '' for key in videodata[0].keys()}):
            p.write(f"{country['iso']};{partinfo['name']};{partinfo['videos']};NaN;{len(part[2])};{part[0]:.2f};{part[1]:.2f}\n")
