<!DOCTYPE html>
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
<base target="_blank">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Serif:wght@400;500&display=swap" rel="stylesheet">
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@300;400;500;600&display=swap" rel="stylesheet">

<link rel="stylesheet" href="horizontal.css">
</head>
<body>

<noscript>
sorry, this page requires javascript to be fully functional. you can still admire the beauty of the world's national borders, but inspecting the borders by means of hovering and clicking will not work.
</noscript>

{{#countries}}
<div class="country" id="{{info.iso3}}" data-osmid="{{info.id}}">
  <div class="description">
    <span>{{info.name}}</span>
  </div>

  <div class="landuse">
  {{#parts}}
    <div class="part">
    {{#landuses}}
      <div {{{attributes}}}></div>
    {{/landuses}}
    </div>
  {{/parts}}
  </div>

  <div class="stats">
    <p>{{summary.totallength}} km of border, {{summary.outerlanduse}}</p>
    {{#summary.misc}}
    <p>{{summary.misc}}</p>
    {{/summary.misc}}
  </div>
</div>
{{/countries}}

<a href="#about" target="_self" id="btn"><div id="foo">?</div></a>
<div id="about"><div>
<a href="#" target="_self" class="modal-close">X</a>
<h1 style="font-family: 'IBM Plex Serif', serif; font-weight: 400; margin-top: 0;">border inspection: landuse</h1>
<p>a service provided by the <a href="https://thiswasyouridea.com">Futile Software Corporation</a>.</p>
<p>you might also enjoy <a href="https://thiswasyouridea.com/borderinspection/">our other border inspection products</a>.</p>
<p>inclusion of countries and territories is based on the <a href="https://en.wikipedia.org/wiki/ISO_3166-1">ISO 3166-1</a> standard.</p>
<p>border trajectory data &copy;&nbsp;<a href="https://www.openstreetmap.org/copyright">OpenStreetMap&nbsp;contributors</a>, landuse data (<a href="https://lpdaac.usgs.gov/products/mcd12q1v006/">MODIS MCD12Q1</a>) courtesy of NASA EOSDIS Land Processes DAAC.</p>
</div></div>

<div id="tooltip"><span></span><span id="touchtooltip"><br>(click to inspect)</span></div>
</body>
<script type="text/javascript" src="horizontal.js"></script>
</html>
