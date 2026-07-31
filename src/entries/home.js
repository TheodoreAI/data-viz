import { createApp } from 'vue';
import ArticleFeed from '../components/ArticleFeed.vue';

const el = document.getElementById('app');
const data = JSON.parse(document.getElementById('feed-data').textContent);

createApp(ArticleFeed, { initialArticle: data.article }).mount(el);