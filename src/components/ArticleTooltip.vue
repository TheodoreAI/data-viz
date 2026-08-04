<script>
import LoadingSpinner from './LoadingSpinner.vue';

export default {
  name: 'ArticleTooltip',
  components: { LoadingSpinner },
  emits: ['hover-start', 'hover-end', 'close'],
  props: {
    visible: { type: Boolean, default: false },
    title: { type: String, default: '' },
    extract: { type: String, default: '' },
    thumbnail: { type: String, default: null },
    loading: { type: Boolean, default: false },
  },
  computed: {
    wikipediaUrl() {
      return `https://en.wikipedia.org/wiki/${encodeURIComponent(this.title.replace(/ /g, '_'))}`;
    },
  },
};
</script>

<template>
  <Teleport to="body">
    <div
      v-if="visible"
      class="article-tooltip"
      @mouseenter="$emit('hover-start')"
      @mouseleave="$emit('hover-end')"
    >
      <button type="button" class="t-close" aria-label="Close" @click="$emit('close')">✕</button>
      <a
        v-if="title"
        class="t-title"
        :href="wikipediaUrl"
        target="_blank"
        rel="noopener"
      >{{ title }}</a>
      <img v-if="thumbnail" :src="thumbnail" :alt="title" class="t-thumb">
      <LoadingSpinner v-if="loading" class="t-meta" inline />
      <div v-else-if="extract" class="t-extract">{{ extract }}</div>
    </div>
  </Teleport>
</template>

<style scoped>
.article-tooltip {
  position: fixed;
  inset: 0;
  width: 100vw;
  height: 100dvh;
  box-sizing: border-box;
  z-index: 2000;
  background: var(--surface);
  box-shadow: inset 0 0 40px rgba(184, 147, 90, 0.18);
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 2rem;
  font-family: "Palatino Linotype", "Palatino", Georgia, serif;
  color: var(--ink);
  pointer-events: auto;
}
.t-close {
  position: absolute;
  bottom: 1rem;
  right: 1rem;
  width: 2.5rem;
  height: 2.5rem;
  border-radius: 50%;
  border: 1px solid var(--olive);
  background: var(--surface);
  color: var(--blue);
  font-family: inherit;
  font-size: 1.1rem;
  line-height: 1;
  cursor: pointer;
  box-shadow: 0 2px 6px rgba(63, 51, 38, 0.2);
  transition: background-color 0.15s ease, border-color 0.15s ease,
    color 0.15s ease, transform 0.15s ease, box-shadow 0.15s ease;
}
.t-close:hover {
  background: var(--blue);
  border-color: var(--blue);
  color: var(--surface);
  transform: translateY(-1px);
  box-shadow: 0 4px 10px rgba(63, 51, 38, 0.25);
}
.t-close:active {
  transform: translateY(0);
}
.t-title {
  display: block;
  pointer-events: auto;
  color: var(--blue);
  font-size: 1.6rem;
  font-weight: 600;
  text-decoration: none;
  cursor: pointer;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  margin-bottom: 1rem;
}
.t-title:hover {
  text-decoration: underline;
}
.t-thumb {
  width: 100%;
  max-height: 45vh;
  object-fit: cover;
  border-radius: 16px;
  border: 1px solid var(--olive);
  display: block;
  margin: 0 0 1rem;
  filter: sepia(0.35) saturate(1.1);
}
.t-meta {
  font-size: 1rem;
  color: var(--ink-soft);
}
.t-meta :deep(.spinner-ring) {
  border-color: var(--olive);
  border-top-color: var(--blue);
}
.t-extract {
  font-size: 1.05rem;
  line-height: 1.5;
  color: var(--ink-soft);
  max-height: 40vh;
  overflow-y: auto;
  -webkit-overflow-scrolling: touch;
  overscroll-behavior: contain;
}
</style>