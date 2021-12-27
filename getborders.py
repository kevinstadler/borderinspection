#!/usr/local/bin/python3

import json
from os import path, rename
from osm2geojson import json2geojson, overpass_call
import time

adminlevel = f'[admin_level~"^[23]$"]'

# go by what OSM thinks about de-facto states
iso = overpass_call(f'[out:csv("ISO3166-1:alpha3", "admin_level")];rel{adminlevel}["ISO3166-1:alpha3"];out;').split("\n")[1:-1]
#[1:]
print(f"Checking for {len(iso)} countries' borders")

for line in iso:
  c, lvl = line.split("\t")
  filename = f'{c}.geojson'
  if path.exists(f'data/{lvl}/{filename}'):# or path.exists(f'data/3/{filename}') or path.exists(f'data/4/{filename}') or path.exists(f'data/6/{filename}'):
    print(f'{filename} already downloaded, skipping')
    continue
  print(c)
  # alternatively: don't filter for admin_level, but check if it's 2 (country) or 3 (overseas something)
  # filter out boundary=claimed_administrative
  # land masses or boundary=claimed_administrative areas are sometimes also tagged with the ISO codes, so best to ask for admin_level explicitly AND set type != land_area
  r = json.loads(overpass_call(f'[out:json];rel["ISO3166-1:alpha3"={c}]{adminlevel}[boundary=administrative][type!=land_area];out geom;'))
#  r = json.loads(overpass_call(f'[out:json];(rel["ISO3166-1:alpha2"={c.alpha_2}];rel["ISO3166-1:alpha3"={c.alpha_3}];)->.a;rel.a[boundary=administrative][admin_level={admin_level}][type!=land_area];out geom;'))
  if len(r['elements']) == 0:
    print('empty result!')
    continue
  filename = f'data/{r["elements"][0]["tags"]["admin_level"]}/{filename}'
  print(f'writing to {filename}')
  with open(filename, 'w') as f:
    json.dump(json2geojson(r), f)
