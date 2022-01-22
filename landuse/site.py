#!/usr/bin/env python3

from math import ceil, log, sqrt

import chevron

import argparse
argparser = argparse.ArgumentParser(description='make the html site')
argparser.add_argument('file', nargs='+', help='landuse json file(s)')
argparser.add_argument('-pxperkm', type=float, default=0.25, help='pixelly pixels')
argparser.add_argument('-template', default="horizontal", help='.html, .css and .js files to include')
args = argparser.parse_args()

import json

print('''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width">
<script async src="https://www.googletagmanager.com/gtag/js?id=UA-96498670-1"></script>
<script>
window.dataLayer = window.dataLayer || [];
function gtag(){dataLayer.push(arguments);}
gtag('js', new Date());
gtag('config', 'UA-96498670-1');
</script>
<title>border inspection: landuse</title>
<base target="_blank">''')

print(f'''<link rel="stylesheet" href="{args.template}.css">
</head>
<body>''')

with open(args.template + '.html') as f:
  print(f.read())

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
13: "Urban and Built-Up",
14: "Cropland/Natural Vegetation Mosaic",
15: "Snow and Ice",
16: "Barren or Sparsely Vegetated",
17: "Sea water",
18: "Inland water",
100: "unknown landuse"
}

def getlanduse(i):
  try:
    return igbp[i]
  except KeyError:
    return "unknown landuse"

def preparepart(country, part):
  lastdist = 0
  lastpx = 0
  lastpoint = part[-1]['to']
  pixellated = []
  for point in part:
    nextpx = round(point['dist'] * args.pxperkm)
    if lastpx + 2 > nextpx:
      continue
    # TODO check if the following landuse is the same as the preceding, in which case they need to be merged...

    size = nextpx - lastpx
    attributes = f'class="i{point["use"]}' + (f' h{size}"' if size < 10 else f'" style="width: {size}px"')
    # calculate midpoint + zoom level that can show both points
    tilewidth = max(.00001, abs(point["bbox"][0] - point["bbox"][2]), abs(point["bbox"][1] - point["bbox"][3]))
    midpoint = ( (point["bbox"][0] + point["bbox"][2]) / 2, ( point["bbox"][1] + point["bbox"][3]) / 2 )
    # assume that the screen is only as wide as one tile, then we need this zoomlevel.. if it's 2 wide, then we can multiply
    zoomlevel = ceil(log((360*2)/tilewidth) / log(2))
    attributes = attributes + f' href="{round(point["dist"] - lastdist, 2)},{country["info"]["id"]},{zoomlevel},{round(midpoint[1], 4)},{round(midpoint[0], 4)}"'
    pixellated.append({ 'attributes': attributes })
    lastpx = nextpx
    lastdist = point["dist"]
    lastpoint = point["to"]

  return { 'landuses': pixellated }
#   print(f"{country['name']};{len(parts)};{sum([ len(part[2]) for part in parts ])};{round(sum(part[0] for part in parts), 4)};{round(max([ part[0] for part in parts ]), 4)};{round(sum(part[1] for part in parts), 2)};{round(max([ part[1] for part in parts ]), 2)}")

def preparecountry(country):
  country['stats'] = { 'nparts': len(country['stats']), 'totallength': round(sum([ part['length'] for part in country['stats']]), 2) }
  # TODO currently outer ring (index 0) only
  country['parts'] = [ preparepart(country, landuse[0]) for landuse in country['landuses'] ]
  return country

for filename in args.file:
  with open(filename) as file:
    country = preparecountry(json.load(file))
    print(chevron.render(open(args.template + '.ms'), country))

print(f'<div id="tooltip"></div></body><script type="text/javascript" src="{args.template}.js"></script></html>')
