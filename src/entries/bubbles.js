import { createApp } from 'vue';
import BubbleChart from '../components/BubbleChart.vue';

const el = document.getElementById('app');
const data = JSON.parse(document.getElementById('chart-data').textContent);

createApp(BubbleChart, { articles: data.articles, date: data.date }).mount(el);