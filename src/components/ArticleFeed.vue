<script>
function readCookie(name) {
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : null;
}

import LoadingSpinner from './LoadingSpinner.vue';

export default {
  name: 'ArticleFeed',
  components: { LoadingSpinner },
  props: {
    initialArticle: { type: Object, required: true },
    topics: { type: Array, default: () => [] },
  },
  data() {
    return {
      history: [this.initialArticle],
      currentIndex: 0,
      loading: false,
      navigating: false,
      direction: 'up',
      selectedTopic: '',
      atStartFlash: false,
      savedTitles: new Set(),
      savingTitle: '',
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
  watch: {
    async selectedTopic() {
      if (this.loading) return;
      this.direction = 'up';
      this.history = [];
      this.currentIndex = -1;
      await this.appendRandomArticle();
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
    cardScrollState() {
      const card = this.$refs.cardEl;
      if (!card) return { atTop: true, atBottom: true };
      return {
        atTop: card.scrollTop <= 0,
        atBottom: card.scrollTop + card.clientHeight >= card.scrollHeight - 1,
      };
    },
    onWheel(event) {
      if (this.loading || this.navigating) return;
      const { atTop, atBottom } = this.cardScrollState();
      if (event.deltaY > 20 && atBottom) this.goNext();
      else if (event.deltaY < -20 && atTop) this.goBack();
    },
    onTouchStart(event) {
      this.touchStartY = event.touches[0].clientY;
    },
    onTouchEnd(event) {
      if (this.loading || this.navigating || this.touchStartY == null) return;
      const deltaY = this.touchStartY - event.changedTouches[0].clientY;
      const { atTop, atBottom } = this.cardScrollState();
      if (deltaY > 40 && atBottom) this.goNext();
      else if (deltaY < -40 && atTop) this.goBack();
      this.touchStartY = null;
    },
    startNavigationCooldown() {
      this.navigating = true;
      setTimeout(() => {
        this.navigating = false;
      }, 400);
    },
    async goNext() {
      this.startNavigationCooldown();
      this.direction = 'up';
      if (this.currentIndex < this.history.length - 1) {
        this.currentIndex += 1;
        return;
      }
      await this.appendRandomArticle();
    },
    goBack() {
      if (!this.canGoBack) {
        this.atStartFlash = true;
        setTimeout(() => {
          this.atStartFlash = false;
        }, 900);
        return;
      }
      this.startNavigationCooldown();
      this.direction = 'down';
      this.currentIndex -= 1;
    },
    async appendRandomArticle() {
      this.loading = true;
      try {
        const url = this.selectedTopic
          ? `/api/random-article?topic=${encodeURIComponent(this.selectedTopic)}`
          : '/api/random-article';
        const response = await fetch(url);
        const article = await response.json();
        this.history.push(article);
        this.currentIndex = this.history.length - 1;
      } finally {
        this.loading = false;
      }
    },
    async saveCurrentArticle() {
      const article = this.currentArticle;
      if (this.savingTitle || this.savedTitles.has(article.title)) return;
      this.savingTitle = article.title;
      try {
        const response = await fetch('/api/saved-items', {
          method: 'POST',
          credentials: 'same-origin',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRF-TOKEN': readCookie('csrf_access_token'),
          },
          body: JSON.stringify({
            itemType: 'article',
            title: article.title,
            imageUrl: article.thumbnail ? article.thumbnail.source : '',
            sourceUrl: article.content_urls.desktop.page,
          }),
        });
        if (response.status === 401) {
          window.location.href = '/login';
          return;
        }
        if (response.ok) {
          this.savedTitles.add(article.title);
        }
      } finally {
        this.savingTitle = '';
      }
    },
  },
};
</script>

<template>
  <div class="feed-root">
    <header class="feed-header">
      <h1>Hello!</h1>
      <p class="subtitle">Swipe up for a new article, down to go back.</p>
      <select
        v-model="selectedTopic"
        class="topic-select"
        :disabled="loading"
      >
        <option value="">All topics</option>
        <option v-for="topic in topics" :key="topic" :value="topic">{{ topic }}</option>
      </select>
    </header>

    <div v-if="canGoBack" class="swipe-hint swipe-hint-up" aria-hidden="true">︿</div>
    <Transition v-if="currentArticle" :name="direction === 'up' ? 'slide-up' : 'slide-down'" mode="out-in">
      <article :key="currentIndex" ref="cardEl" class="feed-card" :class="{ cooling: navigating }">
        <div v-if="currentArticle.thumbnail" class="feed-image">
          <img :src="currentArticle.thumbnail.source" :alt="currentArticle.title">
        </div>
        <div class="feed-body">
          <div class="feed-body-header">
            <h2><a :href="currentArticle.content_urls.desktop.page" target="_blank">{{ currentArticle.title }}</a></h2>
            <button
              type="button"
              class="save-button"
              :disabled="savedTitles.has(currentArticle.title)"
              @click="saveCurrentArticle"
            >{{ savedTitles.has(currentArticle.title) ? 'Saved' : (savingTitle === currentArticle.title ? 'Saving…' : 'Save') }}</button>
          </div>
          <p>{{ currentArticle.extract }}</p>
        </div>
      </article>
    </Transition>
    <div class="swipe-hint swipe-hint-down" aria-hidden="true">﹀</div>

    <div v-if="atStartFlash" class="edge-message">You're at the start</div>
    <LoadingSpinner v-if="loading" class="feed-loading" inline />
  </div>
</template>

<style scoped>
.feed-root {
  position: relative;
  height: calc(100dvh - var(--navbar-height, 44px));
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding: env(safe-area-inset-top) env(safe-area-inset-right) env(safe-area-inset-bottom) env(safe-area-inset-left);
}
.swipe-hint {
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
  z-index: 3;
  color: var(--text-secondary, #52514e);
  opacity: 0.5;
  font-size: 1.1rem;
  line-height: 1;
  pointer-events: none;
}
.swipe-hint-up {
  top: calc(var(--navbar-height, 44px) + 0.25rem);
}
.swipe-hint-down {
  bottom: 0.5rem;
  animation: hint-bob 1.8s ease-in-out infinite;
}
@keyframes hint-bob {
  0%, 100% { transform: translate(-50%, 0); }
  50% { transform: translate(-50%, 4px); }
}
.feed-card.cooling {
  opacity: 0.55;
  transition: opacity 0.15s ease;
}
.edge-message {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  z-index: 4;
  background: var(--surface-1, #fcfcfb);
  color: var(--text-primary, #0b0b0b);
  border: 1px solid var(--gridline, #e1e0d9);
  border-radius: 999px;
  padding: 0.4rem 1rem;
  font-size: 0.8rem;
  box-shadow: 0 2px 8px rgba(63, 51, 38, 0.2);
  pointer-events: none;
}
.feed-header {
  flex: none;
  padding: 1rem 1.25rem 0.5rem;
}
.topic-select {
  display: block;
  margin-top: 0.6rem;
  border: 1px solid var(--gridline, #e1e0d9);
  background: var(--card-bg, #fff);
  color: var(--text-primary, inherit);
  border-radius: var(--pill-radius, 999px);
  padding: 0.4rem 2rem 0.4rem 0.9rem;
  font-size: 0.82rem;
  font-weight: 600;
  text-transform: capitalize;
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
.feed-header h1 {
  margin: 0;
  font-size: 1.1rem;
}
.subtitle {
  color: var(--text-secondary, #52514e);
  font-size: 0.8rem;
  margin: 0.15rem 0 0;
}
.feed-card {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
}
.feed-image {
  flex: none;
  max-height: 40vh;
  overflow: hidden;
}
.feed-image img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}
.feed-body {
  padding: 1rem 1.25rem 2rem;
}
.feed-body-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.75rem;
  margin: 0 0 0.5rem;
}
.feed-body h2 {
  margin: 0;
}
.save-button {
  flex: none;
  background: transparent;
  border: 1px solid var(--gridline, #e1e0d9);
  color: var(--series-1, #2a78d6);
  border-radius: 999px;
  padding: 0.25rem 0.75rem;
  font-size: 0.78rem;
  cursor: pointer;
}
.save-button:disabled {
  opacity: 0.6;
  cursor: default;
}
.feed-loading {
  flex: none;
  text-align: center;
  color: var(--text-secondary, #52514e);
  padding: 0.75rem;
}

.slide-up-enter-active, .slide-up-leave-active,
.slide-down-enter-active, .slide-down-leave-active {
  transition: transform 0.2s ease, opacity 0.2s ease;
}
.slide-up-enter-from { transform: translateY(24px); opacity: 0; }
.slide-up-leave-to { transform: translateY(-24px); opacity: 0; }
.slide-down-enter-from { transform: translateY(-24px); opacity: 0; }
.slide-down-leave-to { transform: translateY(24px); opacity: 0; }

@media (min-width: 641px) {
  .feed-root {
    height: auto;
    min-height: 100dvh;
    max-width: 640px;
    margin: 0 auto;
    overflow: visible;
  }
  .feed-card {
    overflow-y: visible;
  }
  .feed-image {
    max-height: 320px;
    border-radius: 6px;
    margin-top: 0.5rem;
  }
}
</style>