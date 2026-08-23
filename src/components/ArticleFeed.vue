<script>
function readCookie(name) {
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : null;
}

import LoadingSpinner from './LoadingSpinner.vue';
import { useSwipe } from '@vueuse/core';

export default {
  name: 'ArticleFeed',
  components: { LoadingSpinner },
  props: {
    initialArticle: { type: Object, required: true },
    topics: { type: Array, default: () => [] },
    defaultTopic: { type: String, default: '' },
  },
  data() {
    return {
      history: [this.initialArticle],
      currentIndex: 0,
      loading: false,
      navigating: false,
      direction: 'up',
      selectedTopic: this.defaultTopic,
      atStartFlash: false,
      savedTitles: new Set(),
      savingTitle: '',
      feedError: '',
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
    document.body.classList.add('feed-active');
    window.addEventListener('wheel', this.onWheel, { passive: true });
    this.swipe = useSwipe(window, {
      threshold: 40,
      onSwipeEnd: (_event, direction) => {
        if (this.loading || this.navigating) return;
        const { atTop, atBottom } = this.cardScrollState();
        if (direction === 'up' && atBottom) this.goNext();
        else if (direction === 'down' && atTop) this.goBack();
      },
    });
  },
  beforeUnmount() {
    document.body.classList.remove('feed-active');
    window.removeEventListener('wheel', this.onWheel);
    this.swipe?.stop();
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
      this.feedError = '';
      try {
        const params = new URLSearchParams();
        if (this.selectedTopic) params.set('topic', this.selectedTopic);
        const seenTitles = this.history.slice(-50).map((article) => article.title);
        if (seenTitles.length) params.set('exclude', seenTitles.join('|'));
        const url = `/api/random-article?${params.toString()}`;
        const response = await fetch(url);
        const article = await response.json();
        if (!response.ok) throw new Error(article.error || 'Could not load an article.');
        this.history.push(article);
        this.currentIndex = this.history.length - 1;
      } catch (err) {
        this.feedError = err.message || 'Could not load an article. Please try again.';
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
      <div class="kicker">On Display</div>
      <h1>Data Viz</h1>
    </header>

    <nav class="topic-row" aria-label="Filter by topic">
      <button
        type="button"
        class="topic-pill"
        :class="{ active: selectedTopic === '' }"
        :disabled="loading"
        @click="selectedTopic = ''"
      >All</button>
      <button
        v-for="topic in topics"
        :key="topic"
        type="button"
        class="topic-pill"
        :class="{ active: selectedTopic === topic }"
        :disabled="loading"
        @click="selectedTopic = topic"
      >{{ topic }}</button>
    </nav>

    <div v-if="canGoBack" class="swipe-hint swipe-hint-up" aria-hidden="true">︿</div>
    <Transition v-if="currentArticle" :name="direction === 'up' ? 'slide-up' : 'slide-down'" mode="out-in">
      <article :key="currentIndex" ref="cardEl" class="feed-card" :class="{ cooling: navigating }">
        <div class="feed-card-inner">
          <img v-if="currentArticle.thumbnail" class="feed-card-image" :src="currentArticle.thumbnail.source" :alt="currentArticle.title">
          <h2><a :href="currentArticle.content_urls.desktop.page" target="_blank">{{ currentArticle.title }}</a></h2>
          <p>{{ currentArticle.extract }}</p>
          <hr class="caption-rule">
          <div class="feed-card-actions">
            <a :href="currentArticle.content_urls.desktop.page" target="_blank" class="read-more-link">Read Full Entry</a>
            <button
              type="button"
              class="save-button"
              :disabled="savedTitles.has(currentArticle.title)"
              @click="saveCurrentArticle"
            >{{ savedTitles.has(currentArticle.title) ? 'Saved' : (savingTitle === currentArticle.title ? 'Saving…' : 'Save to Collection') }}</button>
          </div>
        </div>
      </article>
    </Transition>
    <div class="swipe-hint swipe-hint-down" aria-hidden="true">﹀</div>

    <div v-if="atStartFlash" class="edge-message">You're at the start</div>
    <p v-if="feedError" class="status feed-error" role="alert">{{ feedError }}</p>
    <LoadingSpinner v-if="loading" class="feed-loading" inline />
    <p class="scroll-note">Scroll down for the next exhibit</p>
  </div>
</template>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Serif:wght@400;500;600&family=Inter:wght@400;500;600;700&display=swap');

.feed-root {
  --mp-wall: #f7f6f3;
  --mp-frame: #e4e1d9;
  --mp-frame-strong: #22201b;
  --mp-ink: #22201b;
  --mp-ink-soft: #756f60;

  position: relative;
  height: calc(100dvh - var(--navbar-height, 44px));
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding: env(safe-area-inset-top) env(safe-area-inset-right) env(safe-area-inset-bottom) env(safe-area-inset-left);
  background: var(--mp-wall);
  color: var(--mp-ink);
  font-family: "IBM Plex Serif", Georgia, serif;
}

@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) .feed-root {
    --mp-wall: #171613;
    --mp-frame: #34312a;
    --mp-frame-strong: #d9d5c9;
    --mp-ink: #f0eee6;
    --mp-ink-soft: #a39d8b;
  }
}
:root[data-theme="dark"] .feed-root {
  --mp-wall: #171613;
  --mp-frame: #34312a;
  --mp-frame-strong: #d9d5c9;
  --mp-ink: #f0eee6;
  --mp-ink-soft: #a39d8b;
}

.swipe-hint {
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
  z-index: 3;
  color: var(--mp-ink-soft);
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
  background: var(--mp-wall);
  color: var(--mp-ink);
  border: 1px solid var(--mp-frame);
  border-radius: 999px;
  padding: 0.4rem 1rem;
  font-family: Inter, sans-serif;
  font-size: 0.8rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
  pointer-events: none;
}
.feed-error {
  flex: none;
  text-align: center;
  color: #b0413e;
  font-family: Inter, sans-serif;
  font-size: 0.85rem;
  padding: 0.5rem 1.25rem;
}
.feed-header {
  flex: none;
  text-align: center;
  padding: 1.25rem 1.1rem 0.5rem;
}
.kicker {
  font-family: Inter, sans-serif;
  font-size: 0.66rem;
  letter-spacing: 0.22em;
  text-transform: uppercase;
  color: var(--mp-ink-soft);
  margin-bottom: 0.5rem;
}
.feed-header h1 {
  margin: 0;
  font-size: 1.1rem;
  font-weight: 500;
  letter-spacing: 0.01em;
}
.topic-row {
  flex: none;
  display: flex;
  justify-content: center;
  gap: 0.4rem;
  flex-wrap: wrap;
  padding: 0.75rem 1rem 0.5rem;
  font-family: Inter, sans-serif;
}
.topic-pill {
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
.topic-pill:hover {
  color: var(--mp-ink);
}
.topic-pill.active {
  color: var(--mp-ink);
  border-color: var(--mp-frame-strong);
}
.topic-pill:disabled {
  opacity: 0.6;
  cursor: default;
}
.feed-card {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  display: flex;
  padding: 0.5rem 1.1rem 1rem;
}
.feed-card-inner {
  flex: 1;
  border: 1px solid var(--mp-frame);
  padding: 1.5rem;
  text-align: start;
}
.feed-card-image {
  width: 100%;
  max-height: 280px;
  object-fit: cover;
  display: block;
  margin: 0 auto 1.5rem;
}
.feed-card-inner h2 {
  margin: 0 0 1rem;
  font-size: 1.4rem;
  font-weight: 600;
  line-height: 1.2;
}
.feed-card-inner h2 a {
  color: inherit;
  text-decoration: none;
}
.feed-card-inner p {
  margin: 0 0 1.5rem;
  font-size: 0.9rem;
  line-height: 1.8;
  color: var(--mp-ink);
}
.caption-rule {
  border: none;
  border-top: 1px solid var(--mp-frame);
  width: 40px;
  margin: 0 auto 1.5rem;
}
.feed-card-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  align-items: center;
  row-gap: 0.5rem;
  column-gap: 1.25rem;
  font-family: Inter, sans-serif;
}
.read-more-link {
  color: var(--mp-ink-soft);
  text-decoration: none;
  font-size: 0.75rem;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}
.read-more-link:hover {
  color: var(--mp-ink);
}
.save-button {
  background: none;
  border: none;
  color: var(--mp-ink-soft);
  font-family: inherit;
  font-size: 0.75rem;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  cursor: pointer;
  padding: 0;
}
.save-button:hover:not(:disabled) {
  color: var(--mp-ink);
}
.save-button:disabled {
  opacity: 0.6;
  cursor: default;
}
.feed-loading {
  flex: none;
  text-align: center;
  color: var(--mp-ink-soft);
  font-family: Inter, sans-serif;
  padding: 0.75rem;
}
.scroll-note {
  flex: none;
  text-align: center;
  font-family: Inter, sans-serif;
  font-size: 0.68rem;
  letter-spacing: 0.05em;
  color: var(--mp-ink-soft);
  margin: 0.5rem 0 0.75rem;
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
  .feed-card-image {
    max-height: 340px;
  }
}
</style>