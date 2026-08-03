<script>
function readCookie(name) {
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : null;
}

import LoadingSpinner from './LoadingSpinner.vue';

export default {
  name: 'MoviesFeed',
  components: { LoadingSpinner },
  props: {
    initialFilms: { type: Array, required: true },
    genres: { type: Array, default: () => [] },
  },
  data() {
    return {
      films: this.initialFilms,
      offset: this.initialFilms.length,
      selectedGenre: '',
      sortMode: 'oldest',
      loading: false,
      exhausted: false,
      error: false,
      copiedKey: '',
      savedKeys: new Set(),
      savingKey: '',
    };
  },
  computed: {
    displayedFilms() {
      if (this.sortMode === 'newest') {
        return [...this.films].sort((a, b) => (b.year ?? -Infinity) - (a.year ?? -Infinity));
      }
      if (this.sortMode === 'oldest') {
        return [...this.films].sort((a, b) => (a.year ?? Infinity) - (b.year ?? Infinity));
      }
      return this.films;
    },
  },
  watch: {
    async selectedGenre() {
      if (this.loading) return;
      this.films = [];
      this.offset = 0;
      this.exhausted = false;
      this.error = false;
      await this.loadMore();
    },
  },
  mounted() {
    this.observer = new IntersectionObserver((entries) => {
      if (entries[0].isIntersecting) this.loadMore();
    }, { rootMargin: '600px' });
    this.observer.observe(this.$refs.sentinel);
  },
  beforeUnmount() {
    if (this.observer) this.observer.disconnect();
  },
  methods: {
    filmKey(film) {
      return `${film.title}::${film.director}`;
    },
    shuffle() {
      const shuffled = [...this.films];
      for (let i = shuffled.length - 1; i > 0; i -= 1) {
        const j = Math.floor(Math.random() * (i + 1));
        [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
      }
      this.films = shuffled;
      this.sortMode = 'shuffled';
    },
    async saveItem(film) {
      const key = this.filmKey(film);
      if (this.savingKey || this.savedKeys.has(key)) return;
      this.savingKey = key;
      try {
        const response = await fetch('/api/saved-items', {
          method: 'POST',
          credentials: 'same-origin',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRF-TOKEN': readCookie('csrf_access_token'),
          },
          body: JSON.stringify({
            itemType: 'film',
            title: film.title,
            subtitle: film.director,
            imageUrl: film.image,
            sourceUrl: this.sourceUrl(film.image),
          }),
        });
        if (response.status === 401) {
          window.location.href = '/login';
          return;
        }
        if (response.ok) {
          this.savedKeys.add(key);
        }
      } finally {
        this.savingKey = '';
      }
    },
    async share(film) {
      const url = this.sourceUrl(film.image);
      if (navigator.share) {
        try {
          await navigator.share({ title: film.title, url });
        } catch {
          // user cancelled the native share sheet — nothing to do
        }
        return;
      }
      try {
        await navigator.clipboard.writeText(url);
        const key = this.filmKey(film);
        this.copiedKey = key;
        setTimeout(() => {
          if (this.copiedKey === key) this.copiedKey = '';
        }, 1600);
      } catch {
        window.open(url, '_blank', 'noopener');
      }
    },
    formatYear(year) {
      if (year == null) return '';
      return year < 0 ? `${Math.abs(year)} BCE` : `${year}`;
    },
    lifespan(film) {
      if (film.birthYear && film.deathYear) {
        return `${this.formatYear(film.birthYear)}–${this.formatYear(film.deathYear)}`;
      }
      if (film.birthYear) return `b. ${this.formatYear(film.birthYear)}`;
      return '';
    },
    feedUrl() {
      const params = new URLSearchParams({ offset: this.offset });
      if (this.selectedGenre) params.set('genre', this.selectedGenre);
      return `/api/film-feed?${params.toString()}`;
    },
    async loadMore() {
      if (this.loading || this.exhausted || this.error) return;
      this.loading = true;
      try {
        const response = await fetch(this.feedUrl());
        if (!response.ok) throw new Error(`Request failed: ${response.status}`);
        const page = await response.json();
        if (page.length === 0) {
          this.exhausted = true;
        } else {
          this.films = this.films.concat(page);
          this.offset += page.length;
        }
      } catch {
        this.error = true;
      } finally {
        this.loading = false;
      }
    },
    retry() {
      this.error = false;
      this.loadMore();
    },
    sourceUrl(image) {
      try {
        const url = new URL(image);
        const filename = decodeURIComponent(url.pathname.split('/').pop());
        return `https://commons.wikimedia.org/wiki/File:${encodeURIComponent(filename)}`;
      } catch {
        return image;
      }
    },
  },
};
</script>

<template>
  <div class="art-feed">
    <header class="art-header">
      <h1>Movies</h1>
      <p class="subtitle">Browse films by genre — pick one, shuffle, or sort by release.</p>
      <div class="filter-row">
        <!-- TODO: known Firefox bug — same topic-select issue as ArticleGraph.vue,
             selecting an option sometimes doesn't fire `change`. Not yet fixed. -->
        <select
          v-model="selectedGenre"
          class="topic-select"
          :disabled="loading"
        >
          <option value="">All genres</option>
          <option v-for="genre in genres" :key="genre.id" :value="genre.id">{{ genre.label }}</option>
        </select>
        <select
          v-model="sortMode"
          class="topic-select"
        >
          <option value="oldest">Oldest first</option>
          <option value="newest">Newest first</option>
        </select>
        <button type="button" class="shuffle-button" @click="shuffle">Shuffle</button>
      </div>
    </header>

    <div class="art-grid">
      <article v-for="(film, index) in displayedFilms" :key="film.title + film.year + index" class="art-card">
        <a :href="sourceUrl(film.image)" target="_blank" rel="noopener">
          <img :src="film.image" :alt="film.title" loading="lazy" class="art-image">
        </a>
        <div class="art-body">
          <h2><a :href="sourceUrl(film.image)" target="_blank" rel="noopener">{{ film.title }}</a></h2>
          <p class="art-meta">
            {{ film.director }}
            <template v-if="lifespan(film)"> ({{ lifespan(film) }})</template>
          </p>
          <p class="art-year" v-if="film.year != null">{{ formatYear(film.year) }} · {{ film.genre }}</p>
          <div class="art-footer">
            <button
              type="button"
              class="share-button"
              :disabled="savedKeys.has(filmKey(film))"
              @click="saveItem(film)"
            >{{ savedKeys.has(filmKey(film)) ? 'Saved' : (savingKey === filmKey(film) ? 'Saving…' : 'Save') }}</button>
            <button type="button" class="share-button" @click="share(film)">
              {{ copiedKey === filmKey(film) ? 'Link copied' : 'Share' }}
            </button>
          </div>
        </div>
      </article>
    </div>

    <div ref="sentinel" class="art-sentinel">
      <LoadingSpinner v-if="loading" size="sm" label="Loading more…" inline />
      <template v-else-if="error">
        <span>Couldn't load more.</span>
        <button type="button" class="retry-button" @click="retry">Retry</button>
      </template>
      <span v-else-if="exhausted">You've reached the end.</span>
    </div>
  </div>
</template>

<style scoped>
.art-feed {
  max-width: 1100px;
  margin: 0 auto;
  padding: 1.5rem 1.25rem 3rem;
}
.art-header h1 {
  margin: 0 0 0.1rem;
  font-size: 1.1rem;
}
.subtitle {
  color: var(--text-secondary, #52514e);
  font-size: 0.8rem;
  margin: 0 0 0.9rem;
}
.filter-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-top: 0.6rem;
}
.topic-select {
  border: 1px solid var(--gridline, #e1e0d9);
  background: var(--card-bg, #fff);
  color: var(--text-primary, inherit);
  border-radius: var(--pill-radius, 999px);
  padding: 0.4rem 2rem 0.4rem 0.9rem;
  font-size: 0.78rem;
  font-weight: 600;
  cursor: pointer;
  appearance: none;
  -webkit-appearance: none;
  background-image: linear-gradient(45deg, transparent 50%, currentColor 50%), linear-gradient(135deg, currentColor 50%, transparent 50%);
  background-position: calc(100% - 16px) calc(50% - 2px), calc(100% - 11px) calc(50% - 2px);
  background-size: 5px 5px, 5px 5px;
  background-repeat: no-repeat;
}
.topic-select:disabled {
  opacity: 0.6;
  cursor: default;
}
.shuffle-button {
  border: 1px solid var(--gridline, #e1e0d9);
  background: transparent;
  color: var(--text-secondary, #52514e);
  border-radius: var(--pill-radius, 999px);
  padding: 0.4rem 0.9rem;
  font-size: 0.78rem;
  font-weight: 600;
  cursor: pointer;
}
.shuffle-button:hover {
  border-color: var(--series-1, #5b5bf0);
  color: var(--series-1, #5b5bf0);
}
.art-grid {
  columns: 1;
  column-gap: 1.25rem;
  margin-top: 1.5rem;
}
@media (min-width: 641px) {
  .art-grid {
    columns: 2;
  }
}
@media (min-width: 961px) {
  .art-grid {
    columns: 3;
  }
}
.art-card {
  break-inside: avoid;
  margin-bottom: 1.5rem;
  background: var(--card-bg, #fff);
  border-radius: var(--card-radius, 16px);
  padding: 0.6rem 0.6rem 0.8rem;
  box-shadow: 0 8px 24px rgba(20, 23, 31, 0.08);
}
.art-image {
  width: 100%;
  object-fit: contain;
  background: var(--gridline, #e1e0d9);
  display: block;
  border-radius: calc(var(--card-radius, 16px) - 6px);
}
.art-body h2 {
  font-size: 1rem;
  margin: 0.6rem 0 0.2rem;
}
.art-body h2 a {
  color: inherit;
  text-decoration: none;
}
.art-body h2 a:hover {
  text-decoration: underline;
}
.art-meta {
  margin: 0;
  font-size: 0.85rem;
  color: var(--text-primary, #0b0b0b);
}
.art-year {
  margin: 0.15rem 0 0;
  font-size: 0.75rem;
  color: var(--text-secondary, #52514e);
}
.art-sentinel {
  text-align: center;
  color: var(--text-secondary, #52514e);
  font-size: 0.8rem;
  padding: 1.5rem 0;
}
.retry-button {
  margin-left: 0.6rem;
  background: transparent;
  border: 1px solid var(--gridline, #e1e0d9);
  color: var(--series-1, #2a78d6);
  border-radius: 999px;
  padding: 0.25rem 0.75rem;
  font-size: 0.78rem;
  cursor: pointer;
}
.retry-button:hover {
  border-color: var(--series-1, #2a78d6);
}
.art-footer {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 0.5rem;
  margin-top: 0.5rem;
}
.share-button:disabled {
  opacity: 0.6;
  cursor: default;
}
.share-button {
  background: transparent;
  border: 1px solid var(--gridline, #e1e0d9);
  color: var(--series-1, #2a78d6);
  border-radius: 999px;
  padding: 0.2rem 0.7rem;
  font-size: 0.72rem;
  cursor: pointer;
}
.share-button:hover {
  border-color: var(--series-1, #2a78d6);
}
</style>
