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

const MAX_BODY_LENGTH = 1000;

export default {
  name: 'Posts',
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

      posts: [],
      postsLoading: true,
      postsError: false,
      hasMore: true,
      loadingMore: false,
      removingId: null,
      copiedId: null,
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
      return !this.posting && this.body.trim().length > 0 && this.remaining >= 0;
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
    this.loadPosts();
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
    async loadPosts() {
      this.postsLoading = true;
      this.postsError = false;
      try {
        const response = await fetch('/api/posts', { credentials: 'same-origin' });
        if (!response.ok) throw new Error(`Request failed: ${response.status}`);
        const data = await response.json();
        this.posts = data;
        this.hasMore = data.length > 0;
      } catch {
        this.postsError = true;
      } finally {
        this.postsLoading = false;
      }
    },
    async loadMore() {
      if (this.loadingMore || !this.hasMore || !this.posts.length) return;
      this.loadingMore = true;
      try {
        const beforeId = this.posts[this.posts.length - 1].id;
        const response = await fetch(`/api/posts?beforeId=${beforeId}`, { credentials: 'same-origin' });
        if (!response.ok) throw new Error(`Request failed: ${response.status}`);
        const data = await response.json();
        this.posts = this.posts.concat(data);
        this.hasMore = data.length > 0;
      } catch {
        this.hasMore = false;
      } finally {
        this.loadingMore = false;
      }
    },
    async submitPost() {
      if (!this.canPost) return;
      this.posting = true;
      this.postError = '';
      try {
        const response = await fetch('/api/posts', {
          method: 'POST',
          credentials: 'same-origin',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRF-TOKEN': readCookie('csrf_access_token'),
          },
          body: JSON.stringify({
            body: this.body.trim(),
            savedItemId: this.selectedSavedItemId,
          }),
        });
        const data = await response.json();
        if (!response.ok) {
          this.postError = data.errors?.body || data.errors?.savedItemId || 'Could not create post.';
          return;
        }
        this.posts.unshift(data);
        this.body = '';
        this.selectedSavedItemId = null;
      } catch {
        this.postError = 'Could not create post.';
      } finally {
        this.posting = false;
      }
    },
    async removePost(post) {
      if (this.removingId) return;
      this.removingId = post.id;
      try {
        const response = await fetch(`/api/posts/${post.id}`, {
          method: 'DELETE',
          credentials: 'same-origin',
          headers: { 'X-CSRF-TOKEN': readCookie('csrf_access_token') },
        });
        if (response.ok) {
          this.posts = this.posts.filter((p) => p.id !== post.id);
        }
      } finally {
        this.removingId = null;
      }
    },
    async sharePost(post) {
      const url = `${window.location.origin}/posts/${post.id}`;
      if (navigator.share) {
        try {
          await navigator.share({ url });
        } catch {
          // User cancelled the share sheet or it failed silently; no action needed.
        }
        return;
      }
      try {
        await navigator.clipboard.writeText(url);
        this.copiedId = post.id;
        setTimeout(() => {
          if (this.copiedId === post.id) this.copiedId = null;
        }, 2000);
      } catch {
        // Clipboard API unavailable (e.g. insecure context); nothing more we can do.
      }
    },
    formatDate,
  },
};
</script>

<template>
  <div class="posts-page">
    <p v-if="loading" class="status">Loading…</p>
    <template v-else-if="error">
      <p class="status form-error">Couldn't load posts. Please refresh the page.</p>
    </template>
    <template v-else>
      <h1>Posts</h1>

      <section class="composer">
        <textarea
          v-model="body"
          :maxlength="MAX_BODY_LENGTH"
          placeholder="Share something…"
          rows="3"
        ></textarea>

        <div v-if="selectedSavedItem" class="attached-item">
          <img v-if="selectedSavedItem.imageUrl" :src="selectedSavedItem.imageUrl" :alt="selectedSavedItem.title" class="attached-thumb">
          <span class="attached-title">{{ selectedSavedItem.title }}</span>
          <button type="button" class="attached-remove" @click="selectedSavedItemId = null">✕</button>
        </div>

        <div class="composer-footer">
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
        <p v-if="postsLoading" class="status">Loading…</p>
        <p v-else-if="postsError" class="status form-error">Couldn't load posts.</p>
        <p v-else-if="!posts.length" class="status">No posts yet — be the first to share something.</p>
        <ul v-else class="post-list">
          <li v-for="post in posts" :key="post.id" class="post">
            <img :src="post.author.avatarUrl" :alt="post.author.username" class="post-avatar">
            <div class="post-body">
              <div class="post-header">
                <span class="post-author">{{ post.author.displayName || post.author.username }}</span>
                <span class="post-date">{{ formatDate(post.createdAt) }}</span>
              </div>
              <p class="post-text">{{ post.body }}</p>
              <a
                v-if="post.sharedItem"
                :href="post.sharedItem.sourceUrl"
                target="_blank"
                rel="noopener"
                class="shared-item"
              >
                <img v-if="post.sharedItem.imageUrl" :src="post.sharedItem.imageUrl" :alt="post.sharedItem.title" class="shared-thumb">
                <div class="shared-info">
                  <span class="shared-title">{{ post.sharedItem.title }}</span>
                  <span v-if="post.sharedItem.subtitle" class="shared-subtitle">{{ post.sharedItem.subtitle }}</span>
                </div>
              </a>
              <div class="post-actions">
                <button
                  type="button"
                  class="share-button"
                  @click="sharePost(post)"
                >{{ copiedId === post.id ? 'Link copied!' : 'Share' }}</button>
                <button
                  v-if="user && post.author.id === user.id"
                  type="button"
                  class="remove-button"
                  :disabled="removingId === post.id"
                  @click="removePost(post)"
                >{{ removingId === post.id ? 'Removing…' : 'Delete' }}</button>
              </div>
            </div>
          </li>
        </ul>
        <button
          v-if="hasMore && posts.length"
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
.posts-page {
  max-width: 640px;
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
  font-size: 0.9rem;
  padding: 0.5rem;
  border: 1px solid var(--gridline, #d8c9a3);
  border-radius: 4px;
  background: var(--surface-1, #fcfcfb);
  color: inherit;
  box-sizing: border-box;
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
  background: transparent;
  border: none;
  cursor: pointer;
  color: var(--text-secondary, #6b5d47);
  font-size: 0.85rem;
}
.composer-footer {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  margin-top: 0.6rem;
}
.saved-picker {
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
  padding: 0.75rem;
  border: 1px solid var(--gridline, #d8c9a3);
  border-radius: 6px;
}
.post-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  flex: none;
  background: var(--surface-1, #fcfcfb);
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
  white-space: pre-wrap;
  overflow-wrap: break-word;
}
.shared-item {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  margin-top: 0.6rem;
  padding: 0.5rem;
  border: 1px solid var(--gridline, #d8c9a3);
  border-radius: 6px;
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
