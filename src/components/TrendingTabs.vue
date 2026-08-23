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
  <div class="mp-root">
    <header class="mp-head">
      <div class="kicker">Right Now</div>
      <h1>What's Hot</h1>
      <p class="mp-sub" v-if="activeTab === 'wikipedia'">Most-viewed Wikipedia articles — {{ initialDate }}</p>
      <p class="mp-sub" v-else>Right now, on {{ activeTabLabel }}</p>
    </header>

    <nav class="mp-tabs" role="tablist">
      <button
        v-for="tab in tabs"
        :key="tab.id"
        type="button"
        role="tab"
        class="mp-tab"
        :class="{ active: activeTab === tab.id }"
        :aria-selected="activeTab === tab.id"
        @click="selectTab(tab.id)"
      >{{ tab.label }}</button>
    </nav>

    <LoadingSpinner v-if="loading" size="sm" inline />
    <p v-else-if="error" class="status form-error">Couldn't load that data. Please try again.</p>
    <p v-else-if="!items.length" class="status">No data available right now. Please try again later.</p>

    <ol v-else class="mp-list">
      <li v-for="(item, i) in items" :key="item.title" class="mp-item">
        <span class="mp-num">{{ i + 1 }}</span>
        <div class="mp-item-body">
          <h2><a :href="item.url" target="_blank" rel="noopener">{{ item.title }}</a></h2>
          <div class="mp-meta">
            <span>{{ formatMetric(item[metrics.primary]) }} {{ metrics.primaryLabel }}</span>
            <span v-if="metrics.secondary != null && item[metrics.secondary] != null">
              {{ formatMetric(item[metrics.secondary]) }} {{ metrics.secondaryLabel }}
            </span>
          </div>
        </div>
      </li>
    </ol>
  </div>
</template>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Serif:wght@400;500;600&family=Inter:wght@400;500;600;700&display=swap');

.mp-root {
  --mp-wall: #f7f6f3;
  --mp-frame: #e4e1d9;
  --mp-frame-strong: #22201b;
  --mp-ink: #22201b;
  --mp-ink-soft: #756f60;

  background: var(--mp-wall);
  color: var(--mp-ink);
  font-family: "IBM Plex Serif", Georgia, serif;
  padding: 1.75rem 1.1rem 3rem;
  border-radius: var(--card-radius, 16px);
}

@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) .mp-root {
    --mp-wall: #171613;
    --mp-frame: #34312a;
    --mp-frame-strong: #d9d5c9;
    --mp-ink: #f0eee6;
    --mp-ink-soft: #a39d8b;
  }
}
:root[data-theme="dark"] .mp-root {
  --mp-wall: #171613;
  --mp-frame: #34312a;
  --mp-frame-strong: #d9d5c9;
  --mp-ink: #f0eee6;
  --mp-ink-soft: #a39d8b;
}

.mp-head {
  text-align: center;
  margin-bottom: 1.5rem;
}
.kicker {
  font-family: Inter, sans-serif;
  font-size: 0.66rem;
  letter-spacing: 0.22em;
  text-transform: uppercase;
  color: var(--mp-ink-soft);
  margin-bottom: 0.5rem;
}
.mp-head h1 {
  margin: 0;
  font-size: 1.5rem;
  font-weight: 500;
  letter-spacing: 0.01em;
}
.mp-sub {
  font-family: Inter, sans-serif;
  font-size: 0.8rem;
  color: var(--mp-ink-soft);
  margin: 0.5rem 0 0;
}

.mp-tabs {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 0.4rem;
  margin-bottom: 1.75rem;
  font-family: Inter, sans-serif;
}
.mp-tab {
  font-family: inherit;
  font-size: 0.72rem;
  color: var(--mp-ink-soft);
  background: transparent;
  border: none;
  border-bottom: 1px solid transparent;
  padding: 0.3rem 0.6rem;
  cursor: pointer;
  text-transform: capitalize;
}
.mp-tab:hover {
  color: var(--mp-ink);
}
.mp-tab.active {
  color: var(--mp-ink);
  border-color: var(--mp-frame-strong);
}

.status {
  color: var(--mp-ink-soft);
  font-family: Inter, sans-serif;
  font-size: 0.9rem;
}
.form-error {
  color: #b0413e;
}

.mp-list {
  list-style: none;
  margin: 0;
  padding: 0;
}
.mp-item {
  display: flex;
  align-items: baseline;
  gap: 1rem;
  border: 1px solid var(--mp-frame);
  padding: 1.1rem 1.25rem;
  margin: 0 0 1rem;
}
.mp-num {
  flex: none;
  font-family: Inter, sans-serif;
  font-size: 0.78rem;
  color: var(--mp-ink-soft);
  min-width: 1.4rem;
}
.mp-item-body {
  min-width: 0;
}
.mp-item h2 {
  font-size: 1.05rem;
  font-weight: 600;
  margin: 0 0 0.4rem;
  line-height: 1.3;
}
.mp-item h2 a {
  color: inherit;
  text-decoration: none;
}
.mp-item h2 a:hover {
  text-decoration: underline;
}
.mp-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem 0.9rem;
  font-family: Inter, sans-serif;
  font-size: 0.72rem;
  letter-spacing: 0.03em;
  text-transform: uppercase;
  color: var(--mp-ink-soft);
}

@media (min-width: 641px) {
  .mp-root {
    max-width: 640px;
    margin: 0 auto;
  }
}
</style>
