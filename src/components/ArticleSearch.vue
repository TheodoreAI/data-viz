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
  background: var(--surface);
  border: 1px solid var(--olive);
  color: var(--ink);
  border-radius: 10px;
  padding: 0.5rem 0.75rem;
  font-family: inherit;
  font-size: 0.9rem;
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}
.search-input:focus {
  outline: none;
  border-color: var(--blue);
  box-shadow: 0 0 0 2px var(--blue-faint);
}
.search-input:disabled {
  opacity: 0.6;
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
  background: var(--surface);
  border: 1px solid var(--olive);
  border-radius: 12px;
  max-height: 260px;
  overflow-y: auto;
  box-shadow: 0 6px 16px rgba(63, 51, 38, 0.18);
}
.search-results li button {
  display: block;
  width: 100%;
  text-align: left;
  background: none;
  border: none;
  border-radius: 8px;
  color: var(--ink);
  font-family: inherit;
  font-size: 0.85rem;
  padding: 0.45rem 0.75rem;
  cursor: pointer;
  transition: background-color 0.15s ease, color 0.15s ease;
}
.search-results li button:hover {
  background: var(--blue-faint);
  color: var(--blue);
}
</style>