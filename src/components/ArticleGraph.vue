<script>
import { forceSimulation, forceLink, forceManyBody, forceCenter, forceCollide, quadtree } from 'd3';
import { defineAsyncComponent } from 'vue';
import ArticleTooltip from './ArticleTooltip.vue';
import ArticleSearch from './ArticleSearch.vue';

const ArticleGraph3D = defineAsyncComponent(() => import('./ArticleGraph3D.vue'));

const BASE_WIDTH = 800;
const BASE_HEIGHT = 600;
const MAX_NODES = 1500;

const SWIPE_MIN_DISTANCE = 60;
const SWIPE_MAX_DURATION = 700;
const DEFAULT_ZOOM_K = 1.9;
const TAP_MOVE_THRESHOLD = 8;
const NEAR_MISS_TOLERANCE_PX = 18;

function computeDefaultZoom(width, height) {
  return { x: (width / 2) * (1 - DEFAULT_ZOOM_K), y: (height / 2) * (1 - DEFAULT_ZOOM_K), k: DEFAULT_ZOOM_K };
}

export default {
  name: 'ArticleGraph',
  components: { ArticleTooltip, ArticleSearch, ArticleGraph3D },
  props: {
    seedTitle: { type: String, required: true },
    seedLinks: { type: Array, required: true },
    topics: { type: Array, default: () => [] },
  },
  data() {
    return {
      nodes: [],
      links: [],
      baseWidth: BASE_WIDTH,
      baseHeight: BASE_HEIGHT,
      canvasWidth: BASE_WIDTH,
      canvasHeight: BASE_HEIGHT,
      tooltip: { visible: false, title: '', extract: '', thumbnail: null, loading: false },
      zoom: computeDefaultZoom(BASE_WIDTH, BASE_HEIGHT),
      dragNode: null,
      dragMoved: false,
      suppressNextClick: false,
      panning: false,
      expandingId: null,
      hoveredId: null,
      currentSeedTitle: this.seedTitle,
      history: [],
      loadingSeed: false,
      graphMode: false,
      selectedTopic: '',
      smoothPan: false,
      helpOpen: false,
      view3D: false,
    };
  },
  computed: {
    transform() {
      return `translate(${this.zoom.x}, ${this.zoom.y}) scale(${this.zoom.k})`;
    },
    atNodeLimit() {
      return this.nodes.length >= MAX_NODES;
    },
    maxNodes() {
      return MAX_NODES;
    },
  },
  created() {
    this.activePointers = new Map();
    this.pinch = null;
    this.swipeStart = null;
    this.summaryCache = {};
    this.pendingTouchNode = null;
    this.touchStartPos = null;
    this.touchMoved = false;
    this.populateGraph(this.seedTitle, this.seedLinks);
  },
  mounted() {
    this.syncAspectRatio();
    this.buildSimulation();
    window.addEventListener('pointermove', this.onPointerMove);
    window.addEventListener('pointerup', this.onPointerUp);
  },
  beforeUnmount() {
    if (this.simulation) this.simulation.stop();
    if (this.hideTimer) clearTimeout(this.hideTimer);
    window.removeEventListener('pointermove', this.onPointerMove);
    window.removeEventListener('pointerup', this.onPointerUp);
    document.body.classList.remove('graph-fullscreen');
  },
  methods: {
    toggleGraphMode() {
      this.graphMode = !this.graphMode;
      document.body.classList.toggle('graph-fullscreen', this.graphMode);
      this.$nextTick(() => this.syncAspectRatio());
    },
    syncAspectRatio() {
      const rect = this.$refs.svg.getBoundingClientRect();
      if (!rect.width || !rect.height) return;
      const aspect = rect.width / rect.height;
      const baseArea = BASE_WIDTH * BASE_HEIGHT;
      const newBaseWidth = Math.round(Math.sqrt(baseArea * aspect));
      const newBaseHeight = Math.round(Math.sqrt(baseArea / aspect));
      if (!newBaseWidth || !newBaseHeight || newBaseWidth === this.baseWidth) return;
      const scaleX = newBaseWidth / this.baseWidth;
      const scaleY = newBaseHeight / this.baseHeight;
      this.nodes.forEach(node => {
        node.x *= scaleX;
        node.y *= scaleY;
        if (node.fx != null) node.fx *= scaleX;
        if (node.fy != null) node.fy *= scaleY;
      });
      this.baseWidth = newBaseWidth;
      this.baseHeight = newBaseHeight;
      this.canvasWidth = Math.round(this.canvasWidth * scaleX);
      this.canvasHeight = Math.round(this.canvasHeight * scaleY);
      this.zoom = computeDefaultZoom(this.canvasWidth, this.canvasHeight);
      if (this.simulation) this.simulation.force('center', forceCenter(this.canvasWidth / 2, this.canvasHeight / 2));
    },
    updateCanvasSize() {
      const oldWidth = this.canvasWidth;
      const scale = Math.max(1, Math.sqrt(this.nodes.length / 25));
      const newWidth = Math.round(this.baseWidth * scale);
      const newHeight = Math.round(this.baseHeight * scale);
      if (newWidth === oldWidth) return;
      const growth = newWidth / oldWidth;
      this.canvasWidth = newWidth;
      this.canvasHeight = newHeight;
      this.smoothPan = true;
      this.applyZoom(this.zoom.k / growth);
    },
    populateGraph(title, linkTitles) {
      this.addArticleNode(title, this.canvasWidth / 2, this.canvasHeight / 2, true);
      const spreadRadius = Math.min(this.canvasWidth, this.canvasHeight) * 0.35;
      linkTitles.forEach((linkTitle, i) => {
        const angle = (i / linkTitles.length) * Math.PI * 2;
        this.addArticleNode(
          linkTitle,
          this.canvasWidth / 2 + Math.cos(angle) * spreadRadius,
          this.canvasHeight / 2 + Math.sin(angle) * spreadRadius
        );
        this.links.push({ source: title, target: linkTitle });
      });
      this.updateCanvasSize();
    },
    buildSimulation() {
      if (this.simulation) this.simulation.stop();
      this.simulation = forceSimulation(this.nodes)
        .force('link', forceLink(this.links).id(d => d.id).distance(90))
        .force('charge', forceManyBody().strength(-160))
        .force('center', forceCenter(this.canvasWidth / 2, this.canvasHeight / 2))
        .force('collide', forceCollide(48));
    },
    addArticleNode(title, x, y, isCenter = false) {
      if (this.nodes.some(n => n.id === title)) return;
      this.nodes.push({ id: title, isCenter, x, y, vx: 0, vy: 0, expanded: isCenter });
    },
    nodeById(id) {
      return this.nodes.find(n => n.id === id);
    },
    nodeRadius(node) {
      const base = node.isCenter ? 28 : 19;
      return this.hoveredId === node.id ? base * 1.35 : base;
    },
    async expandNode(node) {
      if (node.expanded || this.expandingId || this.nodes.length >= MAX_NODES) return;
      this.expandingId = node.id;
      try {
        const response = await fetch(`/api/article-links?title=${encodeURIComponent(node.id)}`);
        const data = await response.json();
        node.expanded = true;
        data.links.forEach((title, i) => {
          if (this.nodes.length >= MAX_NODES) return;
          const angle = (i / data.links.length) * Math.PI * 2;
          this.addArticleNode(title, node.x + Math.cos(angle) * 90, node.y + Math.sin(angle) * 90);
          const alreadyLinked = this.links.some(
            l => (l.source.id ?? l.source) === node.id && (l.target.id ?? l.target) === title
          );
          if (!alreadyLinked) this.links.push({ source: node.id, target: title });
        });
        this.updateCanvasSize();
        this.simulation.nodes(this.nodes);
        this.simulation.force('link', forceLink(this.links).id(d => d.id).distance(90));
        this.simulation.force('center', forceCenter(this.canvasWidth / 2, this.canvasHeight / 2));
        this.simulation.alpha(0.35).restart();
      } finally {
        this.expandingId = null;
      }
    },
    randomArticleUrl() {
      return this.selectedTopic
        ? `/api/random-article?topic=${encodeURIComponent(this.selectedTopic)}`
        : '/api/random-article';
    },
    async loadNewSeed() {
      if (this.loadingSeed) return;
      this.loadingSeed = true;
      try {
        this.history.push(this.currentSeedTitle);
        const randomResponse = await fetch(this.randomArticleUrl());
        const article = await randomResponse.json();
        await this.rebuildGraph(article.title);
      } finally {
        this.loadingSeed = false;
      }
    },
    async selectTopic(topic) {
      if (this.loadingSeed || topic === this.selectedTopic) return;
      this.selectedTopic = topic;
      this.loadingSeed = true;
      try {
        this.history.push(this.currentSeedTitle);
        const randomResponse = await fetch(this.randomArticleUrl());
        const article = await randomResponse.json();
        await this.rebuildGraph(article.title);
      } finally {
        this.loadingSeed = false;
      }
    },
    async selectSearchResult(title) {
      if (this.loadingSeed) return;
      this.selectedTopic = '';
      this.loadingSeed = true;
      try {
        this.history.push(this.currentSeedTitle);
        await this.rebuildGraph(title);
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
      this.canvasWidth = this.baseWidth;
      this.canvasHeight = this.baseHeight;
      this.currentSeedTitle = title;
      this.populateGraph(title, data.links);
      this.smoothPan = true;
      this.zoom = computeDefaultZoom(this.canvasWidth, this.canvasHeight);
      this.buildSimulation();
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
    async showTooltip(node) {
      this.hoveredId = node.id;
      const cached = this.getCachedSummary(node.id);
      this.tooltip = {
        visible: true,
        title: node.id,
        extract: cached ? cached.extract : '',
        thumbnail: cached ? cached.thumbnail : null,
        loading: !cached,
      };
      if (cached) return;
      try {
        const response = await fetch(`/api/article-summary?title=${encodeURIComponent(node.id)}`);
        const data = await response.json();
        this.setCachedSummary(node.id, data);
        if (this.hoveredId === node.id) {
          this.tooltip = { visible: true, title: data.title, extract: data.extract, thumbnail: data.thumbnail, loading: false };
        }
      } catch {
        if (this.hoveredId === node.id) this.tooltip.loading = false;
      }
    },
    hideTooltip() {
      this.hideTimer = null;
      this.tooltip.visible = false;
      this.hoveredId = null;
    },
    onNodeHoverStart(node) {
      this.hoveredId = node.id;
    },
    onNodeHoverEnd() {
      if (!this.tooltip.visible) this.hoveredId = null;
    },
    nodeLabel(node) {
      return node.id.length > 24 ? `${node.id.slice(0, 23)}…` : node.id;
    },
    cancelHideTooltip() {
      if (this.hideTimer) {
        clearTimeout(this.hideTimer);
        this.hideTimer = null;
      }
    },
    panCameraTo(x, y, k = this.zoom.k) {
      this.smoothPan = true;
      this.zoom = {
        x: this.canvasWidth / 2 - x * k,
        y: this.canvasHeight / 2 - y * k,
        k,
      };
    },
    onNodeClick(node) {
      if (this.suppressNextClick) {
        this.suppressNextClick = false;
        return;
      }
      this.selectAsCenter(node);
    },
    unpinNode(node) {
      node.fx = null;
      node.fy = null;
      node.pinned = false;
      this.simulation.alpha(0.3).restart();
    },
    async selectAsCenter(node) {
      if (this.loadingSeed || node.id === this.currentSeedTitle) return;
      this.history.push(this.currentSeedTitle);
      const previousCenter = this.nodeById(this.currentSeedTitle);
      if (previousCenter) previousCenter.isCenter = false;
      node.isCenter = true;
      this.currentSeedTitle = node.id;
      this.panCameraTo(node.x, node.y, DEFAULT_ZOOM_K);
      await this.expandNode(node);
    },
    registerPointer(event) {
      this.activePointers.set(event.pointerId, { x: event.clientX, y: event.clientY });
    },
    pointerDistance() {
      const points = [...this.activePointers.values()];
      return Math.hypot(points[0].x - points[1].x, points[0].y - points[1].y);
    },
    startPinch() {
      this.smoothPan = false;
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

      if (event.pointerType === 'touch') {
        event.preventDefault();
        this.touchMoved = false;
        this.touchStartPos = { x: event.clientX, y: event.clientY };
        this.pendingTouchNode = node;
        return;
      }

      this.smoothPan = false;
      this.dragMoved = false;
      this.dragNode = node;
      this.simulation.alphaTarget(0.3).restart();
    },
    findNearestNode(canvasX, canvasY, maxDistance) {
      if (!this.nodes.length) return null;
      const tree = quadtree().x(d => d.x).y(d => d.y).addAll(this.nodes);
      return tree.find(canvasX, canvasY, maxDistance) || null;
    },
    onBackgroundPointerDown(event) {
      this.registerPointer(event);
      if (this.activePointers.size >= 2) {
        this.startPinch();
        return;
      }

      // The tap/click missed every node's own hit area (their pointerdown
      // handlers stop propagation, so this only runs on a genuine miss).
      // Snap to a node a few pixels away instead of forcing pixel-perfect
      // hits — this matters most for small nodes on touch screens.
      const rect = this.$refs.svg.getBoundingClientRect();
      const canvasX = (event.clientX - rect.left - this.zoom.x) / this.zoom.k;
      const canvasY = (event.clientY - rect.top - this.zoom.y) / this.zoom.k;
      const nearest = this.findNearestNode(canvasX, canvasY, NEAR_MISS_TOLERANCE_PX / this.zoom.k);
      if (nearest) {
        this.onNodePointerDown(event, nearest);
        return;
      }

      this.smoothPan = false;
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
      if (this.pendingTouchNode && !this.dragNode) {
        const dx = event.clientX - this.touchStartPos.x;
        const dy = event.clientY - this.touchStartPos.y;
        if (Math.hypot(dx, dy) > TAP_MOVE_THRESHOLD) {
          this.touchMoved = true;
          this.smoothPan = false;
          this.dragNode = this.pendingTouchNode;
          this.pendingTouchNode = null;
          this.simulation.alphaTarget(0.3).restart();
        } else {
          return;
        }
      }
      if (this.dragNode) {
        this.dragMoved = true;
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
      if (this.pendingTouchNode) {
        const node = this.pendingTouchNode;
        this.pendingTouchNode = null;
        if (!this.touchMoved) this.selectAsCenter(node);
      }
      if (this.dragNode) {
        if (this.dragMoved) {
          this.dragNode.pinned = true;
          this.suppressNextClick = true;
        } else {
          this.dragNode.fx = null;
          this.dragNode.fy = null;
        }
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
      if (Math.abs(dx) < SWIPE_MIN_DISTANCE) return;
      if (Math.abs(dx) < Math.abs(dy) * 1.5) return;
      if (duration > SWIPE_MAX_DURATION) return;
      if (dx > 0) this.loadNewSeed();
      else this.goToPreviousSeed();
    },
    onWheel(event) {
      event.preventDefault();
      this.smoothPan = false;
      this.applyZoom(this.zoom.k * (event.deltaY > 0 ? 0.9 : 1.1));
    },
    applyZoom(newK, anchor = null) {
      const a = anchor || { x: this.canvasWidth / 2, y: this.canvasHeight / 2 };
      const clamped = Math.min(3, Math.max(0.3, newK));
      const ratio = clamped / this.zoom.k;
      this.zoom.x = a.x - (a.x - this.zoom.x) * ratio;
      this.zoom.y = a.y - (a.y - this.zoom.y) * ratio;
      this.zoom.k = clamped;
    },
    zoomIn() {
      this.smoothPan = true;
      this.applyZoom(this.zoom.k * 1.25);
    },
    zoomOut() {
      this.smoothPan = true;
      this.applyZoom(this.zoom.k * 0.8);
    },
    resetZoom() {
      this.smoothPan = true;
      this.zoom = computeDefaultZoom(this.canvasWidth, this.canvasHeight);
    },
  },
};
</script>

<template>
  <div class="graph-root" :class="{ fullscreen: graphMode }">
    <header class="graph-header">
      <div class="graph-header-row">
        <h1>Article Link Graph</h1>
        <button class="mode-toggle" type="button" @click="view3D = !view3D">
          {{ view3D ? '🕸 2D view' : '🧊 3D view' }}
        </button>
        <button class="mode-toggle" type="button" @click="toggleGraphMode">
          {{ graphMode ? '✕ Exit graph mode' : '⛶ Graph mode' }}
        </button>
      </div>
      <p v-if="!graphMode" class="subtitle">
        Starting from “{{ currentSeedTitle }}”. Click a node to recenter on it, + to expand its links, ⓘ for a summary.
        Drag a node to pin it in place — tap 📌 to release it. Pinch/scroll to zoom, swipe right for a new article, swipe left to go back.
      </p>
      <ArticleSearch v-if="!graphMode" :disabled="loadingSeed" @select="selectSearchResult" />
      <div v-if="!graphMode" class="topic-row">
        <button
          class="topic-pill"
          :class="{ active: selectedTopic === '' }"
          :disabled="loadingSeed"
          @click="selectTopic('')"
        >Random</button>
        <button
          v-for="topic in topics"
          :key="topic"
          class="topic-pill"
          :class="{ active: selectedTopic === topic }"
          :disabled="loadingSeed"
          @click="selectTopic(topic)"
        >{{ topic }}</button>
      </div>
      <p v-if="loadingSeed" class="subtitle loading">Loading…</p>
      <p v-else-if="atNodeLimit && !graphMode" class="subtitle loading">Node limit reached ({{ maxNodes }}) — swipe for a new article to keep exploring.</p>
    </header>

    <ArticleGraph3D
      v-if="view3D"
      class="graph-3d"
      :seed-title="currentSeedTitle"
      :seed-links="nodes.filter(n => !n.isCenter).map(n => n.id)"
      @select="selectSearchResult"
    />
    <div v-else class="graph-canvas">
      <svg
        ref="svg"
        class="graph-svg"
        :viewBox="`0 0 ${canvasWidth} ${canvasHeight}`"
        @pointerdown="onBackgroundPointerDown"
        @wheel="onWheel"
      >
      <g :transform="transform" :class="{ 'camera-animated': smoothPan }">
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
          @mouseenter="onNodeHoverStart(node)"
          @mouseleave="onNodeHoverEnd"
          @click="onNodeClick(node)"
        >
          <circle :r="nodeRadius(node)" />
          <text
            v-if="!node.isCenter"
            class="node-hover-label"
            text-anchor="middle"
            :y="nodeRadius(node) + 13"
          >{{ nodeLabel(node) }}</text>
          <g
            v-if="!node.expanded && !atNodeLimit"
            class="expand-badge"
            :transform="`translate(${-nodeRadius(node) * 0.75}, ${nodeRadius(node) * 0.75})`"
            @click.stop="expandNode(node)"
            @pointerdown.stop
          >
            <circle r="12" />
            <line x1="-6" y1="0" x2="6" y2="0" />
            <line x1="0" y1="-6" x2="0" y2="6" />
          </g>
          <g
            class="info-badge"
            :transform="`translate(${nodeRadius(node) * 0.75}, ${nodeRadius(node) * 0.75})`"
            @click.stop="showTooltip(node)"
            @pointerdown.stop
          >
            <circle r="12" />
            <text text-anchor="middle" dominant-baseline="central">i</text>
          </g>
          <g
            v-if="node.pinned"
            class="pin-badge"
            :title="`Unpin ${node.id}`"
            :transform="`translate(${-nodeRadius(node) * 0.75}, ${-nodeRadius(node) * 0.75})`"
            @click.stop="unpinNode(node)"
            @pointerdown.stop
          >
            <circle r="10" />
            <text text-anchor="middle" dominant-baseline="central">📌</text>
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
      <div class="scanlines" aria-hidden="true"></div>

      <div v-if="graphMode" class="zoom-controls">
        <button type="button" aria-label="Zoom in" @click="zoomIn">+</button>
        <button type="button" aria-label="Reset zoom" @click="resetZoom">⟳</button>
        <button type="button" aria-label="Zoom out" @click="zoomOut">−</button>
      </div>

      <button
        v-if="graphMode"
        type="button"
        class="help-toggle"
        aria-label="Show controls help"
        @click="helpOpen = !helpOpen"
      >?</button>
      <div v-if="graphMode && helpOpen" class="help-panel">
        <button type="button" class="help-close" aria-label="Close help" @click="helpOpen = false">✕</button>
        <ul>
          <li><strong>Tap a node</strong> — recenter the graph on it</li>
          <li><strong>+</strong> — expand that node's links</li>
          <li><strong>ⓘ</strong> — view its summary</li>
          <li><strong>Drag a node</strong> — reposition and pin it; tap 📌 to release</li>
          <li><strong>Pinch / scroll</strong> — zoom</li>
          <li><strong>Drag background</strong> — pan</li>
          <li><strong>Swipe right / left</strong> — new article / go back</li>
        </ul>
      </div>
    </div>

    <ArticleTooltip
      :visible="tooltip.visible"
      :title="tooltip.title"
      :extract="tooltip.extract"
      :thumbnail="tooltip.thumbnail"
      :loading="tooltip.loading"
      @hover-start="cancelHideTooltip"
      @hover-end="hideTooltip"
      @close="hideTooltip"
    />
  </div>
</template>

<style scoped>
.graph-root {
  --surface: #f3e9d2;
  --surface-deep: #e9dbb6;
  --ink: #3f3326;
  --ink-soft: #6b5d47;
  --blue: #2f6690;
  --blue-faint: rgba(47, 102, 144, 0.22);
  --olive: #74804a;
  --olive-soft: rgba(116, 128, 74, 0.35);
  --gold: #b8935a;
  max-width: 900px;
  margin: 0 auto;
  padding: 1.5rem 1.25rem;
  background: var(--surface);
  font-family: "Palatino Linotype", "Palatino", Georgia, serif;
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
}
.graph-header-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.6rem 0.75rem;
}
.graph-header-row h1 {
  flex: 1 1 auto;
  min-width: 0;
}
.graph-header h1 {
  margin: 0 0 0.1rem;
  font-size: 1.3rem;
  color: var(--blue);
  text-transform: uppercase;
  letter-spacing: 0.08em;
}
.mode-toggle {
  height: 2.75rem;
  flex: none;
  background: var(--surface);
  border: 1px solid var(--olive);
  color: var(--blue);
  border-radius: 2px;
  padding: 0.3rem 0.9rem;
  font-family: inherit;
  font-size: 0.85rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  cursor: pointer;
}
.mode-toggle:hover {
  border-color: var(--blue);
  box-shadow: 0 0 8px var(--blue-faint);
}
.subtitle {
  color: var(--ink-soft);
  font-size: 0.9rem;
  margin: 0 0 1rem;
  line-height: 1.4;
}
.subtitle.loading {
  color: var(--blue);
  margin-top: -0.5rem;
}
.subtitle.loading::after {
  content: '…';
  animation: gentle-blink 1.2s steps(1) infinite;
}
.topic-row {
  display: flex;
  gap: 0.4rem;
  overflow-x: auto;
  margin: 0 0 1rem;
  padding-bottom: 0.2rem;
}
.topic-pill {
  flex: none;
  border: 1px solid var(--olive);
  background: var(--surface);
  color: var(--ink-soft);
  border-radius: 2px;
  padding: 0.3rem 0.8rem;
  font-family: inherit;
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  cursor: pointer;
}
.topic-pill.active {
  background: var(--blue);
  border-color: var(--blue);
  color: var(--surface);
}
.topic-pill:hover {
  border-color: var(--blue);
}
.topic-pill:disabled {
  opacity: 0.5;
  cursor: default;
}
.graph-svg {
  width: 100%;
  height: 70vh;
  touch-action: none;
  background: var(--surface);
  border: 1px solid var(--olive);
  border-radius: 4px;
  box-shadow: inset 0 0 40px rgba(184, 147, 90, 0.18);
  cursor: grab;
}
.graph-3d {
  width: 100%;
  height: 70vh;
  display: block;
  background: #0c1220;
  border: 1px solid var(--olive);
  border-radius: 4px;
}
.fullscreen .graph-header {
  flex: none;
}
.fullscreen .graph-svg,
.fullscreen .graph-3d {
  flex: 1;
  height: auto;
  border: none;
  border-radius: 0;
  box-shadow: none;
}
.graph-canvas {
  position: relative;
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
}
.scanlines {
  position: absolute;
  inset: 0;
  pointer-events: none;
  z-index: 4;
  background:
    radial-gradient(ellipse at 20% 15%, rgba(184, 147, 90, 0.12), transparent 55%),
    radial-gradient(ellipse at 80% 85%, rgba(116, 128, 74, 0.10), transparent 55%);
  mix-blend-mode: multiply;
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
  border: 1px solid var(--olive);
  background: var(--surface);
  color: var(--blue);
  font-family: inherit;
  font-size: 1.4rem;
  line-height: 1;
  cursor: pointer;
  box-shadow: 0 2px 6px rgba(63, 51, 38, 0.25);
}
.zoom-controls button:hover {
  border-color: var(--blue);
  box-shadow: 0 0 10px var(--blue-faint);
}
.help-toggle {
  position: absolute;
  left: 1rem;
  bottom: 1rem;
  z-index: 5;
  width: 2.5rem;
  height: 2.5rem;
  border-radius: 50%;
  border: 1px solid var(--olive);
  background: var(--surface);
  color: var(--blue);
  font-family: "Palatino Linotype", "Palatino", Georgia, serif;
  font-weight: 700;
  font-size: 1.1rem;
  cursor: pointer;
  box-shadow: 0 2px 6px rgba(63, 51, 38, 0.25);
}
.help-toggle:hover {
  border-color: var(--blue);
  box-shadow: 0 0 10px var(--blue-faint);
}
.help-panel {
  position: absolute;
  left: 1rem;
  bottom: calc(1rem + 3rem);
  z-index: 6;
  width: 240px;
  max-width: calc(100% - 2rem);
  background: var(--surface);
  border: 1px solid var(--olive);
  border-radius: 4px;
  padding: 0.75rem 1rem;
  box-shadow: 0 4px 12px rgba(63, 51, 38, 0.25);
}
.help-close {
  position: absolute;
  top: 0.4rem;
  right: 0.4rem;
  background: none;
  border: none;
  color: var(--ink-soft);
  font-size: 0.9rem;
  cursor: pointer;
}
.help-panel ul {
  list-style: none;
  margin: 0;
  padding: 0;
}
.help-panel li {
  font-size: 0.8rem;
  color: var(--ink);
  line-height: 1.5;
  padding-right: 1rem;
}
.help-panel li strong {
  color: var(--blue);
}
.camera-animated {
  transition: transform 0.6s cubic-bezier(0.22, 1, 0.36, 1);
}
.graph-edge {
  stroke: var(--olive);
  stroke-width: 1.5;
}
.graph-node circle {
  fill: var(--surface);
  stroke: var(--olive);
  stroke-width: 2;
  cursor: pointer;
  transition: r 0.15s ease, stroke 0.15s ease;
}
.graph-node:hover circle {
  stroke: var(--blue);
}
.graph-node.center circle {
  fill: var(--blue);
  stroke: var(--gold);
  stroke-width: 3;
}
.graph-node.expanding circle {
  opacity: 0.5;
}
.expand-badge circle {
  fill: var(--gold);
  stroke: var(--surface);
  stroke-width: 1.5;
  cursor: pointer;
}
.expand-badge line {
  stroke: var(--surface);
  stroke-width: 1.5;
  pointer-events: none;
}
.info-badge circle {
  fill: var(--blue);
  stroke: var(--surface);
  stroke-width: 1.5;
  cursor: pointer;
}
.info-badge text {
  fill: var(--surface);
  font-family: "Palatino Linotype", "Palatino", Georgia, serif;
  font-style: italic;
  font-weight: 700;
  font-size: 13px;
  pointer-events: none;
}
.pin-badge circle {
  fill: var(--surface);
  stroke: var(--gold);
  stroke-width: 1.5;
  cursor: pointer;
}
.pin-badge text {
  font-size: 11px;
  pointer-events: none;
}
.graph-center-label {
  fill: var(--ink);
  font-family: "Palatino Linotype", "Palatino", Georgia, serif;
  font-size: 15px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  pointer-events: none;
  paint-order: stroke fill;
  stroke: var(--surface);
  stroke-width: 3px;
  stroke-linejoin: round;
}
.node-hover-label {
  fill: var(--ink);
  font-family: "Palatino Linotype", "Palatino", Georgia, serif;
  font-size: 9px;
  font-weight: 700;
  text-transform: uppercase;
  pointer-events: none;
  paint-order: stroke fill;
  stroke: var(--surface);
  stroke-width: 3px;
  stroke-linejoin: round;
}
@keyframes gentle-blink {
  0%, 50% { opacity: 1; }
  50.01%, 100% { opacity: 0; }
}
</style>