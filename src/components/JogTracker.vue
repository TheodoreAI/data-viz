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

function distanceOf(readings) {
  let total = 0;
  for (let i = 0; i < readings.length - 1; i++) {
    total += haversineMeters(readings[i], readings[i + 1]);
  }
  return total;
}

// Minutes spent in each UV band across the session, by attributing the time
// between two consecutive readings to the band of the earlier (leading) one.
function bandMinutesOf(readings) {
  const totals = new Map(UV_BANDS.map(b => [b.label, 0]));
  for (let i = 0; i < readings.length - 1; i++) {
    const a = readings[i];
    const b = readings[i + 1];
    const minutes = (new Date(b.recordedAt) - new Date(a.recordedAt)) / 60000;
    const band = bandFor(a.uvIndex);
    if (band) totals.set(band.label, totals.get(band.label) + minutes);
  }
  return UV_BANDS.map(b => ({ ...b, minutes: totals.get(b.label) })).filter(b => b.minutes > 0);
}

function summarize(readings, session) {
  if (!readings.length) return null;
  const uvValues = readings.map(r => r.uvIndex);
  const durationMinutes = session?.startedAt && session?.endedAt
    ? (new Date(session.endedAt) - new Date(session.startedAt)) / 60000
    : null;
  const distanceMeters = distanceOf(readings);
  const exposureScore = (() => {
    if (readings.length < 2) return 0;
    let total = 0;
    for (let i = 0; i < readings.length - 1; i++) {
      const minutes = (new Date(readings[i + 1].recordedAt) - new Date(readings[i].recordedAt)) / 60000;
      total += readings[i].uvIndex * minutes;
    }
    return Math.round(total * 10) / 10;
  })();
  return {
    durationMinutes,
    distanceMeters,
    distanceKm: distanceMeters / 1000,
    avgUv: Math.round((uvValues.reduce((a, b) => a + b, 0) / uvValues.length) * 10) / 10,
    maxUv: Math.max(...uvValues),
    maxUvBand: bandFor(Math.max(...uvValues)),
    exposureScore,
    bandMinutes: bandMinutesOf(readings),
  };
}

function formatClock(totalSeconds) {
  const s = Math.max(0, Math.floor(totalSeconds));
  const hh = Math.floor(s / 3600);
  const mm = Math.floor((s % 3600) / 60);
  const ss = s % 60;
  const pad = (n) => String(n).padStart(2, '0');
  return hh > 0 ? `${hh}:${pad(mm)}:${pad(ss)}` : `${mm}:${pad(ss)}`;
}

function dayLabel(dateString) {
  if (dateString === 'Unknown') return 'Unknown date';
  const day = new Date(dateString);
  const today = new Date();
  const yesterday = new Date();
  yesterday.setDate(today.getDate() - 1);
  if (day.toDateString() === today.toDateString()) return 'Today';
  if (day.toDateString() === yesterday.toDateString()) return 'Yesterday';
  return day.toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' });
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
      showRoute: false,
      now: Date.now(),
      expandedDays: new Set(),
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
    elapsedSeconds() {
      if (!this.session?.startedAt) return 0;
      return (this.now - new Date(this.session.startedAt).getTime()) / 1000;
    },
    elapsedClock() {
      return formatClock(this.elapsedSeconds);
    },
    elapsedMinutes() {
      return this.elapsedSeconds / 60;
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
    justEnded() {
      return !this.tracking && !!this.session?.endedAt;
    },
    distanceMeters() {
      return distanceOf(this.readings);
    },
    summaryStats() {
      return summarize(this.readings, this.session);
    },
    historyByDay() {
      const groups = new Map();
      for (const s of this.history) {
        const key = s.startedAt ? new Date(s.startedAt).toDateString() : 'Unknown';
        if (!groups.has(key)) groups.set(key, []);
        groups.get(key).push(s);
      }
      return [...groups.entries()].map(([key, sessions]) => ({
        key,
        label: dayLabel(key),
        sessions,
        count: sessions.length,
        totalMinutes: sessions.reduce((sum, s) => sum + (s.durationMinutes || 0), 0),
      }));
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
    this.stopClock();
  },
  methods: {
    bandFor,
    startClock() {
      this.now = Date.now();
      this.clockId = setInterval(() => { this.now = Date.now(); }, 1000);
    },
    stopClock() {
      if (this.clockId != null) {
        clearInterval(this.clockId);
        this.clockId = null;
      }
    },
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
        if (response.ok) {
          this.history = await response.json();
          const mostRecentKey = this.historyByDay[0]?.key;
          if (mostRecentKey) this.expandedDays = new Set([mostRecentKey]);
        }
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
        this.showRoute = false;
        this.startWatch();
        this.startClock();
      } catch (err) {
        this.error = err.message || 'Could not start tracking. Please try again.';
      } finally {
        this.starting = false;
      }
    },
    startWatch() {
      this.watchId = navigator.geolocation.watchPosition(
        this.onPosition,
        this.onGeoError,
        { enableHighAccuracy: true, maximumAge: 5000, timeout: 15000 }
      );
    },
    onGeoError(err) {
      if (err.code === err.PERMISSION_DENIED) {
        this.geoError =
          "Location access is turned off for this app. On iPhone: Settings → Data Viz → Location " +
          '(or Settings → Privacy & Security → Location Services), then come back and tap Start Jog again.';
      } else if (err.code === err.POSITION_UNAVAILABLE) {
        this.geoError = "Couldn't determine your location. Make sure Location Services are on and you have a GPS signal.";
      } else {
        this.geoError = 'Lost access to location. Make sure Location Services are on for this app.';
      }
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
      this.stopClock();
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
    toggleDay(key) {
      if (this.expandedDays.has(key)) this.expandedDays.delete(key);
      else this.expandedDays.add(key);
      // Trigger reactivity — mutating a Set in place doesn't notify Vue.
      this.expandedDays = new Set(this.expandedDays);
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
          <svg class="btn-icon" viewBox="0 0 16 16" aria-hidden="true"><path d="M4 2.5v11l10-5.5z" fill="currentColor" /></svg>
          {{ starting ? 'Starting…' : 'Start Jog' }}
        </button>
        <button v-else type="button" class="btn-stop" @click="stopTracking">
          <svg class="btn-icon" viewBox="0 0 16 16" aria-hidden="true"><rect x="3" y="3" width="10" height="10" rx="1.5" fill="currentColor" /></svg>
          Stop Jog
        </button>
      </div>

      <p v-if="error" class="status form-error" role="alert">{{ error }}</p>
      <p v-if="geoError" class="status form-error" role="alert">{{ geoError }}</p>

      <template v-if="tracking">
        <div class="timer" role="timer">{{ elapsedClock }}</div>
        <div class="live-stats">
          <div class="live-stat">
            <span class="live-stat-value" :style="{ color: latestBand?.color }">{{ latestReading?.uvIndex ?? '—' }}</span>
            <span class="live-stat-label">Current UV{{ latestBand ? ` · ${latestBand.label}` : '' }}</span>
          </div>
          <div class="live-stat">
            <span class="live-stat-value">{{ exposureScore }}</span>
            <span class="live-stat-label">UV-index·min exposure</span>
          </div>
        </div>
        <p v-if="readings.length < 2" class="status">Walking/running a bit before stats fill in…</p>
      </template>

      <section v-else-if="justEnded && summaryStats" class="session-summary">
        <h2>Jog Summary</h2>
        <div class="summary-grid">
          <div class="summary-stat">
            <span class="summary-value">{{ summaryStats.durationMinutes?.toFixed(0) ?? '—' }}</span>
            <span class="summary-label">Minutes</span>
          </div>
          <div class="summary-stat">
            <span class="summary-value">{{ summaryStats.distanceKm.toFixed(2) }}</span>
            <span class="summary-label">Km covered</span>
          </div>
          <div class="summary-stat">
            <span class="summary-value" :style="{ color: summaryStats.maxUvBand?.color }">{{ summaryStats.maxUv }}</span>
            <span class="summary-label">Peak UV{{ summaryStats.maxUvBand ? ` · ${summaryStats.maxUvBand.label}` : '' }}</span>
          </div>
          <div class="summary-stat">
            <span class="summary-value">{{ summaryStats.avgUv }}</span>
            <span class="summary-label">Average UV</span>
          </div>
          <div class="summary-stat summary-stat-wide">
            <span class="summary-value">{{ summaryStats.exposureScore }}</span>
            <span class="summary-label">Total UV exposure (UV-index·min)</span>
          </div>
        </div>

        <div v-if="summaryStats.bandMinutes.length" class="band-breakdown">
          <h3>Time by UV level</h3>
          <div class="band-bar">
            <span
              v-for="b in summaryStats.bandMinutes"
              :key="b.label"
              class="band-bar-segment"
              :style="{ width: `${(b.minutes / summaryStats.durationMinutes) * 100}%`, background: b.color }"
              :title="`${b.label}: ${b.minutes.toFixed(1)} min`"
            ></span>
          </div>
          <div class="band-breakdown-legend">
            <span v-for="b in summaryStats.bandMinutes" :key="b.label" class="legend-item">
              <span class="legend-swatch" :style="{ background: b.color }"></span>
              {{ b.label }} · {{ b.minutes.toFixed(0) }} min
            </span>
          </div>
        </div>

        <button type="button" class="btn-secondary route-toggle" @click="showRoute = !showRoute">
          {{ showRoute ? 'Hide route' : 'View route map' }}
        </button>
        <svg v-if="showRoute && readings.length > 1" class="path-map" viewBox="0 0 320 240" preserveAspectRatio="xMidYMid meet">
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
      </section>

      <section v-if="history.length" class="history">
        <h3>Past sessions</h3>
        <LoadingSpinner v-if="historyLoading" size="sm" inline />
        <div v-for="day in historyByDay" :key="day.key" class="history-day">
          <button type="button" class="history-day-header" @click="toggleDay(day.key)">
            <span class="history-day-label">{{ day.label }}</span>
            <span class="history-day-meta">
              {{ day.count }} {{ day.count === 1 ? 'jog' : 'jogs' }} · {{ day.totalMinutes.toFixed(0) }} min
            </span>
            <svg class="history-day-chevron" :class="{ open: expandedDays.has(day.key) }" viewBox="0 0 16 16" aria-hidden="true">
              <path d="M4 6l4 4 4-4" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" />
            </svg>
          </button>
          <ul v-if="expandedDays.has(day.key)" class="history-list">
            <li v-for="s in day.sessions" :key="s.id" class="history-item">
              <button type="button" class="history-row" @click="viewPastSession(s.id)">
                <span class="history-date">{{ formatTime(s.startedAt) }}</span>
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
        </div>

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
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  font-family: inherit;
  font-size: 0.85rem;
  padding: 0.6rem 1.3rem;
  border-radius: 999px;
  cursor: pointer;
  border: 1px solid var(--series-1, #2f6690);
}
.btn-icon {
  width: 14px;
  height: 14px;
  flex: none;
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
.timer {
  font-size: 2.75rem;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  color: var(--text-primary, inherit);
  margin-bottom: 1rem;
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
  margin-top: 1rem;
}
.session-summary {
  margin-bottom: 1.5rem;
}
.session-summary h2 {
  font-size: 1rem;
  margin: 0 0 1rem;
}
.summary-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem 1.5rem;
  margin-bottom: 1.5rem;
}
.summary-stat {
  display: flex;
  flex-direction: column;
}
.summary-stat-wide {
  grid-column: 1 / -1;
}
.summary-value {
  font-size: 1.6rem;
  font-weight: 700;
  color: var(--text-primary, inherit);
  line-height: 1.1;
}
.summary-label {
  font-size: 0.72rem;
  color: var(--text-secondary, #6b5d47);
}
.band-breakdown {
  margin-bottom: 1.25rem;
}
.band-breakdown h3 {
  font-size: 0.85rem;
  margin: 0 0 0.6rem;
}
.band-bar {
  display: flex;
  width: 100%;
  height: 14px;
  border-radius: 999px;
  overflow: hidden;
  background: var(--gridline, #d8c9a3);
}
.band-bar-segment {
  height: 100%;
}
.band-breakdown-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 0.6rem 1rem;
  margin-top: 0.6rem;
  font-size: 0.78rem;
  color: var(--text-secondary, #6b5d47);
}
.legend-item {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
}
.legend-swatch {
  width: 10px;
  height: 10px;
  border-radius: 2px;
  flex: none;
}
.route-toggle {
  font-size: 0.8rem;
  padding: 0.45rem 0.9rem;
}
.path-line {
  fill: none;
  stroke: var(--text-secondary, #98989f);
  stroke-width: 2;
  stroke-linecap: round;
  stroke-linejoin: round;
}
.history-day {
  margin-bottom: 0.6rem;
}
.history-day-header {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  width: 100%;
  text-align: left;
  padding: 0.5rem 0.1rem;
  background: transparent;
  border: none;
  font-family: inherit;
  cursor: pointer;
  color: inherit;
}
.history-day-label {
  font-weight: 700;
  font-size: 0.9rem;
}
.history-day-meta {
  flex: 1;
  font-size: 0.78rem;
  color: var(--text-secondary, #6b5d47);
}
.history-day-chevron {
  width: 12px;
  height: 12px;
  flex: none;
  color: var(--text-secondary, #6b5d47);
  transition: transform 0.15s ease;
}
.history-day-chevron.open {
  transform: rotate(180deg);
}
.history-list {
  list-style: none;
  margin: 0 0 0.5rem;
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
