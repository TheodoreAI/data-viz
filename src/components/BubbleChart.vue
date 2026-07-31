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
  },
  methods: {
    onHover(event, article) {
      this.tooltip.visible = true;
      this.tooltip.x = event.pageX + 14;
      this.tooltip.y = event.pageY - 10;
      this.tooltip.html =
        `<div class="t-title">${article.title}</div>` +
        `<div class="t-meta">${article.views.toLocaleString()} views · ${article.extract_length} chars</div>`;
    },
    hideTooltip() {
      this.tooltip.visible = false;
    },
    openArticle(article) {
      window.open(article.url, '_blank');
    },
  },
};
</script>

<template>
  <div class="viz-root">
    <h1>Most-viewed Wikipedia articles — {{ date }}</h1>
    <p class="subtitle">
      Bubble size and y-position both encode daily pageviews; x-position is article length (characters in summary).
    </p>

    <div class="chart-scroll">
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

        <circle
          v-for="b in bubbles"
          :key="b.title"
          class="bubble"
          :cx="b.cx"
          :cy="b.cy"
          :r="b.r"
          @mousemove="onHover($event, b)"
          @mouseleave="hideTooltip"
          @click="openArticle(b)"
        />
      </svg>
    </div>

    <div
      id="tooltip"
      :style="{ display: tooltip.visible ? 'block' : 'none', left: tooltip.x + 'px', top: tooltip.y + 'px' }"
      v-html="tooltip.html"
    />
  </div>
</template>