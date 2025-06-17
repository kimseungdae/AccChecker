import asyncio
import time
from datetime import datetime
from typing import Dict, List
import logging

from models.report_models import CheckResult, CheckOptions, CategoryScore
from core.browser_automation import BrowserManager
from checkers.aria_checker import AriaChecker
from checkers.semantic_checker import SemanticChecker
from checkers.image_checker import ImageChecker
from checkers.media_checker import MediaChecker
from checkers.visual_checker import VisualChecker
from core.scoring_engine import ScoringEngine

logger = logging.getLogger(__name__)

class AccessibilityChecker:
    def __init__(self):
        self.browser_manager = BrowserManager()
        self.scoring_engine = ScoringEngine()
        self.checkers = {
            'aria': AriaChecker(),
            'semantic': SemanticChecker(),
            'image': ImageChecker(),
            'media': MediaChecker(),
            'visual': VisualChecker()
        }
    
    async def check_website(self, url: str, options: CheckOptions) -> CheckResult:
        """웹사이트의 접근성을 종합적으로 검사합니다."""
        start_time = time.time()
        
        try:
            # 브라우저로 페이지 로드
            driver = await self.browser_manager.get_driver()
            await self.browser_manager.load_page(driver, url, options.wait_time)
            
            # HTML 콘텐츠 및 페이지 정보 수집
            html_content = driver.page_source
            page_info = await self.browser_manager.get_page_info(driver)
            
            # 병렬로 각 검사 실행
            category_results = await self._run_parallel_checks(
                html_content, url, page_info, options
            )
            
            # 전체 점수 계산
            total_score = self.scoring_engine.calculate_total_score(category_results)
            
            # 모든 이슈 수집
            all_issues = []
            category_scores = {}
            
            for category, result in category_results.items():
                all_issues.extend(result.issues)
                category_scores[category] = CategoryScore(
                    category=category,
                    score=result.score,
                    issues_count=len(result.issues),
                    passed_checks=result.passed_checks,
                    total_checks=result.total_checks
                )
            
            end_time = time.time()
            
            return CheckResult(
                url=str(url),
                total_score=total_score,
                category_scores=category_scores,
                issues=all_issues,
                summary=self._generate_summary(category_results),
                checked_at=datetime.now().isoformat(),
                check_duration=end_time - start_time
            )
            
        finally:
            await self.browser_manager.cleanup()
    
    async def _run_parallel_checks(self, html_content: str, url: str, 
                                 page_info: dict, options: CheckOptions) -> Dict:
        """병렬로 모든 검사를 실행합니다."""
        tasks = []
        enabled_checkers = []
        
        if options.enable_aria_check:
            tasks.append(self.checkers['aria'].check(html_content, url, page_info))
            enabled_checkers.append('aria')
        
        if options.enable_semantic_check:
            tasks.append(self.checkers['semantic'].check(html_content, url, page_info))
            enabled_checkers.append('semantic')
        
        if options.enable_image_check:
            tasks.append(self.checkers['image'].check(html_content, url, page_info))
            enabled_checkers.append('image')
        
        if options.enable_media_check:
            tasks.append(self.checkers['media'].check(html_content, url, page_info))
            enabled_checkers.append('media')
        
        if options.enable_visual_check:
            tasks.append(self.checkers['visual'].check(html_content, url, page_info))
            enabled_checkers.append('visual')
        
        results = await asyncio.gather(*tasks)
        
        return dict(zip(enabled_checkers, results))
    
    def _generate_summary(self, category_results: Dict) -> Dict:
        """검사 결과 요약을 생성합니다."""
        total_issues = sum(len(result.issues) for result in category_results.values())
        critical_issues = sum(
            len([issue for issue in result.issues if issue.severity == 'critical'])
            for result in category_results.values()
        )
        
        return {
            'total_issues': total_issues,
            'critical_issues': critical_issues,
            'categories_checked': len(category_results),
            'overall_grade': self._get_grade(
                sum(result.score for result in category_results.values()) / len(category_results)
            )
        }
    
    def _get_grade(self, score: float) -> str:
        """점수를 기반으로 등급을 반환합니다."""
        if score >= 90:
            return 'A'
        elif score >= 80:
            return 'B'
        elif score >= 70:
            return 'C'
        elif score >= 60:
            return 'D'
        else:
            return 'F'