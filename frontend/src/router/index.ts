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
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
});
