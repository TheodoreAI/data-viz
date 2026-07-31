<script setup>
import { reactive, computed } from 'vue';
import { scaleLinear, scaleSqrt, max } from 'd3';

const props = defineProps({
  articles: { type: Array, required: true },
  date: { type: String, required: true },
});

const margin = { top: 20, right: 20, bottom: 40, left: 60 };
const width = 720 - margin.left - margin.right;
const height = 420 - margin.top - margin.bottom;

const xScale = computed(() =>
  scaleLinear()
    .domain([0, max(props.articles, a => a.extract_length) * 1.1 || 1])
    .range([margin.left, margin.left + width])
);

const yScale = computed(() =>
  scaleLinear()
    .domain([0, max(props.articles, a => a.views) * 1.1 || 1])
    .range([margin.top + height, margin.top])
);

const rScale = computed(() =>
  scaleSqrt()
    .domain([0, max(props.articles, a => a.views) || 1])
    .range([8, 40])
);

const yTicks = computed(() => yScale.value.ticks(4));
const xTicks = computed(() => xScale.value.ticks(4));

const bubbles = computed(() =>
  props.articles.map(a => ({
    ...a,
    cx: xScale.value(a.extract_length),
    cy: yScale.value(a.views),
    r: rScale.value(a.views),
  }))
);

const tooltip = reactive({
  visible: false,
  x: 0,
  y: 0,
  html: '',
});

function onHover(event, article) {
  tooltip.visible = true;
  tooltip.x = event.pageX + 14;
  tooltip.y = event.pageY - 10;
  tooltip.html =
    `<div class="t-title">${article.title}</div>` +
    `<div class="t-meta">${article.views.toLocaleString()} views · ${article.extract_length} chars</div>`;
}

function hideTooltip() {
  tooltip.visible = false;
}

function openArticle(article) {
  window.open(article.url, '_blank');
}
</script>

<template>
  <div class="viz-root">
    <h1>Most-viewed Wikipedia articles — {{ date }}</h1>
    <p class="subtitle">
      Bubble size and y-position both encode daily pageviews; x-position is article length (characters in summary).
    </p>

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
        y="16"
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

    <div
      id="tooltip"
      :style="{ display: tooltip.visible ? 'block' : 'none', left: tooltip.x + 'px', top: tooltip.y + 'px' }"
      v-html="tooltip.html"
    />
  </div>
</template>