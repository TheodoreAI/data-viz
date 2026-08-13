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
      showTable: true,
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
  },
  methods: {
    formatValue(value, format) {
      return format === 'number' && typeof value === 'number' ? value.toLocaleString() : value;
    },
    bubbleLabel(item) {
      return `${item.title}, ${item[this.yField].toLocaleString()} ${this.yLabel.toLowerCase()}, ${item[this.xField]} ${this.xLabel.toLowerCase()}`;
    },
    showTooltipAt(x, y, item) {
      this.tooltip.visible = true;
      this.tooltip.x = x + 14;
      this.tooltip.y = y - 10;
      this.tooltip.html =
        `<div class="t-title">${item.title}</div>` +
        `<div class="t-meta">${item[this.yField].toLocaleString()} ${this.yLabel.toLowerCase()} · ${item[this.xField]} ${this.xLabel.toLowerCase()}</div>`;
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
        Bubble size is {{ sizeField }}; y-position is {{ yLabel.toLowerCase() }}; x-position is {{ xLabel.toLowerCase() }}.
      </p>
      <button type="button" class="table-toggle" @click="showTable = !showTable">
        {{ showTable ? 'View as chart' : 'View as table' }}
      </button>
    </div>

    <div v-if="!showTable" class="chart-scroll">
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

    <table v-else class="data-table">
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
