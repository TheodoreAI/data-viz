<script>
import BubbleChart from './BubbleChart.vue';
import LoadingSpinner from './LoadingSpinner.vue';

const TRENDING_CHART_PROPS = {
  xField: 'age_hours',
  yField: 'score',
  sizeField: 'comments',
  xLabel: 'Age (hours)',
  yLabel: 'Score',
  columns: [
    { field: 'title', label: 'Title', link: true },
    { field: 'score', label: 'Score', format: 'number' },
    { field: 'comments', label: 'Comments', format: 'number' },
    { field: 'age_hours', label: 'Age (hours)' },
  ],
};

export default {
  name: 'TrendingTabs',
  components: { BubbleChart, LoadingSpinner },
  props: {
    initialArticles: { type: Array, default: () => [] },
    initialDate: { type: String, default: '' },
  },
  data() {
    return {
      activeTab: 'wikipedia',
      tabs: [
        { id: 'wikipedia', label: 'Wikipedia' },
        { id: 'hackernews', label: 'Hacker News' },
        { id: 'youtube', label: 'YouTube' },
        { id: 'stackoverflow', label: 'Stack Overflow' },
        { id: 'devto', label: 'DEV' },
        { id: 'lobsters', label: 'Lobsters' },
      ],
      trendingCache: {},
      loading: false,
      error: false,
    };
  },
  computed: {
    chartProps() {
      return this.activeTab === 'wikipedia'
        ? {
            items: this.initialArticles,
            xField: 'extract_length',
            yField: 'views',
            sizeField: 'views',
            xLabel: 'Summary length (characters)',
            yLabel: 'Pageviews',
            columns: [
              { field: 'title', label: 'Article', link: true },
              { field: 'views', label: 'Views', format: 'number' },
              { field: 'extract_length', label: 'Summary length' },
            ],
          }
        : {
            items: this.trendingCache[this.activeTab] || [],
            ...TRENDING_CHART_PROPS,
          };
    },
  },
  methods: {
    async selectTab(tabId) {
      this.activeTab = tabId;
      if (tabId === 'wikipedia' || this.trendingCache[tabId]) return;

      this.loading = true;
      this.error = false;
      try {
        const response = await fetch(`/api/trending/${tabId}`);
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || `Request failed: ${response.status}`);
        this.trendingCache = { ...this.trendingCache, [tabId]: data.items };
      } catch {
        this.error = true;
      } finally {
        this.loading = false;
      }
    },
  },
};
</script>

<template>
  <div class="viz-root">
    <div class="viz-title-row">
      <h1 v-if="activeTab === 'wikipedia'">Most-viewed Wikipedia articles — {{ initialDate }}</h1>
      <h1 v-else>What's hot on {{ tabs.find(t => t.id === activeTab).label }}</h1>
    </div>

    <div class="trending-tabs" role="tablist">
      <button
        v-for="tab in tabs"
        :key="tab.id"
        type="button"
        role="tab"
        class="trending-tab"
        :class="{ active: activeTab === tab.id }"
        :aria-selected="activeTab === tab.id"
        @click="selectTab(tab.id)"
      >{{ tab.label }}</button>
    </div>

    <LoadingSpinner v-if="loading" size="sm" inline />
    <p v-else-if="error" class="status form-error">Couldn't load that data. Please try again.</p>
    <p v-else-if="!chartProps.items.length" class="status">No data available right now. Please try again later.</p>
    <BubbleChart v-else :key="activeTab" v-bind="chartProps" />
  </div>
</template>

<style scoped>
.viz-title-row h1 {
  font-size: 1.1rem;
  margin: 0 0 0.75rem;
}
.trending-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-bottom: 1rem;
}
.trending-tab {
  background: transparent;
  border: 1px solid var(--gridline, #e2e5eb);
  color: var(--text-secondary, #6b5d47);
  border-radius: 999px;
  padding: 0.35rem 0.9rem;
  font-family: inherit;
  font-size: 0.8rem;
  cursor: pointer;
  transition: border-color 0.15s ease, color 0.15s ease, background-color 0.15s ease;
}
.trending-tab:hover {
  border-color: var(--series-1, #2f6690);
  color: var(--series-1, #2f6690);
}
.trending-tab.active {
  background: var(--series-1, #2f6690);
  border-color: var(--series-1, #2f6690);
  color: var(--surface-1, #fff);
}
.status {
  color: var(--text-secondary, #6b5d47);
  font-size: 0.9rem;
}
.form-error {
  color: #b0413e;
}
</style>
