<template>
  <div class="space-y-6">
    <!-- URL 입력 섹션 -->
    <section class="card" aria-labelledby="url-input-heading">
      <div class="card-header">
        <h2 id="url-input-heading" class="text-xl font-semibold text-gray-900">
          웹사이트 URL 입력
        </h2>
      </div>
      <div class="card-body">
        <form @submit.prevent="handleSubmit" class="space-y-4">
          <div>
            <label for="url-input" class="form-label">
              검사할 웹사이트 URL
            </label>
            <input
              id="url-input"
              v-model="url"
              type="url"
              class="form-input"
              placeholder="https://example.com"
              required
              :disabled="isChecking"
              aria-describedby="url-help"
            />
            <p id="url-help" class="mt-2 text-sm text-gray-500">
              접근성을 검사할 웹사이트의 완전한 URL을 입력해주세요.
            </p>
          </div>
          
          <div class="flex items-center justify-between">
            <button
              type="button"
              @click="showAdvancedOptions = !showAdvancedOptions"
              class="text-sm text-blue-600 hover:text-blue-500"
              :aria-expanded="showAdvancedOptions"
              aria-controls="advanced-options"
            >
              고급 옵션 {{ showAdvancedOptions ? '숨기기' : '보기' }}
            </button>
            
            <button
              type="submit"
              class="btn btn-primary"
              :disabled="!url || isChecking"
              :aria-describedby="isChecking ? 'checking-status' : undefined"
            >
              <span v-if="!isChecking">검사 시작</span>
              <span v-else>검사 중...</span>
            </button>
          </div>
        </form>
        
        <!-- 고급 옵션 -->
        <div
          id="advanced-options"
          v-show="showAdvancedOptions"
          class="mt-6 pt-6 border-t border-gray-200"
        >
          <h3 class="text-lg font-medium text-gray-900 mb-4">검사 옵션</h3>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <label class="flex items-center">
              <input
                v-model="options.enable_aria_check"
                type="checkbox"
                class="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <span class="ml-2 text-sm text-gray-700">WAI-ARIA 검사</span>
            </label>
            
            <label class="flex items-center">
              <input
                v-model="options.enable_semantic_check"
                type="checkbox"
                class="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <span class="ml-2 text-sm text-gray-700">시멘틱 HTML 검사</span>
            </label>
            
            <label class="flex items-center">
              <input
                v-model="options.enable_image_check"
                type="checkbox"
                class="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <span class="ml-2 text-sm text-gray-700">이미지 접근성 검사</span>
            </label>
            
            <label class="flex items-center">
              <input
                v-model="options.enable_media_check"
                type="checkbox"
                class="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <span class="ml-2 text-sm text-gray-700">미디어 접근성 검사</span>
            </label>
            
            <label class="flex items-center">
              <input
                v-model="options.enable_visual_check"
                type="checkbox"
                class="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <span class="ml-2 text-sm text-gray-700">시각적 요소 검사</span>
            </label>
            
            <label class="flex items-center">
              <input
                v-model="options.include_screenshots"
                type="checkbox"
                class="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <span class="ml-2 text-sm text-gray-700">스크린샷 포함</span>
            </label>
          </div>
          
          <div class="mt-4">
            <label for="wait-time" class="form-label">
              페이지 로딩 대기 시간 (초)
            </label>
            <input
              id="wait-time"
              v-model.number="options.wait_time"
              type="number"
              min="1"
              max="30"
              class="form-input max-w-xs"
            />
          </div>
        </div>
      </div>
    </section>

    <!-- 최근 검사 결과 -->
    <section v-if="hasResults" class="card" aria-labelledby="recent-results-heading">
      <div class="card-header">
        <h2 id="recent-results-heading" class="text-xl font-semibold text-gray-900">
          최근 검사 결과
        </h2>
      </div>
      <div class="card-body">
        <div class="space-y-4">
          <div
            v-for="result in checkResults.slice(0, 5)"
            :key="result.checked_at"
            class="flex items-center justify-between p-4 border border-gray-200 rounded-lg hover:bg-gray-50"
          >
            <div class="flex-1">
              <h3 class="font-medium text-gray-900 truncate">
                {{ result.url }}
              </h3>
              <p class="text-sm text-gray-500">
                {{ formatDate(result.checked_at) }} · 
                검사 시간: {{ Math.round(result.check_duration) }}초
              </p>
            </div>
            <div class="flex items-center space-x-4">
              <div class="text-right">
                <div class="text-lg font-semibold" :class="getScoreColor(result.total_score)">
                  {{ result.total_score }}점
                </div>
                <div class="text-sm text-gray-500">
                  {{ result.summary.overall_grade }} 등급
                </div>
              </div>
              <button
                @click="viewResult(result)"
                class="btn btn-secondary btn-sm"
                aria-label="검사 결과 자세히 보기"
              >
                보기
              </button>
            </div>
          </div>
        </div>
        
        <div v-if="checkResults.length > 5" class="mt-4 text-center">
          <button
            @click="$router.push('/report')"
            class="text-blue-600 hover:text-blue-500 text-sm"
          >
            모든 결과 보기 ({{ checkResults.length }}개)
          </button>
        </div>
      </div>
    </section>

    <!-- 사용법 안내 -->
    <section v-if="!hasResults" class="card" aria-labelledby="guide-heading">
      <div class="card-header">
        <h2 id="guide-heading" class="text-xl font-semibold text-gray-900">
          사용법 안내
        </h2>
      </div>
      <div class="card-body">
        <div class="prose prose-sm max-w-none">
          <ol class="list-decimal list-inside space-y-2">
            <li>검사할 웹사이트의 완전한 URL을 입력하세요.</li>
            <li>필요에 따라 고급 옵션을 조정하세요.</li>
            <li>"검사 시작" 버튼을 클릭하여 접근성 검사를 시작하세요.</li>
            <li>검사가 완료되면 상세한 결과와 개선 가이드를 확인할 수 있습니다.</li>
          </ol>
          
          <div class="mt-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
            <h3 class="font-medium text-blue-900 mb-2">💡 팁</h3>
            <ul class="text-blue-800 text-sm space-y-1">
              <li>• 검사 결과는 WCAG 2.1 가이드라인을 기준으로 평가됩니다.</li>
              <li>• 복잡한 웹사이트는 검사 시간이 더 오래 걸릴 수 있습니다.</li>
              <li>• 검사 결과를 JSON, HTML, PDF 형식으로 내보낼 수 있습니다.</li>
            </ul>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useCheckerStore, type CheckOptions, type CheckResult } from '@/stores/checker'

const router = useRouter()
const checkerStore = useCheckerStore()

// State
const url = ref('')
const showAdvancedOptions = ref(false)
const options = ref<CheckOptions>({ ...checkerStore.defaultOptions })

// Computed
const isChecking = computed(() => checkerStore.isChecking)
const hasResults = computed(() => checkerStore.hasResults)
const checkResults = computed(() => checkerStore.checkResults)

// Methods
const handleSubmit = async () => {
  if (!url.value) return
  
  try {
    await checkerStore.startCheck(url.value, options.value)
    // 검사 완료 후 결과 페이지로 이동
    router.push('/report')
  } catch (error) {
    console.error('검사 실패:', error)
    alert('검사 중 오류가 발생했습니다. 다시 시도해주세요.')
  }
}

const viewResult = (result: CheckResult) => {
  checkerStore.currentResult = result
  router.push(`/report/${result.checked_at}`)
}

const formatDate = (dateString: string) => {
  const date = new Date(dateString)
  return date.toLocaleString('ko-KR', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

const getScoreColor = (score: number) => {
  if (score >= 90) return 'text-green-600'
  if (score >= 80) return 'text-blue-600'
  if (score >= 70) return 'text-yellow-600'
  if (score >= 60) return 'text-orange-600'
  return 'text-red-600'
}
</script>