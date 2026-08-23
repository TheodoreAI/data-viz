<script>
import LoadingSpinner from './LoadingSpinner.vue';
import RouteMap from './RouteMap.vue';
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
    distanceMiles: distanceMeters / 1609.344,
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
  components: { LoadingSpinner, RouteMap },
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
      wakeLockActive: false,
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
    justEnded() {
      return !this.tracking && !!this.session?.endedAt;
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
    document.addEventListener('visibilitychange', this.onVisibilityChange);
  },
  beforeUnmount() {
    this.stopWatch();
    this.stopClock();
    this.releaseWakeLock();
    document.removeEventListener('visibilitychange', this.onVisibilityChange);
  },
  methods: {
    bandFor,
    bandTagStyle(band) {
      if (!band) return {};
      return {
        color: band.color,
        background: `color-mix(in srgb, ${band.color} 16%, var(--cl-panel))`,
      };
    },
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
    async requestWakeLock() {
      if (!('wakeLock' in navigator)) return;
      try {
        this.wakeLock = await navigator.wakeLock.request('screen');
        this.wakeLockActive = true;
        this.wakeLock.addEventListener('release', () => {
          this.wakeLockActive = false;
        });
      } catch {
        // Not supported, denied, or refused by the browser (e.g. low battery) —
        // tracking still works fine, the screen just may dim during a jog.
        this.wakeLockActive = false;
      }
    },
    async releaseWakeLock() {
      if (this.wakeLock) {
        try {
          await this.wakeLock.release();
        } catch {
          // already released
        }
        this.wakeLock = null;
      }
      this.wakeLockActive = false;
    },
    onVisibilityChange() {
      // The OS releases the wake lock whenever the tab backgrounds or the
      // screen locks; re-acquire it if the user returns while still tracking.
      if (this.tracking && document.visibilityState === 'visible') {
        this.requestWakeLock();
      }
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
        this.requestWakeLock();
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
      this.releaseWakeLock();
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
    <div class="jt-head">
      <h1>Jog Tracker</h1>
      <span v-if="tracking" class="status-chip status-chip-live">Tracking</span>
      <span v-else-if="loggedIn" class="status-chip status-chip-idle">Idle</span>
      <span v-if="tracking && wakeLockActive" class="wake-hint" title="Your screen will stay on while this jog is tracking">
        <svg viewBox="0 0 16 16" aria-hidden="true"><circle cx="8" cy="8" r="3" fill="currentColor" /><path d="M8 1v2M8 13v2M1 8h2M13 8h2M3.2 3.2l1.4 1.4M11.4 11.4l1.4 1.4M3.2 12.8l1.4-1.4M11.4 4.6l1.4-1.4" stroke="currentColor" stroke-width="1.3" stroke-linecap="round" /></svg>
        Screen staying on
      </span>
    </div>

    <p v-if="loggedIn === false" class="status">
      <a href="/login">Log in</a> to track UV exposure during a run.
    </p>

    <template v-else-if="loggedIn">
      <p class="subtitle">
        Tracks your route with GPS while this page stays open and samples the UV index every ~400m or few minutes.
        On supported iPhones (iOS 16.4+) this keeps the screen from dimming while a jog is active — Safari still
        stops location updates if the app is fully backgrounded or the phone is manually locked.
      </p>

      <div v-if="tracking" class="panel reading-panel">
        <div class="panel-head">Current Reading</div>
        <div class="panel-body">
          <div class="primary-reading">
            <span class="primary-reading-value" :style="{ color: latestBand?.color }">{{ latestReading?.uvIndex ?? '—' }}</span>
            <span v-if="latestBand" class="band-tag" :style="bandTagStyle(latestBand)">{{ latestBand.label.toUpperCase() }}</span>
          </div>
          <div class="sub-metric">UV Index · elapsed {{ elapsedClock }}</div>
        </div>
      </div>

      <div class="tracker-controls">
        <button v-if="!tracking" type="button" class="btn btn-start" :disabled="starting" @click="startTracking">
          <svg class="btn-icon" viewBox="0 0 16 16" aria-hidden="true"><path d="M4 2.5v11l10-5.5z" fill="currentColor" /></svg>
          {{ starting ? 'Starting…' : 'Start Jog' }}
        </button>
        <button v-else type="button" class="btn btn-stop" @click="stopTracking">
          <svg class="btn-icon" viewBox="0 0 16 16" aria-hidden="true"><rect x="3" y="3" width="10" height="10" rx="1.5" fill="currentColor" /></svg>
          Stop Session
        </button>
      </div>

      <p v-if="error" class="status form-error" role="alert">{{ error }}</p>
      <p v-if="geoError" class="status form-error" role="alert">{{ geoError }}</p>
      <p v-if="tracking && readings.length < 2" class="status">Walking/running a bit before stats fill in…</p>

      <section v-if="justEnded && summaryStats" class="panel session-summary">
        <div class="panel-head">Session Summary</div>
        <div class="metric-grid">
          <div class="metric">
            <div class="metric-val">{{ summaryStats.durationMinutes?.toFixed(0) ?? '—' }}</div>
            <div class="metric-label">Duration (min)</div>
          </div>
          <div class="metric">
            <div class="metric-val">{{ summaryStats.distanceMiles.toFixed(2) }}</div>
            <div class="metric-label">Miles</div>
          </div>
          <div class="metric">
            <div class="metric-val">{{ summaryStats.exposureScore.toFixed(1) }}</div>
            <div class="metric-label">Exposure score</div>
          </div>
          <div class="metric">
            <div class="metric-val">{{ summaryStats.avgUv }}</div>
            <div class="metric-label">Average UV</div>
          </div>
        </div>

        <div class="peak-row">
          <span class="peak-label">Peak UV</span>
          <span class="peak-value" :style="{ color: summaryStats.maxUvBand?.color }">{{ summaryStats.maxUv }}</span>
          <span v-if="summaryStats.maxUvBand" class="band-tag" :style="bandTagStyle(summaryStats.maxUvBand)">{{ summaryStats.maxUvBand.label.toUpperCase() }}</span>
        </div>

        <div v-if="summaryStats.bandMinutes.length" class="exposure-bar-wrap">
          <div class="exposure-bar-title">Time by UV level</div>
          <div class="exposure-bar">
            <span
              v-for="b in summaryStats.bandMinutes"
              :key="b.label"
              class="exposure-bar-segment"
              :style="{ width: `${(b.minutes / summaryStats.durationMinutes) * 100}%`, background: b.color }"
              :title="`${b.label}: ${b.minutes.toFixed(1)} min`"
            ></span>
          </div>
          <div class="exposure-legend">
            <span v-for="b in summaryStats.bandMinutes" :key="b.label" class="legend-item">
              <i :style="{ background: b.color }"></i>{{ b.label }} {{ b.minutes.toFixed(0) }}m
            </span>
          </div>
        </div>

        <button type="button" class="btn-link route-toggle" @click="showRoute = !showRoute">
          {{ showRoute ? 'Hide route' : 'View route map' }}
        </button>
        <div v-if="showRoute && readings.length >= 1" class="route-map-frame">
          <RouteMap :readings="readings" :band-for="bandFor" />
        </div>
      </section>

      <section v-if="history.length" class="panel history">
        <div class="panel-head">Session Log</div>
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
          <LoadingSpinner v-if="historyLoading" size="sm" inline />
          <div v-if="expandedDays.has(day.key)">
            <div v-for="s in day.sessions" :key="s.id" class="history-row">
              <button type="button" class="history-row-main" @click="viewPastSession(s.id)">
                <div class="history-time">{{ formatTime(s.startedAt) }}</div>
                <div class="history-meta">{{ s.durationMinutes ?? '—' }} min · avg UV {{ s.avgUvIndex ?? '—' }} · max UV {{ s.maxUvIndex ?? '—' }}</div>
              </button>
              <span v-if="bandFor(s.maxUvIndex)" class="history-badge" :style="bandTagStyle(bandFor(s.maxUvIndex))">{{ s.maxUvIndex ?? '—' }}</span>
              <button
                type="button"
                class="delete-button"
                :disabled="deletingId === s.id"
                aria-label="Delete session"
                @click="deleteSession(s.id)"
              >
                <LoadingSpinner v-if="deletingId === s.id" size="sm" inline />
                <svg v-else viewBox="0 0 16 16" aria-hidden="true"><path d="M4 4l8 8M12 4l-8 8" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" /></svg>
              </button>
            </div>
          </div>
        </div>

        <div v-if="selectedPastSession" class="past-session-detail">
          <RouteMap
            v-if="selectedPastSession.readings.length >= 1"
            :readings="selectedPastSession.readings"
            :band-for="bandFor"
          />
        </div>
      </section>
    </template>
  </section>
</template>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Serif:wght@400;500;600&family=Inter:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap');

.jog-tracker {
  --cl-bg: #f7f6f3;
  --cl-panel: #ffffff;
  --cl-ink: #22201b;
  --cl-ink-soft: #756f60;
  --cl-line: #e4e1d9;
  --cl-teal: #4d6a5a;
  --cl-teal-deep: #3a5245;
  --cl-teal-tint: #e9efe9;
  --cl-crit: #b8323a;
  --cl-crit-tint: #fce9e6;

  max-width: 640px;
  margin: 0 auto;
  padding: 2rem 1.25rem 3rem;
  background: var(--cl-bg);
  color: var(--cl-ink);
  font-family: "IBM Plex Serif", Georgia, serif;
}

@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) .jog-tracker {
    --cl-bg: #171613;
    --cl-panel: #22201b;
    --cl-ink: #f0eee6;
    --cl-ink-soft: #a39d8b;
    --cl-line: #34312a;
    --cl-teal: #7fa88f;
    --cl-teal-deep: #a3c7ae;
    --cl-teal-tint: #1e2a22;
    --cl-crit: #ef7a80;
    --cl-crit-tint: #3a1f22;
  }
}

:root[data-theme="dark"] .jog-tracker {
  --cl-bg: #171613;
  --cl-panel: #22201b;
  --cl-ink: #f0eee6;
  --cl-ink-soft: #a39d8b;
  --cl-line: #34312a;
  --cl-teal: #7fa88f;
  --cl-teal-deep: #a3c7ae;
  --cl-teal-tint: #1e2a22;
  --cl-crit: #ef7a80;
  --cl-crit-tint: #3a1f22;
}

.mono {
  font-family: "IBM Plex Mono", ui-monospace, monospace;
  font-variant-numeric: tabular-nums;
}

.jt-head {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  margin-bottom: 0.5rem;
}
h1 {
  font-size: 1.3rem;
  font-weight: 500;
  margin: 0;
}
.status-chip {
  font-family: "IBM Plex Mono", monospace;
  font-size: 0.65rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  padding: 0.26rem 0.55rem;
  border-radius: 3px;
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
}
.status-chip::before {
  content: "";
  width: 6px;
  height: 6px;
  border-radius: 50%;
  display: inline-block;
}
.status-chip-live {
  background: var(--cl-teal-tint);
  color: var(--cl-teal-deep);
}
.status-chip-live::before {
  background: var(--cl-teal);
}
.status-chip-idle {
  background: var(--cl-line);
  color: var(--cl-ink-soft);
}
.status-chip-idle::before {
  background: var(--cl-ink-soft);
}
.wake-hint {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  margin-left: auto;
  font-family: "IBM Plex Mono", monospace;
  font-size: 0.62rem;
  color: var(--cl-ink-soft);
}
.wake-hint svg {
  width: 12px;
  height: 12px;
}

.subtitle {
  color: var(--cl-ink-soft);
  font-family: Inter, sans-serif;
  font-size: 0.83rem;
  margin: 0 0 1.25rem;
  line-height: 1.5;
}
.status {
  color: var(--cl-ink-soft);
  font-family: Inter, sans-serif;
  font-size: 0.85rem;
}
.status a {
  color: var(--cl-teal-deep);
}
.form-error {
  color: var(--cl-crit);
}

.panel {
  background: var(--cl-panel);
  border: 1px solid var(--cl-line);
  margin-bottom: 1rem;
  overflow: hidden;
}
.panel-head {
  padding: 0.9rem 1.1rem;
  border-bottom: 1px solid var(--cl-line);
  font-family: Inter, sans-serif;
  font-size: 0.66rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--cl-ink-soft);
}
.panel-body {
  padding: 1.1rem 1.1rem 1.25rem;
}

.primary-reading {
  display: flex;
  align-items: flex-end;
  gap: 0.6rem;
  margin-bottom: 0.3rem;
}
.primary-reading-value {
  font-family: "IBM Plex Mono", monospace;
  font-variant-numeric: tabular-nums;
  font-size: 2.4rem;
  font-weight: 600;
  line-height: 1;
}
.band-tag {
  font-size: 0.68rem;
  font-weight: 700;
  letter-spacing: 0.03em;
  padding: 0.2rem 0.5rem;
  border-radius: 3px;
  margin-bottom: 0.35rem;
  white-space: nowrap;
}
.sub-metric {
  font-size: 0.78rem;
  color: var(--cl-ink-soft);
}

.tracker-controls {
  margin-bottom: 1rem;
}
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  font-family: Inter, sans-serif;
  font-size: 0.78rem;
  font-weight: 600;
  letter-spacing: 0.03em;
  text-transform: uppercase;
  padding: 0.75rem 1.4rem;
  cursor: pointer;
  border: none;
  border-radius: 6px;
}
.btn-icon {
  width: 13px;
  height: 13px;
  flex: none;
}
.btn-start {
  background: var(--cl-teal);
  color: #fff;
}
.btn-start:disabled {
  opacity: 0.6;
  cursor: default;
}
.btn-stop {
  background: var(--cl-crit-tint);
  color: var(--cl-crit);
}

.session-summary {
  margin-bottom: 1rem;
}
.metric-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1px;
  background: var(--cl-line);
}
.metric {
  background: var(--cl-panel);
  padding: 0.95rem 1.1rem;
}
.metric-val {
  font-family: "IBM Plex Mono", monospace;
  font-variant-numeric: tabular-nums;
  font-size: 1.4rem;
  font-weight: 600;
}
.metric-label {
  font-size: 0.68rem;
  color: var(--cl-ink-soft);
  margin-top: 0.25rem;
}

.peak-row {
  display: flex;
  align-items: baseline;
  gap: 0.6rem;
  padding: 0.95rem 1.1rem;
  border-top: 1px solid var(--cl-line);
}
.peak-label {
  font-size: 0.78rem;
  color: var(--cl-ink-soft);
}
.peak-value {
  font-family: "IBM Plex Mono", monospace;
  font-variant-numeric: tabular-nums;
  font-size: 1.15rem;
  font-weight: 600;
}

.exposure-bar-wrap {
  padding: 1.1rem;
  border-top: 1px solid var(--cl-line);
}
.exposure-bar-title {
  font-size: 0.68rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--cl-ink-soft);
  margin-bottom: 0.6rem;
}
.exposure-bar {
  display: flex;
  width: 100%;
  height: 8px;
  border-radius: 999px;
  overflow: hidden;
  background: var(--cl-bg);
  margin-bottom: 0.6rem;
}
.exposure-bar-segment {
  height: 100%;
}
.exposure-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem 1rem;
  font-size: 0.7rem;
  color: var(--cl-ink-soft);
}
.legend-item {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
}
.legend-item i {
  width: 7px;
  height: 7px;
  border-radius: 1px;
  display: inline-block;
}

.btn-link {
  display: block;
  width: 100%;
  text-align: left;
  font-family: inherit;
  font-size: 0.78rem;
  font-weight: 600;
  color: var(--cl-teal-deep);
  background: transparent;
  border: none;
  border-top: 1px solid var(--cl-line);
  padding: 0.85rem 1.1rem;
  cursor: pointer;
}
.route-map-frame {
  padding: 0 1.1rem 1.1rem;
}
.route-map-frame :deep(.route-map) {
  margin-top: 0;
}

.history-day {
  border-bottom: 1px solid var(--cl-line);
}
.history-day:last-child {
  border-bottom: none;
}
.history-day-header {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  width: 100%;
  text-align: left;
  padding: 0.8rem 1.1rem;
  background: transparent;
  border: none;
  font-family: inherit;
  cursor: pointer;
  color: inherit;
}
.history-day-label {
  font-weight: 600;
  font-size: 0.85rem;
}
.history-day-meta {
  flex: 1;
  font-size: 0.74rem;
  color: var(--cl-ink-soft);
}
.history-day-chevron {
  width: 12px;
  height: 12px;
  flex: none;
  color: var(--cl-ink-soft);
  transition: transform 0.15s ease;
}
.history-day-chevron.open {
  transform: rotate(180deg);
}
.history-row {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  padding: 0.7rem 1.1rem 0.7rem 1.1rem;
  border-top: 1px solid var(--cl-line);
}
.history-row-main {
  flex: 1;
  min-width: 0;
  text-align: left;
  background: transparent;
  border: none;
  font-family: inherit;
  cursor: pointer;
  color: inherit;
  padding: 0;
}
.history-time {
  font-family: "IBM Plex Mono", monospace;
  font-variant-numeric: tabular-nums;
  font-size: 0.78rem;
  font-weight: 600;
}
.history-meta {
  font-size: 0.72rem;
  color: var(--cl-ink-soft);
  margin-top: 0.15rem;
}
.history-badge {
  font-family: "IBM Plex Mono", monospace;
  font-variant-numeric: tabular-nums;
  font-size: 0.72rem;
  font-weight: 700;
  padding: 0.2rem 0.5rem;
  border-radius: 3px;
  flex: none;
}
.delete-button {
  flex: none;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  color: var(--cl-ink-soft);
  border-radius: 4px;
  width: 1.6rem;
  height: 1.6rem;
  cursor: pointer;
}
.delete-button svg {
  width: 11px;
  height: 11px;
}
.delete-button:hover {
  color: var(--cl-crit);
}
.delete-button:disabled {
  opacity: 0.6;
  cursor: default;
}
.past-session-detail {
  padding: 1.1rem;
  border-top: 1px solid var(--cl-line);
}
.past-session-detail :deep(.route-map) {
  margin-top: 0;
}
</style>
