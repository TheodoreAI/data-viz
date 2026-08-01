<script>
export default {
  name: 'ArtFeed',
  props: {
    initialPaintings: { type: Array, required: true },
    movements: { type: Array, default: () => [] },
  },
  data() {
    return {
      paintings: this.initialPaintings,
      offset: this.initialPaintings.length,
      selectedMovement: '',
      loading: false,
      exhausted: false,
      error: false,
    };
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
    formatYear(year) {
      if (year == null) return '';
      return year < 0 ? `${Math.abs(year)} BCE` : `${year}`;
    },
    lifespan(painting) {
      if (painting.birthYear && painting.deathYear) {
        return `${this.formatYear(painting.birthYear)}–${this.formatYear(painting.deathYear)}`;
      }
      if (painting.birthYear) return `b. ${this.formatYear(painting.birthYear)}`;
      return '';
    },
    feedUrl() {
      const params = new URLSearchParams({ offset: this.offset });
      if (this.selectedMovement) params.set('movement', this.selectedMovement);
      return `/api/art-feed?${params.toString()}`;
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
          this.paintings = this.paintings.concat(page);
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
    async selectMovement(movementId) {
      if (this.loading || movementId === this.selectedMovement) return;
      this.selectedMovement = movementId;
      this.paintings = [];
      this.offset = 0;
      this.exhausted = false;
      this.error = false;
      await this.loadMore();
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
      <h1>Art Movements</h1>
      <p class="subtitle">Shuffled paintings — pick a movement or browse them all.</p>
      <div class="topic-row">
        <button
          class="topic-pill"
          :class="{ active: selectedMovement === '' }"
          :disabled="loading"
          @click="selectMovement('')"
        >All</button>
        <button
          v-for="movement in movements"
          :key="movement.id"
          class="topic-pill"
          :class="{ active: selectedMovement === movement.id }"
          :disabled="loading"
          @click="selectMovement(movement.id)"
        >{{ movement.label }}</button>
      </div>
    </header>

    <div class="art-grid">
      <article v-for="(painting, index) in paintings" :key="painting.title + painting.year + index" class="art-card">
        <a :href="sourceUrl(painting.image)" target="_blank" rel="noopener">
          <img :src="painting.image" :alt="painting.title" loading="lazy" class="art-image">
        </a>
        <div class="art-body">
          <h2><a :href="sourceUrl(painting.image)" target="_blank" rel="noopener">{{ painting.title }}</a></h2>
          <p class="art-meta">
            {{ painting.artist }}
            <template v-if="lifespan(painting)"> ({{ lifespan(painting) }})</template>
          </p>
          <p class="art-year" v-if="painting.year != null">{{ formatYear(painting.year) }} · {{ painting.movement }}</p>
        </div>
      </article>
    </div>

    <div ref="sentinel" class="art-sentinel">
      <span v-if="loading">Loading more…</span>
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
.topic-row {
  display: flex;
  gap: 0.4rem;
  overflow-x: auto;
  margin-top: 0.6rem;
  padding-bottom: 0.2rem;
  mask-image: linear-gradient(to right, black calc(100% - 28px), transparent 100%);
  -webkit-mask-image: linear-gradient(to right, black calc(100% - 28px), transparent 100%);
}
.topic-pill {
  flex: none;
  border: 1px solid var(--gridline, #e1e0d9);
  background: transparent;
  color: var(--text-secondary, #52514e);
  border-radius: 999px;
  padding: 0.3rem 0.8rem;
  font-size: 0.78rem;
  cursor: pointer;
}
.topic-pill.active {
  background: var(--series-1, #2a78d6);
  border-color: var(--series-1, #2a78d6);
  color: #fff;
}
.topic-pill:disabled {
  opacity: 0.6;
  cursor: default;
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
}
.art-image {
  width: 100%;
  object-fit: contain;
  background: var(--gridline, #e1e0d9);
  display: block;
  border-radius: 4px;
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
</style>
