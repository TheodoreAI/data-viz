<script>
function readCookie(name) {
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : null;
}

function formatDate(iso) {
  if (!iso) return '';
  return new Date(iso).toLocaleString(undefined, {
    year: 'numeric', month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit',
  });
}

const MAX_BODY_LENGTH = 3000;
const COLLAPSE_LENGTH = 500;
const MAX_IMAGE_DIMENSION = 1600;
const IMAGE_JPEG_QUALITY = 0.82;

function resizeImageFile(file) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    const objectUrl = URL.createObjectURL(file);
    img.onload = () => {
      URL.revokeObjectURL(objectUrl);
      const scale = Math.min(1, MAX_IMAGE_DIMENSION / Math.max(img.width, img.height));
      const canvas = document.createElement('canvas');
      canvas.width = Math.round(img.width * scale);
      canvas.height = Math.round(img.height * scale);
      canvas.getContext('2d').drawImage(img, 0, 0, canvas.width, canvas.height);
      canvas.toBlob(
        (blob) => (blob ? resolve(blob) : reject(new Error('Could not process image.'))),
        'image/jpeg',
        IMAGE_JPEG_QUALITY,
      );
    };
    img.onerror = () => {
      URL.revokeObjectURL(objectUrl);
      reject(new Error('Could not read image.'));
    };
    img.src = objectUrl;
  });
}

import LoadingSpinner from './LoadingSpinner.vue';
import { parseJsonResponse } from '../api';
import { useClipboard, useIntersectionObserver } from '@vueuse/core';

const revealOnScroll = {
  mounted(el) {
    const { stop } = useIntersectionObserver(
      el,
      ([{ isIntersecting }]) => {
        if (isIntersecting) {
          el.classList.add('is-visible');
          stop();
        }
      },
      { threshold: 0.15 },
    );
  },
};

export default {
  name: 'Essays',
  components: { LoadingSpinner },
  directives: { revealOnScroll },
  setup() {
    const { copy, isSupported: clipboardSupported } = useClipboard();
    return { copy, clipboardSupported };
  },
  data() {
    return {
      user: null,
      loading: true,
      error: false,

      body: '',
      savedItems: [],
      savedItemsLoading: true,
      selectedSavedItemId: null,
      posting: false,
      postError: '',

      imagePreviewUrl: '',
      uploadedImageUrl: '',
      uploadingImage: false,
      imageError: '',

      essays: [],
      essaysLoading: true,
      essaysError: false,
      hasMore: true,
      loadingMore: false,
      removingId: null,
      copiedId: null,
      expandedIds: new Set(),
    };
  },
  computed: {
    MAX_BODY_LENGTH() {
      return MAX_BODY_LENGTH;
    },
    remaining() {
      return MAX_BODY_LENGTH - this.body.length;
    },
    selectedSavedItem() {
      return this.savedItems.find((item) => item.id === this.selectedSavedItemId) || null;
    },
    canPost() {
      return !this.posting && !this.uploadingImage && this.body.trim().length > 0 && this.remaining >= 0;
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

    this.loadSavedItems();
    this.loadEssays();
  },
  methods: {
    async loadSavedItems() {
      this.savedItemsLoading = true;
      try {
        const response = await fetch('/api/saved-items', { credentials: 'same-origin' });
        if (!response.ok) throw new Error(`Request failed: ${response.status}`);
        this.savedItems = await response.json();
      } catch {
        this.savedItems = [];
      } finally {
        this.savedItemsLoading = false;
      }
    },
    async loadEssays() {
      this.essaysLoading = true;
      this.essaysError = false;
      try {
        const response = await fetch('/api/essays', { credentials: 'same-origin' });
        if (!response.ok) throw new Error(`Request failed: ${response.status}`);
        const data = await response.json();
        this.essays = data;
        this.hasMore = data.length > 0;
      } catch {
        this.essaysError = true;
      } finally {
        this.essaysLoading = false;
      }
    },
    async loadMore() {
      if (this.loadingMore || !this.hasMore || !this.essays.length) return;
      this.loadingMore = true;
      try {
        const beforeId = this.essays[this.essays.length - 1].id;
        const response = await fetch(`/api/essays?beforeId=${beforeId}`, { credentials: 'same-origin' });
        if (!response.ok) throw new Error(`Request failed: ${response.status}`);
        const data = await response.json();
        this.essays = this.essays.concat(data);
        this.hasMore = data.length > 0;
      } catch {
        this.hasMore = false;
      } finally {
        this.loadingMore = false;
      }
    },
    async onImageSelected(event) {
      const file = event.target.files?.[0];
      event.target.value = '';
      if (!file) return;

      this.imageError = '';
      this.uploadingImage = true;
      try {
        const resized = await resizeImageFile(file);
        this.imagePreviewUrl = URL.createObjectURL(resized);

        const formData = new FormData();
        formData.append('file', resized, 'photo.jpg');
        const response = await fetch('/api/uploads', {
          method: 'POST',
          credentials: 'same-origin',
          headers: { 'X-CSRF-TOKEN': readCookie('csrf_access_token') },
          body: formData,
        });
        const data = await parseJsonResponse(response);
        if (!response.ok) {
          this.imageError = data.errors?.file || data.errors?.form || 'Could not upload image.';
          this.removeImage();
          return;
        }
        this.uploadedImageUrl = data.url;
      } catch {
        this.imageError = 'Could not upload image.';
        this.removeImage();
      } finally {
        this.uploadingImage = false;
      }
    },
    removeImage() {
      if (this.imagePreviewUrl) URL.revokeObjectURL(this.imagePreviewUrl);
      this.imagePreviewUrl = '';
      this.uploadedImageUrl = '';
    },
    async submitPost() {
      if (!this.canPost) return;
      this.posting = true;
      this.postError = '';
      try {
        const response = await fetch('/api/essays', {
          method: 'POST',
          credentials: 'same-origin',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRF-TOKEN': readCookie('csrf_access_token'),
          },
          body: JSON.stringify({
            body: this.body.trim(),
            savedItemId: this.selectedSavedItemId,
            imageUrl: this.uploadedImageUrl || null,
          }),
        });
        const data = await response.json();
        if (!response.ok) {
          this.postError = data.errors?.body || data.errors?.savedItemId || 'Could not create essay.';
          return;
        }
        this.essays.unshift(data);
        this.body = '';
        this.selectedSavedItemId = null;
        this.removeImage();
        this.resetComposerHeight();
      } catch {
        this.postError = 'Could not create essay.';
      } finally {
        this.posting = false;
      }
    },
    async removeEssay(essay) {
      if (this.removingId) return;
      if (!window.confirm('Delete this essay? This cannot be undone.')) return;
      this.removingId = essay.id;
      try {
        const response = await fetch(`/api/essays/${essay.id}`, {
          method: 'DELETE',
          credentials: 'same-origin',
          headers: { 'X-CSRF-TOKEN': readCookie('csrf_access_token') },
        });
        if (response.ok) {
          this.essays = this.essays.filter((e) => e.id !== essay.id);
        }
      } finally {
        this.removingId = null;
      }
    },
    async shareEssay(essay) {
      const url = `${window.location.origin}/essays/${essay.id}`;
      if (navigator.share) {
        try {
          await navigator.share({ url });
        } catch {
          // User cancelled the share sheet or it failed silently; no action needed.
        }
        return;
      }
      if (!this.clipboardSupported) return;
      try {
        await this.copy(url);
        this.copiedId = essay.id;
        setTimeout(() => {
          if (this.copiedId === essay.id) this.copiedId = null;
        }, 2000);
      } catch {
        // Clipboard write rejected (e.g. insecure context); nothing more we can do.
      }
    },
    autoGrow(event) {
      const el = event.target;
      el.style.height = 'auto';
      el.style.height = `${el.scrollHeight}px`;
    },
    resetComposerHeight() {
      const el = this.$refs.composerTextarea;
      if (el) el.style.height = '';
    },
    isLongEssay(essay) {
      return essay.body.length > COLLAPSE_LENGTH;
    },
    isExpanded(essay) {
      return this.expandedIds.has(essay.id);
    },
    displayBody(essay) {
      if (!this.isLongEssay(essay) || this.isExpanded(essay)) return essay.body;
      return `${essay.body.slice(0, COLLAPSE_LENGTH).trimEnd()}…`;
    },
    toggleExpanded(essay) {
      const expanded = new Set(this.expandedIds);
      if (expanded.has(essay.id)) {
        expanded.delete(essay.id);
      } else {
        expanded.add(essay.id);
      }
      this.expandedIds = expanded;
    },
    formatDate,
  },
};
</script>

<template>
  <div class="essays-page">
    <LoadingSpinner v-if="loading" size="lg" />
    <template v-else-if="error">
      <p class="status form-error">Couldn't load essays. Please refresh the page.</p>
    </template>
    <template v-else>
      <h1>Essays</h1>

      <section class="composer">
        <textarea
          ref="composerTextarea"
          v-model="body"
          :maxlength="MAX_BODY_LENGTH"
          placeholder="Share something…"
          rows="6"
          @input="autoGrow"
        ></textarea>

        <div v-if="selectedSavedItem" class="attached-item">
          <img v-if="selectedSavedItem.imageUrl" :src="selectedSavedItem.imageUrl" :alt="selectedSavedItem.title" class="attached-thumb">
          <span class="attached-title">{{ selectedSavedItem.title }}</span>
          <button type="button" class="attached-remove" aria-label="Remove attached item" @click="selectedSavedItemId = null">
            <svg viewBox="0 0 16 16" aria-hidden="true"><path d="M4 4l8 8M12 4l-8 8" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" /></svg>
          </button>
        </div>

        <div v-if="imagePreviewUrl" class="attached-image">
          <img :src="imagePreviewUrl" alt="Selected photo" class="attached-image-preview">
          <span v-if="uploadingImage" class="attached-image-status">Uploading…</span>
          <button type="button" class="attached-remove" :disabled="uploadingImage" aria-label="Remove photo" @click="removeImage">
            <svg viewBox="0 0 16 16" aria-hidden="true"><path d="M4 4l8 8M12 4l-8 8" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" /></svg>
          </button>
        </div>
        <p v-if="imageError" class="status form-error">{{ imageError }}</p>

        <div class="composer-footer">
          <label class="photo-button" aria-label="Add photo">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 640"><!--!Font Awesome Free v7.3.1 by @fontawesome - https://fontawesome.com License - https://fontawesome.com/license/free Copyright 2026 Fonticons, Inc.--><path d="M213.1 128.8L202.7 160L128 160C92.7 160 64 188.7 64 224L64 480C64 515.3 92.7 544 128 544L512 544C547.3 544 576 515.3 576 480L576 224C576 188.7 547.3 160 512 160L437.3 160L426.9 128.8C420.4 109.2 402.1 96 381.4 96L258.6 96C237.9 96 219.6 109.2 213.1 128.8zM320 256C373 256 416 299 416 352C416 405 373 448 320 448C267 448 224 405 224 352C224 299 267 256 320 256z"/></svg>
            <input
              type="file"
              accept="image/*"
              capture="environment"
              hidden
              :disabled="uploadingImage"
              @change="onImageSelected"
            >
          </label>
          <select
            v-if="!savedItemsLoading && savedItems.length"
            v-model="selectedSavedItemId"
            class="saved-picker"
          >
            <option :value="null">Attach a saved item…</option>
            <option v-for="item in savedItems" :key="item.id" :value="item.id">{{ item.title }}</option>
          </select>
          <span class="spacer"></span>
          <span class="char-count" :class="{ over: remaining < 0 }">{{ remaining }}</span>
          <button type="button" class="post-button" :disabled="!canPost" @click="submitPost">
            {{ posting ? 'Posting…' : 'Post' }}
          </button>
        </div>
        <p v-if="postError" class="status form-error">{{ postError }}</p>
      </section>

      <section class="feed">
        <LoadingSpinner v-if="essaysLoading" size="sm" inline />
        <p v-else-if="essaysError" class="status form-error">Couldn't load essays.</p>
        <p v-else-if="!essays.length" class="status">No essays yet — be the first to share something.</p>
        <ul v-else class="post-list">
          <li v-for="essay in essays" :key="essay.id" v-reveal-on-scroll class="post">
            <img :src="essay.author.avatarUrl" :alt="essay.author.username" class="post-avatar">
            <div class="post-body">
              <div class="post-header">
                <span class="post-author">{{ essay.author.displayName || essay.author.username }}</span>
                <span class="post-date">{{ formatDate(essay.createdAt) }}</span>
              </div>
              <p class="post-text">{{ displayBody(essay) }}</p>
              <button
                v-if="isLongEssay(essay)"
                type="button"
                class="read-more"
                @click="toggleExpanded(essay)"
              >{{ isExpanded(essay) ? 'Show less' : 'Read more' }}</button>
              <img v-if="essay.imageUrl" :src="essay.imageUrl" alt="" class="post-image">
              <a
                v-if="essay.sharedItem"
                :href="essay.sharedItem.sourceUrl"
                target="_blank"
                rel="noopener"
                class="shared-item"
              >
                <img v-if="essay.sharedItem.imageUrl" :src="essay.sharedItem.imageUrl" :alt="essay.sharedItem.title" class="shared-thumb">
                <div class="shared-info">
                  <span class="shared-title">{{ essay.sharedItem.title }}</span>
                  <span v-if="essay.sharedItem.subtitle" class="shared-subtitle">{{ essay.sharedItem.subtitle }}</span>
                </div>
              </a>
              <div class="post-actions">
                <button
                  type="button"
                  class="share-button"
                  @click="shareEssay(essay)"
                >{{ copiedId === essay.id ? 'Link copied!' : 'Share' }}</button>
                <button
                  v-if="user && essay.author.id === user.id"
                  type="button"
                  class="remove-button"
                  :disabled="removingId === essay.id"
                  @click="removeEssay(essay)"
                >{{ removingId === essay.id ? 'Deleting…' : 'Delete' }}</button>
              </div>
            </div>
          </li>
        </ul>
        <button
          v-if="hasMore && essays.length"
          type="button"
          class="load-more"
          :disabled="loadingMore"
          @click="loadMore"
        >{{ loadingMore ? 'Loading…' : 'Load more' }}</button>
      </section>
    </template>
  </div>
</template>

<style scoped>
.essays-page {
  max-width: 960px;
  margin: 0 auto;
  padding: 2rem 1.25rem 3rem;
}
h1 {
  font-size: 1.3rem;
  margin: 0 0 1.25rem;
}
.status {
  color: var(--text-secondary, #6b5d47);
  font-size: 0.9rem;
}
.form-error {
  color: #b0413e;
}
.composer {
  border: 1px solid var(--gridline, #d8c9a3);
  border-radius: 6px;
  padding: 0.75rem;
  margin-bottom: 2rem;
}
.composer textarea {
  width: 100%;
  resize: vertical;
  font-family: inherit;
  font-size: 1rem;
  line-height: 1.6;
  padding: 0.75rem;
  border: 1px solid var(--gridline, #d8c9a3);
  border-radius: 4px;
  background: var(--surface-1, #fcfcfb);
  color: inherit;
  box-sizing: border-box;
  max-height: 60vh;
  overflow-y: auto;
}
@media (max-width: 480px) {
  .composer textarea {
    font-size: 16px; /* prevents iOS Safari from zooming in on focus */
  }
}
.attached-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-top: 0.6rem;
  padding: 0.4rem 0.5rem;
  border: 1px solid var(--gridline, #d8c9a3);
  border-radius: 4px;
}
.attached-thumb {
  width: 32px;
  height: 32px;
  object-fit: cover;
  border-radius: 4px;
  flex: none;
}
.attached-title {
  font-size: 0.85rem;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.attached-remove {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  cursor: pointer;
  color: var(--text-secondary, #6b5d47);
}
.attached-remove svg {
  width: 12px;
  height: 12px;
}
.attached-image {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-top: 0.6rem;
}
.attached-image-preview {
  width: 64px;
  height: 64px;
  object-fit: cover;
  border-radius: 4px;
  border: 1px solid var(--gridline, #d8c9a3);
}
.attached-image-status {
  font-size: 0.78rem;
  color: var(--text-secondary, #6b5d47);
}
.photo-button {
  flex: none;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 2rem;
  height: 2rem;
  border: 1px solid var(--gridline, #d8c9a3);
  border-radius: 4px;
  cursor: pointer;
  color: var(--series-1, #2f6690);
}
.photo-button:hover {
  border-color: var(--series-1, #2f6690);
}
.photo-button svg {
  width: 1rem;
  height: 1rem;
  fill: currentColor;
}
.composer-footer {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.6rem;
  margin-top: 0.6rem;
}
.saved-picker {
  flex: 1 1 0;
  min-width: 0;
  font-family: inherit;
  font-size: 0.82rem;
  padding: 0.3rem 0.4rem;
  border: 1px solid var(--gridline, #d8c9a3);
  border-radius: 4px;
  background: var(--surface-1, #fcfcfb);
  color: inherit;
  max-width: 55%;
}
.spacer {
  flex: 1;
}
.char-count {
  font-size: 0.78rem;
  color: var(--text-secondary, #6b5d47);
}
.char-count.over {
  color: #b0413e;
}
.post-button {
  background: var(--series-1, #2f6690);
  color: #fff;
  border: none;
  border-radius: 4px;
  padding: 0.4rem 0.9rem;
  font-size: 0.85rem;
  cursor: pointer;
}
.post-button:disabled {
  opacity: 0.5;
  cursor: default;
}
.post-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}
.post {
  display: flex;
  gap: 0.75rem;
  padding: 1rem;
  background: var(--card-bg, #fff);
  border: none;
  border-radius: var(--card-radius, 16px);
  box-shadow: 0 8px 24px rgba(20, 23, 31, 0.08);
  opacity: 0;
  transform: translateY(12px);
  transition: opacity 0.5s ease, transform 0.5s ease;
}
.post.is-visible {
  opacity: 1;
  transform: none;
}
@media (prefers-reduced-motion: reduce) {
  .post {
    opacity: 1;
    transform: none;
    transition: none;
  }
}
.post-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  flex: none;
  background: var(--gridline, #e2e5eb);
}
.post-body {
  flex: 1;
  min-width: 0;
}
.post-header {
  display: flex;
  align-items: baseline;
  gap: 0.5rem;
  flex-wrap: wrap;
}
.post-author {
  font-weight: 700;
  font-size: 0.9rem;
}
.post-date {
  font-size: 0.75rem;
  color: var(--text-secondary, #6b5d47);
}
.post-text {
  margin: 0.3rem 0 0;
  font-size: 0.9rem;
  line-height: 1.6;
  max-width: 65ch;
  white-space: pre-wrap;
  overflow-wrap: break-word;
}
.read-more {
  display: inline-block;
  margin-top: 0.4rem;
  padding: 0;
  background: none;
  border: none;
  font-family: inherit;
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--series-1, #2f6690);
  cursor: pointer;
}
.read-more:hover {
  text-decoration: underline;
}
.post-image {
  display: block;
  width: 100%;
  max-height: 360px;
  object-fit: cover;
  border-radius: 12px;
  margin-top: 0.6rem;
}
.shared-item {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  margin-top: 0.6rem;
  padding: 0.5rem;
  border: 1px solid var(--gridline, #d8c9a3);
  border-radius: 12px;
  text-decoration: none;
  color: inherit;
}
.shared-item:hover {
  border-color: var(--series-1, #2f6690);
}
.shared-thumb {
  width: 40px;
  height: 40px;
  object-fit: cover;
  border-radius: 4px;
  flex: none;
}
.shared-info {
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.shared-title {
  color: var(--series-1, #2f6690);
  font-size: 0.85rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.shared-subtitle {
  font-size: 0.75rem;
  color: var(--text-secondary, #6b5d47);
}
.post-actions {
  display: flex;
  gap: 0.5rem;
  margin-top: 0.5rem;
}
.share-button {
  background: transparent;
  border: 1px solid var(--gridline, #d8c9a3);
  color: var(--series-1, #2f6690);
  border-radius: 4px;
  padding: 0.25rem 0.6rem;
  font-size: 0.75rem;
  cursor: pointer;
}
.remove-button {
  background: transparent;
  border: 1px solid var(--gridline, #d8c9a3);
  color: #b0413e;
  border-radius: 4px;
  padding: 0.25rem 0.6rem;
  font-size: 0.75rem;
  cursor: pointer;
}
.remove-button:disabled {
  opacity: 0.6;
  cursor: default;
}
.load-more {
  display: block;
  margin: 1rem auto 0;
  background: transparent;
  border: 1px solid var(--gridline, #d8c9a3);
  border-radius: 4px;
  padding: 0.4rem 1rem;
  font-size: 0.82rem;
  cursor: pointer;
}
.load-more:disabled {
  opacity: 0.6;
  cursor: default;
}
</style>
