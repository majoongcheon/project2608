import { createRouter, createWebHistory } from 'vue-router';

export const router = createRouter({
  history: createWebHistory(),
  scrollBehavior: () => ({ top: 0 }),
  routes: [
    { path: '/', name: 'home', component: () => import('../pages/HomePage.vue') },
    { path: '/diagnosis/start', name: 'presurvey', component: () => import('../pages/PreSurveyPage.vue') },
    { path: '/diagnosis/survey', name: 'survey', component: () => import('../pages/SurveyPage.vue') },
    { path: '/diagnosis/consent', name: 'consent', component: () => import('../pages/ConsentPage.vue') },
    { path: '/diagnosis/result', name: 'result', component: () => import('../pages/ResultPage.vue') },
    { path: '/map', name: 'map', component: () => import('../pages/MapPage.vue') },
    { path: '/facility/:id', name: 'facility', component: () => import('../pages/FacilityDetailPage.vue') },
    // 2026-09-03 — 방 셋을 더 두었다. 홈 메뉴의 03·04·05 와 번호를 맞춘다.
    { path: '/talk', name: 'talk', component: () => import('../pages/TalkPage.vue') },
    { path: '/reviews', name: 'reviews', component: () => import('../pages/ReviewPage.vue') },
    { path: '/me', name: 'me', component: () => import('../pages/MyPage.vue') },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
});
