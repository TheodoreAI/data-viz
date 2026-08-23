import { createApp } from 'vue';
import JogTracker from '../components/JogTracker.vue';

document.body.classList.add('uv-index-page');

createApp(JogTracker).mount(document.getElementById('app'));
