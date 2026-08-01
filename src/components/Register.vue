<script>
export default {
  name: 'Register',
  data() {
    return {
      username: '',
      email: '',
      password: '',
      confirmPassword: '',
      errors: {},
      submitting: false,
    };
  },
  methods: {
    async submit() {
      if (this.submitting) return;
      this.errors = {};

      if (this.password !== this.confirmPassword) {
        this.errors = { confirmPassword: 'Passwords do not match.' };
        return;
      }

      this.submitting = true;
      try {
        const response = await fetch('/api/register', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'same-origin',
          body: JSON.stringify({
            username: this.username,
            email: this.email,
            password: this.password,
          }),
        });
        const data = await response.json();
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
    <h1>Create an account</h1>
    <form class="auth-form" @submit.prevent="submit" novalidate>
      <p v-if="errors.form" class="form-error" role="alert">{{ errors.form }}</p>

      <label class="field">
        <span>Username</span>
        <input
          v-model="username"
          type="text"
          name="username"
          autocomplete="username"
          required
          :aria-invalid="!!errors.username"
          aria-describedby="username-error"
        >
        <span v-if="errors.username" id="username-error" class="field-error" role="alert">{{ errors.username }}</span>
      </label>

      <label class="field">
        <span>Email</span>
        <input
          v-model="email"
          type="email"
          name="email"
          autocomplete="email"
          required
          :aria-invalid="!!errors.email"
          aria-describedby="email-error"
        >
        <span v-if="errors.email" id="email-error" class="field-error" role="alert">{{ errors.email }}</span>
      </label>

      <label class="field">
        <span>Password</span>
        <input
          v-model="password"
          type="password"
          name="new-password"
          autocomplete="new-password"
          required
          minlength="8"
          :aria-invalid="!!errors.password"
          aria-describedby="password-error"
        >
        <span v-if="errors.password" id="password-error" class="field-error" role="alert">{{ errors.password }}</span>
      </label>

      <label class="field">
        <span>Confirm password</span>
        <input
          v-model="confirmPassword"
          type="password"
          name="confirm-password"
          autocomplete="new-password"
          required
          :aria-invalid="!!errors.confirmPassword"
          aria-describedby="confirm-password-error"
        >
        <span v-if="errors.confirmPassword" id="confirm-password-error" class="field-error" role="alert">{{ errors.confirmPassword }}</span>
      </label>

      <button type="submit" class="submit-button" :disabled="submitting">
        {{ submitting ? 'Creating account…' : 'Create account' }}
      </button>
    </form>
    <p class="auth-switch">Already have an account? <a href="/login">Log in</a></p>
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
