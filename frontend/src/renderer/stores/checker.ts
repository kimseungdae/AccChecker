import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export interface CheckOptions {
  enable_aria_check: boolean
  enable_semantic_check: boolean
  enable_image_check: boolean
  enable_media_check: boolean
  enable_visual_check: boolean
  include_screenshots: boolean
  wait_time: number
}

export interface CheckResult {
  url: string
  total_score: number
  category_scores: Record<string, CategoryScore>
  issues: AccessibilityIssue[]
  summary: Record<string, any>
  checked_at: string
  check_duration: number
}

export interface CategoryScore {
  category: string
  score: number
  max_score: number
  issues_count: number
  passed_checks: number
  total_checks: number
}

export interface AccessibilityIssue {
  type: string
  severity: 'low' | 'medium' | 'high' | 'critical'
  message: string
  description: string
  element?: string
  line_number?: number
  recommendation: string
  wcag_reference?: string
}

export const useCheckerStore = defineStore('checker', () => {
  // State
  const isChecking = ref(false)
  const currentStep = ref('')
  const progress = ref(0)
  const checkResults = ref<CheckResult[]>([])
  const currentResult = ref<CheckResult | null>(null)
  const defaultOptions = ref<CheckOptions>({
    enable_aria_check: true,
    enable_semantic_check: true,
    enable_image_check: true,
    enable_media_check: true,
    enable_visual_check: true,
    include_screenshots: false,
    wait_time: 5
  })

  // Getters
  const hasResults = computed(() => checkResults.value.length > 0)
  const latestResult = computed(() => 
    checkResults.value.length > 0 ? checkResults.value[0] : null
  )

  // Actions
  const startCheck = async (url: string, options?: Partial<CheckOptions>) => {
    try {
      isChecking.value = true
      progress.value = 0
      currentStep.value = '검사 준비 중...'
      
      const checkOptions = { ...defaultOptions.value, ...options }
      
      // 진행 상황 시뮬레이션
      const steps = [
        { message: '페이지 로딩 중...', progress: 10 },
        { message: 'HTML 구조 분석 중...', progress: 20 },
        { message: 'ARIA 속성 검사 중...', progress: 40 },
        { message: '시멘틱 구조 검사 중...', progress: 60 },
        { message: '이미지 접근성 검사 중...', progress: 80 },
        { message: '결과 정리 중...', progress: 95 }
      ]

      // IPC를 통해 메인 프로세스에 검사 요청
      const { ipcRenderer } = window.require('electron')
      
      // 진행 상황 업데이트
      for (const step of steps) {
        currentStep.value = step.message
        progress.value = step.progress
        await new Promise(resolve => setTimeout(resolve, 500))
      }

      const result = await ipcRenderer.invoke('check-accessibility', url, checkOptions)
      
      progress.value = 100
      currentStep.value = '검사 완료!'
      
      // 결과 저장
      addResult(result)
      currentResult.value = result

      return result
      
    } catch (error) {
      console.error('접근성 검사 실패:', error)
      throw error
    } finally {
      setTimeout(() => {
        isChecking.value = false
        currentStep.value = ''
        progress.value = 0
      }, 1000)
    }
  }

  const addResult = (result: CheckResult) => {
    checkResults.value.unshift(result)
    
    // 최대 10개의 결과만 보관
    if (checkResults.value.length > 10) {
      checkResults.value = checkResults.value.slice(0, 10)
    }
  }

  const getResultById = (id: string): CheckResult | null => {
    return checkResults.value.find(result => 
      result.checked_at === id
    ) || null
  }

  const clearResults = () => {
    checkResults.value = []
    currentResult.value = null
  }

  const updateOptions = (options: Partial<CheckOptions>) => {
    defaultOptions.value = { ...defaultOptions.value, ...options }
  }

  const exportResult = async (result: CheckResult, format: 'json' | 'html' | 'pdf') => {
    try {
      const { ipcRenderer } = window.require('electron')
      
      switch (format) {
        case 'json':
          await ipcRenderer.invoke('export-json', result)
          break
        case 'html':
          await ipcRenderer.invoke('export-html', result)
          break
        case 'pdf':
          await ipcRenderer.invoke('export-pdf', result)
          break
        default:
          throw new Error('지원하지 않는 내보내기 형식입니다.')
      }
    } catch (error) {
      console.error('결과 내보내기 실패:', error)
      throw error
    }
  }

  return {
    // State
    isChecking,
    currentStep,
    progress,
    checkResults,
    currentResult,
    defaultOptions,
    
    // Getters
    hasResults,
    latestResult,
    
    // Actions
    startCheck,
    addResult,
    getResultById,
    clearResults,
    updateOptions,
    exportResult
  }
})