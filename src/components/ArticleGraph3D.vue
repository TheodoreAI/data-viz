<script>
import ForceGraph3D from '3d-force-graph';
import * as THREE from 'three';
import ArticleTooltip from './ArticleTooltip.vue';

const MAX_PIXEL_RATIO = 2;
const CENTER_COLOR = 0xb8935a; // gold/bronze
const NODE_COLOR = 0x2f6690; // blue
const MOON_COLOR = 0xcfd3da;
const STAR_COUNT = 1800;
const STAR_FIELD_MIN_RADIUS = 700;
const STAR_FIELD_MAX_RADIUS = 1600;
const BASE_RADIUS = 6;
const CENTER_SCALE = 1.5;
const NODE_SCALE = 1;
const TRANSITION_MS = 380;

function easeOutCubic(t) {
  return 1 - (1 - t) ** 3;
}

// Animates an arbitrary set of numeric/color props from their current value
// to a target over a fixed duration, used both for a new node's entrance
// (scale 0 -> target) and for an existing node smoothly restyling itself
// when it becomes (or stops being) the center node, instead of popping.
function tween(duration, onUpdate) {
  const start = performance.now();
  const step = (now) => {
    const t = Math.min((now - start) / duration, 1);
    onUpdate(easeOutCubic(t));
    if (t < 1) requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
}

function makeLabelSprite(text, heightWorldUnits) {
  const canvas = document.createElement('canvas');
  const ctx = canvas.getContext('2d');
  // Baked at a fairly high resolution since zoomToFit can bring the camera
  // close enough for a low-res label texture to look visibly blurry/pixelated.
  const fontSize = 112;
  ctx.font = `${fontSize}px sans-serif`;
  canvas.width = Math.ceil(ctx.measureText(text).width) + 24;
  canvas.height = fontSize + 24;
  // Re-set font: changing canvas.width/height resets the 2D context state.
  ctx.font = `${fontSize}px sans-serif`;
  ctx.textBaseline = 'middle';
  ctx.textAlign = 'center';
  ctx.fillStyle = 'rgba(0, 0, 0, 0.55)';
  ctx.fillText(text, canvas.width / 2 + 1, canvas.height / 2 + 1);
  ctx.fillStyle = '#f3ecd8';
  ctx.fillText(text, canvas.width / 2, canvas.height / 2);

  const texture = new THREE.CanvasTexture(canvas);
  texture.minFilter = THREE.LinearFilter;
  const material = new THREE.SpriteMaterial({ map: texture, transparent: true, depthWrite: false });
  const sprite = new THREE.Sprite(material);
  const scale = heightWorldUnits / canvas.height;
  sprite.scale.set(canvas.width * scale, canvas.height * scale, 1);
  return sprite;
}

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
    this.moons = [];
    this.spheres = [];
    this.hoveredMesh = null;
    this.nodeVisuals = new Map();
    this.currentCenterId = null;
    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const isTouchPrimary = window.matchMedia('(pointer: coarse)').matches;
    this.zoomToFitDuration = reducedMotion ? 0 : 400;
    this.reducedMotion = reducedMotion;

    this.graph = ForceGraph3D()(this.$refs.container)
      .backgroundColor('#0c1220')
      .showNavInfo(!isTouchPrimary)
      .nodeLabel(node => node.id)
      .nodeThreeObject(node => {
        const group = new THREE.Group();
        const targetScale = node.isCenter ? CENTER_SCALE : NODE_SCALE;

        const geometry = new THREE.SphereGeometry(BASE_RADIUS, 24, 24);
        const material = new THREE.MeshStandardMaterial({
          color: node.isCenter ? CENTER_COLOR : NODE_COLOR,
          metalness: node.isCenter ? 0.75 : 0.4,
          roughness: node.isCenter ? 0.3 : 0.6,
        });
        const sphere = new THREE.Mesh(geometry, material);
        sphere.userData = { isSphere: true, nodeId: node.id };
        group.add(sphere);
        this.spheres.push(sphere);

        const label = makeLabelSprite(node.id, 5);
        label.position.set(0, -(BASE_RADIUS + 6), 0);
        group.add(label);

        const moonRadius = BASE_RADIUS * 0.35;
        const moonGeometry = new THREE.SphereGeometry(moonRadius, 12, 12);
        const moonMaterial = new THREE.MeshStandardMaterial({
          color: MOON_COLOR,
          roughness: 0.9,
          metalness: 0.05,
          emissive: 0x22262b,
          emissiveIntensity: 0.2,
        });
        const moon = new THREE.Mesh(moonGeometry, moonMaterial);
        moon.userData = { isMoon: true, nodeId: node.id };
        moon.position.set(BASE_RADIUS + moonRadius + 1.5, 0, 0);
        group.add(moon);
        this.moons.push(moon);

        this.nodeVisuals.set(node.id, { group, sphere, material, moon });

        // Entrance: pop in from nothing rather than snapping to full size —
        // this only runs for genuinely new nodes (3d-force-graph reuses the
        // existing object, without calling this factory again, for any node
        // id that persists across a graphData() update).
        if (reducedMotion) {
          group.scale.setScalar(targetScale);
        } else {
          group.scale.setScalar(0.001);
          tween(TRANSITION_MS, (t) => group.scale.setScalar(0.001 + (targetScale - 0.001) * t));
        }

        return group;
      })
      .linkColor(() => 'rgba(116, 128, 74, 0.6)')
      .linkWidth(1)
      .cooldownTicks(reducedMotion ? 0 : 150)
      .d3AlphaDecay(reducedMotion ? 1 : 0.012)
      .d3VelocityDecay(0.3)
      .onEngineStop(() => this.graph.zoomToFit(this.zoomToFitDuration, 50))
      .onNodeClick(node => this.navigateToNode(node))
      .onNodeHover(node => {
        this.$refs.container.style.cursor = node ? 'pointer' : 'default';
      });

    // Spread nodes out further than the library defaults so their labels
    // have room to not overlap each other.
    this.graph.d3Force('link').distance(100);
    this.graph.d3Force('charge').strength(-90);

    this.graph.scene().add(new THREE.AmbientLight(0xffffff, 0.6));
    const keyLight = new THREE.DirectionalLight(0xfff2d9, 1.1);
    keyLight.position.set(1, 1, 1);
    this.graph.scene().add(keyLight);
    this.graph.scene().add(buildStarfield());

    this.raycaster = new THREE.Raycaster();
    this.pointer = new THREE.Vector2();
    const pickMesh = (clientX, clientY) => {
      const rect = this.$refs.container.getBoundingClientRect();
      this.pointer.x = ((clientX - rect.left) / rect.width) * 2 - 1;
      this.pointer.y = -((clientY - rect.top) / rect.height) * 2 + 1;
      this.raycaster.setFromCamera(this.pointer, this.graph.camera());
      const hit = this.raycaster.intersectObjects([...this.spheres, ...this.moons], false)[0];
      return hit ? hit.object : null;
    };

    this.handleMoonClick = (event) => {
      const hit = pickMesh(event.clientX, event.clientY);
      if (!hit || !hit.userData.isMoon) return;
      event.stopPropagation();
      event.preventDefault();
      this.showTooltip(hit.userData.nodeId);
    };
    // Capture-phase pointerup: the library's own click handling also listens
    // for pointerup (not pointerdown/click), so intercepting here — before it
    // reaches the library's inner container — is what actually lets us swallow
    // the event and stop a moon click from also firing the node's onNodeClick.
    this.$refs.container.addEventListener('pointerup', this.handleMoonClick, true);

    // Independent hover highlight per mesh (sphere vs moon), rather than
    // relying on the library's onNodeHover, which only knows about the whole
    // node group and would scale the sphere and moon together.
    this.handlePointerMove = (event) => {
      const hit = pickMesh(event.clientX, event.clientY);
      if (this.hoveredMesh && this.hoveredMesh !== hit) {
        this.hoveredMesh.scale.setScalar(1);
      }
      if (hit) hit.scale.setScalar(hit.userData.isMoon ? 1.4 : 1.15);
      this.hoveredMesh = hit;
    };
    this.$refs.container.addEventListener('pointermove', this.handlePointerMove);

    const pixelRatio = Math.min(window.devicePixelRatio || 1, MAX_PIXEL_RATIO);
    this.graph.renderer().setPixelRatio(pixelRatio);
    if (reducedMotion) this.graph.controls().autoRotate = false;
    // Prevent zooming/panning the camera inside node geometry (BASE_RADIUS-scale spheres).
    this.graph.controls().minDistance = BASE_RADIUS * 6;

    this.setGraphData(this.seedTitle, this.seedLinks);
    this.resizeObserver = new ResizeObserver(() => this.syncSize());
    this.resizeObserver.observe(this.$refs.container);
    this.syncSize();
  },
  beforeUnmount() {
    if (this.resizeObserver) this.resizeObserver.disconnect();
    if (this.handleMoonClick) this.$refs.container.removeEventListener('pointerup', this.handleMoonClick, true);
    if (this.handlePointerMove) this.$refs.container.removeEventListener('pointermove', this.handlePointerMove);
    if (this.graph) this.graph._destructor();
  },
  watch: {
    seedTitle(title) {
      this.setGraphData(title, this.seedLinks);
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
      const previousCenterId = this.currentCenterId;
      // 3d-force-graph reuses (rather than recreates) any node whose id
      // persists across this update, so if the new center already existed
      // as a sibling, nodeThreeObject won't run for it again — we have to
      // restyle it ourselves for a smooth transform instead of a hard swap.
      const centerAlreadyExisted = this.nodeVisuals.has(title);
      // Capture where it's actually rendered right now, before the physics
      // simulation gets a chance to yank it toward the center on its own.
      const fromPosition = centerAlreadyExisted
        ? this.nodeVisuals.get(title).group.position.clone()
        : null;

      const nodes = [{ id: title, isCenter: true }, ...linkTitles.map(id => ({ id }))];
      const links = linkTitles.map(id => ({ source: title, target: id }));
      const nextIds = new Set(nodes.map(n => n.id));

      // Nodes dropping out of this update: forget them so raycasting/hover
      // never targets a mesh the library has already removed from the scene.
      this.nodeVisuals.forEach((visual, id) => {
        if (nextIds.has(id)) return;
        this.spheres = this.spheres.filter(s => s !== visual.sphere);
        this.moons = this.moons.filter(m => m !== visual.moon);
        this.nodeVisuals.delete(id);
      });
      this.hoveredMesh = null;

      this.graph.graphData({ nodes, links });
      this.listNodes = nodes;
      this.currentCenterId = title;

      if (centerAlreadyExisted) {
        this.animateNodeRoleChange(title, true);
        if (previousCenterId && previousCenterId !== title && this.nodeVisuals.has(previousCenterId)) {
          this.animateNodeRoleChange(previousCenterId, false);
        }
        this.animateRecenterMove(title, fromPosition);
      }
    },
    // Rather than letting the force simulation yank the recentered node
    // toward the origin at whatever speed its forces dictate (which is what
    // read as a "jump"), pin it at its last known position and manually tween
    // that pin to (0, 0, 0) ourselves — a fully controlled, eased move that
    // doesn't depend on simulation internals. Everything else (new sibling
    // nodes, links) still settles normally via the physics simulation.
    animateRecenterMove(nodeId, fromPosition) {
      const liveNode = this.graph.graphData().nodes.find(n => n.id === nodeId);
      if (!liveNode) return;
      if (this.reducedMotion) {
        liveNode.fx = 0;
        liveNode.fy = 0;
        liveNode.fz = 0;
        requestAnimationFrame(() => {
          liveNode.fx = null;
          liveNode.fy = null;
          liveNode.fz = null;
        });
        return;
      }
      liveNode.fx = fromPosition.x;
      liveNode.fy = fromPosition.y;
      liveNode.fz = fromPosition.z;
      tween(TRANSITION_MS, (t) => {
        liveNode.fx = fromPosition.x * (1 - t);
        liveNode.fy = fromPosition.y * (1 - t);
        liveNode.fz = fromPosition.z * (1 - t);
        if (t >= 1) {
          liveNode.fx = null;
          liveNode.fy = null;
          liveNode.fz = null;
        }
      });
    },
    animateNodeRoleChange(nodeId, isCenter) {
      const visual = this.nodeVisuals.get(nodeId);
      if (!visual) return;
      const { group, material } = visual;
      const targetScale = isCenter ? CENTER_SCALE : NODE_SCALE;
      const targetColor = new THREE.Color(isCenter ? CENTER_COLOR : NODE_COLOR);
      const targetMetalness = isCenter ? 0.75 : 0.4;
      const targetRoughness = isCenter ? 0.3 : 0.6;
      if (this.reducedMotion) {
        group.scale.setScalar(targetScale);
        material.color.copy(targetColor);
        material.metalness = targetMetalness;
        material.roughness = targetRoughness;
        return;
      }
      const fromScale = group.scale.x;
      const fromColor = material.color.clone();
      const fromMetalness = material.metalness;
      const fromRoughness = material.roughness;
      tween(TRANSITION_MS, (t) => {
        group.scale.setScalar(fromScale + (targetScale - fromScale) * t);
        material.color.lerpColors(fromColor, targetColor, t);
        material.metalness = fromMetalness + (targetMetalness - fromMetalness) * t;
        material.roughness = fromRoughness + (targetRoughness - fromRoughness) * t;
      });
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
      if (this.loadingNodeId || node.isCenter) return;
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
  padding: 3rem 0.75rem 0.75rem;
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
