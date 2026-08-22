<script>
import LoadingSpinner from './LoadingSpinner.vue';
import { parseJsonResponse } from '../api';

// Standard WHO/EPA UV index bands.
const UV_BANDS = [
  { max: 2, label: 'Low', className: 'band-low' },
  { max: 5, label: 'Moderate', className: 'band-moderate' },
  { max: 7, label: 'High', className: 'band-high' },
  { max: 10, label: 'Very High', className: 'band-very-high' },
  { max: Infinity, label: 'Extreme', className: 'band-extreme' },
];

function bandFor(uv) {
  if (uv == null) return null;
  return UV_BANDS.find(b => uv <= b.max);
}

function formatDay(iso) {
  return new Date(`${iso}T00:00:00`).toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' });
}

export default {
  name: 'UvIndex',
  components: { LoadingSpinner },
  data() {
    return {
      lat: '',
      lon: '',
      place: '',
      loading: false,
      error: '',
      locating: false,
      result: null,
    };
  },
  computed: {
    currentBand() {
      return this.result ? bandFor(this.result.current.uvIndex) : null;
    },
    maxDailyUv() {
      if (!this.result) return 1;
      return Math.max(1, ...this.result.daily.map(d => d.uvIndexMax ?? 0));
    },
  },
  methods: {
    formatDay,
    bandFor,
    useMyLocation() {
      if (!navigator.geolocation) {
        this.error = 'Geolocation is not available in this browser.';
        return;
      }
      this.locating = true;
      this.error = '';
      navigator.geolocation.getCurrentPosition(
        (position) => {
          this.lat = position.coords.latitude.toFixed(4);
          this.lon = position.coords.longitude.toFixed(4);
          this.locating = false;
          this.lookUp();
        },
        () => {
          this.locating = false;
          this.error = 'Could not get your location. Enter coordinates manually.';
        }
      );
    },
    async lookUp() {
      const lat = parseFloat(this.lat);
      const lon = parseFloat(this.lon);
      if (Number.isNaN(lat) || Number.isNaN(lon)) {
        this.error = 'Enter a valid latitude and longitude.';
        return;
      }
      this.loading = true;
      this.error = '';
      try {
        const params = new URLSearchParams({ lat, lon });
        const response = await fetch(`/api/uv-index?${params.toString()}`);
        const data = await parseJsonResponse(response);
        if (!response.ok) throw new Error(data.error || `Request failed: ${response.status}`);
        this.result = data;
      } catch (err) {
        this.result = null;
        this.error = err.message || 'Could not load the UV index. Please try again.';
      } finally {
        this.loading = false;
      }
    },
  },
};
</script>

<template>
  <div class="uv-page">
    <h1>UV Index</h1>
    <p class="subtitle">Current and 7-day forecast UV index for any coordinate, via Open-Meteo.</p>

    <form class="uv-form" @submit.prevent="lookUp">
      <label class="field">
        <span>Latitude</span>
        <input v-model="lat" type="number" step="any" min="-90" max="90" placeholder="40.7128" required>
      </label>
      <label class="field">
        <span>Longitude</span>
        <input v-model="lon" type="number" step="any" min="-180" max="180" placeholder="-74.0060" required>
      </label>
      <div class="form-actions">
        <button type="submit" class="btn-primary" :disabled="loading">{{ loading ? 'Loading…' : 'Check UV Index' }}</button>
        <button type="button" class="btn-secondary" :disabled="locating" @click="useMyLocation">
          {{ locating ? 'Locating…' : 'Use my location' }}
        </button>
      </div>
    </form>

    <p v-if="error" class="status form-error" role="alert">{{ error }}</p>
    <LoadingSpinner v-if="loading" size="lg" />

    <template v-else-if="result">
      <section class="stat-tile" :class="currentBand?.className">
        <span class="stat-value">{{ result.current.uvIndex ?? '—' }}</span>
        <span class="stat-band">{{ currentBand?.label ?? 'Unknown' }}</span>
        <span class="stat-meta">{{ result.lat.toFixed(2) }}, {{ result.lon.toFixed(2) }}</span>
      </section>

      <section v-if="result.daily.length" class="forecast">
        <h2>7-day forecast (max UV)</h2>
        <div class="forecast-legend">
          <span v-for="b in ['Low', 'Moderate', 'High', 'Very High', 'Extreme']" :key="b" class="legend-item">
            <span class="legend-swatch" :class="`band-${b.toLowerCase().replace(' ', '-')}`"></span>{{ b }}
          </span>
        </div>
        <div class="forecast-bars">
          <div v-for="day in result.daily" :key="day.date" class="forecast-col">
            <span class="forecast-value">{{ day.uvIndexMax ?? '—' }}</span>
            <div class="forecast-bar-track">
              <div
                class="forecast-bar-fill"
                :class="bandFor(day.uvIndexMax)?.className"
                :style="{ height: `${Math.max(4, ((day.uvIndexMax ?? 0) / maxDailyUv) * 100)}%` }"
              ></div>
            </div>
            <span class="forecast-day">{{ formatDay(day.date) }}</span>
          </div>
        </div>
      </section>
    </template>
  </div>
</template>

<style scoped>
.uv-page {
  max-width: 640px;
  margin: 0 auto;
  padding: 2rem 1.25rem 3rem;
}
h1 {
  font-size: 1.3rem;
  margin: 0 0 0.3rem;
}
.subtitle {
  color: var(--text-secondary, #6b5d47);
  font-size: 0.9rem;
  margin: 0 0 1.5rem;
}
.uv-form {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
  align-items: flex-end;
  margin-bottom: 1.5rem;
}
.field {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
  font-size: 0.85rem;
  color: var(--text-secondary, #6b5d47);
  flex: 1 1 140px;
}
.field input {
  font-family: inherit;
  font-size: 0.95rem;
  padding: 0.5rem 0.6rem;
  border: 1px solid var(--gridline, #d8c9a3);
  border-radius: 6px;
  background: var(--surface-1, #fcfcfb);
  color: var(--text-primary, inherit);
}
.form-actions {
  display: flex;
  gap: 0.6rem;
  flex: 1 1 100%;
}
.btn-primary,
.btn-secondary {
  font-family: inherit;
  font-size: 0.85rem;
  padding: 0.55rem 1rem;
  border-radius: 6px;
  cursor: pointer;
  border: 1px solid var(--series-1, #2f6690);
}
.btn-primary {
  background: var(--series-1, #2f6690);
  color: #fff;
}
.btn-primary:disabled,
.btn-secondary:disabled {
  opacity: 0.6;
  cursor: default;
}
.btn-secondary {
  background: transparent;
  color: var(--series-1, #2f6690);
}
.status.form-error {
  color: #b0413e;
  font-size: 0.9rem;
}

/* Status bands — fixed convention colors, not the categorical palette;
   these map 1:1 to the standard WHO/EPA UV index scale, so they stay
   consistent with every other UV chart people already recognize. */
.band-low { --band-color: #0ca30c; }
.band-moderate { --band-color: #eda100; }
.band-high { --band-color: #eb6834; }
.band-very-high { --band-color: #d03b3b; }
.band-extreme { --band-color: #7a3aa7; }

.stat-tile {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.2rem;
  padding: 2rem 1rem;
  border-radius: 12px;
  border: 1px solid var(--gridline, #d8c9a3);
  border-top: 4px solid var(--band-color, var(--series-1));
  margin-bottom: 2rem;
}
.stat-value {
  font-size: 3rem;
  font-weight: 700;
  color: var(--band-color, var(--text-primary));
  line-height: 1;
}
.stat-band {
  font-size: 1rem;
  font-weight: 700;
  color: var(--band-color, var(--text-primary));
}
.stat-meta {
  font-size: 0.8rem;
  color: var(--text-secondary, #6b5d47);
  margin-top: 0.4rem;
}

.forecast h2 {
  font-size: 1rem;
  margin: 0 0 0.75rem;
}
.forecast-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  font-size: 0.75rem;
  color: var(--text-secondary, #6b5d47);
  margin-bottom: 1rem;
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
  background: var(--band-color);
}
.forecast-bars {
  display: flex;
  align-items: flex-end;
  gap: 0.6rem;
  height: 160px;
}
.forecast-col {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  height: 100%;
  gap: 0.3rem;
}
.forecast-value {
  font-size: 0.75rem;
  font-weight: 700;
  color: var(--text-primary, inherit);
}
.forecast-bar-track {
  flex: 1;
  width: 100%;
  display: flex;
  align-items: flex-end;
  min-height: 0;
}
.forecast-bar-fill {
  width: 100%;
  border-radius: 4px 4px 0 0;
  background: var(--band-color, var(--series-1));
}
.forecast-day {
  font-size: 0.7rem;
  color: var(--text-secondary, #6b5d47);
  text-align: center;
}
</style>
