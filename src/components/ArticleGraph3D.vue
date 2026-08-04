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
// Label sizing is a *budget*, not a fixed size: a label is capped on both axes
// and takes whichever scale is smaller, so a long title shrinks to stay inside
// its width budget instead of sprawling across its neighbours. Sized in the
// same world units as LINK_DISTANCE, which is what actually separates labels.
const LABEL_HEIGHT = 5;
const LABEL_MAX_WIDTH = 34;
const LABEL_MAX_CHARS = 24;
// Gap between the bottom of a node's sphere and the top of its label.
const LABEL_GAP = 6;
// The fit solves for the distance where the outermost node sits exactly on the
// frame edge, so without a margin that node's label touches the boundary and
// any rounding clips it. Proportional rather than a fixed world-unit amount so
// the visual margin stays the same however far out the camera ends up.
const FIT_MARGIN = 1.06;
// Caps how far the user can scroll/pinch-zoom out: a multiple of whatever
// distance the current graph actually needs to fit on screen, so "zoom out"
// gives a bit of breathing room around the graph without ever letting it
// shrink to a lost speck in an empty void.
const MAX_DISTANCE_FACTOR = 3;
// Narrow (phone) viewports fit fewer world units across the screen, so the
// same label eats proportionally more of the frame — tighten the budget there.
const NARROW_VIEWPORT_PX = 600;
const NARROW_LABEL_SCALE = 0.72;
// Radius of the sphere leaf nodes are placed on around whichever node they
// hang off (the center, or an expanded leaf).
const LINK_DISTANCE = 100;
// Golden-angle spiral: successive points advance by this angle in longitude
// while stepping evenly in latitude, which is the standard way to place N
// points roughly evenly across a sphere for arbitrary N with no clumping.
const GOLDEN_ANGLE = Math.PI * (3 - Math.sqrt(5));

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

// Wikipedia titles run long ("Producer–consumer problem"); past a couple of
// dozen characters the extra width buys no legibility once the width budget
// has scaled the glyphs down, so spend the budget on fewer, bigger characters.
function truncateLabel(text, maxChars) {
  if (text.length <= maxChars) return text;
  return `${text.slice(0, maxChars - 1).trimEnd()}…`;
}

// How far the layout stays from being aligned with the camera: 0 would allow
// points right up against the view axis (where they'd project on top of the
// node they orbit); 1 would spread all the way to the poles. 0.35 keeps every
// point at least ~58° off-axis, comfortably clear in screen space.
const POLAR_BAND = 0.35;

// Deterministic stand-in for letting the d3-force simulation find a resting
// spot for each leaf: places `count` points evenly around `origin` on a
// sphere of `radius`, confined to a band around the equator relative to
// `viewAxis` (the direction from `origin` toward the camera). Points spread
// over a *full* sphere have no regard for where the camera is looking, so for
// small counts it's easy for one to land almost exactly on the view axis —
// invisible from the side, but overlapping `origin` head-on. Nodes render in
// their final position on the very first frame — no settle-in animation, no
// waiting on the physics engine to stop before the camera can be framed.
function sphereLayout(origin, count, radius, viewAxis) {
  if (count === 0) return [];
  // Any helper vector not parallel to viewAxis, just to seed a basis for the
  // plane perpendicular to it.
  const helper = Math.abs(viewAxis.y) < 0.9 ? new THREE.Vector3(0, 1, 0) : new THREE.Vector3(1, 0, 0);
  const u = new THREE.Vector3().crossVectors(viewAxis, helper).normalize();
  const v = new THREE.Vector3().crossVectors(viewAxis, u).normalize();

  const positions = [];
  const dir = new THREE.Vector3();
  for (let i = 0; i < count; i += 1) {
    const t = count === 1 ? 0.5 : i / (count - 1); // 0 .. 1
    // Polar angle measured from viewAxis, confined to a band around 90° (the
    // equator) so it never approaches 0° or 180° (the view axis itself).
    const polar = Math.PI / 2 + (t * 2 - 1) * (Math.PI / 2) * POLAR_BAND;
    const azimuth = GOLDEN_ANGLE * i;
    dir.set(0, 0, 0)
      .addScaledVector(viewAxis, Math.cos(polar))
      .addScaledVector(u, Math.sin(polar) * Math.cos(azimuth))
      .addScaledVector(v, Math.sin(polar) * Math.sin(azimuth));
    positions.push({
      x: origin.x + dir.x * radius,
      y: origin.y + dir.y * radius,
      z: origin.z + dir.z * radius,
    });
  }
  return positions;
}

// Fixes a node at an exact position: d3-force forces a pinned node's x/y/z to
// match fx/fy/fz on every tick regardless of simulated forces, so this is
// permanent until something explicitly un-pins it (which nothing here does —
// every node in this graph stays exactly where it's deterministically placed,
// unless the user drags it).
function pinNodeAt(node, pos) {
  node.x = node.fx = pos.x;
  node.y = node.fy = pos.y;
  node.z = node.fz = pos.z;
}

function makeLabelSprite(text, heightWorldUnits, maxWidthWorldUnits) {
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
  // Labels are baked well above their on-screen size, and nodes further from
  // the camera sample them far below it, which aliases badly without mipmaps.
  // Non-power-of-two mipmaps are fine on the WebGL2 context three renders with.
  texture.minFilter = THREE.LinearMipmapLinearFilter;
  texture.generateMipmaps = true;
  const material = new THREE.SpriteMaterial({ map: texture, transparent: true, depthWrite: false });
  const sprite = new THREE.Sprite(material);
  // Fit inside *both* budgets rather than scaling by height alone: height alone
  // lets a long title grow arbitrarily wide and overlap neighbouring nodes.
  const scale = Math.min(heightWorldUnits / canvas.height, maxWidthWorldUnits / canvas.width);
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
    this.labelBudget = this.computeLabelBudget();

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

        const { height, maxWidth, maxChars } = this.labelBudget;
        const label = makeLabelSprite(truncateLabel(node.id, maxChars), height, maxWidth);
        label.position.set(0, -(BASE_RADIUS + LABEL_GAP), 0);
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
      // Every node is pinned (fx/fy/fz) to a deterministic position the
      // instant it's created, so the physics simulation never has anything
      // to do — cooldownTicks(0) just lets the engine take its one
      // obligatory tick and stop, which is what fires onEngineStop below.
      // That wiring stays useful for the one case nodes AREN'T pre-placed:
      // dragging one reheats the simulation, and this is what re-fits the
      // camera once the drag settles.
      .cooldownTicks(0)
      .onEngineStop(() => this.fitView(this.zoomToFitDuration))
      .onNodeClick(node => this.navigateToNode(node))
      .onNodeHover(node => {
        this.$refs.container.style.cursor = node ? 'pointer' : 'default';
      });

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
    clearTimeout(this.zoomToFitTimer);
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
    computeLabelBudget() {
      // Orientation-independent: the short edge is what constrains how many
      // world units fit across the frame, whichever way the phone is held.
      const narrow = Math.min(window.innerWidth, window.innerHeight) < NARROW_VIEWPORT_PX;
      const scale = narrow ? NARROW_LABEL_SCALE : 1;
      return {
        height: LABEL_HEIGHT * scale,
        maxWidth: LABEL_MAX_WIDTH * scale,
        maxChars: narrow ? Math.round(LABEL_MAX_CHARS * NARROW_LABEL_SCALE) : LABEL_MAX_CHARS,
      };
    },
    // Direction from the camera's current position toward the origin, used
    // as sphereLayout's axis to avoid — approximate (it ignores wherever the
    // camera is actually looking versus its raw position vector), but good
    // enough since camera distance is always much larger than the graph's
    // extent, and it naturally tracks wherever the user has orbited to.
    currentViewAxis() {
      const pos = this.graph.camera().position;
      const axis = new THREE.Vector3(pos.x, pos.y, pos.z);
      return axis.lengthSq() > 0 ? axis.normalize() : new THREE.Vector3(0, 0, 1);
    },
    // Replaces the library's zoomToFit, which frames the graph by its largest
    // bounding-box axis — including the axis pointing at the camera, which
    // contributes nothing to what you actually see — and then divides by the
    // aspect ratio on top. On a tall narrow phone (aspect ~0.46) those compound
    // into a camera parked far too far back, leaving the graph a small clump in
    // the middle of the frame; on desktop (aspect > 1) the penalty disappears,
    // which is why this only ever looked wrong on mobile.
    //
    // Instead, project every node onto the current view axes and solve for the
    // nearest camera distance that still contains them all. A sparse star graph
    // is mostly empty space, so fitting what is actually on screen frames it far
    // tighter than any bounding-volume approximation can.
    fitView(durationMs) {
      if (!this.graph || !this.$refs.container) return;
      const rect = this.$refs.container.getBoundingClientRect();
      if (!rect.width || !rect.height) return;
      const { nodes } = this.graph.graphData();
      if (!nodes.length) return;

      // Cheap fingerprint of everything the fit depends on (container size +
      // every node position). onEngineStop and the resize-settle debounce can
      // both call fitView repeatedly for reasons unrelated to the graph's
      // actual layout — skip the recompute, and critically the
      // cameraPosition() call (which reassigns OrbitControls' target object
      // every time), when nothing that would change the result has moved.
      let fingerprint = `${Math.round(rect.width)}x${Math.round(rect.height)}|${nodes.length}`;
      for (const node of nodes) {
        fingerprint += `|${(node.x || 0).toFixed(1)},${(node.y || 0).toFixed(1)},${(node.z || 0).toFixed(1)}`;
      }
      if (fingerprint === this.lastFitFingerprint) return;
      this.lastFitFingerprint = fingerprint;

      const box = new THREE.Box3();
      const point = new THREE.Vector3();
      nodes.forEach(node => box.expandByPoint(point.set(node.x || 0, node.y || 0, node.z || 0)));
      const center = box.getCenter(new THREE.Vector3());

      const camera = this.graph.camera();
      const current = this.graph.cameraPosition();
      const axis = new THREE.Vector3(current.x, current.y, current.z).sub(center);
      // Degenerate only if the camera sits exactly on the centre; fall back to
      // the library's default viewing axis rather than producing NaN.
      if (axis.lengthSq() === 0) axis.set(0, 0, 1);
      axis.normalize();

      // Screen right/up in world space. camera.up is what OrbitControls keeps
      // the camera rolled against, so the basis matches what gets rendered.
      const right = new THREE.Vector3().crossVectors(camera.up, axis);
      if (right.lengthSq() < 1e-8) right.set(1, 0, 0);
      right.normalize();
      const up = new THREE.Vector3().crossVectors(axis, right).normalize();

      const tanV = Math.tan(((camera.fov * Math.PI) / 180) / 2);
      const tanH = tanV * (rect.width / rect.height);

      // A node at screen offset `off` and depth `depth` along the view axis is
      // inside the frustum when distance >= depth + off / tan(halfFov). Take
      // the binding node on each axis.
      const offset = new THREE.Vector3();
      let distance = 0;
      nodes.forEach(node => {
        const scale = node.isCenter ? CENTER_SCALE : NODE_SCALE;
        // Sphere mesh and label sprite both stick out past the node centre.
        const padH = scale * Math.max(BASE_RADIUS, this.labelBudget.maxWidth / 2);
        const padV = scale * (BASE_RADIUS + LABEL_GAP + this.labelBudget.height / 2);
        offset.set(node.x || 0, node.y || 0, node.z || 0).sub(center);
        const depth = offset.dot(axis);
        distance = Math.max(
          distance,
          depth + (Math.abs(offset.dot(right)) + padH) / tanH,
          depth + (Math.abs(offset.dot(up)) + padV) / tanV,
        );
      });

      distance = Math.max(distance * FIT_MARGIN, this.graph.controls().minDistance || 0);
      // Keep the zoom-out ceiling in step with the graph's current extent —
      // it grows as expandNode() adds more nodes, rather than staying fixed
      // at whatever it was on initial load.
      this.graph.controls().maxDistance = distance * MAX_DISTANCE_FACTOR;
      axis.setLength(distance).add(center);
      this.graph.cameraPosition({ x: axis.x, y: axis.y, z: axis.z }, center, durationMs);
    },
    syncSize() {
      const rect = this.$refs.container.getBoundingClientRect();
      if (!this.graph || !rect.width || !rect.height) return;
      const sizeChanged = rect.width !== this.lastSyncedWidth || rect.height !== this.lastSyncedHeight;
      this.graph.width(rect.width).height(rect.height);
      if (!sizeChanged) return;
      this.lastSyncedWidth = rect.width;
      this.lastSyncedHeight = rect.height;
      // The container can go through several intermediate sizes in quick
      // succession (fullscreen flex layout settling, mobile browser chrome
      // animating away) before landing on its final size. Debounce so we only
      // ever fit against the size that actually sticks, and wait a frame past
      // that so the renderer has committed the matching camera aspect ratio
      // before we compute the fit against it.
      clearTimeout(this.zoomToFitTimer);
      this.zoomToFitTimer = setTimeout(() => {
        requestAnimationFrame(() => this.fitView(0));
      }, 150);
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

      const center = { id: title, isCenter: true };
      const leaves = linkTitles.map(id => ({ id }));
      // Place deterministically rather than leaving it to the physics
      // simulation: the center always sits at the origin fitView frames
      // around, and leaves are spaced evenly on a sphere at LINK_DISTANCE —
      // so the graph is already in its final layout before the first paint.
      pinNodeAt(center, { x: 0, y: 0, z: 0 });
      sphereLayout({ x: 0, y: 0, z: 0 }, leaves.length, LINK_DISTANCE, this.currentViewAxis())
        .forEach((pos, i) => pinNodeAt(leaves[i], pos));

      const nodes = [center, ...leaves];
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
      // Positions are already final (pinned above), so frame them right now
      // instead of waiting a frame for onEngineStop to fire.
      this.fitView(this.zoomToFitDuration);
    },
    // The recentering node is already pinned (every node always is); this
    // just manually tweens that pin from its last known position to the
    // origin — a fully controlled, eased move — instead of snapping straight
    // there the instant setGraphData() re-pins it, which read as a "jump".
    animateRecenterMove(nodeId, fromPosition) {
      const liveNode = this.graph.graphData().nodes.find(n => n.id === nodeId);
      if (!liveNode) return;
      if (this.reducedMotion) {
        pinNodeAt(liveNode, { x: 0, y: 0, z: 0 });
        return;
      }
      pinNodeAt(liveNode, fromPosition);
      tween(TRANSITION_MS, (t) => {
        pinNodeAt(liveNode, {
          x: fromPosition.x * (1 - t),
          y: fromPosition.y * (1 - t),
          z: fromPosition.z * (1 - t),
        });
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
        const newTitles = linkTitles.filter(title => !existingIds.has(title));
        // Place new leaves around the expanded node's own (already pinned)
        // position, same as any other leaf — deterministic, no simulation.
        const origin = { x: node.x || 0, y: node.y || 0, z: node.z || 0 };
        sphereLayout(origin, newTitles.length, LINK_DISTANCE, this.currentViewAxis()).forEach((pos, i) => {
          const leaf = { id: newTitles[i] };
          pinNodeAt(leaf, pos);
          nodes.push(leaf);
          existingIds.add(newTitles[i]);
        });
        linkTitles.forEach(title => {
          if (!links.some(l => (l.source.id ?? l.source) === node.id && (l.target.id ?? l.target) === title)) {
            links.push({ source: node.id, target: title });
          }
        });
        this.graph.graphData({ nodes, links });
        this.listNodes = nodes;
        this.fitView(this.zoomToFitDuration);
        const added = newTitles.length;
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
