<script>
import { forceSimulation, forceLink, forceManyBody, forceCenter, forceCollide } from 'd3';

const WIDTH = 800;
const HEIGHT = 600;

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
      zoom: { x: 0, y: 0, k: 1 },
      dragNode: null,
      panning: false,
      expandingId: null,
      hoveredId: null,
    };
  },
  computed: {
    transform() {
      return `translate(${this.zoom.x}, ${this.zoom.y}) scale(${this.zoom.k})`;
    },
  },
  created() {
    this.addArticleNode(this.seedTitle, WIDTH / 2, HEIGHT / 2, true);
    this.seedLinks.forEach((title, i) => {
      const angle = (i / this.seedLinks.length) * Math.PI * 2;
      this.addArticleNode(title, WIDTH / 2 + Math.cos(angle) * 40, HEIGHT / 2 + Math.sin(angle) * 40);
      this.links.push({ source: this.seedTitle, target: title });
    });
  },
  mounted() {
    this.simulation = forceSimulation(this.nodes)
      .force('link', forceLink(this.links).id(d => d.id).distance(90))
      .force('charge', forceManyBody().strength(-160))
      .force('center', forceCenter(WIDTH / 2, HEIGHT / 2))
      .force('collide', forceCollide(26));

    window.addEventListener('pointermove', this.onPointerMove);
    window.addEventListener('pointerup', this.onPointerUp);
  },
  beforeUnmount() {
    if (this.simulation) this.simulation.stop();
    window.removeEventListener('pointermove', this.onPointerMove);
    window.removeEventListener('pointerup', this.onPointerUp);
  },
  methods: {
    addArticleNode(title, x, y, isCenter = false) {
      if (this.nodes.some(n => n.id === title)) return;
      this.nodes.push({ id: title, isCenter, x, y, vx: 0, vy: 0, expanded: isCenter });
    },
    nodeById(id) {
      return this.nodes.find(n => n.id === id);
    },
    nodeRadius(node) {
      const base = node.isCenter ? 14 : 9;
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
    showTooltip(event, node) {
      const point = event.touches ? event.touches[0] : event;
      this.tooltip = { visible: true, x: point.pageX + 14, y: point.pageY - 10, text: node.id };
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
    onNodePointerDown(event, node) {
      event.stopPropagation();
      this.dragNode = node;
      this.simulation.alphaTarget(0.3).restart();
    },
    onBackgroundPointerDown(event) {
      this.panning = true;
      this.panStart = { x: event.clientX, y: event.clientY, zx: this.zoom.x, zy: this.zoom.y };
    },
    onPointerMove(event) {
      if (this.dragNode) {
        const rect = this.$refs.svg.getBoundingClientRect();
        this.dragNode.fx = (event.clientX - rect.left - this.zoom.x) / this.zoom.k;
        this.dragNode.fy = (event.clientY - rect.top - this.zoom.y) / this.zoom.k;
      } else if (this.panning) {
        this.zoom.x = this.panStart.zx + (event.clientX - this.panStart.x);
        this.zoom.y = this.panStart.zy + (event.clientY - this.panStart.y);
      }
    },
    onPointerUp() {
      if (this.dragNode) {
        this.dragNode.fx = null;
        this.dragNode.fy = null;
        this.simulation.alphaTarget(0);
        this.dragNode = null;
      }
      this.panning = false;
    },
    onWheel(event) {
      event.preventDefault();
      const next = Math.min(3, Math.max(0.3, this.zoom.k * (event.deltaY > 0 ? 0.9 : 1.1)));
      this.zoom.k = next;
    },
  },
};
</script>

<template>
  <div class="graph-root">
    <header class="graph-header">
      <h1>Article Link Graph</h1>
      <p class="subtitle">Starting from “{{ seedTitle }}”. Click a node to open it on Wikipedia, tap the + to expand its links. Drag to reposition, scroll to zoom.</p>
    </header>

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
          @mousemove="showTooltip($event, node)"
          @touchstart="showTooltip($event, node)"
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
            @touchstart.stop="showTooltip($event, node)"
          >
            <circle r="7" />
            <line x1="-3.5" y1="0" x2="3.5" y2="0" />
            <line x1="0" y1="-3.5" x2="0" y2="3.5" />
          </g>
        </g>
        <text
          v-if="nodeById(seedTitle)"
          class="graph-center-label"
          :x="nodeById(seedTitle).x"
          :y="nodeById(seedTitle).y - 20"
          text-anchor="middle"
        >{{ seedTitle }}</text>
      </g>
    </svg>

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
.graph-header h1 {
  margin: 0 0 0.1rem;
  font-size: 1.1rem;
}
.subtitle {
  color: var(--text-secondary, #52514e);
  font-size: 0.8rem;
  margin: 0 0 1rem;
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