<script>
import { scaleLinear, scaleSqrt, max } from 'd3';

export default {
  name: 'BubbleChart',
  props: {
    articles: { type: Array, required: true },
    date: { type: String, required: true },
  },
  data() {
    return {
      margin: { top: 20, right: 20, bottom: 40, left: 70 },
      width: 720 - 70 - 20,
      height: 420 - 20 - 40,
      showTable: false,
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
        .domain([0, max(this.articles, a => a.extract_length) * 1.1 || 1])
        .range([this.margin.left, this.margin.left + this.width]);
    },
    yScale() {
      return scaleLinear()
        .domain([0, max(this.articles, a => a.views) * 1.1 || 1])
        .range([this.margin.top + this.height, this.margin.top]);
    },
    rScale() {
      return scaleSqrt()
        .domain([0, max(this.articles, a => a.views) || 1])
        .range([8, 40]);
    },
    yTicks() {
      return this.yScale.ticks(4);
    },
    xTicks() {
      return this.xScale.ticks(4);
    },
    bubbles() {
      return this.articles.map(a => ({
        ...a,
        cx: this.xScale(a.extract_length),
        cy: this.yScale(a.views),
        r: this.rScale(a.views),
      }));
    },
    sortedByViews() {
      return [...this.articles].sort((a, b) => b.views - a.views);
    },
  },
  methods: {
    bubbleLabel(article) {
      return `${article.title}, ${article.views.toLocaleString()} views, ${article.extract_length} characters`;
    },
    showTooltipAt(x, y, article) {
      this.tooltip.visible = true;
      this.tooltip.x = x + 14;
      this.tooltip.y = y - 10;
      this.tooltip.html =
        `<div class="t-title">${article.title}</div>` +
        `<div class="t-meta">${article.views.toLocaleString()} views · ${article.extract_length} chars</div>`;
    },
    onHover(event, article) {
      this.showTooltipAt(event.pageX, event.pageY, article);
    },
    onTouch(event, article) {
      const touch = event.touches[0];
      this.showTooltipAt(touch.pageX, touch.pageY, article);
    },
    hideTooltip() {
      this.tooltip.visible = false;
    },
  },
};
</script>

<template>
  <div class="viz-root">
    <div class="viz-header">
      <div>
        <h1>Most-viewed Wikipedia articles — {{ date }}</h1>
        <p class="subtitle">
          Bubble size and y-position both encode daily pageviews; x-position is article length (characters in summary).
        </p>
      </div>
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
          Summary length (characters)
        </text>
        <text
          class="axis-label"
          transform="rotate(-90)"
          :x="-(margin.top + height / 2)"
          y="14"
          text-anchor="middle"
        >Pageviews</text>

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
          <th scope="col">Article</th>
          <th scope="col">Views</th>
          <th scope="col">Summary length</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="a in sortedByViews" :key="a.title">
          <td><a :href="a.url" target="_blank" rel="noopener">{{ a.title }}</a></td>
          <td>{{ a.views.toLocaleString() }}</td>
          <td>{{ a.extract_length }}</td>
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