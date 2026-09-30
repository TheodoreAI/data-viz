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
  go: { primary: 'score', primaryLabel: 'stars', secondary: 'comments', secondaryLabel: 'forks' },
  arxiv: { primary: 'citations', primaryLabel: 'citations', secondary: 'year', secondaryLabel: 'published' },
  pypi: { primary: 'downloads', primaryLabel: 'downloads/wk', secondary: null },
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
        { id: 'devto', label: 'DEV' },
        { id: 'lobsters', label: 'Lobsters' },
        { id: 'github', label: 'GitHub' },
        { id: 'go', label: 'Go' },
        { id: 'npm', label: 'npm' },
        { id: 'cargo', label: 'Cargo' },
        { id: 'pypi', label: 'PyPI' },
        { id: 'arxiv', label: 'arXiv' },
      ],
      trendingCache: {},
      loading: false,
      loadingMore: false,
      error: false,
      loadMoreError: false,
      arxivPage: 0,
      arxivHasMore: true,
    };
  },
  mounted() {
    window.addEventListener('scroll', this.onScroll, { passive: true });
  },
  beforeUnmount() {
    window.removeEventListener('scroll', this.onScroll);
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
      const dir = m.sortDesc === false ? -1 : 1;
      return [...items].sort((a, b) => dir * ((b[m.primary] || 0) - (a[m.primary] || 0)));
    },
  },
  methods: {
    async selectTab(tabId) {
      this.activeTab = tabId;
      if (tabId === 'wikipedia' || this.trendingCache[tabId]) return;

      this.loading = true;
      this.error = false;
      try {
        const query = tabId === 'arxiv' ? '?page=1' : '';
        const response = await fetch(`/api/trending/${tabId}${query}`);
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || `Request failed: ${response.status}`);
        this.trendingCache = { ...this.trendingCache, [tabId]: data.items };
        if (tabId === 'arxiv') {
          this.arxivPage = 1;
          this.arxivHasMore = data.items.length > 0;
        }
      } catch {
        this.error = true;
      } finally {
        this.loading = false;
      }
    },
    onScroll() {
      if (this.activeTab !== 'arxiv' || this.loading || this.loadingMore || !this.arxivHasMore) return;
      const distanceFromBottom = document.documentElement.scrollHeight - window.innerHeight - window.scrollY;
      if (distanceFromBottom < 500) this.loadMoreArxiv();
    },
    async loadMoreArxiv() {
      this.loadingMore = true;
      this.loadMoreError = false;
      try {
        const nextPage = this.arxivPage + 1;
        const response = await fetch(`/api/trending/arxiv?page=${nextPage}`);
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || `Request failed: ${response.status}`);

        const currentItems = this.trendingCache.arxiv || [];
        const knownUrls = new Set(currentItems.map(item => item.url));
        const newItems = data.items.filter(item => !knownUrls.has(item.url));
        this.trendingCache = {
          ...this.trendingCache,
          arxiv: [...currentItems, ...newItems],
        };
        this.arxivPage = nextPage;
        this.arxivHasMore = data.items.length > 0;
      } catch {
        this.loadMoreError = true;
      } finally {
        this.loadingMore = false;
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
      <p class="mp-sub" v-else-if="activeTab === 'arxiv'">All-time most cited Computer Science papers available on arXiv</p>
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
            <span class="metric-chip">{{ formatMetric(item[metrics.primary]) }} {{ metrics.primaryLabel }}</span>
            <span v-if="metrics.secondary != null && item[metrics.secondary] != null" class="metric-chip">
              {{ formatMetric(item[metrics.secondary]) }} {{ metrics.secondaryLabel }}
            </span>
          </div>
        </div>
      </li>
    </ol>
    <LoadingSpinner v-if="loadingMore" size="sm" inline />
    <p v-else-if="loadMoreError" class="status form-error">Couldn't load more papers. Scroll again to retry.</p>
    <p v-else-if="activeTab === 'arxiv' && !arxivHasMore && items.length" class="status">You've reached the end.</p>
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
  transition: background 0.15s ease, color 0.15s ease, border-radius 0.15s ease;
}
.mp-tab:hover {
  color: var(--mp-ink);
}
.mp-tab.active {
  color: var(--mp-wall);
  background: var(--mp-frame-strong);
  border-radius: var(--pill-radius, 999px);
}
.mp-tab:active {
  transform: scale(0.96);
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
  border-radius: var(--card-radius, 16px);
  padding: 1.1rem 1.25rem;
  margin: 0 0 1rem;
  background: var(--card-bg, var(--mp-wall));
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
  transition: transform 0.12s ease, box-shadow 0.12s ease, opacity 0.12s ease;
}
.mp-item:active {
  transform: scale(0.99);
  opacity: 0.85;
}
.mp-num {
  flex: none;
  font-family: Inter, sans-serif;
  font-size: 0.78rem;
  font-weight: 600;
  color: var(--mp-ink);
  min-width: 1.6rem;
  height: 1.6rem;
  line-height: 1.6rem;
  text-align: center;
  border: 1px solid var(--mp-frame);
  border-radius: 50%;
  padding: 0 0.35rem;
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
.metric-chip {
  display: inline-flex;
  align-items: center;
  padding: 0.15rem 0.5rem;
  border-radius: var(--pill-radius, 999px);
  background: var(--mp-frame);
  color: var(--mp-ink);
  font-size: 0.68rem;
  letter-spacing: 0.02em;
}

@media (max-width: 640px) {
  /* Full-bleed container: edge-to-edge with a smaller gutter and a
     comfortable top/bottom so the page reads like an app on phones. */
  .mp-root {
    padding: 1.5rem 1rem 2.5rem;
  }
  .mp-head {
    margin-bottom: 1.1rem;
  }
  .mp-head h1 {
    font-size: 1.35rem;
  }

  /* Tabs: keep all 10 on one line and let the row scroll horizontally
     thumb-friendly instead of wrapping into a cramped stack. Scrollbars
     are hidden so it reads as a clean strip. */
  .mp-tabs {
    flex-wrap: nowrap;
    justify-content: flex-start;
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
    scrollbar-width: none;
    margin: 0 -1rem 1.4rem;
    padding: 0 1rem;
  }
  .mp-tabs::-webkit-scrollbar {
    display: none;
  }
  .mp-tab {
    flex: none;
    min-height: 40px;
    padding: 0.4rem 0.9rem;
    font-size: 0.8rem;
  }

  /* Cards: let the title sit on one line so rows stay uniform height, and
     anchor the last card above the home indicator. */
  .mp-item h2 {
    display: -webkit-box;
    -webkit-line-clamp: 1;
    line-clamp: 1;
    -webkit-box-orient: vertical;
    overflow: hidden;
    font-size: 1rem;
  }
  .mp-item:last-of-type {
    margin-bottom: calc(1rem + env(safe-area-inset-bottom));
  }
}

@media (min-width: 641px) {
  .mp-root {
    max-width: 640px;
    margin: 0 auto;
  }
}
</style>
