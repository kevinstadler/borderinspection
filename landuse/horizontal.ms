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
<meta name="description" content="what the world's national borders are used for" />
<meta property="og:title" content="border inspection: landuse">
<meta property="og:url" content="https://thiswasyouridea.com/landuse/">
<meta property="og:image" content="http://res.cloudinary.com/futile/image/upload/w_auto,c_crop,q_auto/meta/landuse.png">
<meta property="og:image:secure_url" content="https://res.cloudinary.com/futile/image/upload/w_auto,c_crop,q_auto/meta/landuse.png">
<meta property="og:type" content="website">
<meta property="og:description" content="what the world's national borders are used for" >

<base target="_blank">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Serif:wght@400;500&display=swap" rel="stylesheet">

<style type="text/css">
html {
  width: 100%;
  font-family: 'IBM Plex Sans', sans-serif;
  --neon: #ccc;
  font-weight: 300;
  font-size: .9rem;
}

body {
  display: flex;
  flex-direction: column;
  justify-content: center;
  background: black;
  color: var(--neon);
  margin: auto;
  /* max-width: 80em; */
  width: 90%;
}

a, a:active, a:visited, a:hover {
  color: #aa0;
}

div#tooltip {
  visibility: hidden;
  position: absolute;
  z-index: 1000;
  transition: color 250ms;
}

#tooltip > :first-child {
  z-index: 1001;
  height: 14px;
  border-left: 1px solid var(--neon);
}

#tooltip > :nth-child(2) {
  text-align: center;
  min-width: 5em;
  max-width: 90vw;
  padding: .1rem .4rem;
  border-radius: .7rem;
  /* backdrop-filter: blur(10px); */
  /* transform-origin: top left; */
  /* transform: translate(-1em, -30px) rotate(-35deg); */
  /* transform: translateY(-8px) rotate(35deg); */
  transform: translateX(-50%);
}

/* div#tooltip:before { */
/*   content : " "; */
/*   width: 0; */
/*   height: 0; */
/*   border-left: 1px solid transparent; */
/*   border-right: 1px solid transparent; */
/*   border-top: 7px solid var(--neon); */
/*   position: absolute; */
/*   bottom: -7px; */
/*   left: calc(50% - 7px); */
/* } */

#touchtooltip {
  display: none;
}

@media (hover: none) {
  #touchtooltip {
    display: initial;
  }
}


div.country {
  flex: 0 0 auto;
  min-width: 0;
  padding: .5em 1.5em;
  color: transparent;
  transition: color 750ms;
  margin: 3px 0;
  display: flex;
  flex-direction: column;
}

div.country:hover {
  color: var(--neon);
}

div.country > div {
  flex: 0 0 3rem;

  display: flex;
  flex-direction: column;
  justify-content: center;
  text-align: center;
}

div.description {
  font-size: 1.4rem;
}

div.country > div.landuse {
  visibility: visible;
  width: fit-content;
  max-width: 100%;
  margin: .2em auto 0;
  flex-direction: row;
  justify-content: flex-start;
  overflow-x: scroll;
  overflow-y: visible;
  scrollbar-width: thin;
  scrollbar-color: var(--neon);
}

div.landuse::-webkit-scrollbar {
  height: .2em;
  border-radius: .25em;
}

div.landuse::-webkit-scrollbar-thumb {
  visibility: hidden;
  background: var(--neon);
  border-radius: 0;
}
div.landuse:hover::-webkit-scrollbar-thumb {
  visibility: visible;
}

div.landuse + div {
}

div.landuse:hover + div {
  transition: color 250ms;
  color: transparent;
}

div.part {
  display: flex;
  flex-direction: row;
  margin: 0 .3em;
  overflow: visible;
  cursor: pointer;
}

div.part:first-child {
  margin-left: 0;
}

div.part:last-child {
  margin-right: 0;
}

div.part > :hover {
  overflow-y: visible;
  /* FIXME landuse gets a scrollbar when this becomes too high height: 4em; */
}
/* div.part > a { */
/*   display: block; */
/* } */

.i1 { background-color: #008000; }
.i2 { background-color: #0f0; }
.i3 { background-color: #9c0; }
.i4 { background-color: #9f9; }
.i5 { background-color: #396; }
.i6 { background-color: #936; }
.i7 { background-color: #fc9; }
.i8 { background-color: #cfc; }
.i9 { background-color: #fc0; }
.i10 { background-color: #f90; }
.i11 { background-color: #069; }
.i12 { background-color: #ff0; }
.i13 { background-color: #f00; }
.i14 { background-color: #996; }
.i15 { background-color: #fff; }
.i16 { background-color: #808080; }
.i17 { background-color: #000080; }
.i18 { background-color: #48f; } <!-- 18 is fresh -->
.i100 { background-color: #000; } 
.h1 { width: 1px; }
.h2 { width: 2px; }
.h3 { width: 3px; }
.h4 { width: 4px; }
.h5 { width: 5px; }
.h6 { width: 6px; }
.h7 { width: 7px; }
.h8 { width: 8px; }
.h9 { width: 9px; }
.h10 { width: 10px; }

.i1 > div > span:first-child::after { content: " of evergreen needleleaf forest"; }
.i2 > div > span:first-child::after { content: " of evergreen broadleaf forest"; }
.i3 > div > span:first-child::after { content: " of deciduous needleleaf forest"; }
.i4 > div > span:first-child::after { content: " of deciduous broadleaf forest"; }
.i5 > div > span:first-child::after { content: " of mixed forest"; }
.i6 > div > span:first-child::after { content: " of closed shrublands"; }
.i7 > div > span:first-child::after { content: " of open shrublands"; }
.i8 > div > span:first-child::after { content: " of woody savannas"; }
.i9 > div > span:first-child::after { content: " of savannas"; }
.i10 > div > span:first-child::after { content: " of grasslands"; }
.i11 > div > span:first-child::after { content: " of permanent wetlands"; }
.i12 > div > span:first-child::after { content: " of croplands"; }
.i13 > div > span:first-child::after { content: " of urban and built-up"; }
.i14 > div > span:first-child::after { content: " of cropland/natural vegetation mosaic"; }
.i15 > div > span:first-child::after { content: " of snow and ice"; }
.i16 > div > span:first-child::after { content: " of sparsely vegetated land"; }
.i17 > div > span:first-child::after { content: " of sea water"; }
.i18 > div > span:first-child::after { content: " of fresh water"; }
.i100 > div > span:first-child::after { content: " of unknown landuse"; }

/* div.part > div > div > span:nth-child(2)::before { content: " ["; } */
/* div.part > div > div > span:nth-child(2)::after { content: "]"; } */

#btn {
  position: fixed;
  bottom: 1em;
  right: 1.5em;
  width: 1.8em;
  height: 1.8em;
  /* border: 1px solid var(--neon); */
  border-radius: .9em;
  color: var(--neon);
  text-align: center;
  display: flex;
  justify-content: center;
  align-items: middle;
  text-decoration: none;
}

#btn:hover {
  text-shadow: 0 0 2px;
  /* box-shadow: var(--neon) 0 0 3px; */
}

#about {
  position: fixed;
  backdrop-filter: blur(10px);
  top: 0;
  right: 0;
  bottom: 0;
  left: 0;
  z-index: 999;
  visibility: hidden;
  opacity: 0;
  pointer-events: none;
  transition: all 0.3s;
}

#about:target {
  visibility: visible;
  opacity: 1;
  pointer-events: auto;
}

#about > div {
  box-shadow: var(--neon) 0 0 8px;

  background-color: black;
  border-radius: 5px;
  width: 80%;
  max-width: 40em;
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  padding: 1.5em 2em;
}

hr {
  /* width: 10em; */
}

#about hr ~ * {
  font-size: .85rem;
}

.modal-close {
  display: block;
  font-size: 80%;
  position: absolute;
  right: .5em;
  top: .5em;
  width: 1em;
  height: 1em;
  text-decoration: none;
}
</style>
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
<h1 style="font-family: 'IBM Plex Serif', serif; font-weight: 400; margin-top: 0;">landuse</h1>
<p>what are the world's national borders used for?</p>
<p>a border is never just a boundary <i>between</i> two abstract political entities, it also runs <i>through</i> concrete physical space.
<p>this website shows linear representations of all national border segments of the world based on their physical landuse according to the <a href="https://yceo.yale.edu/modis-land-cover-product-mcd12q1">17 IGBP land cover classes</a>.</p>
<hr>
<p>a service provided by the <a href="https://thiswasyouridea.com">Futile Software Corporation</a>. you might also enjoy <a href="https://thiswasyouridea.com/borderinspection/">our other border inspection products</a>.</p>
<p>border trajectory data &copy;&nbsp;<a href="https://www.openstreetmap.org/copyright">OpenStreetMap&nbsp;contributors</a>, landuse data (<a href="https://lpdaac.usgs.gov/products/mcd12q1v006/">MODIS MCD12Q1</a>) courtesy of NASA EOSDIS Land Processes DAAC. inclusion of countries and territories is based on the <a href="https://en.wikipedia.org/wiki/ISO_3166-1">ISO 3166-1</a> standard.</p>
</div></div>

<div id="tooltip"><div></div><div><span></span><span id="touchtooltip"><br>(click to inspect border)</span></div></div>
</body>
<script type="text/javascript">
const tooltip = document.getElementById('tooltip');

const usenames = { 1: "evergreen needleleaf forest",
2: "evergreen broadleaf forest",
3: "deciduous needleleaf forest",
4: "deciduous broadleaf forest",
5: "mixed forest",
6: "closed shrublands",
7: "open shrublands",
8: "woody savannas",
9: "savannas",
10: "grasslands",
11: "permanent wetlands",
12: "croplands",
13: "urban and built-up land",
14: "cropland/natural vegetation mosaic", 
15: "snow and ice", 
16: "barren land", 
17: "sea water", 
18: "inland water", 
99: "unknown landuse"
};

const getInfo = function(el) {
  if (el.getAttribute('data-x') === null) {
    return;
  }
  return el.getAttribute('data-x').split(',');
}

var touched;
const handleClick = function(e) {
  if (e.pointerType === 'touch' && touched !== e.target) {
    touched = e.target;
    return;
  }
  inspectBorder(e.target);
}

const inspectBorder = function(segment) {
  const info = getInfo(segment);
  if (info) {
    const osmId = segment.parentNode.parentNode.parentNode.getAttribute('data-osmid');
    window.open('https://openstreetmap.org/relation/' + osmId + '#map=' + info[1] + '/' + info[2] + '/' + info[3] );
  }
}
tooltip.addEventListener('click', function(e) { inspectBorder(touched); });

var lastHov;
const createTip = function(e) {
  const info = getInfo(e.target);
  if (info) {
    if (e.target !== lastHov) {
      lastHov = e.target;
      lastHov.title = 'click to inspect border';
      const use = parseInt(lastHov.className.substring(1, 3));
      tooltip.childNodes[1].firstChild.innerHTML = info[0] + ' km of ' + usenames[use];
    }
    const hoverrect = e.target.getBoundingClientRect();
    const tiprect = tooltip.getBoundingClientRect();
    // TODO limit because hoverrect might be much wider than whats actually visible
    //tooltip.style.left = Math.round((hoverrect.left + hoverrect.right)/2 - tiprect.width/2) + 'px';
    // tooltip.style.left = Math.round(e.pageX - tiprect.width/2) + 'px';
    tooltip.style.left = Math.round(e.pageX) + 'px';

    // tooltip.style.top = Math.round(window.scrollY + hoverrect.top - 23) + 'px';
    tooltip.style.top = Math.round(window.scrollY + hoverrect.top + hoverrect.height + 1) + 'px';
    tooltip.style.visibility = 'visible';
  }
}

const cancelTip = function(e) {
  tooltip.style.visibility = 'hidden';
}

const countries = document.querySelectorAll('.landuse');
for (let i = 0; i < countries.length; i++) {
  countries[i].addEventListener('mousemove', createTip);
  countries[i].addEventListener('mouseout', cancelTip);
  countries[i].addEventListener('click', handleClick);
}
</script>
</html>
