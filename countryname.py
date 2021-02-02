from pycountry import countries

# get a nicely verbose name of a country from a geojson feature
def countryname(feature):
  name = countries.get(alpha_3=feature['properties']['tags']['ISO3166-1:alpha3'])
  if name:
    # get some good one
    try:
      name = name.official_name
    except AttributeError:
      name = name.name
  else:
    # revert to the OSM feature, take first that is there
    for key in ['official_name:en', 'official_name', 'int_name', 'name:en']:
      try:
        name = feature['properties']['tags'][key]
        # if it worked, break
        break
      except KeyError:
        continue
  # sometimes prepend 'The' (https://www.grammar-quizzes.com/article4c.html)
  # skip first letter because it might be upper or lower case 'the'
  if not name.startswith('he ', 1) and any([part in name for part in ['Commonwealth', 'Democratic', 'Duchy', 'Federation', 'Holy', 'Kingdom', 'Principality', 'Republic', 'Union', 'United']]): # capture Union and United
    name = 'The ' + name
  return name
