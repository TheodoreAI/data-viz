<script>
import { parseJsonResponse } from '../api';

export default {
  name: 'Login',
  data() {
    return {
      identifier: '',
      password: '',
      errors: {},
      submitting: false,
      showPassword: false,
    };
  },
  methods: {
    async submit() {
      if (this.submitting) return;
      this.errors = {};
      this.submitting = true;
      try {
        const response = await fetch('/api/login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'same-origin',
          body: JSON.stringify({ identifier: this.identifier, password: this.password }),
        });
        const data = await parseJsonResponse(response);
        if (!response.ok) {
          this.errors = data.errors || { form: 'Something went wrong. Please try again.' };
          return;
        }
        window.location.href = '/profile';
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
    <h1>Log in</h1>
    <form class="auth-form" @submit.prevent="submit" novalidate>
      <p v-if="errors.form" class="form-error" role="alert">{{ errors.form }}</p>

      <label class="field">
        <span>Username or email</span>
        <input
          v-model="identifier"
          type="text"
          name="identifier"
          autocomplete="username"
          required
        >
      </label>

      <label class="field">
        <span>Password</span>
        <div class="password-row">
          <input
            v-model="password"
            :type="showPassword ? 'text' : 'password'"
            name="password"
            autocomplete="current-password"
            required
          >
          <button
            type="button"
            class="toggle-password"
            :aria-label="showPassword ? 'Hide password' : 'Show password'"
            @click="showPassword = !showPassword"
          >{{ showPassword ? 'Hide' : 'Show' }}</button>
        </div>
      </label>

      <button type="submit" class="submit-button" :disabled="submitting">
        {{ submitting ? 'Logging in…' : 'Log in' }}
      </button>
    </form>
    <p class="auth-switch"><a href="/forgot-password">Forgot your password?</a></p>
    <p class="auth-switch">Need an account? <a href="/register">Register</a></p>
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
