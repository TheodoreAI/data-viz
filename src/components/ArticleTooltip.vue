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
  --surface: #f3e9d2;
  --ink: #3f3326;
  --ink-soft: #6b5d47;
  --blue: #2f6690;
  --blue-faint: rgba(47, 102, 144, 0.22);
  --olive: #74804a;
  --gold: #b8935a;
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
}
.t-close:hover {
  border-color: var(--blue);
  box-shadow: 0 0 8px var(--blue-faint);
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
  border-radius: 0;
  border: 1px solid var(--olive);
  display: block;
  margin: 0 0 1rem;
  filter: sepia(0.35) saturate(1.1);
}
.t-meta {
  font-size: 1rem;
  color: var(--ink-soft);
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