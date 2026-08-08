import { createApp } from 'vue';
import TrendingTabs from '../components/TrendingTabs.vue';

const el = document.getElementById('app');
const data = JSON.parse(document.getElementById('chart-data').textContent);

createApp(TrendingTabs, { initialArticles: data.articles, initialDate: data.date }).mount(el);
