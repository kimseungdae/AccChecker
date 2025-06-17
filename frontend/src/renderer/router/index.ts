import { createRouter, createWebHistory } from 'vue-router'
import CheckerView from '@/views/CheckerView.vue'
import ReportView from '@/views/ReportView.vue'

const routes = [
  {
    path: '/',
    name: 'Checker',
    component: CheckerView,
    meta: {
      title: '접근성 검사'
    }
  },
  {
    path: '/report/:id?',
    name: 'Report',
    component: ReportView,
    meta: {
      title: '검사 결과'
    }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 페이지 제목 설정
router.beforeEach((to, from, next) => {
  document.title = `${to.meta.title} - 웹 접근성 검사 도구`
  next()
})

export default router