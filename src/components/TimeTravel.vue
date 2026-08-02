<script>
function normalizeUrl(input) {
  const trimmed = input.trim();
  if (!trimmed) return '';
  return /^https?:\/\//i.test(trimmed) ? trimmed : `https://${trimmed}`;
}

export default {
  name: 'TimeTravel',
  data() {
    return {
      urlInput: '',
      searchedUrl: '',
      loading: false,
      error: '',
      mode: null, // 'timeline' | 'popular'
      snapshots: [],
      popularPages: [],
      selectedTimestamp: null,
      selectedArchiveUrl: '',
    };
  },
  computed: {
    selectedSnapshot() {
      return this.snapshots.find((s) => s.timestamp === this.selectedTimestamp) || null;
    },
  },
  methods: {
    async search() {
      const url = normalizeUrl(this.urlInput);
      if (!url || this.loading) return;

      this.loading = true;
      this.error = '';
      this.mode = null;
      this.snapshots = [];
      this.popularPages = [];
      this.selectedTimestamp = null;
      this.selectedArchiveUrl = '';
      try {
        const response = await fetch(`/api/wayback/snapshots?url=${encodeURIComponent(url)}`);
        const data = await response.json();
        if (!response.ok) {
          this.error = data.error || "Couldn't load snapshots for that URL.";
          return;
        }
        this.searchedUrl = url;
        this.mode = data.mode;
        if (data.mode === 'timeline') {
          this.snapshots = data.snapshots;
          this.selectedTimestamp = data.snapshots[0]?.timestamp || null;
          this.selectedArchiveUrl = data.snapshots[0]?.archiveUrl || '';
        } else {
          this.popularPages = data.pages;
          this.selectPopularPage(data.pages[0]);
        }
      } catch {
        this.error = "Couldn't reach the Wayback Machine. Please try again.";
      } finally {
        this.loading = false;
      }
    },
    selectYear(snapshot) {
      this.selectedTimestamp = snapshot.timestamp;
      this.selectedArchiveUrl = snapshot.archiveUrl;
    },
    selectPopularPage(page) {
      if (!page) return;
      this.selectedTimestamp = page.timestamp;
      this.selectedArchiveUrl = page.archiveUrl;
    },
  },
};
</script>

<template>
  <div class="time-travel-page">
    <h1>Time Travel</h1>
    <p class="subtitle">See how a website looked in the past, via the Wayback Machine.</p>

    <form class="search-form" @submit.prevent="search">
      <input
        v-model="urlInput"
        type="text"
        placeholder="e.g. wikipedia.org"
        :disabled="loading"
      >
      <button type="submit" class="search-button" :disabled="loading || !urlInput.trim()">
        {{ loading ? 'Searching…' : 'Search' }}
      </button>
    </form>

    <p v-if="error" class="status form-error">{{ error }}</p>

    <template v-if="mode === 'timeline'">
      <div class="year-row">
        <button
          v-for="snapshot in snapshots"
          :key="snapshot.timestamp"
          type="button"
          class="year-pill"
          :class="{ active: snapshot.timestamp === selectedTimestamp }"
          @click="selectYear(snapshot)"
        >{{ snapshot.year }}</button>
      </div>
    </template>

    <template v-else-if="mode === 'popular'">
      <p class="status">
        No exact match for <strong>{{ searchedUrl }}</strong> — here are the most-archived pages we found on that site instead:
      </p>
      <ul class="popular-list">
        <li v-for="page in popularPages" :key="page.url">
          <button
            type="button"
            class="popular-item"
            :class="{ active: page.timestamp === selectedTimestamp && page.archiveUrl === selectedArchiveUrl }"
            @click="selectPopularPage(page)"
          >
            <span class="popular-url">{{ page.url }}</span>
            <span class="popular-meta">{{ page.captureCount.toLocaleString() }} captures · last seen {{ page.date }}</span>
          </button>
        </li>
      </ul>
    </template>

    <template v-if="selectedArchiveUrl">
      <p class="snapshot-meta">
        <a :href="selectedArchiveUrl" target="_blank" rel="noopener">open in a new tab</a>
      </p>
      <iframe
        :key="selectedArchiveUrl"
        :src="selectedArchiveUrl"
        class="snapshot-frame"
        title="Archived page"
      ></iframe>
    </template>
  </div>
</template>

<style scoped>
.time-travel-page {
  max-width: 900px;
  margin: 0 auto;
  padding: 1.5rem 1.25rem 3rem;
  font-family: "Palatino Linotype", "Palatino", Georgia, serif;
}
h1 {
  font-size: 1.3rem;
  margin: 0 0 0.2rem;
  color: var(--series-1, #2f6690);
}
.subtitle {
  color: var(--text-secondary, #6b5d47);
  font-size: 0.9rem;
  margin: 0 0 1.25rem;
}
.search-form {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1rem;
}
.search-form input {
  flex: 1;
  min-width: 0;
  font-family: inherit;
  font-size: 0.95rem;
  padding: 0.5rem 0.75rem;
  border: 1px solid var(--gridline, #d8c9a3);
  border-radius: 4px;
  background: var(--surface-1, #fcfcfb);
  color: inherit;
}
.search-button {
  flex: none;
  background: var(--series-1, #2f6690);
  color: #fff;
  border: none;
  border-radius: 4px;
  padding: 0.5rem 1.1rem;
  font-size: 0.9rem;
  cursor: pointer;
}
.search-button:disabled {
  opacity: 0.5;
  cursor: default;
}
.status {
  font-size: 0.9rem;
}
.form-error {
  color: #b0413e;
}
.year-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
  margin-bottom: 0.75rem;
}
.year-pill {
  border: 1px solid var(--gridline, #d8c9a3);
  background: var(--surface-1, #fcfcfb);
  color: var(--text-secondary, #6b5d47);
  border-radius: 999px;
  padding: 0.3rem 0.8rem;
  font-family: inherit;
  font-size: 0.82rem;
  cursor: pointer;
}
.year-pill.active {
  background: var(--series-1, #2f6690);
  border-color: var(--series-1, #2f6690);
  color: #fff;
}
.popular-list {
  list-style: none;
  margin: 0 0 1rem;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}
.popular-item {
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.15rem;
  text-align: left;
  background: var(--surface-1, #fcfcfb);
  border: 1px solid var(--gridline, #d8c9a3);
  border-radius: 4px;
  padding: 0.5rem 0.7rem;
  cursor: pointer;
  font-family: inherit;
}
.popular-item.active {
  border-color: var(--series-1, #2f6690);
}
.popular-url {
  font-size: 0.88rem;
  color: var(--series-1, #2f6690);
  overflow-wrap: break-word;
}
.popular-meta {
  font-size: 0.75rem;
  color: var(--text-secondary, #6b5d47);
}
.snapshot-meta {
  font-size: 0.82rem;
  color: var(--text-secondary, #6b5d47);
  margin: 0 0 0.6rem;
}
.snapshot-meta a {
  color: var(--series-1, #2f6690);
}
.snapshot-frame {
  width: 100%;
  height: 70vh;
  border: 1px solid var(--gridline, #d8c9a3);
  border-radius: 4px;
  background: #fff;
}
</style>
