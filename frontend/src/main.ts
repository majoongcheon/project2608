import { createApp } from 'vue';
import { createPinia } from 'pinia';
import App from './App.vue';
import { router } from './router';
import './assets/tokens.css';
// 디자인 템플릿 = Notion(DESIGN.notion.md). tokens.css 뒤에 와야 한다.
// 이 줄을 지우면 Airbnb(DESIGN.md)로 돌아간다.
import './assets/theme-notion.css';

createApp(App).use(createPinia()).use(router).mount('#app');
