<script>
export default {
  name: 'ArtFeed',
  props: {
    initialPaintings: { type: Array, required: true },
  },
  data() {
    return {
      paintings: this.initialPaintings,
      offset: this.initialPaintings.length,
      loading: false,
      exhausted: false,
      error: false,
    };
  },
  computed: {
    feedItems() {
      return this.paintings.map((painting, index) => ({
        painting,
        showDivider: index === 0 || this.paintings[index - 1].movement !== painting.movement,
      }));
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
    async loadMore() {
      if (this.loading || this.exhausted || this.error) return;
      this.loading = true;
      try {
        const response = await fetch(`/api/art-feed?offset=${this.offset}`);
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
      <p class="subtitle">Paintings ordered chronologically by creation date — keep scrolling.</p>
    </header>

    <div class="art-list">
      <template v-for="item in feedItems" :key="item.painting.title + item.painting.year">
        <div v-if="item.showDivider" class="movement-divider">
          <span>{{ item.painting.movement }}<template v-if="item.painting.year != null"> · {{ formatYear(item.painting.year) }}</template></span>
        </div>
        <article class="art-card">
          <a :href="sourceUrl(item.painting.image)" target="_blank" rel="noopener">
            <img :src="item.painting.image" :alt="item.painting.title" loading="lazy" class="art-image">
          </a>
          <div class="art-body">
            <h2><a :href="sourceUrl(item.painting.image)" target="_blank" rel="noopener">{{ item.painting.title }}</a></h2>
            <p class="art-meta">
              {{ item.painting.artist }}
              <template v-if="lifespan(item.painting)"> ({{ lifespan(item.painting) }})</template>
            </p>
            <p class="art-year" v-if="item.painting.year != null">{{ formatYear(item.painting.year) }} · {{ item.painting.movement }}</p>
          </div>
        </article>
      </template>
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
  max-width: 640px;
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
  margin: 0 0 1.5rem;
}
.movement-divider {
  position: sticky;
  top: calc(var(--navbar-height, 44px) + 0.5rem);
  z-index: 5;
  text-align: center;
  margin: 1.5rem 0 1rem;
}
.movement-divider span {
  display: inline-block;
  background: var(--series-1, #2a78d6);
  color: #fff;
  font-size: 0.75rem;
  font-weight: 600;
  letter-spacing: 0.03em;
  text-transform: uppercase;
  padding: 0.35rem 0.9rem;
  border-radius: 999px;
}
.art-card {
  margin-bottom: 2rem;
}
.art-image {
  width: 100%;
  max-height: 60vh;
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