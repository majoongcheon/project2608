import { createApp } from 'vue';
import { createPinia } from 'pinia';
import App from './App.vue';
import { router } from './router';
import './assets/tokens.css';
// 디자인 템플릿 = claude · 편지 톤(DESIGN.claude.md). tokens.css 뒤에 와야 한다.
// 이 줄을 지우면 기반인 Airbnb(DESIGN.md · tokens.css)만 남는다.
import './assets/theme-claude.css';
// 에디토리얼 레이어(2026-09-03 개편) — 큰 활자·넓은 여백·스크롤 등장.
// theme-claude.css 뒤에 와야 한다. 이 줄을 지우면 편지 톤 그대로 돌아간다.
import './assets/theme-editorial.css';

createApp(App).use(createPinia()).use(router).mount('#app');
