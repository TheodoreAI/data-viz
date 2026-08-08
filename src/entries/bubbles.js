import { createApp } from 'vue';
import LiveDataTabs from '../components/LiveDataTabs.vue';

const el = document.getElementById('app');
const data = JSON.parse(document.getElementById('chart-data').textContent);

createApp(LiveDataTabs, { initialArticles: data.articles, initialDate: data.date }).mount(el);
