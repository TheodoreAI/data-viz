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

      editingDisplayName: false,
      displayNameDraft: '',
      displayNameErrors: {},
      savingDisplayName: false,
      changingPassword: false,
      currentPassword: '',
      newPassword: '',
      confirmNewPassword: '',
      passwordErrors: {},
      passwordSuccess: false,
      savingPassword: false,
      deletingAccount: false,
      deletePassword: '',
      deleteErrors: {},
      deletingInFlight: false,
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
    startEditingDisplayName() {
      this.displayNameDraft = this.user.displayName || '';
      this.displayNameErrors = {};
      this.editingDisplayName = true;
    },
    cancelEditingDisplayName() {
      this.editingDisplayName = false;
    },
    async saveDisplayName() {
      if (this.savingDisplayName) return;
      this.savingDisplayName = true;
      this.displayNameErrors = {};
      try {
        const response = await fetch('/api/profile', {
          method: 'PATCH',
          credentials: 'same-origin',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRF-TOKEN': readCookie('csrf_access_token'),
          },
          body: JSON.stringify({ displayName: this.displayNameDraft }),
        });
        const data = await response.json();
        if (!response.ok) {
          this.displayNameErrors = data.errors || { displayName: 'Something went wrong. Please try again.' };
          return;
        }
        this.user = data;
        this.editingDisplayName = false;
      } catch {
        this.displayNameErrors = { displayName: "Couldn't reach the server. Check your connection and try again." };
      } finally {
        this.savingDisplayName = false;
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
    startChangingPassword() {
      this.currentPassword = '';
      this.newPassword = '';
      this.confirmNewPassword = '';
      this.passwordErrors = {};
      this.passwordSuccess = false;
      this.changingPassword = true;
    },
    cancelChangingPassword() {
      this.changingPassword = false;
    },
    async savePassword() {
      if (this.savingPassword) return;
      this.passwordErrors = {};

      if (this.newPassword !== this.confirmNewPassword) {
        this.passwordErrors = { confirmNewPassword: 'New passwords do not match.' };
        return;
      }

      this.savingPassword = true;
      try {
        const response = await fetch('/api/profile/password', {
          method: 'POST',
          credentials: 'same-origin',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRF-TOKEN': readCookie('csrf_access_token'),
          },
          body: JSON.stringify({
            currentPassword: this.currentPassword,
            newPassword: this.newPassword,
          }),
        });
        const data = await response.json();
        if (!response.ok) {
          this.passwordErrors = data.errors || { form: 'Something went wrong. Please try again.' };
          return;
        }
        this.changingPassword = false;
        this.passwordSuccess = true;
      } catch {
        this.passwordErrors = { form: "Couldn't reach the server. Check your connection and try again." };
      } finally {
        this.savingPassword = false;
      }
    },
    startDeletingAccount() {
      this.deletePassword = '';
      this.deleteErrors = {};
      this.deletingAccount = true;
    },
    cancelDeletingAccount() {
      this.deletingAccount = false;
    },
    async confirmDeleteAccount() {
      if (this.deletingInFlight) return;
      this.deletingInFlight = true;
      this.deleteErrors = {};
      try {
        const response = await fetch('/api/account', {
          method: 'DELETE',
          credentials: 'same-origin',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRF-TOKEN': readCookie('csrf_access_token'),
          },
          body: JSON.stringify({ password: this.deletePassword }),
        });
        const data = await response.json();
        if (!response.ok) {
          this.deleteErrors = data.errors || { form: 'Something went wrong. Please try again.' };
          return;
        }
        window.location.href = '/register';
      } catch {
        this.deleteErrors = { form: "Couldn't reach the server. Check your connection and try again." };
      } finally {
        this.deletingInFlight = false;
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
          <h1>{{ user.displayName || user.username }}</h1>
          <p v-if="user.displayName" class="username-sub">@{{ user.username }}</p>
          <p class="email">{{ user.email }}</p>
        </div>
      </div>

      <div v-if="!editingDisplayName" class="display-name-row">
        <button type="button" class="edit-button" @click="startEditingDisplayName">
          {{ user.displayName ? 'Edit display name' : 'Set a display name' }}
        </button>
      </div>
      <form v-else class="settings-form" @submit.prevent="saveDisplayName" novalidate>
        <p v-if="displayNameErrors.displayName" class="form-error" role="alert">{{ displayNameErrors.displayName }}</p>
        <label class="field">
          <span>Display name</span>
          <input
            v-model="displayNameDraft"
            type="text"
            maxlength="64"
            placeholder="How should we show your name?"
            :aria-invalid="!!displayNameErrors.displayName"
          >
        </label>
        <div class="bio-actions">
          <button type="submit" class="save-button" :disabled="savingDisplayName">
            {{ savingDisplayName ? 'Saving…' : 'Save' }}
          </button>
          <button type="button" class="cancel-button" :disabled="savingDisplayName" @click="cancelEditingDisplayName">Cancel</button>
        </div>
      </form>

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

      <div class="settings-section">
        <h2>Password</h2>
        <p v-if="passwordSuccess && !changingPassword" class="success-message">Password updated.</p>
        <button v-if="!changingPassword" type="button" class="edit-button" @click="startChangingPassword">
          Change password
        </button>
        <form v-else class="settings-form" @submit.prevent="savePassword" novalidate>
          <p v-if="passwordErrors.form" class="form-error" role="alert">{{ passwordErrors.form }}</p>

          <label class="field">
            <span>Current password</span>
            <input
              v-model="currentPassword"
              type="password"
              autocomplete="current-password"
              required
              :aria-invalid="!!passwordErrors.currentPassword"
            >
            <span v-if="passwordErrors.currentPassword" class="field-error" role="alert">{{ passwordErrors.currentPassword }}</span>
          </label>

          <label class="field">
            <span>New password</span>
            <input
              v-model="newPassword"
              type="password"
              autocomplete="new-password"
              minlength="8"
              required
              :aria-invalid="!!passwordErrors.newPassword"
            >
            <span v-if="passwordErrors.newPassword" class="field-error" role="alert">{{ passwordErrors.newPassword }}</span>
          </label>

          <label class="field">
            <span>Confirm new password</span>
            <input
              v-model="confirmNewPassword"
              type="password"
              autocomplete="new-password"
              required
              :aria-invalid="!!passwordErrors.confirmNewPassword"
            >
            <span v-if="passwordErrors.confirmNewPassword" class="field-error" role="alert">{{ passwordErrors.confirmNewPassword }}</span>
          </label>

          <div class="bio-actions">
            <button type="submit" class="save-button" :disabled="savingPassword">
              {{ savingPassword ? 'Saving…' : 'Save password' }}
            </button>
            <button type="button" class="cancel-button" :disabled="savingPassword" @click="cancelChangingPassword">Cancel</button>
          </div>
        </form>
      </div>

      <div class="settings-section danger-zone">
        <h2>Delete account</h2>
        <p class="danger-copy">This permanently deletes your account. This can't be undone.</p>
        <button v-if="!deletingAccount" type="button" class="danger-button" @click="startDeletingAccount">
          Delete my account
        </button>
        <form v-else class="settings-form" @submit.prevent="confirmDeleteAccount" novalidate>
          <p v-if="deleteErrors.form" class="form-error" role="alert">{{ deleteErrors.form }}</p>
          <label class="field">
            <span>Enter your password to confirm</span>
            <input
              v-model="deletePassword"
              type="password"
              autocomplete="current-password"
              required
              :aria-invalid="!!deleteErrors.password"
            >
            <span v-if="deleteErrors.password" class="field-error" role="alert">{{ deleteErrors.password }}</span>
          </label>
          <div class="bio-actions">
            <button type="submit" class="danger-button" :disabled="deletingInFlight">
              {{ deletingInFlight ? 'Deleting…' : 'Permanently delete account' }}
            </button>
            <button type="button" class="cancel-button" :disabled="deletingInFlight" @click="cancelDeletingAccount">Cancel</button>
          </div>
        </form>
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
.username-sub {
  color: var(--text-secondary, #6b5d47);
  font-size: 0.8rem;
  margin: 0.1rem 0 0;
}
.email {
  color: var(--text-secondary, #6b5d47);
  font-size: 0.9rem;
  margin: 0.15rem 0 0;
}
.display-name-row {
  margin-bottom: 1rem;
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
.settings-section {
  margin: 1.5rem 0;
}
.settings-section h2 {
  font-size: 1rem;
  margin: 0 0 0.5rem;
}
.settings-form {
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
  margin-top: 0.5rem;
}
.field {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
  font-size: 0.85rem;
}
.field input {
  font-family: inherit;
  font-size: 1rem;
  padding: 0.5rem 0.65rem;
  border: 1px solid var(--gridline, #d8c9a3);
  border-radius: 4px;
  background: var(--surface-1, #fcfcfb);
  color: inherit;
}
.field input:focus {
  outline: 2px solid var(--series-1, #2f6690);
  outline-offset: 1px;
}
.field input[aria-invalid="true"] {
  border-color: #b0413e;
}
.field-error {
  color: #b0413e;
  font-size: 0.78rem;
}
.success-message {
  color: #3a7a4e;
  font-size: 0.85rem;
  margin: 0 0 0.5rem;
}
.danger-zone {
  padding: 1rem;
  border: 1px solid rgba(176, 65, 62, 0.4);
  border-radius: 6px;
}
.danger-zone h2 {
  color: #b0413e;
}
.danger-copy {
  font-size: 0.85rem;
  color: var(--text-secondary, #6b5d47);
  margin: 0 0 0.75rem;
}
.danger-button {
  background: transparent;
  border: 1px solid #b0413e;
  color: #b0413e;
  border-radius: 4px;
  padding: 0.4rem 0.9rem;
  font-size: 0.85rem;
  font-family: inherit;
  cursor: pointer;
}
.danger-button:disabled {
  opacity: 0.6;
  cursor: default;
}
</style>
