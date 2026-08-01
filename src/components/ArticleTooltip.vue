<script>
export default {
  name: 'ArticleTooltip',
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
      <div v-if="loading" class="t-meta">Loading…</div>
      <div v-else-if="extract" class="t-extract">{{ extract }}</div>
    </div>
  </Teleport>
</template>

<style scoped>
.article-tooltip {
  --crt-bg: #04140a;
  --crt-green: #33ff66;
  --crt-green-soft: #8dffb0;
  --crt-green-dim: #1a8f3f;
  --crt-green-faint: rgba(51, 255, 102, 0.25);
  position: fixed;
  inset: 0;
  width: 100vw;
  height: 100dvh;
  box-sizing: border-box;
  z-index: 2000;
  background: var(--crt-bg);
  box-shadow: inset 0 0 40px var(--crt-green-faint);
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 2rem;
  font-family: "Courier New", Courier, monospace;
  pointer-events: auto;
}
.t-close {
  position: absolute;
  /* lets place it at the bottom */
  bottom: 1rem;
  right: 1rem;
  width: 2.5rem;
  height: 2.5rem;
  border-radius: 50%;
  border: 1px solid var(--crt-green-dim);
  background: var(--crt-bg);
  color: var(--crt-green);
  font-family: inherit;
  font-size: 1.1rem;
  line-height: 1;
  cursor: pointer;
}
.t-close:hover {
  border-color: var(--crt-green);
  box-shadow: 0 0 8px var(--crt-green-faint);
}
.t-title {
  display: block;
  pointer-events: auto;
  color: var(--crt-green);
  font-size: 1.6rem;
  font-weight: 600;
  text-decoration: none;
  cursor: pointer;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  text-shadow: 0 0 8px var(--crt-green-faint);
  margin-bottom: 1rem;
}
.t-title:hover {
  text-decoration: underline;
}
.t-thumb {
  width: 100%;
  max-height: 45vh;
  object-fit: cover;
  border-radius: 0;
  border: 1px solid var(--crt-green-dim);
  display: block;
  margin: 0 0 1rem;
  filter: grayscale(0.3) sepia(0.15) hue-rotate(60deg) saturate(1.4);
}
.t-meta {
  font-size: 1rem;
  color: var(--crt-green-soft);
}
.t-extract {
  font-size: 1.05rem;
  line-height: 1.5;
  color: var(--crt-green-soft);
  max-height: 40vh;
  overflow-y: auto;
  -webkit-overflow-scrolling: touch;
  overscroll-behavior: contain;
}
</style>