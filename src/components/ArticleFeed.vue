<script>
export default {
  name: 'ArticleFeed',
  props: {
    initialArticle: { type: Object, required: true },
    personName: { type: String, required: true },
  },
  data() {
    return {
      history: [this.initialArticle],
      currentIndex: 0,
      loading: false,
      direction: 'up',
    };
  },
  computed: {
    currentArticle() {
      return this.history[this.currentIndex];
    },
    canGoBack() {
      return this.currentIndex > 0;
    },
  },
  mounted() {
    window.addEventListener('wheel', this.onWheel, { passive: true });
    window.addEventListener('touchstart', this.onTouchStart, { passive: true });
    window.addEventListener('touchend', this.onTouchEnd, { passive: true });
  },
  beforeUnmount() {
    window.removeEventListener('wheel', this.onWheel);
    window.removeEventListener('touchstart', this.onTouchStart);
    window.removeEventListener('touchend', this.onTouchEnd);
  },
  methods: {
    onWheel(event) {
      if (this.loading) return;
      if (event.deltaY > 20) this.goNext();
      else if (event.deltaY < -20) this.goBack();
    },
    onTouchStart(event) {
      this.touchStartY = event.touches[0].clientY;
    },
    onTouchEnd(event) {
      if (this.loading || this.touchStartY == null) return;
      const deltaY = this.touchStartY - event.changedTouches[0].clientY;
      if (deltaY > 40) this.goNext();
      else if (deltaY < -40) this.goBack();
      this.touchStartY = null;
    },
    async goNext() {
      this.direction = 'up';
      if (this.currentIndex < this.history.length - 1) {
        this.currentIndex += 1;
        return;
      }
      this.loading = true;
      try {
        const response = await fetch('/api/random-article');
        const article = await response.json();
        this.history.push(article);
        this.currentIndex += 1;
      } finally {
        this.loading = false;
      }
    },
    goBack() {
      if (!this.canGoBack) return;
      this.direction = 'down';
      this.currentIndex -= 1;
    },
  },
};
</script>

<template>
  <div class="feed-root">
    <h1>Hello {{ personName }}!</h1>
    <p class="subtitle">Scroll or swipe up for a new random article, down to go back.</p>

    <Transition :name="direction === 'up' ? 'slide-up' : 'slide-down'" mode="out-in">
      <article :key="currentIndex" class="feed-card">
        <h2><a :href="currentArticle.content_urls.desktop.page" target="_blank">{{ currentArticle.title }}</a></h2>
        <img v-if="currentArticle.thumbnail" :src="currentArticle.thumbnail.source" :alt="currentArticle.title">
        <p>{{ currentArticle.extract }}</p>
      </article>
    </Transition>

    <div v-if="loading" class="feed-loading">Loading…</div>
  </div>
</template>

<style scoped>
.feed-root {
  max-width: 640px;
  margin: 0 auto;
  padding: 1.5rem;
}
.subtitle {
  color: var(--text-secondary, #52514e);
  font-size: 0.85rem;
}
.feed-card img {
  max-width: 100%;
  border-radius: 6px;
  margin: 0.75rem 0;
}
.feed-loading {
  text-align: center;
  color: var(--text-secondary, #52514e);
  padding: 1rem;
}

.slide-up-enter-active, .slide-up-leave-active,
.slide-down-enter-active, .slide-down-leave-active {
  transition: transform 0.2s ease, opacity 0.2s ease;
}
.slide-up-enter-from { transform: translateY(24px); opacity: 0; }
.slide-up-leave-to { transform: translateY(-24px); opacity: 0; }
.slide-down-enter-from { transform: translateY(-24px); opacity: 0; }
.slide-down-leave-to { transform: translateY(24px); opacity: 0; }
</style>