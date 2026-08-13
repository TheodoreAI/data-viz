<script>
const SEARCH_DEBOUNCE_MS = 250;
const BLUR_CLOSE_MS = 150;

export default {
  name: 'ArticleSearch',
  emits: ['select'],
  props: {
    disabled: { type: Boolean, default: false },
  },
  data() {
    return {
      query: '',
      results: [],
      open: false,
    };
  },
  created() {
    this.searchTimer = null;
  },
  beforeUnmount() {
    if (this.searchTimer) clearTimeout(this.searchTimer);
  },
  methods: {
    onInput() {
      this.open = true;
      if (this.searchTimer) clearTimeout(this.searchTimer);
      const query = this.query.trim();
      if (!query) {
        this.results = [];
        return;
      }
      this.searchTimer = setTimeout(async () => {
        try {
          const response = await fetch(`/api/article-search?q=${encodeURIComponent(query)}`);
          this.results = await response.json();
        } catch {
          this.results = [];
        }
      }, SEARCH_DEBOUNCE_MS);
    },
    selectResult(title) {
      this.open = false;
      this.query = '';
      this.results = [];
      this.$emit('select', title);
    },
    onBlur() {
      setTimeout(() => {
        this.open = false;
      }, BLUR_CLOSE_MS);
    },
  },
};
</script>

<template>
  <div class="search-row">
    <input
      v-model="query"
      type="text"
      class="search-input"
      placeholder="Search for an article…"
      :disabled="disabled"
      @input="onInput"
      @focus="open = true"
      @blur="onBlur"
    >
    <ul v-if="open && results.length" class="search-results">
      <li v-for="result in results" :key="result">
        <button type="button" @click="selectResult(result)">{{ result }}</button>
      </li>
    </ul>
  </div>
</template>

<style scoped>
.search-row {
  position: relative;
  margin: 0 0 0.75rem;
}
.search-input {
  width: 100%;
  box-sizing: border-box;
  background: var(--card-bg, #ffffff);
  border: 1px solid var(--gridline, #d8c9a3);
  color: var(--text-primary, #0d2e30);
  border-radius: var(--radius-md, 0.625rem);
  padding: 0.5rem 0.75rem;
  font-family: inherit;
  font-size: 0.9rem;
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}
.search-input:focus {
  outline: none;
  border-color: var(--series-1, #0068d9);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--series-1, #0068d9) 18%, transparent);
}
.search-input:disabled {
  opacity: 0.4;
  cursor: default;
}
.search-results {
  position: absolute;
  top: calc(100% + 6px);
  left: 0;
  right: 0;
  z-index: 30;
  list-style: none;
  margin: 0;
  padding: 0.35rem;
  background: var(--card-bg, #ffffff);
  border: 1px solid var(--gridline, #d8c9a3);
  border-radius: var(--card-radius, 0.875rem);
  max-height: 260px;
  overflow-y: auto;
  box-shadow: var(--shadow-raised, 0 6px 16px rgba(63, 51, 38, 0.18));
}
.search-results li button {
  display: block;
  width: 100%;
  text-align: left;
  background: none;
  border: none;
  border-radius: var(--radius-md, 0.625rem);
  color: var(--text-primary, #0d2e30);
  font-family: inherit;
  font-size: 0.85rem;
  padding: 0.45rem 0.75rem;
  cursor: pointer;
  transition: background-color 0.15s ease, color 0.15s ease;
}
.search-results li button:hover {
  background: var(--series-1-fill, color-mix(in srgb, #0068d9 24%, transparent));
  color: var(--series-1, #0068d9);
}
</style>