<script>
export default {
  name: 'LoadingSpinner',
  props: {
    label: { type: String, default: 'Loading…' },
    size: { type: String, default: 'md' }, // sm | md | lg
    inline: { type: Boolean, default: false },
  },
};
</script>

<template>
  <span class="loading-spinner" :class="[`size-${size}`, { inline }]" role="status">
    <span class="spinner-ring" aria-hidden="true"></span>
    <span v-if="label" class="spinner-label">{{ label }}</span>
  </span>
</template>

<style scoped>
.loading-spinner {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 1.5rem 0;
  color: var(--text-secondary, #5b6270);
}
.loading-spinner.inline {
  display: inline-flex;
  padding: 0;
}
.spinner-ring {
  display: block;
  flex: none;
  border-radius: 50%;
  border: 2.5px solid var(--gridline, #e2e5eb);
  border-top-color: var(--series-1, #5b5bf0);
  animation: spinner-rotate 0.7s linear infinite;
}
.size-sm .spinner-ring { width: 14px; height: 14px; border-width: 2px; }
.size-md .spinner-ring { width: 22px; height: 22px; }
.size-lg .spinner-ring { width: 32px; height: 32px; border-width: 3px; }
.spinner-label {
  font-size: 0.85rem;
}
@keyframes spinner-rotate {
  to { transform: rotate(360deg); }
}
@media (prefers-reduced-motion: reduce) {
  .spinner-ring {
    animation-duration: 1.6s;
  }
}
</style>
