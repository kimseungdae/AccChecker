# 웹 접근성 검사 도구 (Web Accessibility Checker)

웹 콘텐츠의 접근성을 종합적으로 검사하는 데스크톱 애플리케이션입니다. Python 백엔드와 Electron 프론트엔드를 활용하여 WCAG 2.1 가이드라인을 기준으로 웹사이트의 접근성을 자동으로 분석하고 개선 가이드를 제공합니다.

## 주요 기능

### 🔍 종합적인 접근성 검사
- **WAI-ARIA 검사**: aria-label, role 속성, 키보드 접근성 등
- **시멘틱 HTML 검사**: 제목 계층구조, 폼 구조, 테이블 접근성 등
- **이미지 접근성**: alt 텍스트 품질, 장식용 이미지 구분, 복잡한 이미지 설명
- **미디어 접근성**: 비디오 자막, 오디오 대본, 미디어 컨트롤
- **시각적 접근성**: 색상 대비, 텍스트 크기, 포커스 표시

### 📊 직관적인 결과 표시
- 100점 만점 점수 시스템
- 카테고리별 상세 점수
- 심각도별 이슈 분류
- WCAG 참조 표준 제시

### 📁 다양한 내보내기 형식
- JSON (프로그래밍 연동용)
- HTML (웹 보기용)
- PDF (보고서용)

## 기술 스택

### 백엔드 (Python)
- **FastAPI**: 고성능 웹 API 프레임워크
- **BeautifulSoup4**: HTML 파싱 및 분석
- **Selenium**: 브라우저 자동화 및 동적 콘텐츠 검사
- **Pydantic**: 데이터 검증 및 모델링

### 프론트엔드 (Electron + Vue.js)
- **Electron**: 크로스플랫폼 데스크톱 애플리케이션
- **Vue.js 3**: 모던 JavaScript 프레임워크
- **TypeScript**: 타입 안전성
- **Tailwind CSS**: 유틸리티 우선 CSS 프레임워크
- **Pinia**: 상태 관리

## 설치 및 실행

### 요구 사항
- Python 3.8+
- Node.js 16+
- Chrome 브라우저 (Selenium WebDriver용)

### 백엔드 설정
```bash
# 의존성 설치
pip install -r requirements.txt

# 서버 실행
cd src
python main.py
```

### 프론트엔드 설정
```bash
# 의존성 설치
cd frontend
npm install

# 개발 모드 실행
npm run electron-dev

# 프로덕션 빌드
npm run build
npm run electron-pack
```

## 사용법

1. **URL 입력**: 검사할 웹사이트의 URL을 입력합니다.
2. **옵션 설정**: 필요에 따라 검사 옵션을 조정합니다.
3. **검사 실행**: "검사 시작" 버튼을 클릭합니다.
4. **결과 확인**: 점수와 상세 이슈 목록을 확인합니다.
5. **결과 내보내기**: 필요한 형식으로 결과를 내보냅니다.

## 검사 항목

### WAI-ARIA 검사
- aria-label, aria-labelledby 적절성
- role 속성 정확성 및 필수 속성 확인
- landmark roles 존재 여부
- 키보드 네비게이션 순서

### 시멘틱 HTML 검사
- 제목 태그(h1-h6) 계층 구조
- 폼 요소 label 연결
- 테이블 구조 및 caption
- 리스트 구조 적절성

### 이미지 접근성 검사
- img 태그 alt 속성 존재 및 품질
- 장식용 이미지 적절한 처리
- 복잡한 이미지 상세 설명
- 배경 이미지 대체 텍스트

### 미디어 접근성 검사
- 비디오 자막 제공 여부
- 오디오 대본 제공 여부
- 자동재생 설정 검사
- 미디어 컨트롤 접근성

### 시각적 접근성 검사
- 색상 대비율 (WCAG AA/AAA 기준)
- 색상만으로 정보 전달 금지
- 텍스트 간격 및 크기
- 포커스 표시 가시성

## 점수 계산 시스템

각 카테고리별 가중치:
- WAI-ARIA: 25%
- 시멘틱 HTML: 20%
- 이미지 접근성: 15%
- 미디어 접근성: 15%
- 시각적 접근성: 10%
- 키보드 네비게이션: 15%

심각도별 감점:
- 치명적: -10~20점
- 높음: -5~10점
- 보통: -2~5점
- 낮음: -1~2점

## 개발 가이드

### 새로운 검사 모듈 추가
1. `src/checkers/` 디렉토리에 새 검사기 클래스 생성
2. `AccessibilityChecker` 인터페이스 구현
3. `core/accessibility_checker.py`에 새 검사기 등록

### 프론트엔드 컴포넌트 추가
1. `frontend/src/components/` 디렉토리에 컴포넌트 생성
2. TypeScript 타입 정의
3. Tailwind CSS 스타일링 적용

## 라이선스

MIT License

## 기여하기

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 지원

문제가 발생했거나 제안사항이 있으시면 GitHub Issues를 통해 알려주세요.