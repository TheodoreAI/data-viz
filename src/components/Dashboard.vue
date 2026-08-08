<script>
function readCookie(name) {
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : null;
}

function formatDate(iso) {
  if (!iso) return null;
  return new Date(iso).toLocaleDateString(undefined, { year: 'numeric', month: 'long', day: 'numeric' });
}

function pad(n) {
  return String(n).padStart(2, '0');
}

function isoDate(d) {
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

function isoMonth(d) {
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}`;
}

const yesterday = new Date();
yesterday.setDate(yesterday.getDate() - 1);

import LoadingSpinner from './LoadingSpinner.vue';

export default {
  name: 'Dashboard',
  components: { LoadingSpinner },
  data() {
    return {
      user: null,
      loading: true,
      error: false,

      stats: null,
      statsLoading: true,
      statsError: false,

      articlesMode: 'yesterday',
      articlesDate: isoDate(yesterday),
      articlesMonth: isoMonth(yesterday),
      maxDate: isoDate(yesterday),
      maxMonth: isoMonth(yesterday),
      articles: [],
      articlesLoading: false,
      articlesError: false,

      savedItems: [],
      savedItemsLoading: true,
      savedItemsError: false,
      removingId: null,
    };
  },
  computed: {
    memberSince() {
      return formatDate(this.user?.createdAt);
    },
    lastLogin() {
      return formatDate(this.user?.lastLoginAt);
    },
  },
  async mounted() {
    try {
      const response = await fetch('/api/profile', { credentials: 'same-origin' });
      if (response.status === 401) {
        window.location.href = '/login';
        return;
      }
      if (!response.ok) throw new Error(`Request failed: ${response.status}`);
      this.user = await response.json();
    } catch {
      this.error = true;
    } finally {
      this.loading = false;
    }

    this.loadStats();
    this.loadArticles();
    this.loadSavedItems();
  },
  methods: {
    async loadSavedItems() {
      this.savedItemsLoading = true;
      this.savedItemsError = false;
      try {
        const response = await fetch('/api/saved-items', { credentials: 'same-origin' });
        if (!response.ok) throw new Error(`Request failed: ${response.status}`);
        this.savedItems = await response.json();
      } catch {
        this.savedItemsError = true;
      } finally {
        this.savedItemsLoading = false;
      }
    },
    async removeSavedItem(item) {
      if (this.removingId) return;
      if (!window.confirm(`Remove "${item.title}" from your saves?`)) return;
      this.removingId = item.id;
      try {
        const response = await fetch(`/api/saved-items/${item.id}`, {
          method: 'DELETE',
          credentials: 'same-origin',
          headers: { 'X-CSRF-TOKEN': readCookie('csrf_access_token') },
        });
        if (response.ok) {
          this.savedItems = this.savedItems.filter((i) => i.id !== item.id);
        }
      } finally {
        this.removingId = null;
      }
    },
    async loadStats() {
      this.statsLoading = true;
      this.statsError = false;
      try {
        const response = await fetch('/api/stats', { credentials: 'same-origin' });
        if (!response.ok) throw new Error(`Request failed: ${response.status}`);
        this.stats = await response.json();
      } catch {
        this.statsError = true;
      } finally {
        this.statsLoading = false;
      }
    },
    async loadArticles() {
      this.articlesLoading = true;
      this.articlesError = false;
      try {
        const params = new URLSearchParams();
        if (this.articlesMode === 'date') {
          const [year, month, day] = this.articlesDate.split('-');
          params.set('year', year);
          params.set('month', month);
          params.set('day', day);
        } else if (this.articlesMode === 'month') {
          const [year, month] = this.articlesMonth.split('-');
          params.set('year', year);
          params.set('month', month);
        }
        const response = await fetch(`/api/top-articles?${params.toString()}`, { credentials: 'same-origin' });
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || `Request failed: ${response.status}`);
        this.articles = data.articles;
      } catch {
        this.articlesError = true;
      } finally {
        this.articlesLoading = false;
      }
    },
  },
};
</script>

<template>
  <div class="dashboard-page">
    <LoadingSpinner v-if="loading" size="lg" />
    <template v-else-if="error">
      <p class="status form-error">Couldn't load your dashboard. Please refresh the page.</p>
    </template>
    <template v-else-if="user">
      <h1>Welcome back, {{ user.displayName || user.username }}</h1>
      <p class="meta">
        <span v-if="memberSince">Member since {{ memberSince }}</span>
        <span v-if="lastLogin"> · Last login {{ lastLogin }}</span>
      </p>

      <div class="quick-links">
        <a href="/nodes" class="quick-link">
          <span class="quick-link-title">Nodes</span>
          <span class="quick-link-copy">Explore article link graphs</span>
        </a>
        <a href="/trending" class="quick-link">
          <span class="quick-link-title">Trending</span>
          <span class="quick-link-copy">See what's hot on Wikipedia, Hacker News, YouTube, and Stack Overflow</span>
        </a>
        <a href="/profile" class="quick-link">
          <span class="quick-link-title">Profile</span>
          <span class="quick-link-copy">Edit your bio, password, and account</span>
        </a>
        <a v-if="user.isAdmin" href="/admin" class="quick-link">
          <span class="quick-link-title">Admin</span>
          <span class="quick-link-copy">View registered users</span>
        </a>
      </div>

      <section class="widget">
        <h2>Your saves</h2>
        <LoadingSpinner v-if="savedItemsLoading" size="sm" inline />
        <p v-else-if="savedItemsError" class="status form-error">Couldn't load your saved items.</p>
        <p v-else-if="!savedItems.length" class="status">
          Nothing saved yet — look for a Save button on articles on Home.
        </p>
        <ul v-else class="saved-list">
          <li v-for="item in savedItems" :key="item.id" class="saved-item">
            <img v-if="item.imageUrl" :src="item.imageUrl" :alt="item.title" class="saved-thumb">
            <div class="saved-info">
              <a :href="item.sourceUrl" target="_blank" rel="noopener" class="saved-title">{{ item.title }}</a>
              <span v-if="item.subtitle" class="saved-subtitle">{{ item.subtitle }}</span>
            </div>
            <button
              type="button"
              class="remove-button"
              :disabled="removingId === item.id"
              @click="removeSavedItem(item)"
            >{{ removingId === item.id ? 'Removing…' : 'Remove' }}</button>
          </li>
        </ul>
      </section>

      <section class="widget">
        <h2>App stats</h2>
        <LoadingSpinner v-if="statsLoading" size="sm" inline />
        <p v-else-if="statsError" class="status form-error">Couldn't load stats.</p>
        <div v-else-if="stats" class="stat-row">
          <div class="stat">
            <span class="stat-value">{{ stats.totalUsers }}</span>
            <span class="stat-label">registered users</span>
          </div>
        </div>
      </section>

      <section class="widget">
        <h2>Most-viewed Wikipedia articles</h2>
        <div class="articles-controls">
          <label class="mode-option">
            <input type="radio" value="yesterday" v-model="articlesMode" @change="loadArticles">
            Yesterday
          </label>
          <label class="mode-option">
            <input type="radio" value="date" v-model="articlesMode" @change="loadArticles">
            Specific date
            <input
              v-if="articlesMode === 'date'"
              type="date"
              v-model="articlesDate"
              :max="maxDate"
              @change="loadArticles"
            >
          </label>
          <label class="mode-option">
            <input type="radio" value="month" v-model="articlesMode" @change="loadArticles">
            Whole month
            <input
              v-if="articlesMode === 'month'"
              type="month"
              v-model="articlesMonth"
              :max="maxMonth"
              @change="loadArticles"
            >
          </label>
        </div>

        <LoadingSpinner v-if="articlesLoading" size="sm" inline />
        <p v-else-if="articlesError" class="status form-error">Couldn't load article data for that period.</p>
        <div v-else-if="articles.length" class="table-scroll">
          <table class="articles-table">
            <thead>
              <tr>
                <th>Article</th>
                <th class="views-col">Views</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="article in articles" :key="article.title">
                <td><a :href="article.url" target="_blank" rel="noopener">{{ article.title }}</a></td>
                <td class="views-col">{{ article.views.toLocaleString() }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </template>
  </div>
</template>

<style scoped>
.dashboard-page {
  max-width: 640px;
  margin: 0 auto;
  padding: 2rem 1.25rem 3rem;
}
h1 {
  font-size: 1.3rem;
  margin: 0 0 0.3rem;
}
.meta {
  color: var(--text-secondary, #6b5d47);
  font-size: 0.85rem;
  margin: 0 0 1.5rem;
}
.status {
  color: var(--text-secondary, #6b5d47);
  font-size: 0.9rem;
}
.form-error {
  color: #b0413e;
}
.quick-links {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.9rem;
}
@media (max-width: 480px) {
  .quick-links {
    grid-template-columns: 1fr;
  }
}
.quick-link {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  padding: 1rem;
  border: 1px solid var(--gridline, #d8c9a3);
  border-radius: 6px;
  text-decoration: none;
  color: inherit;
}
.quick-link:hover {
  border-color: var(--series-1, #2f6690);
}
.quick-link-title {
  font-weight: 700;
  color: var(--series-1, #2f6690);
}
.quick-link-copy {
  font-size: 0.85rem;
  color: var(--text-secondary, #6b5d47);
}
.widget {
  margin-top: 2rem;
}
.widget h2 {
  font-size: 1rem;
  margin: 0 0 0.75rem;
}
.stat-row {
  display: flex;
  flex-wrap: wrap;
  gap: 1.5rem 2rem;
}
.stat {
  display: flex;
  flex-direction: column;
}
.stat-value {
  font-size: 1.6rem;
  font-weight: 700;
  color: var(--series-1, #2f6690);
}
.stat-label {
  font-size: 0.78rem;
  color: var(--text-secondary, #6b5d47);
}
.articles-controls {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
  margin-bottom: 1rem;
  font-size: 0.85rem;
}
.mode-option {
  display: flex;
  align-items: center;
  gap: 0.4rem;
}
.mode-option input[type="date"],
.mode-option input[type="month"] {
  font-family: inherit;
  font-size: 0.85rem;
  padding: 0.2rem 0.4rem;
  border: 1px solid var(--gridline, #d8c9a3);
  border-radius: 4px;
  background: var(--surface-1, #fcfcfb);
  color: inherit;
}
.table-scroll {
  overflow-x: auto;
}
.articles-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.85rem;
}
.articles-table th {
  text-align: left;
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  color: var(--text-secondary, #6b5d47);
  border-bottom: 1px solid var(--gridline, #d8c9a3);
  padding: 0.4rem 0.5rem;
}
.articles-table td {
  padding: 0.45rem 0.5rem;
  border-bottom: 1px solid var(--gridline, #d8c9a3);
}
.articles-table a {
  color: var(--series-1, #2f6690);
  text-decoration: none;
}
.articles-table a:hover {
  text-decoration: underline;
}
.views-col {
  text-align: right;
  white-space: nowrap;
}
.saved-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
}
.saved-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.5rem;
  border: 1px solid var(--gridline, #d8c9a3);
  border-radius: 6px;
}
.saved-thumb {
  width: 48px;
  height: 48px;
  object-fit: cover;
  border-radius: 4px;
  flex: none;
  background: var(--surface-1, #fcfcfb);
}
.saved-info {
  display: flex;
  flex-direction: column;
  min-width: 0;
  flex: 1;
}
.saved-title {
  color: var(--series-1, #2f6690);
  text-decoration: none;
  font-size: 0.9rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.saved-title:hover {
  text-decoration: underline;
}
.saved-subtitle {
  font-size: 0.78rem;
  color: var(--text-secondary, #6b5d47);
}
.remove-button {
  flex: none;
  background: transparent;
  border: 1px solid var(--gridline, #d8c9a3);
  color: #b0413e;
  border-radius: 4px;
  padding: 0.3rem 0.7rem;
  font-size: 0.78rem;
  cursor: pointer;
}
.remove-button:disabled {
  opacity: 0.6;
  cursor: default;
}
</style>
