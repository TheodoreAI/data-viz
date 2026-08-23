<script>
import LoadingSpinner from './LoadingSpinner.vue';
import { parseJsonResponse } from '../api';

// Standard WHO/EPA UV index bands.
const UV_BANDS = [
  { max: 2, label: 'Low', color: '#0ca30c' },
  { max: 5, label: 'Moderate', color: '#eda100' },
  { max: 7, label: 'High', color: '#eb6834' },
  { max: 10, label: 'Very High', color: '#d03b3b' },
  { max: Infinity, label: 'Extreme', color: '#7a3aa7' },
];

function bandFor(uv) {
  if (uv == null) return null;
  return UV_BANDS.find(b => uv <= b.max);
}

// Only fetch a new UV reading once the runner has covered real distance or
// enough time has passed — Open-Meteo is forecast-grid data, not a live feed,
// so sampling every GPS tick would be wasted calls against a value that
// hasn't actually changed.
const MIN_SAMPLE_DISTANCE_METERS = 400;
const MIN_SAMPLE_INTERVAL_MS = 3 * 60 * 1000;

function haversineMeters(a, b) {
  const R = 6371000;
  const toRad = (deg) => (deg * Math.PI) / 180;
  const dLat = toRad(b.lat - a.lat);
  const dLon = toRad(b.lon - a.lon);
  const lat1 = toRad(a.lat);
  const lat2 = toRad(b.lat);
  const h = Math.sin(dLat / 2) ** 2 + Math.cos(lat1) * Math.cos(lat2) * Math.sin(dLon / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(h));
}

function readCookie(name) {
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : null;
}

export default {
  name: 'JogTracker',
  components: { LoadingSpinner },
  data() {
    return {
      loggedIn: null, // null = checking, true/false once known
      tracking: false,
      starting: false,
      session: null, // { id, readings: [], ... } while active
      error: '',
      geoError: '',
      history: [],
      historyLoading: false,
      selectedPastSession: null,
      deletingId: null,
    };
  },
  computed: {
    readings() {
      return this.session?.readings || [];
    },
    latestReading() {
      return this.readings[this.readings.length - 1] || null;
    },
    latestBand() {
      return this.latestReading ? bandFor(this.latestReading.uvIndex) : null;
    },
    elapsedMinutes() {
      if (!this.session?.startedAt) return 0;
      return (Date.now() - new Date(this.session.startedAt).getTime()) / 60000;
    },
    exposureScore() {
      if (this.readings.length < 2) return 0;
      let total = 0;
      for (let i = 0; i < this.readings.length - 1; i++) {
        const a = this.readings[i];
        const b = this.readings[i + 1];
        const minutes = (new Date(b.recordedAt) - new Date(a.recordedAt)) / 60000;
        total += a.uvIndex * minutes;
      }
      return Math.round(total * 10) / 10;
    },
    pathBounds() {
      if (!this.readings.length) return null;
      const lats = this.readings.map(r => r.lat);
      const lons = this.readings.map(r => r.lon);
      return {
        minLat: Math.min(...lats), maxLat: Math.max(...lats),
        minLon: Math.min(...lons), maxLon: Math.max(...lons),
      };
    },
  },
  async mounted() {
    try {
      const response = await fetch('/api/profile', { credentials: 'same-origin' });
      this.loggedIn = response.ok;
      if (response.ok) this.loadHistory();
    } catch {
      this.loggedIn = false;
    }
  },
  beforeUnmount() {
    this.stopWatch();
  },
  methods: {
    bandFor,
    boundsOf(readings) {
      const lats = readings.map(r => r.lat);
      const lons = readings.map(r => r.lon);
      return {
        minLat: Math.min(...lats), maxLat: Math.max(...lats),
        minLon: Math.min(...lons), maxLon: Math.max(...lons),
      };
    },
    projectToSvg(reading, width, height, padding, readings = this.readings) {
      const b = readings.length ? this.boundsOf(readings) : null;
      if (!b) return { x: width / 2, y: height / 2 };
      const spanLat = b.maxLat - b.minLat || 0.0005;
      const spanLon = b.maxLon - b.minLon || 0.0005;
      const x = padding + ((reading.lon - b.minLon) / spanLon) * (width - padding * 2);
      // Latitude increases northward; SVG y increases downward, so flip it.
      const y = padding + (1 - (reading.lat - b.minLat) / spanLat) * (height - padding * 2);
      return { x, y };
    },
    pathPoints(width, height, padding) {
      return this.readings.map(r => this.projectToSvg(r, width, height, padding));
    },
    pathD(width, height, padding) {
      const points = this.pathPoints(width, height, padding);
      if (!points.length) return '';
      return points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(' ');
    },
    pathDFor(readings, width, height, padding) {
      if (readings.length < 2) return '';
      const b = this.boundsOf(readings);
      const spanLat = b.maxLat - b.minLat || 0.0005;
      const spanLon = b.maxLon - b.minLon || 0.0005;
      return readings.map((r, i) => {
        const x = padding + ((r.lon - b.minLon) / spanLon) * (width - padding * 2);
        const y = padding + (1 - (r.lat - b.minLat) / spanLat) * (height - padding * 2);
        return `${i === 0 ? 'M' : 'L'} ${x.toFixed(1)} ${y.toFixed(1)}`;
      }).join(' ');
    },
    async loadHistory() {
      this.historyLoading = true;
      try {
        const response = await fetch('/api/uv-sessions', { credentials: 'same-origin' });
        if (response.ok) this.history = await response.json();
      } finally {
        this.historyLoading = false;
      }
    },
    async startTracking() {
      if (!navigator.geolocation) {
        this.error = 'Geolocation is not available in this browser.';
        return;
      }
      this.starting = true;
      this.error = '';
      this.geoError = '';
      try {
        const response = await fetch('/api/uv-sessions', {
          method: 'POST',
          credentials: 'same-origin',
          headers: { 'X-CSRF-TOKEN': readCookie('csrf_access_token') },
        });
        const data = await parseJsonResponse(response);
        if (!response.ok) throw new Error(data.error || `Request failed: ${response.status}`);
        this.session = { ...data, readings: [] };
        this.tracking = true;
        this.lastSample = null;
        this.startWatch();
      } catch (err) {
        this.error = err.message || 'Could not start tracking. Please try again.';
      } finally {
        this.starting = false;
      }
    },
    startWatch() {
      this.watchId = navigator.geolocation.watchPosition(
        this.onPosition,
        () => {
          this.geoError = "Lost access to location. Make sure Location Services are on for this app.";
        },
        { enableHighAccuracy: true, maximumAge: 5000, timeout: 15000 }
      );
    },
    stopWatch() {
      if (this.watchId != null) {
        navigator.geolocation.clearWatch(this.watchId);
        this.watchId = null;
      }
    },
    async onPosition(position) {
      const point = { lat: position.coords.latitude, lon: position.coords.longitude };
      const now = Date.now();
      const dueByDistance = !this.lastSample || haversineMeters(this.lastSample.point, point) >= MIN_SAMPLE_DISTANCE_METERS;
      const dueByTime = !this.lastSample || now - this.lastSample.time >= MIN_SAMPLE_INTERVAL_MS;
      if (!dueByDistance && !dueByTime) return;
      if (this.sampling) return;

      this.sampling = true;
      this.lastSample = { point, time: now };
      try {
        const response = await fetch(`/api/uv-sessions/${this.session.id}/readings`, {
          method: 'POST',
          credentials: 'same-origin',
          headers: { 'Content-Type': 'application/json', 'X-CSRF-TOKEN': readCookie('csrf_access_token') },
          body: JSON.stringify(point),
        });
        const data = await parseJsonResponse(response);
        if (response.ok) {
          this.session.readings.push(data);
          this.geoError = '';
        }
      } catch {
        // Transient network blip mid-jog — the next GPS tick will retry.
      } finally {
        this.sampling = false;
      }
    },
    async stopTracking() {
      this.stopWatch();
      this.tracking = false;
      if (!this.session) return;
      try {
        const response = await fetch(`/api/uv-sessions/${this.session.id}/end`, {
          method: 'POST',
          credentials: 'same-origin',
          headers: { 'X-CSRF-TOKEN': readCookie('csrf_access_token') },
        });
        if (response.ok) {
          const ended = await response.json();
          this.session = { ...this.session, ...ended };
        }
      } finally {
        this.loadHistory();
      }
    },
    async viewPastSession(id) {
      const response = await fetch(`/api/uv-sessions/${id}`, { credentials: 'same-origin' });
      if (response.ok) this.selectedPastSession = await response.json();
    },
    async deleteSession(id) {
      if (this.deletingId) return;
      if (!window.confirm('Delete this jog and its tracked route? This cannot be undone.')) return;
      this.deletingId = id;
      try {
        const response = await fetch(`/api/uv-sessions/${id}`, {
          method: 'DELETE',
          credentials: 'same-origin',
          headers: { 'X-CSRF-TOKEN': readCookie('csrf_access_token') },
        });
        if (response.ok) {
          this.history = this.history.filter((s) => s.id !== id);
          if (this.selectedPastSession?.id === id) this.selectedPastSession = null;
        }
      } finally {
        this.deletingId = null;
      }
    },
    formatTime(iso) {
      return iso ? new Date(iso).toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' }) : '';
    },
    formatDate(iso) {
      return iso ? new Date(iso).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }) : '';
    },
  },
};
</script>

<template>
  <section class="jog-tracker">
    <h1>Jog Tracker</h1>
    <p v-if="loggedIn === false" class="status">
      <a href="/login">Log in</a> to track UV exposure during a run.
    </p>

    <template v-else-if="loggedIn">
      <p class="subtitle">
        Tracks your route with GPS while this page stays open and samples the UV index every ~400m or few minutes.
        On iPhone, keep this tab open and the screen on — Safari stops location updates once the app is backgrounded.
      </p>

      <div class="tracker-controls">
        <button v-if="!tracking" type="button" class="btn-primary" :disabled="starting" @click="startTracking">
          {{ starting ? 'Starting…' : '▶ Start Jog' }}
        </button>
        <button v-else type="button" class="btn-stop" @click="stopTracking">■ Stop Jog</button>
      </div>

      <p v-if="error" class="status form-error" role="alert">{{ error }}</p>
      <p v-if="geoError" class="status form-error" role="alert">{{ geoError }}</p>

      <template v-if="tracking || (session && session.readings.length)">
        <div class="live-stats">
          <div class="live-stat">
            <span class="live-stat-value" :style="{ color: latestBand?.color }">{{ latestReading?.uvIndex ?? '—' }}</span>
            <span class="live-stat-label">Current UV{{ latestBand ? ` · ${latestBand.label}` : '' }}</span>
          </div>
          <div class="live-stat">
            <span class="live-stat-value">{{ elapsedMinutes.toFixed(0) }}</span>
            <span class="live-stat-label">Minutes</span>
          </div>
          <div class="live-stat">
            <span class="live-stat-value">{{ exposureScore }}</span>
            <span class="live-stat-label">UV-index·min exposure</span>
          </div>
        </div>

        <svg v-if="readings.length > 1" class="path-map" viewBox="0 0 320 240" preserveAspectRatio="xMidYMid meet">
          <path :d="pathD(320, 240, 24)" class="path-line" />
          <circle
            v-for="(r, i) in readings"
            :key="r.id ?? i"
            :cx="projectToSvg(r, 320, 240, 24).x"
            :cy="projectToSvg(r, 320, 240, 24).y"
            r="4"
            :fill="bandFor(r.uvIndex)?.color"
          />
        </svg>
        <p v-else-if="tracking" class="status">Walking/running a bit before the map fills in…</p>
      </template>

      <section v-if="history.length" class="history">
        <h3>Past sessions</h3>
        <LoadingSpinner v-if="historyLoading" size="sm" inline />
        <ul class="history-list">
          <li v-for="s in history" :key="s.id" class="history-item">
            <button type="button" class="history-row" @click="viewPastSession(s.id)">
              <span class="history-date">{{ formatDate(s.startedAt) }} · {{ formatTime(s.startedAt) }}</span>
              <span class="history-meta">
                {{ s.durationMinutes ?? '—' }} min · avg UV {{ s.avgUvIndex ?? '—' }} · max UV {{ s.maxUvIndex ?? '—' }}
              </span>
            </button>
            <button
              type="button"
              class="delete-button"
              :disabled="deletingId === s.id"
              aria-label="Delete session"
              @click="deleteSession(s.id)"
            >{{ deletingId === s.id ? 'Deleting…' : 'Delete' }}</button>
          </li>
        </ul>

        <div v-if="selectedPastSession" class="past-session-detail">
          <svg
            v-if="selectedPastSession.readings.length > 1"
            class="path-map"
            viewBox="0 0 320 240"
            preserveAspectRatio="xMidYMid meet"
          >
            <path :d="pathDFor(selectedPastSession.readings, 320, 240, 24)" class="path-line" />
            <circle
              v-for="(r, i) in selectedPastSession.readings"
              :key="r.id ?? i"
              :cx="projectToSvg(r, 320, 240, 24, selectedPastSession.readings).x"
              :cy="projectToSvg(r, 320, 240, 24, selectedPastSession.readings).y"
              r="4"
              :fill="bandFor(r.uvIndex)?.color"
            />
          </svg>
        </div>
      </section>
    </template>
  </section>
</template>

<style scoped>
.jog-tracker {
  max-width: 640px;
  margin: 0 auto;
  padding: 2rem 1.25rem 3rem;
}
h1 {
  font-size: 1.3rem;
  margin: 0 0 0.4rem;
}
h3 {
  font-size: 0.95rem;
  margin: 1.5rem 0 0.6rem;
}
.subtitle {
  color: var(--text-secondary, #6b5d47);
  font-size: 0.85rem;
  margin: 0 0 1.25rem;
  line-height: 1.4;
}
.status {
  color: var(--text-secondary, #6b5d47);
  font-size: 0.9rem;
}
.status a {
  color: var(--series-1, #2f6690);
}
.form-error {
  color: #b0413e;
}
.tracker-controls {
  margin-bottom: 1.25rem;
}
.btn-primary,
.btn-stop {
  font-family: inherit;
  font-size: 0.85rem;
  padding: 0.6rem 1.3rem;
  border-radius: 999px;
  cursor: pointer;
  border: 1px solid var(--series-1, #2f6690);
}
.btn-primary {
  background: var(--series-1, #2f6690);
  color: #fff;
}
.btn-primary:disabled {
  opacity: 0.6;
  cursor: default;
}
.btn-stop {
  background: #b0413e;
  border-color: #b0413e;
  color: #fff;
}
.live-stats {
  display: flex;
  gap: 1.5rem;
  flex-wrap: wrap;
  margin-bottom: 1.25rem;
}
.live-stat {
  display: flex;
  flex-direction: column;
}
.live-stat-value {
  font-size: 1.6rem;
  font-weight: 700;
  color: var(--text-primary, inherit);
}
.live-stat-label {
  font-size: 0.72rem;
  color: var(--text-secondary, #6b5d47);
}
.path-map {
  width: 100%;
  max-width: 400px;
  height: auto;
  aspect-ratio: 4 / 3;
  background: var(--surface-1, #fcfcfb);
  border: 1px solid var(--gridline, #d8c9a3);
  border-radius: 12px;
  display: block;
}
.path-line {
  fill: none;
  stroke: var(--text-secondary, #98989f);
  stroke-width: 2;
  stroke-linecap: round;
  stroke-linejoin: round;
}
.history-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}
.history-item {
  display: flex;
  align-items: stretch;
  gap: 0.5rem;
}
.history-row {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
  flex: 1;
  min-width: 0;
  text-align: left;
  padding: 0.6rem 0.75rem;
  border: 1px solid var(--gridline, #d8c9a3);
  border-radius: 8px;
  background: transparent;
  font-family: inherit;
  cursor: pointer;
  color: inherit;
}
.history-row:hover {
  border-color: var(--series-1, #2f6690);
}
.delete-button {
  flex: none;
  background: transparent;
  border: 1px solid var(--gridline, #d8c9a3);
  color: #b0413e;
  border-radius: 8px;
  padding: 0.3rem 0.7rem;
  font-size: 0.78rem;
  font-family: inherit;
  cursor: pointer;
}
.delete-button:disabled {
  opacity: 0.6;
  cursor: default;
}
.history-date {
  font-size: 0.85rem;
  font-weight: 700;
}
.history-meta {
  font-size: 0.78rem;
  color: var(--text-secondary, #6b5d47);
}
.past-session-detail {
  margin-top: 1rem;
}
</style>
