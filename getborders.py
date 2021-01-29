#!/usr/local/bin/python3.6

import json
from os import path
from osm2geojson import json2geojson, overpass_call
import pycountry
import time

for c in pycountry.countries:
  filename = f'{c.alpha_3}.geojson'
  if path.exists(f'data/2/{filename}') or path.exists(f'data/3/{filename}')):
    continue
  print(c)
  # alternatively: don't filter for admin_level, but check if it's 2 (country) or 3 (overseas something)
  r = json.loads(overpass_call(f'[out:json];(rel["ISO3166-1:alpha2"={c.alpha_2}];rel["ISO3166-1:alpha3"={c.alpha_3}];);out geom;'))
  if len(r['elements']) == 0:
    print('empty result!')
    continue
  filename = f'data/{r["elements"][0]["tags"]["admin_level"]}/{filename}'
  with open(filename, 'w') as f:
    json.dump(json2geojson(r), f)
