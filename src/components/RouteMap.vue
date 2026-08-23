<script>
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

export default {
  name: 'RouteMap',
  props: {
    readings: { type: Array, required: true },
    bandFor: { type: Function, required: true },
  },
  watch: {
    readings: {
      deep: true,
      handler() {
        this.render();
      },
    },
  },
  mounted() {
    // Leaflet only starts loading tiles once the map has a view (setView/fitBounds) —
    // adding the tile layer before that leaves the container blank, so give it an
    // initial view synchronously before anything else touches the map.
    const first = this.readings[0];
    this.map = L.map(this.$refs.mapEl, { attributionControl: true, zoomControl: true })
      .setView(first ? [first.lat, first.lon] : [0, 0], first ? 16 : 2);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    }).addTo(this.map);

    this.render();
    // The container's real size isn't always settled the instant Leaflet reads it
    // (layout/animation timing) — re-measure on the next frame so tiles fill the box.
    requestAnimationFrame(() => this.map.invalidateSize());
  },
  beforeUnmount() {
    if (this.map) this.map.remove();
  },
  methods: {
    render() {
      if (!this.map) return;
      if (this.line) this.map.removeLayer(this.line);
      this.markers?.forEach(m => this.map.removeLayer(m));
      this.markers = [];

      if (!this.readings.length) return;

      const latLngs = this.readings.map(r => [r.lat, r.lon]);
      if (latLngs.length > 1) {
        const lineColor = getComputedStyle(this.$refs.mapEl).getPropertyValue('--series-1').trim() || '#2f6690';
        this.line = L.polyline(latLngs, { color: lineColor, weight: 3, opacity: 0.85 }).addTo(this.map);
      }

      this.readings.forEach((r) => {
        const color = this.bandFor(r.uvIndex)?.color || '#666';
        const marker = L.circleMarker([r.lat, r.lon], {
          radius: 5,
          color: '#fff',
          weight: 1.5,
          fillColor: color,
          fillOpacity: 1,
        }).addTo(this.map);
        marker.bindTooltip(`UV ${r.uvIndex}`, { direction: 'top', offset: [0, -6] });
        this.markers.push(marker);
      });

      if (latLngs.length === 1) {
        this.map.setView(latLngs[0], 16);
      } else {
        this.map.fitBounds(this.line.getBounds(), { padding: [24, 24] });
      }
    },
  },
};
</script>

<template>
  <div ref="mapEl" class="route-map"></div>
</template>

<style scoped>
.route-map {
  width: 100%;
  height: 320px;
  border-radius: 12px;
  border: 1px solid var(--gridline, #d8c9a3);
  margin-top: 1rem;
}
</style>
