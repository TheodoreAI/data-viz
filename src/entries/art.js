import { createApp } from 'vue';
import ArtFeed from '../components/ArtFeed.vue';

const el = document.getElementById('app');
const data = JSON.parse(document.getElementById('art-data').textContent);

createApp(ArtFeed, { initialPaintings: data.paintings, movements: data.movements }).mount(el);