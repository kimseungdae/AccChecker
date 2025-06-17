<template>
  <div v-if="currentResult" class="space-y-6">
    <!-- 결과 헤더 -->
    <section class="card" aria-labelledby="result-header">
      <div class="card-header">
        <div class="flex items-center justify-between">
          <h1 id="result-header" class="text-2xl font-bold text-gray-900">
            접근성 검사 결과
          </h1>
          <div class="flex space-x-2">
            <button
              @click="exportResult('json')"
              class="btn btn-secondary btn-sm"
              aria-label="JSON 형식으로 내보내기"
            >
              JSON 내보내기
            </button>
            <button
              @click="exportResult('html')"
              class="btn btn-secondary btn-sm"
              aria-label="HTML 형식으로 내보내기"
            >
              HTML 내보내기
            </button>
            <button
              @click="startNewCheck"
              class="btn btn-primary btn-sm"
            >
              새 검사
            </button>
          </div>
        </div>
      </div>
      <div class="card-body">
        <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
          <!-- 총점 -->
          <div class="text-center">
            <div class="text-4xl font-bold mb-2" :class="getScoreColor(currentResult.total_score)">
              {{ currentResult.total_score }}점
            </div>
            <div class="text-lg text-gray-600">
              {{ currentResult.summary.overall_grade }} 등급
            </div>
            <div class="text-sm text-gray-500 mt-1">
              검사 시간: {{ Math.round(currentResult.check_duration) }}초
            </div>
          </div>
          
          <!-- 사이트 정보 -->
          <div class="md:col-span-2">
            <h3 class="font-semibold text-gray-900 mb-2">검사 대상</h3>
            <div class="space-y-2 text-sm">
              <div>
                <span class="font-medium">URL:</span>
                <a :href="currentResult.url" target="_blank" class="text-blue-600 hover:underline ml-2">
                  {{ currentResult.url }}
                </a>
              </div>
              <div>
                <span class="font-medium">검사 일시:</span>
                <span class="ml-2">{{ formatDate(currentResult.checked_at) }}</span>
              </div>
              <div>
                <span class="font-medium">발견된 이슈:</span>
                <span class="ml-2">{{ currentResult.issues.length }}개</span>
                <span class="text-red-600 ml-2">(치명적: {{ getCriticalIssueCount() }}개)</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- 카테고리별 점수 -->
    <section class="card" aria-labelledby="category-scores-heading">
      <div class="card-header">
        <h2 id="category-scores-heading" class="text-xl font-semibold text-gray-900">
          카테고리별 점수
        </h2>
      </div>
      <div class="card-body">
        <div class="space-y-4">
          <div
            v-for="(score, category) in currentResult.category_scores"
            :key="category"
            class="flex items-center justify-between p-4 border border-gray-200 rounded-lg"
          >
            <div class="flex-1">
              <h3 class="font-medium text-gray-900">{{ getCategoryName(category) }}</h3>
              <p class="text-sm text-gray-500">
                {{ score.passed_checks }}/{{ score.total_checks }} 검사 통과
                · {{ score.issues_count }}개 이슈
              </p>
            </div>
            <div class="flex items-center space-x-4">
              <div class="w-32 bg-gray-200 rounded-full h-2">
                <div
                  class="h-2 rounded-full transition-all duration-300"
                  :class="getScoreBarColor(score.score)"
                  :style="{ width: `${score.score}%` }"
                ></div>
              </div>
              <div class="text-lg font-semibold w-16 text-right" :class="getScoreColor(score.score)">
                {{ score.score }}점
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- 이슈 목록 -->
    <section class="card" aria-labelledby="issues-heading">
      <div class="card-header">
        <div class="flex items-center justify-between">
          <h2 id="issues-heading" class="text-xl font-semibold text-gray-900">
            발견된 이슈 ({{ filteredIssues.length }}개)
          </h2>
          <div class="flex space-x-2">
            <!-- 심각도 필터 -->
            <select
              v-model="selectedSeverity"
              class="form-input text-sm"
              aria-label="심각도별 필터"
            >
              <option value="">모든 심각도</option>
              <option value="critical">치명적</option>
              <option value="high">높음</option>
              <option value="medium">보통</option>
              <option value="low">낮음</option>
            </select>
            
            <!-- 카테고리 필터 -->
            <select
              v-model="selectedCategory"
              class="form-input text-sm"
              aria-label="카테고리별 필터"
            >
              <option value="">모든 카테고리</option>
              <option value="aria">WAI-ARIA</option>
              <option value="semantic">시멘틱</option>
              <option value="image">이미지</option>
              <option value="media">미디어</option>
              <option value="visual">시각적</option>
            </select>
          </div>
        </div>
      </div>
      <div class="card-body">
        <div v-if="filteredIssues.length === 0" class="text-center py-8">
          <p class="text-gray-500">해당 조건에 맞는 이슈가 없습니다.</p>
        </div>
        
        <div v-else class="space-y-4">
          <div
            v-for="(issue, index) in filteredIssues"
            :key="index"
            class="border border-gray-200 rounded-lg p-4 hover:bg-gray-50"
          >
            <!-- 이슈 헤더 -->
            <div class="flex items-start justify-between mb-3">
              <div class="flex-1">
                <div class="flex items-center space-x-2 mb-1">
                  <span
                    class="badge"
                    :class="getSeverityBadgeClass(issue.severity)"
                  >
                    {{ getSeverityLabel(issue.severity) }}
                  </span>
                  <span class="badge badge-info">
                    {{ getCategoryName(issue.type) }}
                  </span>
                  <span v-if="issue.wcag_reference" class="text-xs text-gray-500">
                    {{ issue.wcag_reference }}
                  </span>
                </div>
                <h3 class="font-medium text-gray-900">{{ issue.message }}</h3>
              </div>
              <button
                @click="toggleIssueDetails(index)"
                class="text-gray-400 hover:text-gray-600"
                :aria-expanded="expandedIssues.has(index)"
                :aria-controls="`issue-details-${index}`"
                aria-label="이슈 세부사항 토글"
              >
                <svg class="w-5 h-5 transform transition-transform" :class="{ 'rotate-180': expandedIssues.has(index) }" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path>
                </svg>
              </button>
            </div>
            
            <!-- 이슈 설명 -->
            <p class="text-gray-700 mb-3">{{ issue.description }}</p>
            
            <!-- 개선 권장사항 -->
            <div class="bg-blue-50 border border-blue-200 rounded p-3 mb-3">
              <h4 class="font-medium text-blue-900 mb-1">개선 권장사항</h4>
              <p class="text-blue-800 text-sm">{{ issue.recommendation }}</p>
            </div>
            
            <!-- 세부사항 (토글) -->
            <div
              v-if="expandedIssues.has(index)"
              :id="`issue-details-${index}`"
              class="border-t border-gray-200 pt-3 mt-3"
            >
              <div v-if="issue.element" class="mb-3">
                <h4 class="font-medium text-gray-900 mb-1">관련 HTML 요소</h4>
                <pre class="bg-gray-100 p-2 rounded text-xs overflow-x-auto"><code>{{ issue.element }}</code></pre>
              </div>
              
              <div v-if="issue.line_number" class="mb-3">
                <h4 class="font-medium text-gray-900 mb-1">위치</h4>
                <p class="text-sm text-gray-600">라인 {{ issue.line_number }}</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- 개선 요약 -->
    <section class="card" aria-labelledby="improvement-summary-heading">
      <div class="card-header">
        <h2 id="improvement-summary-heading" class="text-xl font-semibold text-gray-900">
          개선 요약
        </h2>
      </div>
      <div class="card-body">
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
          <!-- 우선순위 이슈 -->
          <div>
            <h3 class="font-medium text-gray-900 mb-3">우선 해결해야 할 이슈</h3>
            <div class="space-y-2">
              <div
                v-for="issue in priorityIssues"
                :key="issue.message"
                class="flex items-center justify-between p-2 bg-red-50 border border-red-200 rounded"
              >
                <span class="text-sm text-red-800">{{ issue.message }}</span>
                <span class="badge badge-error text-xs">{{ getSeverityLabel(issue.severity) }}</span>
              </div>
            </div>
          </div>
          
          <!-- 카테고리별 개선 포인트 -->
          <div>
            <h3 class="font-medium text-gray-900 mb-3">카테고리별 개선 포인트</h3>
            <div class="space-y-2">
              <div
                v-for="(count, category) in issueCountByCategory"
                :key="category"
                class="flex items-center justify-between p-2 bg-gray-50 border border-gray-200 rounded"
              >
                <span class="text-sm text-gray-700">{{ getCategoryName(category) }}</span>
                <span class="text-sm font-medium">{{ count }}개 이슈</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  </div>
  
  <!-- 결과가 없는 경우 -->
  <div v-else class="text-center py-12">
    <div class="mx-auto w-24 h-24 bg-gray-100 rounded-full flex items-center justify-center mb-4">
      <svg class="w-12 h-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
      </svg>
    </div>
    <h2 class="text-xl font-semibold text-gray-900 mb-2">검사 결과가 없습니다</h2>
    <p class="text-gray-600 mb-4">먼저 웹사이트 접근성 검사를 실행해주세요.</p>
    <button @click="startNewCheck" class="btn btn-primary">
      새 검사 시작
    </button>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useCheckerStore, type AccessibilityIssue } from '@/stores/checker'

const router = useRouter()
const route = useRoute()
const checkerStore = useCheckerStore()

// State
const selectedSeverity = ref('')
const selectedCategory = ref('')
const expandedIssues = ref(new Set<number>())

// Computed
const currentResult = computed(() => {
  if (route.params.id) {
    return checkerStore.getResultById(route.params.id as string)
  }
  return checkerStore.currentResult
})

const filteredIssues = computed(() => {
  if (!currentResult.value) return []
  
  let issues = currentResult.value.issues
  
  if (selectedSeverity.value) {
    issues = issues.filter(issue => issue.severity === selectedSeverity.value)
  }
  
  if (selectedCategory.value) {
    issues = issues.filter(issue => issue.type === selectedCategory.value)
  }
  
  return issues.sort((a, b) => {
    const severityOrder = { critical: 0, high: 1, medium: 2, low: 3 }
    return severityOrder[a.severity] - severityOrder[b.severity]
  })
})

const priorityIssues = computed(() => {
  if (!currentResult.value) return []
  return currentResult.value.issues
    .filter(issue => issue.severity === 'critical' || issue.severity === 'high')
    .slice(0, 5)
})

const issueCountByCategory = computed(() => {
  if (!currentResult.value) return {}
  
  const counts: Record<string, number> = {}
  currentResult.value.issues.forEach(issue => {
    counts[issue.type] = (counts[issue.type] || 0) + 1
  })
  
  return counts
})

// Methods
const getCriticalIssueCount = () => {
  if (!currentResult.value) return 0
  return currentResult.value.issues.filter(issue => issue.severity === 'critical').length
}

const toggleIssueDetails = (index: number) => {
  if (expandedIssues.value.has(index)) {
    expandedIssues.value.delete(index)
  } else {
    expandedIssues.value.add(index)
  }
}

const startNewCheck = () => {
  router.push('/')
}

const exportResult = async (format: 'json' | 'html' | 'pdf') => {
  if (!currentResult.value) return
  
  try {
    await checkerStore.exportResult(currentResult.value, format)
    alert(`${format.toUpperCase()} 파일로 내보내기가 완료되었습니다.`)
  } catch (error) {
    alert('내보내기 중 오류가 발생했습니다.')
  }
}

const formatDate = (dateString: string) => {
  const date = new Date(dateString)
  return date.toLocaleString('ko-KR', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

const getScoreColor = (score: number) => {
  if (score >= 90) return 'text-green-600'
  if (score >= 80) return 'text-blue-600'
  if (score >= 70) return 'text-yellow-600'
  if (score >= 60) return 'text-orange-600'
  return 'text-red-600'
}

const getScoreBarColor = (score: number) => {
  if (score >= 90) return 'bg-green-500'
  if (score >= 80) return 'bg-blue-500'
  if (score >= 70) return 'bg-yellow-500'
  if (score >= 60) return 'bg-orange-500'
  return 'bg-red-500'
}

const getSeverityBadgeClass = (severity: string) => {
  const classes = {
    critical: 'bg-red-100 text-red-800',
    high: 'bg-orange-100 text-orange-800',
    medium: 'bg-yellow-100 text-yellow-800',
    low: 'bg-gray-100 text-gray-800'
  }
  return classes[severity] || classes.low
}

const getSeverityLabel = (severity: string) => {
  const labels = {
    critical: '치명적',
    high: '높음',
    medium: '보통',
    low: '낮음'
  }
  return labels[severity] || severity
}

const getCategoryName = (category: string) => {
  const names = {
    aria: 'WAI-ARIA',
    semantic: '시멘틱 HTML',
    image: '이미지 접근성',
    media: '미디어 접근성',
    visual: '시각적 접근성'
  }
  return names[category] || category
}

// Lifecycle
onMounted(() => {
  // URL 파라미터로 특정 결과 로드
  if (route.params.id && !currentResult.value) {
    router.push('/')
  }
})
</script>