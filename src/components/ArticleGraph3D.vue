<script>
import ForceGraph3D from '3d-force-graph';

const MAX_PIXEL_RATIO = 2;

export default {
  name: 'ArticleGraph3D',
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
    };
  },
  mounted() {
    this.linksCache = {};
    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    this.graph = ForceGraph3D()(this.$refs.container)
      .backgroundColor('#00000000')
      .nodeLabel(node => node.id)
      .nodeColor(node => (node.isCenter ? '#b8935a' : '#2f6690'))
      .nodeRelSize(5)
      .linkColor(() => 'rgba(116, 128, 74, 0.6)')
      .linkWidth(1)
      .cooldownTicks(reducedMotion ? 0 : 200)
      .onNodeClick(node => this.expandNode(node));

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
    async expandNode(node) {
      if (node.isCenter) {
        this.$emit('select', node.id);
        return;
      }
      if (this.loadingNodeId) return;
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
      :aria-label="`3D force graph centered on ${seedTitle}, with ${listNodes.length - 1} linked articles. Use the list view for keyboard access.`"
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
