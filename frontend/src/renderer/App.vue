<template>
  <div id="app" class="min-h-screen bg-gray-50">
    <div class="container mx-auto px-4 py-6">
      <header class="mb-8">
        <h1 class="text-3xl font-bold text-gray-900 mb-2">
          웹 접근성 검사 도구
        </h1>
        <p class="text-gray-600">
          웹사이트의 접근성을 종합적으로 분석하고 개선 가이드를 제공합니다.
        </p>
      </header>

      <main>
        <router-view />
      </main>
    </div>

    <!-- 글로벌 로딩 오버레이 -->
    <div
      v-if="isLoading"
      class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
    >
      <div class="bg-white rounded-lg p-6 max-w-sm w-full mx-4">
        <div class="text-center">
          <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <h3 class="text-lg font-semibold mb-2">접근성 검사 중...</h3>
          <p class="text-gray-600 mb-4">{{ loadingMessage }}</p>
          <div class="w-full bg-gray-200 rounded-full h-2">
            <div 
              class="bg-blue-600 h-2 rounded-full transition-all duration-300"
              :style="{ width: `${progress}%` }"
            ></div>
          </div>
          <p class="text-sm text-gray-500 mt-2">{{ progress }}% 완료</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useCheckerStore } from '@/stores/checker'

const checkerStore = useCheckerStore()

const isLoading = computed(() => checkerStore.isChecking)
const loadingMessage = computed(() => checkerStore.currentStep)
const progress = computed(() => checkerStore.progress)
</script>

<style>
#app {
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}

/* 스크롤바 스타일링 */
::-webkit-scrollbar {
  width: 8px;
}

::-webkit-scrollbar-track {
  background: #f1f1f1;
}

::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 4px;
}

::-webkit-scrollbar-thumb:hover {
  background: #a8a8a8;
}

/* 트랜지션 */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* 접근성 포커스 스타일 */
*:focus {
  outline: 2px solid #3b82f6;
  outline-offset: 2px;
}

/* 고대비 모드 지원 */
@media (prefers-contrast: high) {
  .bg-gray-50 {
    background-color: white;
  }
  
  .text-gray-600 {
    color: black;
  }
  
  .border-gray-200 {
    border-color: black;
  }
}

/* 다크모드 지원 */
@media (prefers-color-scheme: dark) {
  .bg-gray-50 {
    background-color: #1f2937;
  }
  
  .text-gray-900 {
    color: white;
  }
  
  .text-gray-600 {
    color: #d1d5db;
  }
  
  .bg-white {
    background-color: #374151;
  }
}
</style>