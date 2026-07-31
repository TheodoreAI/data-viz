import { createApp } from 'vue';
import ArticleGraph from '../components/ArticleGraph.vue';

const el = document.getElementById('app');
const data = JSON.parse(document.getElementById('graph-data').textContent);

createApp(ArticleGraph, { seedTitle: data.title, seedLinks: data.links }).mount(el);