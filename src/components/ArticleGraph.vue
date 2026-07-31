<script>
import { forceSimulation, forceLink, forceManyBody, forceCenter, forceCollide } from 'd3';

const WIDTH = 800;
const HEIGHT = 600;

const SWIPE_MIN_DISTANCE = 60;
const SWIPE_MAX_DURATION = 700;
const DEFAULT_ZOOM_K = 1.9;

function defaultZoom() {
  return { x: (WIDTH / 2) * (1 - DEFAULT_ZOOM_K), y: (HEIGHT / 2) * (1 - DEFAULT_ZOOM_K), k: DEFAULT_ZOOM_K };
}

export default {
  name: 'ArticleGraph',
  props: {
    seedTitle: { type: String, required: true },
    seedLinks: { type: Array, required: true },
  },
  data() {
    return {
      nodes: [],
      links: [],
      tooltip: { visible: false, x: 0, y: 0, text: '' },
      zoom: defaultZoom(),
      dragNode: null,
      panning: false,
      expandingId: null,
      hoveredId: null,
      currentSeedTitle: this.seedTitle,
      history: [],
      loadingSeed: false,
      graphMode: false,
    };
  },
  computed: {
    transform() {
      return `translate(${this.zoom.x}, ${this.zoom.y}) scale(${this.zoom.k})`;
    },
  },
  created() {
    this.activePointers = new Map();
    this.pinch = null;
    this.swipeStart = null;
    this.populateGraph(this.seedTitle, this.seedLinks);
  },
  mounted() {
    this.buildSimulation();
    window.addEventListener('pointermove', this.onPointerMove);
    window.addEventListener('pointerup', this.onPointerUp);
  },
  beforeUnmount() {
    if (this.simulation) this.simulation.stop();
    window.removeEventListener('pointermove', this.onPointerMove);
    window.removeEventListener('pointerup', this.onPointerUp);
    document.body.classList.remove('graph-fullscreen');
  },
  methods: {
    toggleGraphMode() {
      this.graphMode = !this.graphMode;
      document.body.classList.toggle('graph-fullscreen', this.graphMode);
    },
    populateGraph(title, linkTitles) {
      this.addArticleNode(title, WIDTH / 2, HEIGHT / 2, true);
      linkTitles.forEach((linkTitle, i) => {
        const angle = (i / linkTitles.length) * Math.PI * 2;
        this.addArticleNode(linkTitle, WIDTH / 2 + Math.cos(angle) * 40, HEIGHT / 2 + Math.sin(angle) * 40);
        this.links.push({ source: title, target: linkTitle });
      });
    },
    buildSimulation() {
      if (this.simulation) this.simulation.stop();
      this.simulation = forceSimulation(this.nodes)
        .force('link', forceLink(this.links).id(d => d.id).distance(90))
        .force('charge', forceManyBody().strength(-160))
        .force('center', forceCenter(WIDTH / 2, HEIGHT / 2))
        .force('collide', forceCollide(36));
    },
    addArticleNode(title, x, y, isCenter = false) {
      if (this.nodes.some(n => n.id === title)) return;
      this.nodes.push({ id: title, isCenter, x, y, vx: 0, vy: 0, expanded: isCenter });
    },
    nodeById(id) {
      return this.nodes.find(n => n.id === id);
    },
    nodeRadius(node) {
      const base = node.isCenter ? 20 : 13;
      return this.hoveredId === node.id ? base * 1.35 : base;
    },
    async expandNode(node) {
      if (node.expanded || this.expandingId) return;
      this.expandingId = node.id;
      try {
        const response = await fetch(`/api/article-links?title=${encodeURIComponent(node.id)}`);
        const data = await response.json();
        node.expanded = true;
        data.links.forEach((title, i) => {
          const angle = (i / data.links.length) * Math.PI * 2;
          this.addArticleNode(title, node.x + Math.cos(angle) * 60, node.y + Math.sin(angle) * 60);
          const alreadyLinked = this.links.some(
            l => (l.source.id ?? l.source) === node.id && (l.target.id ?? l.target) === title
          );
          if (!alreadyLinked) this.links.push({ source: node.id, target: title });
        });
        this.simulation.nodes(this.nodes);
        this.simulation.force('link', forceLink(this.links).id(d => d.id).distance(90));
        this.simulation.alpha(0.7).restart();
      } finally {
        this.expandingId = null;
      }
    },
    async loadNewSeed() {
      if (this.loadingSeed) return;
      this.loadingSeed = true;
      try {
        this.history.push(this.currentSeedTitle);
        const randomResponse = await fetch('/api/random-article');
        const article = await randomResponse.json();
        await this.rebuildGraph(article.title);
      } finally {
        this.loadingSeed = false;
      }
    },
    async goToPreviousSeed() {
      if (this.loadingSeed || this.history.length === 0) return;
      this.loadingSeed = true;
      try {
        const title = this.history.pop();
        await this.rebuildGraph(title);
      } finally {
        this.loadingSeed = false;
      }
    },
    async rebuildGraph(title) {
      const response = await fetch(`/api/article-links?title=${encodeURIComponent(title)}`);
      const data = await response.json();
      this.nodes = [];
      this.links = [];
      this.zoom = defaultZoom();
      this.currentSeedTitle = title;
      this.populateGraph(title, data.links);
      this.buildSimulation();
    },
    nodeScreenPosition(node) {
      const rect = this.$refs.svg.getBoundingClientRect();
      const scaleX = rect.width / WIDTH;
      const scaleY = rect.height / HEIGHT;
      return {
        x: rect.left + window.scrollX + (this.zoom.x + node.x * this.zoom.k) * scaleX,
        y: rect.top + window.scrollY + (this.zoom.y + node.y * this.zoom.k) * scaleY,
      };
    },
    showTooltip(node) {
      const pos = this.nodeScreenPosition(node);
      const radius = this.nodeRadius(node);
      this.tooltip = { visible: true, x: pos.x, y: pos.y - radius - 8, text: node.id };
      this.hoveredId = node.id;
    },
    hideTooltip() {
      this.tooltip.visible = false;
      this.hoveredId = null;
    },
    openArticle(node) {
      const url = `https://en.wikipedia.org/wiki/${encodeURIComponent(node.id.replace(/ /g, '_'))}`;
      window.open(url, '_blank');
    },
    registerPointer(event) {
      this.activePointers.set(event.pointerId, { x: event.clientX, y: event.clientY });
    },
    pointerDistance() {
      const points = [...this.activePointers.values()];
      return Math.hypot(points[0].x - points[1].x, points[0].y - points[1].y);
    },
    startPinch() {
      this.dragNode = null;
      this.panning = false;
      this.swipeStart = null;
      this.pinch = { startDist: this.pointerDistance(), startK: this.zoom.k };
    },
    onNodePointerDown(event, node) {
      this.registerPointer(event);
      if (this.activePointers.size >= 2) {
        this.startPinch();
        return;
      }
      event.stopPropagation();
      this.dragNode = node;
      this.simulation.alphaTarget(0.3).restart();
    },
    onBackgroundPointerDown(event) {
      this.registerPointer(event);
      if (this.activePointers.size >= 2) {
        this.startPinch();
        return;
      }
      this.panning = true;
      this.swipeStart = { x: event.clientX, y: event.clientY, time: Date.now() };
      this.panStart = { x: event.clientX, y: event.clientY, zx: this.zoom.x, zy: this.zoom.y };
    },
    onPointerMove(event) {
      if (this.activePointers.has(event.pointerId)) {
        this.activePointers.set(event.pointerId, { x: event.clientX, y: event.clientY });
      }
      if (this.pinch && this.activePointers.size >= 2) {
        const ratio = this.pointerDistance() / this.pinch.startDist;
        this.applyZoom(this.pinch.startK * ratio);
        return;
      }
      if (this.dragNode) {
        const rect = this.$refs.svg.getBoundingClientRect();
        this.dragNode.fx = (event.clientX - rect.left - this.zoom.x) / this.zoom.k;
        this.dragNode.fy = (event.clientY - rect.top - this.zoom.y) / this.zoom.k;
      } else if (this.panning) {
        this.zoom.x = this.panStart.zx + (event.clientX - this.panStart.x);
        this.zoom.y = this.panStart.zy + (event.clientY - this.panStart.y);
      }
    },
    onPointerUp(event) {
      this.activePointers.delete(event.pointerId);
      if (this.pinch) {
        if (this.activePointers.size < 2) this.pinch = null;
        return;
      }
      if (this.dragNode) {
        this.dragNode.fx = null;
        this.dragNode.fy = null;
        this.simulation.alphaTarget(0);
        this.dragNode = null;
      }
      if (this.panning) {
        this.panning = false;
        this.detectSwipe(event);
      }
    },
    detectSwipe(event) {
      if (!this.swipeStart) return;
      const dx = event.clientX - this.swipeStart.x;
      const dy = event.clientY - this.swipeStart.y;
      const duration = Date.now() - this.swipeStart.time;
      this.swipeStart = null;
      if (Math.abs(dy) < SWIPE_MIN_DISTANCE) return;
      if (Math.abs(dy) < Math.abs(dx) * 1.5) return;
      if (duration > SWIPE_MAX_DURATION) return;
      if (dy > 0) this.loadNewSeed();
      else this.goToPreviousSeed();
    },
    onWheel(event) {
      event.preventDefault();
      this.applyZoom(this.zoom.k * (event.deltaY > 0 ? 0.9 : 1.1));
    },
    applyZoom(newK, anchor = { x: WIDTH / 2, y: HEIGHT / 2 }) {
      const clamped = Math.min(3, Math.max(0.3, newK));
      const ratio = clamped / this.zoom.k;
      this.zoom.x = anchor.x - (anchor.x - this.zoom.x) * ratio;
      this.zoom.y = anchor.y - (anchor.y - this.zoom.y) * ratio;
      this.zoom.k = clamped;
    },
    zoomIn() {
      this.applyZoom(this.zoom.k * 1.25);
    },
    zoomOut() {
      this.applyZoom(this.zoom.k * 0.8);
    },
    resetZoom() {
      this.zoom = defaultZoom();
    },
  },
};
</script>

<template>
  <div class="graph-root" :class="{ fullscreen: graphMode }">
    <header class="graph-header">
      <div class="graph-header-row">
        <h1>Article Link Graph</h1>
        <button class="mode-toggle" type="button" @click="toggleGraphMode">
          {{ graphMode ? '✕ Exit graph mode' : '⛶ Graph mode' }}
        </button>
      </div>
      <p v-if="!graphMode" class="subtitle">
        Starting from “{{ currentSeedTitle }}”. Click a node to open it on Wikipedia, tap the + to expand its links.
        Drag to reposition, pinch/scroll to zoom, swipe down for a new article, swipe up to go back.
      </p>
      <p v-if="loadingSeed" class="subtitle loading">Loading…</p>
    </header>

    <div class="graph-canvas">
      <svg
        ref="svg"
        class="graph-svg"
        viewBox="0 0 800 600"
        @pointerdown="onBackgroundPointerDown"
        @wheel="onWheel"
      >
      <g :transform="transform">
        <line
          v-for="(link, i) in links"
          :key="'l' + i"
          class="graph-edge"
          :x1="(link.source.x ?? nodeById(link.source)?.x) || 0"
          :y1="(link.source.y ?? nodeById(link.source)?.y) || 0"
          :x2="(link.target.x ?? nodeById(link.target)?.x) || 0"
          :y2="(link.target.y ?? nodeById(link.target)?.y) || 0"
        />
        <g
          v-for="node in nodes"
          :key="node.id"
          class="graph-node"
          :class="{ center: node.isCenter, expanding: expandingId === node.id }"
          :transform="`translate(${node.x}, ${node.y})`"
          @pointerdown="onNodePointerDown($event, node)"
          @mouseenter="showTooltip(node)"
          @touchstart="showTooltip(node)"
          @mouseleave="hideTooltip"
          @click="openArticle(node)"
        >
          <circle :r="nodeRadius(node)" />
          <g
            v-if="!node.expanded && hoveredId === node.id"
            class="expand-badge"
            :transform="`translate(${nodeRadius(node) * 0.75}, ${nodeRadius(node) * 0.75})`"
            @click.stop="expandNode(node)"
            @pointerdown.stop
            @touchstart.stop="showTooltip(node)"
          >
            <circle r="9" />
            <line x1="-4.5" y1="0" x2="4.5" y2="0" />
            <line x1="0" y1="-4.5" x2="0" y2="4.5" />
          </g>
        </g>
        <text
          v-if="nodeById(currentSeedTitle)"
          class="graph-center-label"
          :x="nodeById(currentSeedTitle).x"
          :y="nodeById(currentSeedTitle).y - 20"
          text-anchor="middle"
        >{{ currentSeedTitle }}</text>
      </g>
      </svg>

      <div v-if="graphMode" class="zoom-controls">
        <button type="button" aria-label="Zoom in" @click="zoomIn">+</button>
        <button type="button" aria-label="Reset zoom" @click="resetZoom">⟳</button>
        <button type="button" aria-label="Zoom out" @click="zoomOut">−</button>
      </div>
    </div>

    <div
      id="tooltip"
      :style="{ display: tooltip.visible ? 'block' : 'none', left: tooltip.x + 'px', top: tooltip.y + 'px' }"
    >{{ tooltip.text }}</div>
  </div>
</template>

<style scoped>
.graph-root {
  max-width: 900px;
  margin: 0 auto;
  padding: 1.5rem 1.25rem;
}
.graph-root.fullscreen {
  position: fixed;
  inset: 0;
  z-index: 1000;
  max-width: none;
  margin: 0;
  padding: env(safe-area-inset-top) env(safe-area-inset-right) env(safe-area-inset-bottom) env(safe-area-inset-left);
  display: flex;
  flex-direction: column;
  background: var(--surface-1, #fcfcfb);
}
.graph-header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
}
.graph-header h1 {
  margin: 0 0 0.1rem;
  font-size: 1.1rem;
}
.mode-toggle {
  height: 2.5rem;
  flex: none;
  background: transparent;
  border: 1px solid var(--gridline, #e1e0d9);
  color: var(--text-secondary, #52514e);
  border-radius: 999px;
  padding: 0.3rem 0.8rem;
  font-size: 0.75rem;
  cursor: pointer;
}
.subtitle {
  color: var(--text-secondary, #52514e);
  font-size: 0.8rem;
  margin: 0 0 1rem;
}
.subtitle.loading {
  color: var(--series-1, #2a78d6);
  margin-top: -0.5rem;
}
#tooltip {
  transform: translate(-50%, -100%);
}
.graph-svg {
  width: 100%;
  height: 70vh;
  touch-action: none;
  background: var(--surface-1, #fcfcfb);
  border: 1px solid var(--gridline, #e1e0d9);
  border-radius: 6px;
  cursor: grab;
}
.fullscreen .graph-header {
  flex: none;
}
.fullscreen .graph-svg {
  flex: 1;
  height: auto;
  border: none;
  border-radius: 0;
}
.graph-canvas {
  position: relative;
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
}
.zoom-controls {
  position: absolute;
  right: 1rem;
  bottom: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  z-index: 5;
}
.zoom-controls button {
  width: 3.5rem;
  height: 3.5rem;
  border-radius: 50%;
  border: 1px solid var(--gridline, #e1e0d9);
  background: var(--surface-1, #fcfcfb);
  color: var(--text-primary, #0b0b0b);
  font-size: 1.1rem;
  line-height: 1;
  cursor: pointer;
  box-shadow: 0 2px 6px rgba(0,0,0,0.15);
}
.zoom-controls button:hover {
  border-color: var(--series-1, #2a78d6);
}
.graph-edge {
  stroke: var(--gridline, #e1e0d9);
  stroke-width: 1.5;
}
.graph-node circle {
  fill: var(--surface-1, #fcfcfb);
  stroke: var(--muted, #898781);
  stroke-width: 2;
  cursor: pointer;
  transition: r 0.15s ease;
}
.graph-node:hover circle {
  stroke: var(--series-1, #2a78d6);
}
.graph-node.center circle {
  fill: var(--series-1, #2a78d6);
  stroke: var(--series-1, #2a78d6);
}
.graph-node.expanding circle {
  opacity: 0.5;
}
.expand-badge circle {
  fill: var(--series-1, #2a78d6);
  stroke: var(--surface-1, #fcfcfb);
  stroke-width: 1.5;
  cursor: pointer;
}
.expand-badge line {
  stroke: #fff;
  stroke-width: 1.5;
  pointer-events: none;
}
.graph-center-label {
  fill: var(--text-primary, #0b0b0b);
  font-size: 12px;
  font-weight: 600;
  pointer-events: none;
}
</style>