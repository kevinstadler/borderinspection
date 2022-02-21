#!/usr/bin/env python3

from math import ceil, log, sqrt

import chevron

import argparse
argparser = argparse.ArgumentParser(description='make the html site')
argparser.add_argument('file', nargs='+', help='landuse json file(s)')
argparser.add_argument('-pxperkm', type=float, default=0.25, help='pixelly pixels')
argparser.add_argument('-minpx', type=int, default=2, help='minimal required pixels for a landuse segment to be output')
argparser.add_argument('-template', default="horizontal", help='.html, .css and .js files to include')
args = argparser.parse_args()

import json

igbp = {
1: "Evergreen Needleleaf Forest",
2: "Evergreen Broadleaf Forest",
3: "Deciduous Needleleaf Forest",
4: "Deciduous Broadleaf Forest",
5: "Mixed Forest",
6: "Closed Shrublands",
7: "Open Shrublands",
8: "Woody Savannas",
9: "Savannas",
10: "Grasslands",
11: "Permanent Wetlands",
12: "Croplands",
13: "Urban and Built-Up Land",
14: "Cropland/Natural Vegetation Mosaic",
15: "Snow and Ice",
16: "Barren Land", #or Sparsely Vegetated Land",
17: "Sea water",
18: "Inland water",
100: "unknown landuse"
}
igbp = dict((k, v.lower()) for k, v in igbp.items() )

def getlanduse(i):
  try:
    return igbp[i]
  except KeyError:
    return "unknown landuse"

def preparepart(country, part):
  startpx = 0
  startdist = 0
  lastpoint = part[0]
  lastpx = ceil(part[0]['dist'] * args.pxperkm)
  pixellated = []
  # first point never leads to writeout, but last one needs to trigger twice
  for point in part[1:] + [ part[-1] ]:

    nextpx = ceil(point['dist'] * args.pxperkm)
    if point != part[-1]:
      # don't render if too short to be worth rendering
      if nextpx < lastpx + args.minpx:
        continue

      # if the new landuse is the same as the preceding they need to be merged...
      if point["use"] == lastpoint["use"]:
        lastpx = nextpx
        lastpoint = point
        continue

    # else: new landuse (or last part), so write it out (until lastpoint)
    size = max(args.minpx, lastpx - startpx)
    attributes = f'class="i{lastpoint["use"]}' + (f' h{size}"' if size < 10 else f'" style="width: {size}px"')
    # calculate midpoint + zoom level that can show both points
    # FIXME need to incorporate startpoint for this!
    tilewidth = max(.00001, abs(lastpoint["bbox"][0] - lastpoint["bbox"][2]), abs(lastpoint["bbox"][1] - lastpoint["bbox"][3]))
    midpoint = ( (lastpoint["bbox"][0] + lastpoint["bbox"][2]) / 2, ( lastpoint["bbox"][1] + lastpoint["bbox"][3]) / 2 )
    # assume that the screen is only as wide as one tile, then we need this zoomlevel.. if it's 2 wide, then we can multiply
    zoomlevel = ceil(log((360*2)/tilewidth) / log(2))
    dist = lastpoint['dist'] - startdist
    dist = int(dist) if dist >= 100 else round(dist, 1 if dist >= 10 else 2)
    attributes = attributes + f' data-x="{dist},{zoomlevel},{round(midpoint[1], 4)},{round(midpoint[0], 4)}"'
    pixellated.append({ 'attributes': attributes })
    startpx = lastpx
    startdist = lastpoint['dist']
    lastpx = nextpx
    lastpoint = point

  return { 'landuses': pixellated }
#   print(f"{country['name']};{len(parts)};{sum([ len(part[2]) for part in parts ])};{round(sum(part[0] for part in parts), 4)};{round(max([ part[0] for part in parts ]), 4)};{round(sum(part[1] for part in parts), 2)};{round(max([ part[1] for part in parts ]), 2)}")

def igbpstring(cat, percent):
  return f'{igbp[cat]} ({percent}%)'

def preparecountry(country):
  # compute landuse histogram
  landuse = {}
  for part in country['landuses']:
    for ring in part:
      lastdist = 0
      for entry in ring:
        landuse.update({ entry['use']: landuse.get(entry['use'], 0) + entry['dist'] - lastdist })
        lastdist = entry['dist']

  hist = list(landuse.values())
  if len(hist) == 1:
    outerlanduse = "all of it " + igbp[list(landuse.keys())[0]]
  else:
    total = sum(hist)
    prevalence = sorted(landuse.items(), key=lambda x: x[1], reverse=True)
    outerlanduse = igbpstring(prevalence[0][0], round(100*prevalence[0][1]/total)) + " and " + igbpstring(prevalence[1][0], round(100*prevalence[1][1]/total))
    if len(hist) > 2:
      outerlanduse = "mainly " + outerlanduse

  misc = ''
  if False: #len(country['stats']) > 1:
    misc += 'the border is split across {{summary.nparts}} parts, ranging in their border length from MX to MIN km'
  if False:
   misc += 'the area encloses TODO enclaves within it, making up a total of TODO km of inner borders.'

  # TODO sort descending
  country['summary'] = {
    'nparts': len(country['stats']),
    'totallength': round(sum([ part['length'] for part in country['stats']]), 2),
    'totallanduse': landuse,
    'outerlanduse': outerlanduse,
    'innerlanduse': landuse,
    'misc': misc
  }
  # TODO currently outer ring (index 0) only
  country['parts'] = [ preparepart(country, landuse[0]) for landuse in country['landuses'] ]
  return country

countries = [ preparecountry(json.load(open(filename))) for filename in args.file ]

# TODO sort by short name
import pycountry
# pycountry.countries()

# name = countries.get(alpha_3=feature['properties']['tags']['ISO3166-1:alpha3'])

print(chevron.render(open(args.template + '.ms'), { 'countries': countries }))

