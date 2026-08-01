<script>
import ForceGraph3D from '3d-force-graph';
import * as THREE from 'three';
import ArticleTooltip from './ArticleTooltip.vue';

const MAX_PIXEL_RATIO = 2;
const CENTER_COLOR = 0xb8935a; // gold/bronze
const NODE_COLOR = 0x2f6690; // blue
const STAR_COUNT = 1800;
const STAR_FIELD_MIN_RADIUS = 700;
const STAR_FIELD_MAX_RADIUS = 1600;

function buildStarfield() {
  const positions = new Float32Array(STAR_COUNT * 3);
  for (let i = 0; i < STAR_COUNT; i += 1) {
    const radius = STAR_FIELD_MIN_RADIUS + Math.random() * (STAR_FIELD_MAX_RADIUS - STAR_FIELD_MIN_RADIUS);
    const theta = Math.random() * Math.PI * 2;
    const phi = Math.acos(2 * Math.random() - 1);
    positions[i * 3] = radius * Math.sin(phi) * Math.cos(theta);
    positions[i * 3 + 1] = radius * Math.sin(phi) * Math.sin(theta);
    positions[i * 3 + 2] = radius * Math.cos(phi);
  }
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
  const material = new THREE.PointsMaterial({
    color: 0xf3e9d2,
    size: 2,
    sizeAttenuation: true,
    transparent: true,
    opacity: 0.85,
  });
  return new THREE.Points(geometry, material);
}

export default {
  name: 'ArticleGraph3D',
  components: { ArticleTooltip },
  props: {
    seedTitle: { type: String, required: true },
    seedLinks: { type: Array, required: true },
  },
  emits: ['select'],
  data() {
    return {
      loadingNodeId: null,
      errorNodeId: null,
      showList: false,
      announcement: '',
      listNodes: [],
      tooltip: { visible: false, title: '', extract: '', thumbnail: null, loading: false },
    };
  },
  mounted() {
    this.linksCache = {};
    this.summaryCache = {};
    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    this.graph = ForceGraph3D()(this.$refs.container)
      .backgroundColor('#0c1220')
      .nodeLabel(node => node.id)
      .nodeThreeObject(node => {
        const geometry = new THREE.SphereGeometry(node.isCenter ? 9 : 6, 24, 24);
        const material = new THREE.MeshStandardMaterial({
          color: node.isCenter ? CENTER_COLOR : NODE_COLOR,
          metalness: node.isCenter ? 0.75 : 0.4,
          roughness: node.isCenter ? 0.3 : 0.6,
        });
        return new THREE.Mesh(geometry, material);
      })
      .linkColor(() => 'rgba(116, 128, 74, 0.6)')
      .linkWidth(1)
      .cooldownTicks(reducedMotion ? 0 : 200)
      .onNodeClick(node => this.navigateToNode(node))
      .onNodeHover(node => {
        this.$refs.container.style.cursor = node ? 'pointer' : 'default';
      });

    this.graph.scene().add(new THREE.AmbientLight(0xffffff, 0.6));
    const keyLight = new THREE.DirectionalLight(0xfff2d9, 1.1);
    keyLight.position.set(1, 1, 1);
    this.graph.scene().add(keyLight);
    this.graph.scene().add(buildStarfield());

    const pixelRatio = Math.min(window.devicePixelRatio || 1, MAX_PIXEL_RATIO);
    this.graph.renderer().setPixelRatio(pixelRatio);
    if (reducedMotion) this.graph.controls().autoRotate = false;

    this.setGraphData(this.seedTitle, this.seedLinks);
    this.resizeObserver = new ResizeObserver(() => this.syncSize());
    this.resizeObserver.observe(this.$refs.container);
    this.syncSize();
  },
  beforeUnmount() {
    if (this.resizeObserver) this.resizeObserver.disconnect();
    if (this.graph) this.graph._destructor();
  },
  watch: {
    seedTitle(title) {
      this.setGraphData(title, this.seedLinks);
      this.showTooltip(title);
    },
  },
  methods: {
    syncSize() {
      const rect = this.$refs.container.getBoundingClientRect();
      if (this.graph && rect.width && rect.height) {
        this.graph.width(rect.width).height(rect.height);
      }
    },
    setGraphData(title, linkTitles) {
      const nodes = [{ id: title, isCenter: true }, ...linkTitles.map(id => ({ id }))];
      const links = linkTitles.map(id => ({ source: title, target: id }));
      this.graph.graphData({ nodes, links });
      this.listNodes = nodes;
    },
    async fetchLinksFor(title) {
      if (this.linksCache[title]) return this.linksCache[title];
      const response = await fetch(`/api/article-links?title=${encodeURIComponent(title)}`);
      if (!response.ok) throw new Error(`Request failed: ${response.status}`);
      const data = await response.json();
      this.linksCache[title] = data.links;
      return data.links;
    },
    wikipediaUrl(title) {
      return `https://en.wikipedia.org/wiki/${encodeURIComponent(title.replace(/ /g, '_'))}`;
    },
    getCachedSummary(title) {
      if (this.summaryCache[title]) return this.summaryCache[title];
      try {
        const stored = localStorage.getItem(`article-summary:${title}`);
        if (stored) {
          const data = JSON.parse(stored);
          this.summaryCache[title] = data;
          return data;
        }
      } catch {
        // localStorage unavailable (private mode, quota, etc) — fall back to network.
      }
      return null;
    },
    setCachedSummary(title, data) {
      this.summaryCache[title] = data;
      try {
        localStorage.setItem(`article-summary:${title}`, JSON.stringify(data));
      } catch {
        // ignore quota/availability errors, in-memory cache still works
      }
    },
    async showTooltip(title) {
      const cached = this.getCachedSummary(title);
      this.tooltip = {
        visible: true,
        title,
        extract: cached ? cached.extract : '',
        thumbnail: cached ? cached.thumbnail : null,
        loading: !cached,
      };
      if (cached) return;
      try {
        const response = await fetch(`/api/article-summary?title=${encodeURIComponent(title)}`);
        const data = await response.json();
        this.setCachedSummary(title, data);
        if (this.tooltip.title === title) {
          this.tooltip = { visible: true, title: data.title, extract: data.extract, thumbnail: data.thumbnail, loading: false };
        }
      } catch {
        if (this.tooltip.title === title) this.tooltip.loading = false;
      }
    },
    hideTooltip() {
      this.tooltip.visible = false;
    },
    navigateToNode(node) {
      if (this.loadingNodeId) return;
      if (node.isCenter) {
        this.showTooltip(node.id);
        return;
      }
      this.hideTooltip();
      this.$emit('select', node.id);
    },
    async expandNode(node) {
      if (node.isCenter || this.loadingNodeId) return;
      this.loadingNodeId = node.id;
      this.errorNodeId = null;
      this.announcement = `Loading links for ${node.id}…`;
      try {
        const linkTitles = await this.fetchLinksFor(node.id);
        const { nodes, links } = this.graph.graphData();
        const existingIds = new Set(nodes.map(n => n.id));
        let added = 0;
        linkTitles.forEach(title => {
          if (!existingIds.has(title)) {
            nodes.push({ id: title });
            existingIds.add(title);
            added += 1;
          }
          if (!links.some(l => (l.source.id ?? l.source) === node.id && (l.target.id ?? l.target) === title)) {
            links.push({ source: node.id, target: title });
          }
        });
        this.graph.graphData({ nodes, links });
        this.listNodes = nodes;
        this.announcement = `Added ${added} new link${added === 1 ? '' : 's'} from ${node.id}.`;
      } catch {
        this.errorNodeId = node.id;
        this.announcement = `Couldn't load links for ${node.id}. Try again.`;
      } finally {
        this.loadingNodeId = null;
      }
    },
  },
};
</script>

<template>
  <div class="graph-3d-wrapper">
    <button
      type="button"
      class="list-toggle"
      :title="showList ? 'Switch to the 3D view' : 'Switch to a keyboard-accessible list view'"
      :aria-label="showList ? 'Switch to the 3D view' : 'Switch to a keyboard-accessible list view'"
      @click="showList = !showList"
    >{{ showList ? '🧊 Show 3D view' : '☰ Show as list' }}</button>

    <div
      v-show="!showList"
      ref="container"
      class="graph-3d-container"
      role="img"
      :aria-label="`3D force graph centered on ${seedTitle}, with ${listNodes.length - 1} linked articles. Click a node to move there and see its summary; click the highlighted center node to see its summary. Use the list view for keyboard access.`"
    ></div>

    <div v-if="showList" class="graph-3d-list">
      <ul>
        <li v-for="node in listNodes" :key="node.id">
          <span v-if="node.isCenter" class="node-row center">{{ node.id }} (current)</span>
          <button
            v-else
            type="button"
            class="node-row"
            :class="{ errored: errorNodeId === node.id }"
            :title="`Expand links from ${node.id}`"
            @click="expandNode(node)"
          >
            {{ node.id }}
            <span v-if="loadingNodeId === node.id"> — loading…</span>
            <span v-else-if="errorNodeId === node.id"> — couldn't load, tap to retry</span>
          </button>
          <button
            type="button"
            class="info-button"
            :title="`View a summary of ${node.id}`"
            :aria-label="`View a summary of ${node.id}`"
            @click="showTooltip(node.id)"
          >ⓘ</button>
          <a
            class="wiki-link"
            :href="wikipediaUrl(node.id)"
            target="_blank"
            rel="noopener"
            :title="`Read ${node.id} on Wikipedia`"
            :aria-label="`Read ${node.id} on Wikipedia`"
          >Read ↗</a>
          <button
            v-if="!node.isCenter"
            type="button"
            class="recenter-button"
            title="Make this the graph's center article"
            @click="$emit('select', node.id)"
          >Recenter</button>
        </li>
      </ul>
    </div>

    <p class="sr-only" role="status" aria-live="polite">{{ announcement }}</p>

    <ArticleTooltip
      :visible="tooltip.visible"
      :title="tooltip.title"
      :extract="tooltip.extract"
      :thumbnail="tooltip.thumbnail"
      :loading="tooltip.loading"
      @hover-end="hideTooltip"
      @close="hideTooltip"
    />
  </div>
</template>

<style scoped>
.graph-3d-wrapper {
  position: relative;
  width: 100%;
  height: 100%;
}
.graph-3d-container {
  width: 100%;
  height: 100%;
}
.list-toggle {
  position: absolute;
  top: 0.5rem;
  right: 0.5rem;
  z-index: 2;
  background: var(--surface, #f3e9d2);
  border: 1px solid var(--olive, #74804a);
  color: var(--blue, #2f6690);
  border-radius: 2px;
  padding: 0.3rem 0.7rem;
  font-size: 0.75rem;
  cursor: pointer;
}
.graph-3d-list {
  width: 100%;
  height: 100%;
  overflow-y: auto;
  padding: 0.75rem;
  background: var(--surface, #f3e9d2);
}
.graph-3d-list ul {
  list-style: none;
  margin: 0;
  padding: 0;
}
.graph-3d-list li {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.4rem 0;
  border-bottom: 1px solid var(--olive, #74804a);
}
.node-row {
  flex: 1;
  text-align: left;
  background: none;
  border: none;
  color: var(--ink, #3f3326);
  font-size: 0.85rem;
  cursor: pointer;
  padding: 0.3rem 0;
}
.node-row.center {
  color: var(--gold, #b8935a);
  font-weight: 700;
  cursor: default;
}
.node-row.errored {
  color: #b0413e;
}
.info-button {
  flex: none;
  background: transparent;
  border: 1px solid var(--olive, #74804a);
  color: var(--blue, #2f6690);
  border-radius: 50%;
  width: 1.6rem;
  height: 1.6rem;
  font-size: 0.75rem;
  cursor: pointer;
}
.wiki-link {
  flex: none;
  color: var(--blue, #2f6690);
  font-size: 0.75rem;
  text-decoration: none;
  padding: 0.2rem 0.4rem;
}
.wiki-link:hover {
  text-decoration: underline;
}
.recenter-button {
  flex: none;
  background: transparent;
  border: 1px solid var(--blue, #2f6690);
  color: var(--blue, #2f6690);
  border-radius: 2px;
  padding: 0.2rem 0.6rem;
  font-size: 0.72rem;
  cursor: pointer;
}
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}
</style>
