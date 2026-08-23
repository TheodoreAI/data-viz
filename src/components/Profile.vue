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

import LoadingSpinner from './LoadingSpinner.vue';
import { parseJsonResponse } from '../api';

export default {
  name: 'Profile',
  components: { LoadingSpinner },
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
      bioSuccess: false,
      bioMax: BIO_MAX_LENGTH,

      editingDisplayName: false,
      displayNameDraft: '',
      displayNameErrors: {},
      savingDisplayName: false,
      displayNameSuccess: false,
      activeTab: 'profile',
      changingPassword: false,
      currentPassword: '',
      newPassword: '',
      confirmNewPassword: '',
      passwordErrors: {},
      passwordSuccess: false,
      savingPassword: false,
      showPasswordFields: false,
      deletingAccount: false,
      deletePassword: '',
      deleteConfirmText: '',
      deleteErrors: {},
      deletingInFlight: false,

      savedItems: [],
      savedItemsLoading: false,
      savedItemsError: false,
      removingId: null,
    };
  },
  computed: {
    memberSince() {
      return formatDate(this.user?.createdAt);
    },
    lastLogin() {
      return formatDate(this.user?.lastLoginAt);
    },
    deleteConfirmMatches() {
      return this.deleteConfirmText === this.user?.username;
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
      this.loadSavedItems();
    } catch {
      this.error = true;
    } finally {
      this.loading = false;
    }
  },
  methods: {
    async loadSavedItems() {
      this.savedItemsLoading = true;
      this.savedItemsError = false;
      try {
        const response = await fetch('/api/saved-items', { credentials: 'same-origin' });
        if (!response.ok) throw new Error(`Request failed: ${response.status}`);
        this.savedItems = await response.json();
      } catch {
        this.savedItemsError = true;
      } finally {
        this.savedItemsLoading = false;
      }
    },
    async removeSavedItem(id) {
      if (this.removingId) return;
      this.removingId = id;
      try {
        const response = await fetch(`/api/saved-items/${id}`, {
          method: 'DELETE',
          credentials: 'same-origin',
          headers: { 'X-CSRF-TOKEN': readCookie('csrf_access_token') },
        });
        if (response.ok) {
          this.savedItems = this.savedItems.filter(item => item.id !== id);
        }
      } finally {
        this.removingId = null;
      }
    },
    startEditingBio() {
      this.bioDraft = this.user.bio;
      this.bioErrors = {};
      this.bioSuccess = false;
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
        this.bioSuccess = true;
      } catch {
        this.bioErrors = { bio: "Couldn't reach the server. Check your connection and try again." };
      } finally {
        this.savingBio = false;
      }
    },
    startEditingDisplayName() {
      this.displayNameDraft = this.user.displayName || '';
      this.displayNameErrors = {};
      this.displayNameSuccess = false;
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
        this.displayNameSuccess = true;
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
        const data = await parseJsonResponse(response);
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
      this.deleteConfirmText = '';
      this.deleteErrors = {};
      this.deletingAccount = true;
    },
    cancelDeletingAccount() {
      this.deletingAccount = false;
    },
    async confirmDeleteAccount() {
      if (this.deletingInFlight || !this.deleteConfirmMatches) return;
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
        const data = await parseJsonResponse(response);
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
    <LoadingSpinner v-if="loading" size="lg" />
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

      <div class="tab-bar" role="tablist">
        <button
          type="button"
          role="tab"
          class="tab-button"
          :class="{ active: activeTab === 'profile' }"
          :aria-selected="activeTab === 'profile'"
          @click="activeTab = 'profile'"
        >Profile</button>
        <button
          type="button"
          role="tab"
          class="tab-button"
          :class="{ active: activeTab === 'collection' }"
          :aria-selected="activeTab === 'collection'"
          @click="activeTab = 'collection'"
        >Collection</button>
        <button
          type="button"
          role="tab"
          class="tab-button"
          :class="{ active: activeTab === 'security' }"
          :aria-selected="activeTab === 'security'"
          @click="activeTab = 'security'"
        >Security</button>
        <button
          type="button"
          role="tab"
          class="tab-button danger"
          :class="{ active: activeTab === 'danger' }"
          :aria-selected="activeTab === 'danger'"
          @click="activeTab = 'danger'"
        >Danger Zone</button>
      </div>

      <section v-show="activeTab === 'profile'" role="tabpanel">
        <div v-if="!editingDisplayName" class="display-name-row">
          <p v-if="displayNameSuccess" class="success-message" role="status">Display name updated.</p>
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
            <p v-if="bioSuccess" class="success-message" role="status">Bio updated.</p>
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
      </section>

      <section v-show="activeTab === 'collection'" role="tabpanel" class="settings-section">
        <h2>Saved Collection</h2>
        <LoadingSpinner v-if="savedItemsLoading" size="sm" inline />
        <p v-else-if="savedItemsError" class="status form-error">Couldn't load your collection. Please try again.</p>
        <p v-else-if="!savedItems.length" class="status">Nothing saved yet — look for the save button on an article.</p>
        <ul v-else class="saved-list">
          <li v-for="item in savedItems" :key="item.id" class="saved-item">
            <img v-if="item.imageUrl" class="saved-thumb" :src="item.imageUrl" alt="" width="52" height="52">
            <div v-else class="saved-thumb saved-thumb-empty" aria-hidden="true"></div>
            <div class="saved-body">
              <a :href="item.sourceUrl" target="_blank" rel="noopener" class="saved-title">{{ item.title }}</a>
              <p v-if="item.subtitle" class="saved-subtitle">{{ item.subtitle }}</p>
            </div>
            <button
              type="button"
              class="saved-remove"
              :disabled="removingId === item.id"
              :aria-label="`Remove ${item.title} from your collection`"
              @click="removeSavedItem(item.id)"
            >
              <LoadingSpinner v-if="removingId === item.id" size="sm" inline />
              <svg v-else viewBox="0 0 16 16" aria-hidden="true"><path d="M4 4l8 8M12 4l-8 8" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" /></svg>
            </button>
          </li>
        </ul>
      </section>

      <section v-show="activeTab === 'security'" role="tabpanel" class="settings-section">
        <h2>Password</h2>
        <p v-if="passwordSuccess && !changingPassword" class="success-message" role="status">Password updated.</p>
        <button v-if="!changingPassword" type="button" class="edit-button" @click="startChangingPassword">
          Change password
        </button>
        <form v-else class="settings-form" @submit.prevent="savePassword" novalidate>
          <p v-if="passwordErrors.form" class="form-error" role="alert">{{ passwordErrors.form }}</p>

          <label class="field">
            <span>Current password</span>
            <input
              v-model="currentPassword"
              :type="showPasswordFields ? 'text' : 'password'"
              autocomplete="current-password"
              required
              :aria-invalid="!!passwordErrors.currentPassword"
              aria-describedby="current-password-error"
            >
            <span v-if="passwordErrors.currentPassword" id="current-password-error" class="field-error" role="alert">{{ passwordErrors.currentPassword }}</span>
          </label>

          <label class="field">
            <span>New password</span>
            <div class="password-row">
              <input
                v-model="newPassword"
                :type="showPasswordFields ? 'text' : 'password'"
                autocomplete="new-password"
                minlength="8"
                required
                :aria-invalid="!!passwordErrors.newPassword"
                aria-describedby="new-password-error"
              >
              <button
                type="button"
                class="toggle-password"
                :aria-label="showPasswordFields ? 'Hide passwords' : 'Show passwords'"
                @click="showPasswordFields = !showPasswordFields"
              >{{ showPasswordFields ? 'Hide' : 'Show' }}</button>
            </div>
            <span v-if="passwordErrors.newPassword" id="new-password-error" class="field-error" role="alert">{{ passwordErrors.newPassword }}</span>
          </label>

          <label class="field">
            <span>Confirm new password</span>
            <input
              v-model="confirmNewPassword"
              :type="showPasswordFields ? 'text' : 'password'"
              autocomplete="new-password"
              required
              :aria-invalid="!!passwordErrors.confirmNewPassword"
              aria-describedby="confirm-new-password-error"
            >
            <span v-if="passwordErrors.confirmNewPassword" id="confirm-new-password-error" class="field-error" role="alert">{{ passwordErrors.confirmNewPassword }}</span>
          </label>

          <div class="bio-actions">
            <button type="submit" class="save-button" :disabled="savingPassword">
              {{ savingPassword ? 'Saving…' : 'Save password' }}
            </button>
            <button type="button" class="cancel-button" :disabled="savingPassword" @click="cancelChangingPassword">Cancel</button>
          </div>
        </form>
      </section>

      <section v-show="activeTab === 'danger'" role="tabpanel" class="settings-section danger-zone">
        <h2>Delete account</h2>
        <p class="danger-copy">This permanently deletes your account. This can't be undone.</p>
        <button v-if="!deletingAccount" type="button" class="danger-button" @click="startDeletingAccount">
          Delete my account
        </button>
        <form v-else class="settings-form" @submit.prevent="confirmDeleteAccount" novalidate>
          <p v-if="deleteErrors.form" class="form-error" role="alert">{{ deleteErrors.form }}</p>
          <label class="field">
            <span>Type <strong>{{ user.username }}</strong> to confirm</span>
            <input
              v-model="deleteConfirmText"
              type="text"
              autocomplete="off"
              required
            >
          </label>
          <label class="field">
            <span>Enter your password to confirm</span>
            <input
              v-model="deletePassword"
              type="password"
              autocomplete="current-password"
              required
              :aria-invalid="!!deleteErrors.password"
              aria-describedby="delete-password-error"
            >
            <span v-if="deleteErrors.password" id="delete-password-error" class="field-error" role="alert">{{ deleteErrors.password }}</span>
          </label>
          <div class="bio-actions">
            <button type="submit" class="danger-button" :disabled="deletingInFlight || !deleteConfirmMatches">
              {{ deletingInFlight ? 'Deleting…' : 'Permanently delete account' }}
            </button>
            <button type="button" class="cancel-button" :disabled="deletingInFlight" @click="cancelDeletingAccount">Cancel</button>
          </div>
        </form>
      </section>
    </template>
  </div>
</template>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Serif:wght@400;500;600&family=Inter:wght@400;500;600;700&display=swap');

.profile-page {
  --mp-wall: #f7f6f3;
  --mp-frame: #e4e1d9;
  --mp-frame-strong: #22201b;
  --mp-ink: #22201b;
  --mp-ink-soft: #756f60;

  max-width: 420px;
  margin: 0 auto;
  padding: 2.5rem 1.25rem 3rem;
  background: var(--mp-wall);
  color: var(--mp-ink);
  font-family: "IBM Plex Serif", Georgia, serif;
}

@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) .profile-page {
    --mp-wall: #171613;
    --mp-frame: #34312a;
    --mp-frame-strong: #d9d5c9;
    --mp-ink: #f0eee6;
    --mp-ink-soft: #a39d8b;
  }
}
:root[data-theme="dark"] .profile-page {
  --mp-wall: #171613;
  --mp-frame: #34312a;
  --mp-frame-strong: #d9d5c9;
  --mp-ink: #f0eee6;
  --mp-ink-soft: #a39d8b;
}

.profile-header {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 0.75rem;
}
.profile-header > div {
  min-width: 0;
}
.avatar {
  border-radius: 50%;
  border: 1px solid var(--mp-frame);
  background: var(--mp-wall);
  flex: none;
}
h1 {
  font-size: 1.3rem;
  font-weight: 500;
  margin: 0;
  overflow-wrap: break-word;
}
.username-sub {
  color: var(--mp-ink-soft);
  font-family: Inter, sans-serif;
  font-size: 0.8rem;
  margin: 0.1rem 0 0;
}
.email {
  color: var(--mp-ink-soft);
  font-family: Inter, sans-serif;
  font-size: 0.9rem;
  margin: 0.15rem 0 0;
}
.display-name-row {
  margin-bottom: 1rem;
}
.meta {
  color: var(--mp-ink-soft);
  font-family: Inter, sans-serif;
  font-size: 0.8rem;
  margin: 0.2rem 0;
}
.bio-section {
  margin: 1.25rem 0;
  padding: 1.25rem;
  border: 1px solid var(--mp-frame);
}
.bio-text {
  margin: 0 0 0.6rem;
  font-size: 0.9rem;
  line-height: 1.6;
  white-space: pre-wrap;
}
.bio-empty {
  color: var(--mp-ink-soft);
  font-style: italic;
}
.bio-input {
  width: 100%;
  font-family: Inter, sans-serif;
  font-size: 0.9rem;
  padding: 0.5rem;
  border: 1px solid var(--mp-frame);
  background: var(--mp-wall);
  color: inherit;
  resize: vertical;
}
.char-count {
  margin: 0.3rem 0 0;
  font-family: Inter, sans-serif;
  font-size: 0.75rem;
  color: var(--mp-ink-soft);
  text-align: right;
}
.bio-actions {
  display: flex;
  gap: 0.5rem;
  margin-top: 0.6rem;
}
.status {
  color: var(--mp-ink-soft);
  font-family: Inter, sans-serif;
  font-size: 0.9rem;
}
.form-error {
  color: #b0413e;
  font-family: Inter, sans-serif;
  font-size: 0.85rem;
  margin: 0 0 0.5rem;
}
.edit-button,
.save-button,
.cancel-button,
.logout-button {
  background: transparent;
  border: 1px solid var(--mp-frame-strong);
  color: var(--mp-ink);
  font-family: Inter, sans-serif;
  font-size: 0.72rem;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  padding: 0.4rem 0.9rem;
  cursor: pointer;
}
.save-button {
  background: var(--mp-frame-strong);
  color: var(--mp-wall);
}
.edit-button:disabled,
.save-button:disabled,
.cancel-button:disabled,
.logout-button:disabled {
  opacity: 0.6;
  cursor: default;
}
.tab-bar {
  display: flex;
  gap: 0.4rem;
  margin: 1.5rem 0 1.75rem;
  border-bottom: 1px solid var(--mp-frame);
}
.tab-button {
  flex: 1;
  background: transparent;
  border: none;
  border-bottom: 2px solid transparent;
  color: var(--mp-ink-soft);
  font-family: Inter, sans-serif;
  font-size: 0.72rem;
  letter-spacing: 0.03em;
  text-transform: uppercase;
  padding: 0.6rem 0.4rem;
  cursor: pointer;
}
.tab-button.active {
  color: var(--mp-ink);
  border-bottom-color: var(--mp-frame-strong);
  font-weight: 600;
}
.tab-button.danger.active {
  color: #b0413e;
  border-bottom-color: #b0413e;
}
.settings-section {
  margin: 1.5rem 0;
}
.settings-section h2 {
  font-size: 1.1rem;
  font-weight: 500;
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
  font-family: Inter, sans-serif;
  font-size: 0.85rem;
  overflow-wrap: break-word;
}
.field input {
  font-family: Inter, sans-serif;
  font-size: 1rem;
  padding: 0.5rem 0.65rem;
  border: 1px solid var(--mp-frame);
  background: var(--mp-wall);
  color: inherit;
}
.field input:focus {
  outline: 2px solid var(--mp-frame-strong);
  outline-offset: 1px;
}
.field input[aria-invalid="true"] {
  border-color: #b0413e;
}
.password-row {
  display: flex;
  gap: 0.5rem;
}
.password-row input {
  flex: 1;
  min-width: 0;
}
.toggle-password {
  flex: none;
  background: transparent;
  border: 1px solid var(--mp-frame);
  color: var(--mp-ink);
  font-family: Inter, sans-serif;
  border-radius: 0;
  padding: 0 0.75rem;
  font-size: 0.8rem;
  cursor: pointer;
}
.field-error {
  color: #b0413e;
  font-family: Inter, sans-serif;
  font-size: 0.78rem;
}
.success-message {
  color: #3a7a4e;
  font-family: Inter, sans-serif;
  font-size: 0.85rem;
  margin: 0 0 0.5rem;
}
.danger-zone {
  padding: 1.25rem;
  border: 1px solid rgba(176, 65, 62, 0.4);
}
.danger-zone h2 {
  color: #b0413e;
}
.danger-copy {
  font-family: Inter, sans-serif;
  font-size: 0.85rem;
  color: var(--mp-ink-soft);
  margin: 0 0 0.75rem;
}
.danger-button {
  background: transparent;
  border: 1px solid #b0413e;
  color: #b0413e;
  font-family: Inter, sans-serif;
  font-size: 0.72rem;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  padding: 0.4rem 0.9rem;
  cursor: pointer;
}
.danger-button:disabled {
  opacity: 0.6;
  cursor: default;
}

.saved-list {
  list-style: none;
  margin: 0.5rem 0 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
}
.saved-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem;
  border: 1px solid var(--mp-frame);
}
.saved-thumb {
  flex: none;
  width: 52px;
  height: 52px;
  object-fit: cover;
  background: var(--mp-wall);
}
.saved-thumb-empty {
  border: 1px dashed var(--mp-frame);
}
.saved-body {
  min-width: 0;
  flex: 1;
}
.saved-title {
  display: block;
  font-size: 0.9rem;
  font-weight: 600;
  color: inherit;
  text-decoration: none;
  overflow-wrap: break-word;
}
.saved-title:hover {
  text-decoration: underline;
}
.saved-subtitle {
  margin: 0.2rem 0 0;
  font-family: Inter, sans-serif;
  font-size: 0.78rem;
  color: var(--mp-ink-soft);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.saved-remove {
  flex: none;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: 1px solid var(--mp-frame);
  border-radius: 50%;
  color: var(--mp-ink-soft);
  cursor: pointer;
}
.saved-remove svg {
  width: 14px;
  height: 14px;
}
.saved-remove:disabled {
  opacity: 0.6;
  cursor: default;
}
</style>
