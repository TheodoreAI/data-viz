<script>
import { parseJsonResponse } from '../api';

export default {
  name: 'ResetPassword',
  data() {
    return {
      token: '',
      newPassword: '',
      confirmNewPassword: '',
      submitting: false,
      succeeded: false,
      errors: {},
      showPasswords: false,
    };
  },
  mounted() {
    this.token = new URLSearchParams(window.location.search).get('token') || '';
    if (!this.token) {
      this.errors = { form: 'This reset link is missing its token. Request a new one.' };
    }
  },
  methods: {
    async submit() {
      if (this.submitting || !this.token) return;
      this.errors = {};

      if (this.newPassword !== this.confirmNewPassword) {
        this.errors = { confirmNewPassword: 'Passwords do not match.' };
        return;
      }

      this.submitting = true;
      try {
        const response = await fetch('/api/reset-password', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'same-origin',
          body: JSON.stringify({ token: this.token, newPassword: this.newPassword }),
        });
        const data = await parseJsonResponse(response);
        if (!response.ok) {
          this.errors = data.errors || { form: 'Something went wrong. Please try again.' };
          return;
        }
        this.succeeded = true;
      } catch {
        this.errors = { form: "Couldn't reach the server. Check your connection and try again." };
      } finally {
        this.submitting = false;
      }
    },
  },
};
</script>

<template>
  <div class="auth-page">
    <h1>Reset your password</h1>
    <template v-if="succeeded">
      <p class="confirmation" role="status">Your password has been reset.</p>
      <p class="auth-switch"><a href="/login">Log in</a></p>
    </template>
    <template v-else>
      <form v-if="token" class="auth-form" @submit.prevent="submit" novalidate>
        <p v-if="errors.form" class="form-error" role="alert">{{ errors.form }}</p>

        <label class="field">
          <span>New password</span>
          <div class="password-row">
            <input
              v-model="newPassword"
              :type="showPasswords ? 'text' : 'password'"
              autocomplete="new-password"
              minlength="8"
              required
              :aria-invalid="!!errors.newPassword"
              aria-describedby="new-password-error"
            >
            <button
              type="button"
              class="toggle-password"
              :aria-label="showPasswords ? 'Hide passwords' : 'Show passwords'"
              @click="showPasswords = !showPasswords"
            >{{ showPasswords ? 'Hide' : 'Show' }}</button>
          </div>
          <span v-if="errors.newPassword" id="new-password-error" class="field-error" role="alert">{{ errors.newPassword }}</span>
        </label>

        <label class="field">
          <span>Confirm new password</span>
          <input
            v-model="confirmNewPassword"
            :type="showPasswords ? 'text' : 'password'"
            autocomplete="new-password"
            required
            :aria-invalid="!!errors.confirmNewPassword"
            aria-describedby="confirm-new-password-error"
          >
          <span v-if="errors.confirmNewPassword" id="confirm-new-password-error" class="field-error" role="alert">{{ errors.confirmNewPassword }}</span>
        </label>

        <button type="submit" class="submit-button" :disabled="submitting">
          {{ submitting ? 'Resetting…' : 'Reset password' }}
        </button>
      </form>
      <template v-else>
        <p class="form-error" role="alert">{{ errors.form }}</p>
        <p class="auth-switch"><a href="/forgot-password">Request a new reset link</a></p>
      </template>
    </template>
  </div>
</template>

<style scoped>
.auth-page {
  max-width: 420px;
  margin: 0 auto;
  padding: 2rem 1.25rem 3rem;
}
h1 {
  font-size: 1.3rem;
  margin: 0 0 1.25rem;
}
.confirmation {
  font-size: 0.9rem;
  color: var(--emphasis-text, #207b37);
  background: color-mix(in srgb, var(--emphasis, #34c759) 10%, transparent);
  border: 1px solid color-mix(in srgb, var(--emphasis, #34c759) 30%, transparent);
  border-radius: var(--radius-sm, 0.5rem);
  padding: 0.75rem 0.9rem;
}
.auth-form {
  display: flex;
  flex-direction: column;
  gap: 1rem;
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
  padding: 0.55rem 0.7rem;
  border: 1px solid var(--gridline, #d8c9a3);
  border-radius: var(--radius-md, 0.625rem);
  background: var(--surface-1, #fcfcfb);
  color: inherit;
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}
.field input:focus {
  outline: none;
  border-color: var(--series-1, #2f6690);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--series-1, #2f6690) 18%, transparent);
}
.field input[aria-invalid="true"] {
  border-color: var(--danger, #cc2f26);
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
  border: 1px solid var(--gridline, #d8c9a3);
  color: var(--series-1, #2f6690);
  border-radius: var(--radius-sm, 0.5rem);
  padding: 0 0.75rem;
  font-size: 0.8rem;
  cursor: pointer;
}
.field-error {
  color: var(--danger-text, #99231d);
  font-size: 0.78rem;
}
.form-error {
  background: color-mix(in srgb, var(--danger, #cc2f26) 10%, transparent);
  color: var(--danger-text, #99231d);
  border: 1px solid color-mix(in srgb, var(--danger, #cc2f26) 30%, transparent);
  border-radius: var(--radius-sm, 0.5rem);
  padding: 0.6rem 0.8rem;
  font-size: 0.85rem;
  margin: 0;
}
.submit-button {
  margin-top: 0.5rem;
  background: var(--series-1, #2f6690);
  color: var(--accent-contrast, #fff);
  border: none;
  border-radius: var(--radius-md, 0.625rem);
  padding: 0.65rem 1rem;
  font-size: 0.95rem;
  font-family: inherit;
  font-weight: 700;
  cursor: pointer;
  box-shadow: var(--shadow-raised, none);
  transition: opacity 0.15s ease, transform 0.1s cubic-bezier(0.32, 0.72, 0, 1);
}
.submit-button:active:not(:disabled) {
  transform: scale(0.98);
}
.submit-button:disabled {
  opacity: 0.4;
  cursor: default;
}
.auth-switch {
  margin-top: 1.25rem;
  font-size: 0.85rem;
  color: var(--text-secondary, #6b5d47);
}
.auth-switch a {
  color: var(--series-1, #2f6690);
}
</style>
