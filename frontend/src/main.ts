import { createApp } from 'vue';
import { createPinia } from 'pinia';
import App from './App.vue';
import { router } from './router';
import './assets/tokens.css';
// 디자인 템플릿 = claude · 편지 톤(DESIGN.claude.md). tokens.css 뒤에 와야 한다.
// theme-notion.css 로 바꾸면 Notion, 이 줄을 지우면 Airbnb(DESIGN.md)로 돌아간다.
import './assets/theme-claude.css';

createApp(App).use(createPinia()).use(router).mount('#app');
