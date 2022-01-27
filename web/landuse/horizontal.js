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
      const use = parseInt(e.target.className.substring(1, 3));
      tooltip.firstChild.innerHTML = info[0] + ' km of ' + usenames[use]; // + '<br>(click to inspect)';
      lastHov = e.target;
    }
    const hoverrect = e.target.getBoundingClientRect();
    const tiprect = tooltip.getBoundingClientRect();
    // TODO limit because hoverrect might be much wider than whats actually visible
    //tooltip.style.left = Math.round((hoverrect.left + hoverrect.right)/2 - tiprect.width/2) + 'px';
    tooltip.style.left = Math.round(e.pageX - tiprect.width/2) + 'px';
    tooltip.style.top = Math.round(window.scrollY + hoverrect.top - tiprect.height - 8) + 'px';
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

