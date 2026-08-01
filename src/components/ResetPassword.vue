<script>
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
        const data = await response.json();
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
      <p class="confirmation">Your password has been reset.</p>
      <p class="auth-switch"><a href="/login">Log in</a></p>
    </template>
    <template v-else>
      <form v-if="token" class="auth-form" @submit.prevent="submit" novalidate>
        <p v-if="errors.form" class="form-error" role="alert">{{ errors.form }}</p>

        <label class="field">
          <span>New password</span>
          <input
            v-model="newPassword"
            type="password"
            autocomplete="new-password"
            minlength="8"
            required
            :aria-invalid="!!errors.newPassword"
          >
          <span v-if="errors.newPassword" class="field-error" role="alert">{{ errors.newPassword }}</span>
        </label>

        <label class="field">
          <span>Confirm new password</span>
          <input
            v-model="confirmNewPassword"
            type="password"
            autocomplete="new-password"
            required
            :aria-invalid="!!errors.confirmNewPassword"
          >
          <span v-if="errors.confirmNewPassword" class="field-error" role="alert">{{ errors.confirmNewPassword }}</span>
        </label>

        <button type="submit" class="submit-button" :disabled="submitting">
          {{ submitting ? 'Saving…' : 'Reset password' }}
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
  background: rgba(58, 122, 78, 0.12);
  border: 1px solid rgba(58, 122, 78, 0.4);
  border-radius: 4px;
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
.form-error {
  background: rgba(176, 65, 62, 0.12);
  color: #b0413e;
  border: 1px solid rgba(176, 65, 62, 0.4);
  border-radius: 4px;
  padding: 0.6rem 0.8rem;
  font-size: 0.85rem;
  margin: 0;
}
.submit-button {
  margin-top: 0.5rem;
  background: var(--series-1, #2f6690);
  color: #fff;
  border: none;
  border-radius: 4px;
  padding: 0.65rem 1rem;
  font-size: 0.95rem;
  font-family: inherit;
  cursor: pointer;
}
.submit-button:disabled {
  opacity: 0.6;
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
