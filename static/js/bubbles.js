const articles = JSON.parse(document.getElementById('chart-data').textContent);
const svg = document.getElementById('chart');
const tooltip = document.getElementById('tooltip');

const margin = { top: 20, right: 20, bottom: 40, left: 60 };
const width = 720 - margin.left - margin.right;
const height = 420 - margin.top - margin.bottom;

const xMax = Math.max(...articles.map(a => a.extract_length)) * 1.1 || 1;
const yMax = Math.max(...articles.map(a => a.views)) * 1.1 || 1;
const rMax = Math.max(...articles.map(a => a.views)) || 1;

const xScale = v => margin.left + (v / xMax) * width;
const yScale = v => margin.top + height - (v / yMax) * height;
const rScale = v => 8 + (v / rMax) * 32;

const ns = 'http://www.w3.org/2000/svg';
function el(tag, attrs) {
  const node = document.createElementNS(ns, tag);
  for (const key in attrs) node.setAttribute(key, attrs[key]);
  return node;
}

// gridlines + axis labels
for (let i = 0; i <= 4; i++) {
  const y = margin.top + (height / 4) * i;
  svg.appendChild(el('line', { x1: margin.left, x2: margin.left + width, y1: y, y2: y, class: 'gridline' }));
  const val = Math.round(yMax * (1 - i / 4));
  const label = el('text', { x: margin.left - 8, y: y + 4, class: 'axis-label', 'text-anchor': 'end' });
  label.textContent = val.toLocaleString();
  svg.appendChild(label);
}
for (let i = 0; i <= 4; i++) {
  const x = margin.left + (width / 4) * i;
  const val = Math.round(xMax * (i / 4));
  const label = el('text', { x: x, y: margin.top + height + 20, class: 'axis-label', 'text-anchor': 'middle' });
  label.textContent = val;
  svg.appendChild(label);
}
const xAxisLabel = el('text', { x: margin.left + width / 2, y: 410, class: 'axis-label', 'text-anchor': 'middle' });
xAxisLabel.textContent = 'Summary length (characters)';
svg.appendChild(xAxisLabel);
const yAxisLabel = el('text', {
  x: -(margin.top + height / 2), y: 16, class: 'axis-label', 'text-anchor': 'middle',
  transform: 'rotate(-90)'
});
yAxisLabel.textContent = 'Pageviews';
svg.appendChild(yAxisLabel);

// bubbles
articles.forEach(a => {
  const circle = el('circle', {
    cx: xScale(a.extract_length),
    cy: yScale(a.views),
    r: rScale(a.views),
    class: 'bubble'
  });
  circle.addEventListener('mousemove', (e) => {
    tooltip.style.display = 'block';
    tooltip.style.left = (e.pageX + 14) + 'px';
    tooltip.style.top = (e.pageY - 10) + 'px';
    tooltip.innerHTML =
      '<div class="t-title">' + a.title + '</div>' +
      '<div class="t-meta">' + a.views.toLocaleString() + ' views · ' + a.extract_length + ' chars</div>';
  });
  circle.addEventListener('mouseleave', () => { tooltip.style.display = 'none'; });
  circle.addEventListener('click', () => window.open(a.url, '_blank'));
  svg.appendChild(circle);
});