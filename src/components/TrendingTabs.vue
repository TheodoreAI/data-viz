<script>
import LoadingSpinner from './LoadingSpinner.vue';

// Which fields to show as the primary (bold) and secondary metric per source —
// the underlying APIs return different shapes (score/comments for link
// aggregators, downloads/growth for package registries, views for Wikipedia).
const METRICS_BY_TAB = {
  wikipedia: { primary: 'views', primaryLabel: 'views', secondary: null },
  npm: { primary: 'downloads', primaryLabel: 'downloads/wk', secondary: 'growth_pct', secondaryLabel: 'growth' },
  cargo: { primary: 'downloads', primaryLabel: 'downloads', secondary: 'total_downloads', secondaryLabel: 'all-time' },
  github: { primary: 'score', primaryLabel: 'stars', secondary: 'comments', secondaryLabel: 'forks' },
};
const DEFAULT_METRICS = { primary: 'score', primaryLabel: 'points', secondary: 'comments', secondaryLabel: 'comments' };

function metricsFor(tabId) {
  return METRICS_BY_TAB[tabId] || DEFAULT_METRICS;
}

export default {
  name: 'TrendingTabs',
  components: { LoadingSpinner },
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
        { id: 'github', label: 'GitHub' },
        { id: 'npm', label: 'npm' },
        { id: 'cargo', label: 'Cargo' },
      ],
      trendingCache: {},
      loading: false,
      error: false,
    };
  },
  computed: {
    activeTabLabel() {
      return this.tabs.find(t => t.id === this.activeTab).label;
    },
    metrics() {
      return metricsFor(this.activeTab);
    },
    items() {
      const items = this.activeTab === 'wikipedia' ? this.initialArticles : (this.trendingCache[this.activeTab] || []);
      const m = this.metrics;
      return [...items].sort((a, b) => (b[m.primary] || 0) - (a[m.primary] || 0));
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
    formatMetric(value) {
      return typeof value === 'number' ? value.toLocaleString() : value;
    },
  },
};
</script>

<template>
  <div class="zine-root">
    <div class="zine-head">
      <h1>What's Hot</h1>
      <p class="zine-sub" v-if="activeTab === 'wikipedia'">Most-viewed Wikipedia articles — {{ initialDate }}</p>
      <p class="zine-sub" v-else>Right now, on {{ activeTabLabel }}</p>
    </div>

    <div class="zine-tabs" role="tablist">
      <span
        v-for="tab in tabs"
        :key="tab.id"
        role="tab"
        class="zine-tab"
        :class="{ active: activeTab === tab.id }"
        :aria-selected="activeTab === tab.id"
        @click="selectTab(tab.id)"
      >{{ tab.label }}</span>
    </div>

    <LoadingSpinner v-if="loading" size="sm" inline />
    <p v-else-if="error" class="status form-error">Couldn't load that data. Please try again.</p>
    <p v-else-if="!items.length" class="status">No data available right now. Please try again later.</p>

    <ol v-else class="zine-list">
      <li v-for="(item, i) in items" :key="item.title" class="zine-item">
        <span class="zine-num">{{ i + 1 }}</span>
        <span class="zine-tape" aria-hidden="true"></span>
        <h2><a :href="item.url" target="_blank" rel="noopener">{{ item.title }}</a></h2>
        <div class="zine-meta">
          <span>{{ formatMetric(item[metrics.primary]) }} {{ metrics.primaryLabel }}</span>
          <span v-if="metrics.secondary != null && item[metrics.secondary] != null">
            {{ formatMetric(item[metrics.secondary]) }} {{ metrics.secondaryLabel }}
          </span>
        </div>
      </li>
    </ol>
  </div>
</template>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Archivo+Black&family=Archivo:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');

.zine-root {
  --zn-bg: #f2ede0;
  --zn-ink: #1c1a17;
  --zn-ink-soft: #6b6455;
  --zn-hot: #e8432f;
  --zn-card: #ffffff;
  --zn-tape: #f6e27a;

  background: var(--zn-bg);
  color: var(--zn-ink);
  font-family: Archivo, system-ui, sans-serif;
  padding: 1.5rem 1.1rem 3rem;
  border-radius: var(--card-radius, 16px);
}

@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) .zine-root {
    --zn-bg: #1a1712;
    --zn-ink: #ede8da;
    --zn-ink-soft: #a49c86;
    --zn-hot: #ff6a52;
    --zn-card: #241f18;
    --zn-tape: #6b5a1f;
  }
}
:root[data-theme="dark"] .zine-root {
  --zn-bg: #1a1712;
  --zn-ink: #ede8da;
  --zn-ink-soft: #a49c86;
  --zn-hot: #ff6a52;
  --zn-card: #241f18;
  --zn-tape: #6b5a1f;
}

.zine-head { margin-bottom: 1.25rem; transform: rotate(-0.6deg); }
.zine-head h1 {
  font-family: "Archivo Black", sans-serif;
  font-size: 1.9rem;
  text-transform: uppercase;
  margin: 0;
  line-height: 0.95;
}
.zine-sub {
  font-size: 0.8rem;
  color: var(--zn-ink-soft);
  margin: 0.4rem 0 0;
}

.zine-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
  margin-bottom: 1.25rem;
}
.zine-tab {
  font-family: "Archivo Black", sans-serif;
  font-size: 0.66rem;
  text-transform: uppercase;
  padding: 0.35rem 0.7rem;
  border: 2px solid var(--zn-ink);
  color: var(--zn-ink);
  cursor: pointer;
  transform: rotate(-1deg);
}
.zine-tab:nth-child(even) { transform: rotate(1deg); }
.zine-tab.active {
  background: var(--zn-hot);
  color: #fff;
  border-color: var(--zn-hot);
}

.status {
  color: var(--zn-ink-soft);
  font-size: 0.9rem;
}
.form-error {
  color: #b0413e;
}

.zine-list {
  list-style: none;
  margin: 0;
  padding: 0;
}
.zine-item {
  position: relative;
  background: var(--zn-card);
  border: 2px solid var(--zn-ink);
  padding: 1.1rem 1.25rem;
  margin: 0 0 1.25rem;
}
.zine-item:nth-child(odd) { transform: rotate(0.5deg); }
.zine-item:nth-child(even) { transform: rotate(-0.5deg); }
.zine-num {
  position: absolute;
  top: -14px;
  left: -10px;
  background: var(--zn-hot);
  color: #fff;
  font-family: "Archivo Black", sans-serif;
  font-size: 1.05rem;
  width: 34px;
  height: 34px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 2px solid var(--zn-ink);
  transform: rotate(-8deg);
}
.zine-tape {
  position: absolute;
  top: -8px;
  right: 14px;
  width: 40px;
  height: 16px;
  background: var(--zn-tape);
  opacity: 0.85;
  transform: rotate(4deg);
}
.zine-item h2 {
  font-size: 1.05rem;
  font-weight: 700;
  margin: 0.5rem 0 0.5rem;
  line-height: 1.25;
}
.zine-item h2 a {
  color: inherit;
  text-decoration: none;
}
.zine-item h2 a:hover {
  text-decoration: underline;
}
.zine-meta {
  display: flex;
  gap: 0.9rem;
  font-size: 0.72rem;
  color: var(--zn-ink-soft);
  font-family: "JetBrains Mono", monospace;
}
</style>
