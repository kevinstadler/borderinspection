# border inspection

generate [Earth Studio](https://earth.google.com/studio/) inspection tours of the world's borders

## dependencies / usage

### `getborders.py`
```
pip3 install geojson more_itertools osm2geojson pycountry percache mapbox mercantile Pillow
mkdir -p data/2

./getborders.py
```

### `stats.py`

```
pip3 install area geotiff great-circle-calculator Pillow

./stats.py -summary data/2/AUT.geojson
```
