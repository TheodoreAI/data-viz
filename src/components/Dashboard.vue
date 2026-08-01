<script>
function formatDate(iso) {
  if (!iso) return null;
  return new Date(iso).toLocaleDateString(undefined, { year: 'numeric', month: 'long', day: 'numeric' });
}

export default {
  name: 'Dashboard',
  data() {
    return {
      user: null,
      loading: true,
      error: false,
    };
  },
  computed: {
    memberSince() {
      return formatDate(this.user?.createdAt);
    },
    lastLogin() {
      return formatDate(this.user?.lastLoginAt);
    },
  },
  async mounted() {
    try {
      const response = await fetch('/api/profile', { credentials: 'same-origin' });
      if (response.status === 401) {
        window.location.href = '/login';
        return;
      }
      if (!response.ok) throw new Error(`Request failed: ${response.status}`);
      this.user = await response.json();
    } catch {
      this.error = true;
    } finally {
      this.loading = false;
    }
  },
};
</script>

<template>
  <div class="dashboard-page">
    <p v-if="loading" class="status">Loading…</p>
    <template v-else-if="error">
      <p class="status form-error">Couldn't load your dashboard. Please refresh the page.</p>
    </template>
    <template v-else-if="user">
      <h1>Welcome back, {{ user.displayName || user.username }}</h1>
      <p class="meta">
        <span v-if="memberSince">Member since {{ memberSince }}</span>
        <span v-if="lastLogin"> · Last login {{ lastLogin }}</span>
      </p>

      <div class="quick-links">
        <a href="/art" class="quick-link">
          <span class="quick-link-title">Art</span>
          <span class="quick-link-copy">Browse paintings by movement</span>
        </a>
        <a href="/graph" class="quick-link">
          <span class="quick-link-title">Graph</span>
          <span class="quick-link-copy">Explore article link graphs in 2D or 3D</span>
        </a>
        <a href="/bubbles" class="quick-link">
          <span class="quick-link-title">Bubbles</span>
          <span class="quick-link-copy">See yesterday's most-viewed articles</span>
        </a>
        <a href="/profile" class="quick-link">
          <span class="quick-link-title">Profile</span>
          <span class="quick-link-copy">Edit your bio, password, and account</span>
        </a>
      </div>
    </template>
  </div>
</template>

<style scoped>
.dashboard-page {
  max-width: 640px;
  margin: 0 auto;
  padding: 2rem 1.25rem 3rem;
}
h1 {
  font-size: 1.3rem;
  margin: 0 0 0.3rem;
}
.meta {
  color: var(--text-secondary, #6b5d47);
  font-size: 0.85rem;
  margin: 0 0 1.5rem;
}
.status {
  color: var(--text-secondary, #6b5d47);
  font-size: 0.9rem;
}
.form-error {
  color: #b0413e;
}
.quick-links {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.9rem;
}
@media (max-width: 480px) {
  .quick-links {
    grid-template-columns: 1fr;
  }
}
.quick-link {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  padding: 1rem;
  border: 1px solid var(--gridline, #d8c9a3);
  border-radius: 6px;
  text-decoration: none;
  color: inherit;
}
.quick-link:hover {
  border-color: var(--series-1, #2f6690);
}
.quick-link-title {
  font-weight: 700;
  color: var(--series-1, #2f6690);
}
.quick-link-copy {
  font-size: 0.85rem;
  color: var(--text-secondary, #6b5d47);
}
</style>
