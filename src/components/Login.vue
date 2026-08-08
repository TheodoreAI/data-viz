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
  border-radius: 4px;
  background: var(--surface-1, #fcfcfb);
  color: inherit;
}
.field input:focus {
  outline: 2px solid var(--series-1, #2f6690);
  outline-offset: 1px;
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
  border-radius: 4px;
  padding: 0 0.75rem;
  font-size: 0.8rem;
  cursor: pointer;
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
