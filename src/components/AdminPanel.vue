<script>
import LoadingSpinner from './LoadingSpinner.vue';

function formatDate(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' });
}

export default {
  name: 'AdminPanel',
  components: { LoadingSpinner },
  data() {
    return {
      users: [],
      loading: true,
      error: false,
      forbidden: false,
      query: '',
    };
  },
  computed: {
    filteredUsers() {
      const q = this.query.trim().toLowerCase();
      if (!q) return this.users;
      return this.users.filter(u =>
        u.username.toLowerCase().includes(q) ||
        u.email.toLowerCase().includes(q) ||
        (u.displayName || '').toLowerCase().includes(q)
      );
    },
  },
  async mounted() {
    try {
      const response = await fetch('/api/admin/users', { credentials: 'same-origin' });
      if (response.status === 401 || response.status === 404) {
        this.forbidden = true;
        return;
      }
      if (!response.ok) throw new Error(`Request failed: ${response.status}`);
      this.users = await response.json();
    } catch {
      this.error = true;
    } finally {
      this.loading = false;
    }
  },
  methods: {
    formatDate,
  },
};
</script>

<template>
  <div class="admin-page">
    <LoadingSpinner v-if="loading" size="lg" />
    <template v-else-if="forbidden">
      <p class="status form-error">You don't have access to this page.</p>
    </template>
    <template v-else-if="error">
      <p class="status form-error">Couldn't load users. Please refresh the page.</p>
    </template>
    <template v-else>
      <h1>Users</h1>
      <p class="meta">{{ users.length }} registered</p>

      <input
        v-model="query"
        type="search"
        class="user-search"
        placeholder="Search by username, email, or display name"
      >

      <div class="table-scroll">
        <table class="users-table">
          <thead>
            <tr>
              <th>User</th>
              <th>Email</th>
              <th>Joined</th>
              <th>Last login</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="u in filteredUsers" :key="u.id">
              <td class="user-cell">
                <img :src="u.avatarUrl" :alt="u.username" class="user-avatar">
                <div class="user-info">
                  <span class="user-name">{{ u.displayName || u.username }}</span>
                  <span class="user-username">@{{ u.username }}</span>
                </div>
                <span v-if="u.isAdmin" class="admin-badge">Admin</span>
              </td>
              <td>{{ u.email }}</td>
              <td>{{ formatDate(u.createdAt) }}</td>
              <td>{{ formatDate(u.lastLoginAt) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <p v-if="!filteredUsers.length" class="status">No users match your search.</p>
    </template>
  </div>
</template>

<style scoped>
.admin-page {
  max-width: 780px;
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
  margin: 0 0 1.25rem;
}
.status {
  color: var(--text-secondary, #6b5d47);
  font-size: 0.9rem;
}
.form-error {
  color: var(--danger-text, #99231d);
}
.user-search {
  display: block;
  width: 100%;
  max-width: 360px;
  margin: 0 0 1.25rem;
  padding: 0.45rem 0.7rem;
  border: 1px solid var(--gridline, #d8c9a3);
  border-radius: var(--radius-md, 0.625rem);
  background: var(--surface-1, #fcfcfb);
  color: inherit;
  font-family: inherit;
  font-size: 0.85rem;
}
.user-search:focus {
  outline: none;
  border-color: var(--series-1, #2f6690);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--series-1, #2f6690) 18%, transparent);
}
.table-scroll {
  overflow-x: auto;
}
.users-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.85rem;
}
.users-table th {
  text-align: left;
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  color: var(--text-secondary, #6b5d47);
  border-bottom: 1px solid var(--gridline, #d8c9a3);
  padding: 0.5rem 0.6rem;
  white-space: nowrap;
}
.users-table td {
  padding: 0.5rem 0.6rem;
  border-bottom: 1px solid var(--gridline, #d8c9a3);
  white-space: nowrap;
}
.user-cell {
  display: flex;
  align-items: center;
  gap: 0.6rem;
}
.user-avatar {
  width: 28px;
  height: 28px;
  border-radius: var(--pill-radius, 9999px);
  flex: none;
  background: var(--surface-1, #fcfcfb);
}
.user-info {
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.user-name {
  font-weight: 600;
}
.user-username {
  font-size: 0.75rem;
  color: var(--text-secondary, #6b5d47);
}
.admin-badge {
  flex: none;
  background: var(--series-1, #2f6690);
  color: var(--surface-1, #fff);
  border-radius: var(--pill-radius, 9999px);
  padding: 0.1rem 0.55rem;
  font-size: 0.7rem;
  font-weight: 600;
}
</style>
