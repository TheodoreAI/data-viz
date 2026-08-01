<script>
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
          const data = await response.json().catch(() => ({}));
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
  color: var(--text-primary, inherit);
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
