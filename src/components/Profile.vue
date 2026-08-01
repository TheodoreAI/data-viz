<script>
const BIO_MAX_LENGTH = 280;

function readCookie(name) {
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : null;
}

function formatDate(iso) {
  if (!iso) return null;
  return new Date(iso).toLocaleDateString(undefined, { year: 'numeric', month: 'long', day: 'numeric' });
}

export default {
  name: 'Profile',
  data() {
    return {
      user: null,
      loading: true,
      error: false,
      loggingOut: false,
      editingBio: false,
      bioDraft: '',
      bioErrors: {},
      savingBio: false,
      bioMax: BIO_MAX_LENGTH,
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
  methods: {
    startEditingBio() {
      this.bioDraft = this.user.bio;
      this.bioErrors = {};
      this.editingBio = true;
    },
    cancelEditingBio() {
      this.editingBio = false;
    },
    async saveBio() {
      if (this.savingBio) return;
      this.savingBio = true;
      this.bioErrors = {};
      try {
        const response = await fetch('/api/profile', {
          method: 'PATCH',
          credentials: 'same-origin',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRF-TOKEN': readCookie('csrf_access_token'),
          },
          body: JSON.stringify({ bio: this.bioDraft }),
        });
        const data = await response.json();
        if (!response.ok) {
          this.bioErrors = data.errors || { bio: 'Something went wrong. Please try again.' };
          return;
        }
        this.user = data;
        this.editingBio = false;
      } catch {
        this.bioErrors = { bio: "Couldn't reach the server. Check your connection and try again." };
      } finally {
        this.savingBio = false;
      }
    },
    async logout() {
      if (this.loggingOut) return;
      this.loggingOut = true;
      try {
        await fetch('/api/logout', {
          method: 'POST',
          credentials: 'same-origin',
          headers: { 'X-CSRF-TOKEN': readCookie('csrf_access_token') },
        });
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
      <div class="profile-header">
        <img class="avatar" :src="user.avatarUrl" :alt="`${user.username}'s avatar`" width="72" height="72">
        <div>
          <h1>{{ user.username }}</h1>
          <p class="email">{{ user.email }}</p>
        </div>
      </div>

      <p v-if="memberSince" class="meta">Member since {{ memberSince }}</p>
      <p v-if="lastLogin" class="meta">Last login {{ lastLogin }}</p>

      <div class="bio-section">
        <template v-if="!editingBio">
          <p v-if="user.bio" class="bio-text">{{ user.bio }}</p>
          <p v-else class="bio-text bio-empty">No bio yet.</p>
          <button type="button" class="edit-button" @click="startEditingBio">Edit bio</button>
        </template>
        <template v-else>
          <p v-if="bioErrors.bio" class="form-error" role="alert">{{ bioErrors.bio }}</p>
          <textarea
            v-model="bioDraft"
            class="bio-input"
            :maxlength="bioMax"
            rows="3"
            aria-label="Bio"
          ></textarea>
          <p class="char-count">{{ bioDraft.length }} / {{ bioMax }}</p>
          <div class="bio-actions">
            <button type="button" class="save-button" :disabled="savingBio" @click="saveBio">
              {{ savingBio ? 'Saving…' : 'Save' }}
            </button>
            <button type="button" class="cancel-button" :disabled="savingBio" @click="cancelEditingBio">Cancel</button>
          </div>
        </template>
      </div>

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
.profile-header {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 0.75rem;
}
.avatar {
  border-radius: 50%;
  border: 1px solid var(--gridline, #d8c9a3);
  background: var(--surface-1, #fcfcfb);
  flex: none;
}
h1 {
  font-size: 1.3rem;
  margin: 0;
}
.email {
  color: var(--text-secondary, #6b5d47);
  font-size: 0.9rem;
  margin: 0.15rem 0 0;
}
.meta {
  color: var(--text-secondary, #6b5d47);
  font-size: 0.8rem;
  margin: 0.2rem 0;
}
.bio-section {
  margin: 1.25rem 0;
  padding: 1rem;
  border: 1px solid var(--gridline, #d8c9a3);
  border-radius: 6px;
}
.bio-text {
  margin: 0 0 0.6rem;
  font-size: 0.9rem;
  line-height: 1.4;
  white-space: pre-wrap;
}
.bio-empty {
  color: var(--text-secondary, #6b5d47);
  font-style: italic;
}
.bio-input {
  width: 100%;
  font-family: inherit;
  font-size: 0.9rem;
  padding: 0.5rem;
  border: 1px solid var(--gridline, #d8c9a3);
  border-radius: 4px;
  background: var(--surface-1, #fcfcfb);
  color: inherit;
  resize: vertical;
}
.char-count {
  margin: 0.3rem 0 0;
  font-size: 0.75rem;
  color: var(--text-secondary, #6b5d47);
  text-align: right;
}
.bio-actions {
  display: flex;
  gap: 0.5rem;
  margin-top: 0.6rem;
}
.status {
  color: var(--text-secondary, #6b5d47);
  font-size: 0.9rem;
}
.form-error {
  color: #b0413e;
  font-size: 0.85rem;
  margin: 0 0 0.5rem;
}
.edit-button,
.save-button,
.cancel-button,
.logout-button {
  background: transparent;
  border: 1px solid var(--series-1, #2f6690);
  color: var(--series-1, #2f6690);
  border-radius: 4px;
  padding: 0.4rem 0.9rem;
  font-size: 0.85rem;
  font-family: inherit;
  cursor: pointer;
}
.save-button {
  background: var(--series-1, #2f6690);
  color: #fff;
}
.edit-button:disabled,
.save-button:disabled,
.cancel-button:disabled,
.logout-button:disabled {
  opacity: 0.6;
  cursor: default;
}
</style>
