<script>
import { scaleLinear, scaleSqrt, max } from 'd3';

export default {
  name: 'BubbleChart',
  props: {
    items: { type: Array, required: true },
    xField: { type: String, default: 'extract_length' },
    yField: { type: String, default: 'views' },
    sizeField: { type: String, default: 'views' },
    xLabel: { type: String, default: 'Summary length (characters)' },
    yLabel: { type: String, default: 'Pageviews' },
    columns: {
      type: Array,
      default: () => [
        { field: 'title', label: 'Article', link: true },
        { field: 'views', label: 'Views', format: 'number' },
        { field: 'extract_length', label: 'Summary length' },
      ],
    },
  },
  data() {
    return {
      margin: { top: 20, right: 20, bottom: 40, left: 70 },
      width: 720 - 70 - 20,
      height: 420 - 20 - 40,
      barHeight: 28,
      barGap: 10,
      barLeftMargin: 160,
      barRightMargin: 60,
      view: 'table',
      tooltip: {
        visible: false,
        x: 0,
        y: 0,
        html: '',
      },
    };
  },
  computed: {
    xScale() {
      return scaleLinear()
        .domain([0, max(this.items, i => i[this.xField]) * 1.1 || 1])
        .range([this.margin.left, this.margin.left + this.width]);
    },
    yScale() {
      return scaleLinear()
        .domain([0, max(this.items, i => i[this.yField]) * 1.1 || 1])
        .range([this.margin.top + this.height, this.margin.top]);
    },
    rScale() {
      return scaleSqrt()
        .domain([0, max(this.items, i => i[this.sizeField]) || 1])
        .range([8, 40]);
    },
    yTicks() {
      return this.yScale.ticks(4);
    },
    xTicks() {
      return this.xScale.ticks(4);
    },
    bubbles() {
      return this.items.map(i => ({
        ...i,
        cx: this.xScale(i[this.xField]),
        cy: this.yScale(i[this.yField]),
        r: this.rScale(i[this.sizeField]),
      }));
    },
    sortedByY() {
      return [...this.items].sort((a, b) => b[this.yField] - a[this.yField]);
    },
    barChartHeight() {
      return this.sortedByY.length * (this.barHeight + this.barGap) + this.barGap;
    },
    barScale() {
      return scaleLinear()
        .domain([0, max(this.items, i => i[this.yField]) * 1.05 || 1])
        .range([0, 720 - this.barLeftMargin - this.barRightMargin]);
    },
    bars() {
      return this.sortedByY.map((item, i) => ({
        ...item,
        barWidth: this.barScale(item[this.yField]),
        barY: this.barGap + i * (this.barHeight + this.barGap),
      }));
    },
  },
  methods: {
    formatValue(value, format) {
      return format === 'number' && typeof value === 'number' ? value.toLocaleString() : value;
    },
    bubbleLabel(item) {
      return `${item.title}, ${item[this.yField].toLocaleString()} ${this.yLabel.toLowerCase()}, ${item[this.xField]} ${this.xLabel.toLowerCase()}`;
    },
    barLabel(item) {
      return `${item.title}, ${item[this.yField].toLocaleString()} ${this.yLabel.toLowerCase()}`;
    },
    showTooltipAt(x, y, item) {
      this.tooltip.visible = true;
      this.tooltip.x = x + 14;
      this.tooltip.y = y - 10;
      this.tooltip.html =
        `<div class="t-title">${item.title}</div>` +
        `<div class="t-meta">${item[this.yField].toLocaleString()} ${this.yLabel.toLowerCase()} · ${item[this.xField]} ${this.xLabel.toLowerCase()}</div>`;
    },
    showBarTooltipAt(x, y, item) {
      this.tooltip.visible = true;
      this.tooltip.x = x + 14;
      this.tooltip.y = y - 10;
      this.tooltip.html =
        `<div class="t-title">${item.title}</div>` +
        `<div class="t-meta">${item[this.yField].toLocaleString()} ${this.yLabel.toLowerCase()}</div>`;
    },
    onBarHover(event, item) {
      this.showBarTooltipAt(event.pageX, event.pageY, item);
    },
    onBarTouch(event, item) {
      const touch = event.touches[0];
      this.showBarTooltipAt(touch.pageX, touch.pageY, item);
    },
    onHover(event, item) {
      this.showTooltipAt(event.pageX, event.pageY, item);
    },
    onTouch(event, item) {
      const touch = event.touches[0];
      this.showTooltipAt(touch.pageX, touch.pageY, item);
    },
    hideTooltip() {
      this.tooltip.visible = false;
    },
  },
};
</script>

<template>
  <div class="viz-body">
    <div class="viz-header">
      <p class="subtitle">
        <template v-if="view === 'bubble'">Bubble size is {{ sizeField }}; y-position is {{ yLabel.toLowerCase() }}; x-position is {{ xLabel.toLowerCase() }}.</template>
        <template v-else-if="view === 'bars'">Ranked by {{ yLabel.toLowerCase() }}.</template>
        <template v-else>Table view, ranked by {{ yLabel.toLowerCase() }}.</template>
      </p>
      <div class="view-toggle" role="tablist" aria-label="Chart view">
        <button type="button" class="table-toggle" :class="{ active: view === 'bubble' }" @click="view = 'bubble'">Bubble</button>
        <button type="button" class="table-toggle" :class="{ active: view === 'bars' }" @click="view = 'bars'">Bars</button>
        <button type="button" class="table-toggle" :class="{ active: view === 'table' }" @click="view = 'table'">Table</button>
      </div>
    </div>

    <div v-if="view === 'bubble'" class="chart-scroll">
      <svg width="720" height="420" viewBox="0 0 720 420">
        <line
          v-for="tick in yTicks"
          :key="'gy' + tick"
          class="gridline"
          :x1="margin.left"
          :x2="margin.left + width"
          :y1="yScale(tick)"
          :y2="yScale(tick)"
        />
        <text
          v-for="tick in yTicks"
          :key="'ly' + tick"
          class="axis-label"
          :x="margin.left - 8"
          :y="yScale(tick) + 4"
          text-anchor="end"
        >{{ tick.toLocaleString() }}</text>

        <text
          v-for="tick in xTicks"
          :key="'lx' + tick"
          class="axis-label"
          :x="xScale(tick)"
          :y="margin.top + height + 20"
          text-anchor="middle"
        >{{ tick }}</text>

        <text class="axis-label" :x="margin.left + width / 2" y="410" text-anchor="middle">
          {{ xLabel }}
        </text>
        <text
          class="axis-label"
          transform="rotate(-90)"
          :x="-(margin.top + height / 2)"
          y="14"
          text-anchor="middle"
        >{{ yLabel }}</text>

        <a
          v-for="b in bubbles"
          :key="b.title"
          :href="b.url"
          target="_blank"
          rel="noopener"
          :aria-label="bubbleLabel(b)"
          @mousemove="onHover($event, b)"
          @touchstart="onTouch($event, b)"
          @mouseleave="hideTooltip"
        >
          <circle
            class="bubble"
            :cx="b.cx"
            :cy="b.cy"
            :r="b.r"
          />
        </a>
      </svg>
    </div>

    <div v-else-if="view === 'bars'" class="chart-scroll">
      <svg width="720" :height="barChartHeight" :viewBox="`0 0 720 ${barChartHeight}`">
        <g v-for="b in bars" :key="b.title">
          <text
            class="bar-label"
            :x="barLeftMargin - 10"
            :y="b.barY + barHeight / 2 + 4"
            text-anchor="end"
          >{{ b.title.length > 22 ? b.title.slice(0, 21) + '…' : b.title }}</text>
          <a
            :href="b.url"
            target="_blank"
            rel="noopener"
            :aria-label="barLabel(b)"
            @mousemove="onBarHover($event, b)"
            @touchstart="onBarTouch($event, b)"
            @mouseleave="hideTooltip"
          >
            <rect
              class="bar"
              :x="barLeftMargin"
              :y="b.barY"
              :width="b.barWidth"
              :height="barHeight"
              rx="4"
            />
            <text
              class="bar-value"
              :x="barLeftMargin + b.barWidth + 8"
              :y="b.barY + barHeight / 2 + 4"
            >{{ b[yField].toLocaleString() }}</text>
          </a>
        </g>
      </svg>
    </div>

    <table v-else-if="view === 'table'" class="data-table">
      <thead>
        <tr>
          <th v-for="col in columns" :key="col.field" scope="col">{{ col.label }}</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="item in sortedByY" :key="item.title">
          <td v-for="col in columns" :key="col.field">
            <a v-if="col.link" :href="item.url" target="_blank" rel="noopener">{{ item[col.field] }}</a>
            <template v-else>{{ formatValue(item[col.field], col.format) }}</template>
          </td>
        </tr>
      </tbody>
    </table>

    <div
      id="tooltip"
      :style="{ display: tooltip.visible ? 'block' : 'none', left: tooltip.x + 'px', top: tooltip.y + 'px' }"
      v-html="tooltip.html"
    />
  </div>
</template>
