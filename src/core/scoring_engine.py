from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class ScoringEngine:
    """접근성 검사 결과의 점수를 계산하는 엔진"""
    
    # 각 카테고리별 가중치 설정
    WEIGHT_CONFIG = {
        'aria': 0.25,        # WAI-ARIA 준수 (25%)
        'semantic': 0.20,    # 시멘틱 HTML (20%)
        'image': 0.15,       # 이미지 접근성 (15%)
        'media': 0.15,       # 미디어 접근성 (15%)
        'visual': 0.10,      # 시각적 설계 (10%)
        'keyboard': 0.15     # 키보드 네비게이션 (15%)
    }
    
    def __init__(self):
        self.max_score = 100.0
    
    def calculate_total_score(self, category_results: Dict[str, Any]) -> float:
        """카테고리별 점수를 종합하여 총점을 계산합니다."""
        try:
            total_weighted_score = 0.0
            total_weight = 0.0
            
            for category, result in category_results.items():
                if category in self.WEIGHT_CONFIG:
                    weight = self.WEIGHT_CONFIG[category]
                    score = result.score if hasattr(result, 'score') else result.get('score', 0)
                    
                    total_weighted_score += score * weight
                    total_weight += weight
                    
                    logger.debug(f"카테고리: {category}, 점수: {score}, 가중치: {weight}")
            
            # 가중치가 없는 경우 기본 평균 계산
            if total_weight == 0:
                scores = [
                    result.score if hasattr(result, 'score') else result.get('score', 0)
                    for result in category_results.values()
                ]
                return round(sum(scores) / len(scores), 1) if scores else 0.0
            
            final_score = total_weighted_score / total_weight if total_weight > 0 else 0.0
            return round(final_score, 1)
            
        except Exception as e:
            logger.error(f"총점 계산 중 오류 발생: {str(e)}")
            return 0.0
    
    def calculate_category_score(self, passed_checks: int, total_checks: int, 
                               severity_penalties: Dict[str, int] = None) -> float:
        """카테고리별 점수를 계산합니다."""
        if total_checks == 0:
            return 100.0
        
        # 기본 점수 계산 (통과한 검사 비율)
        base_score = (passed_checks / total_checks) * 100
        
        # 심각도별 감점 적용
        penalty = 0.0
        if severity_penalties:
            penalty += severity_penalties.get('critical', 0) * 10   # 치명적: -10점
            penalty += severity_penalties.get('high', 0) * 5       # 높음: -5점
            penalty += severity_penalties.get('medium', 0) * 2     # 보통: -2점
            penalty += severity_penalties.get('low', 0) * 1        # 낮음: -1점
        
        final_score = max(0.0, base_score - penalty)
        return round(final_score, 1)
    
    def get_grade(self, score: float) -> str:
        """점수를 기반으로 등급을 반환합니다."""
        if score >= 95:
            return 'A+'
        elif score >= 90:
            return 'A'
        elif score >= 85:
            return 'B+'
        elif score >= 80:
            return 'B'
        elif score >= 75:
            return 'C+'
        elif score >= 70:
            return 'C'
        elif score >= 65:
            return 'D+'
        elif score >= 60:
            return 'D'
        else:
            return 'F'
    
    def get_accessibility_level(self, score: float) -> str:
        """WCAG 준수 수준을 반환합니다."""
        if score >= 95:
            return 'AAA (최고 수준)'
        elif score >= 80:
            return 'AA (권장 수준)'
        elif score >= 60:
            return 'A (최소 수준)'
        else:
            return '미준수'
    
    def calculate_improvement_potential(self, current_score: float, 
                                     fixable_issues: int, total_issues: int) -> Dict[str, Any]:
        """개선 가능성을 계산합니다."""
        if total_issues == 0:
            return {
                'potential_score': current_score,
                'improvement_points': 0.0,
                'fixable_ratio': 1.0
            }
        
        fixable_ratio = fixable_issues / total_issues
        improvement_points = (100 - current_score) * fixable_ratio
        potential_score = min(100.0, current_score + improvement_points)
        
        return {
            'potential_score': round(potential_score, 1),
            'improvement_points': round(improvement_points, 1),
            'fixable_ratio': round(fixable_ratio, 2)
        }