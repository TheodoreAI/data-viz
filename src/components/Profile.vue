<script>
export default {
  name: 'Profile',
  data() {
    return {
      user: null,
      loading: true,
      error: false,
      loggingOut: false,
    };
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
  methods: {
    async logout() {
      if (this.loggingOut) return;
      this.loggingOut = true;
      try {
        await fetch('/api/logout', { method: 'POST', credentials: 'same-origin' });
      } finally {
        window.location.href = '/login';
      }
    },
  },
};
</script>

<template>
  <div class="profile-page">
    <p v-if="loading" class="status">Loading…</p>
    <template v-else-if="error">
      <p class="status form-error">Couldn't load your profile. Please refresh the page.</p>
    </template>
    <template v-else-if="user">
      <h1>{{ user.username }}</h1>
      <p class="email">{{ user.email }}</p>
      <button type="button" class="logout-button" :disabled="loggingOut" @click="logout">
        {{ loggingOut ? 'Logging out…' : 'Log out' }}
      </button>
    </template>
  </div>
</template>

<style scoped>
.profile-page {
  max-width: 420px;
  margin: 0 auto;
  padding: 2rem 1.25rem 3rem;
}
h1 {
  font-size: 1.3rem;
  margin: 0 0 0.3rem;
}
.email {
  color: var(--text-secondary, #6b5d47);
  font-size: 0.9rem;
  margin: 0 0 1.5rem;
}
.status {
  color: var(--text-secondary, #6b5d47);
  font-size: 0.9rem;
}
.form-error {
  color: #b0413e;
}
.logout-button {
  background: transparent;
  border: 1px solid var(--series-1, #2f6690);
  color: var(--series-1, #2f6690);
  border-radius: 4px;
  padding: 0.5rem 1rem;
  font-size: 0.9rem;
  font-family: inherit;
  cursor: pointer;
}
.logout-button:disabled {
  opacity: 0.6;
  cursor: default;
}
</style>
