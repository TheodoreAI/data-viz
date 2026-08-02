import { createApp } from 'vue';
import MoviesFeed from '../components/MoviesFeed.vue';

const el = document.getElementById('app');
const data = JSON.parse(document.getElementById('movies-data').textContent);

createApp(MoviesFeed, { initialFilms: data.films, genres: data.genres }).mount(el);