<script>
import { parseJsonResponse } from '../api';

export default {
  name: 'ForgotPassword',
  data() {
    return {
      email: '',
      submitting: false,
      submitted: false,
      errors: {},
    };
  },
  methods: {
    async submit() {
      if (this.submitting) return;
      this.submitting = true;
      this.errors = {};
      try {
        const response = await fetch('/api/forgot-password', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'same-origin',
          body: JSON.stringify({ email: this.email }),
        });
        if (!response.ok) {
          const data = await parseJsonResponse(response);
          this.errors = data.errors || { form: 'Something went wrong. Please try again.' };
          return;
        }
        this.submitted = true;
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
    <h1>Forgot your password?</h1>
    <template v-if="submitted">
      <p class="confirmation" role="status">
        If an account exists for that email, we've sent a link to reset your password.
      </p>
    </template>
    <form v-else class="auth-form" @submit.prevent="submit" novalidate>
      <p v-if="errors.form" class="form-error" role="alert">{{ errors.form }}</p>
      <p class="hint">Enter your account email and we'll send you a link to reset your password.</p>
      <label class="field">
        <span>Email</span>
        <input
          v-model="email"
          type="email"
          name="email"
          autocomplete="email"
          required
        >
      </label>
      <button type="submit" class="submit-button" :disabled="submitting">
        {{ submitting ? 'Sending…' : 'Send reset link' }}
      </button>
    </form>
    <p class="auth-switch"><a href="/login">Back to log in</a></p>
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
.hint {
  font-size: 0.85rem;
  color: var(--text-secondary, #6b5d47);
  margin: 0 0 0.25rem;
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
