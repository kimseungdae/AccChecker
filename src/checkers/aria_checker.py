from bs4 import BeautifulSoup, Tag
from typing import List, Dict, Any
import re
import logging

from models.report_models import AccessibilityIssue, SeverityLevel, IssueType

logger = logging.getLogger(__name__)

class CheckerResult:
    def __init__(self):
        self.score = 0.0
        self.issues: List[AccessibilityIssue] = []
        self.passed_checks = 0
        self.total_checks = 0

class AriaChecker:
    """WAI-ARIA 접근성 검사를 수행하는 클래스"""
    
    def __init__(self):
        self.interactive_roles = {
            'button', 'checkbox', 'combobox', 'gridcell', 'link', 'menuitem',
            'menuitemcheckbox', 'menuitemradio', 'option', 'radio', 'searchbox',
            'slider', 'spinbutton', 'switch', 'tab', 'textbox', 'treeitem'
        }
        
        self.landmark_roles = {
            'banner', 'complementary', 'contentinfo', 'form', 'main',
            'navigation', 'region', 'search'
        }
        
        self.required_aria_props = {
            'checkbox': ['aria-checked'],
            'combobox': ['aria-expanded'],
            'gridcell': ['aria-selected'],
            'menuitemcheckbox': ['aria-checked'],
            'menuitemradio': ['aria-checked'],
            'radio': ['aria-checked'],
            'slider': ['aria-valuemin', 'aria-valuemax', 'aria-valuenow'],
            'spinbutton': ['aria-valuemin', 'aria-valuemax', 'aria-valuenow'],
            'switch': ['aria-checked'],
            'tab': ['aria-selected'],
            'treeitem': ['aria-selected']
        }
    
    async def check(self, html_content: str, url: str, page_info: Dict[str, Any]) -> CheckerResult:
        """ARIA 접근성 검사를 수행합니다."""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            result = CheckerResult()
            
            # 각 검사 수행
            checks = [
                self._check_aria_labels,
                self._check_aria_roles,
                self._check_aria_properties,
                self._check_landmark_roles,
                self._check_aria_hidden,
                self._check_aria_live_regions,
                self._check_aria_describedby,
                self._check_tabindex_usage,
                self._check_focus_management
            ]
            
            for check_func in checks:
                issues = check_func(soup, url)
                result.issues.extend(issues)
                result.total_checks += 1
                if not issues:
                    result.passed_checks += 1
            
            # 점수 계산
            result.score = self._calculate_score(result.issues, result.total_checks)
            
            logger.info(f"ARIA 검사 완료: {len(result.issues)}개 이슈 발견")
            return result
            
        except Exception as e:
            logger.error(f"ARIA 검사 중 오류 발생: {str(e)}")
            result = CheckerResult()
            result.issues.append(AccessibilityIssue(
                type=IssueType.ARIA,
                severity=SeverityLevel.HIGH,
                message="ARIA 검사 실행 오류",
                description=f"검사 중 오류가 발생했습니다: {str(e)}",
                recommendation="개발자에게 문의하세요."
            ))
            return result
    
    def _check_aria_labels(self, soup: BeautifulSoup, url: str) -> List[AccessibilityIssue]:
        """aria-label과 aria-labelledby 속성을 검사합니다."""
        issues = []
        
        # 인터랙티브 요소 중 레이블이 없는 것들 찾기
        interactive_elements = soup.find_all(['button', 'input', 'select', 'textarea'])
        
        for element in interactive_elements:
            element_name = element.name
            element_type = element.get('type', '')
            
            # 레이블 확인
            has_label = self._has_accessible_name(element)
            
            if not has_label:
                # 특정 input 타입은 제외
                if element_name == 'input' and element_type in ['hidden', 'submit', 'button']:
                    continue
                
                issues.append(AccessibilityIssue(
                    type=IssueType.ARIA,
                    severity=SeverityLevel.HIGH,
                    message=f"{element_name} 요소에 접근 가능한 이름이 없습니다",
                    description=f"<{element_name}> 요소에 aria-label, aria-labelledby 또는 연결된 label이 필요합니다",
                    element=str(element)[:200],
                    recommendation="aria-label 속성을 추가하거나 label 요소로 연결하세요",
                    wcag_reference="WCAG 2.1 - 4.1.2 Name, Role, Value"
                ))
        
        return issues
    
    def _check_aria_roles(self, soup: BeautifulSoup, url: str) -> List[AccessibilityIssue]:
        """role 속성의 올바른 사용을 검사합니다."""
        issues = []
        
        elements_with_role = soup.find_all(attrs={'role': True})
        
        for element in elements_with_role:
            role = element.get('role')
            
            # 유효하지 않은 role 값 확인
            if not self._is_valid_role(role):
                issues.append(AccessibilityIssue(
                    type=IssueType.ARIA,
                    severity=SeverityLevel.MEDIUM,
                    message=f"유효하지 않은 role 값: '{role}'",
                    description=f"'{role}'은 유효한 ARIA role이 아닙니다",
                    element=str(element)[:200],
                    recommendation="유효한 ARIA role을 사용하세요",
                    wcag_reference="WCAG 2.1 - 4.1.2 Name, Role, Value"
                ))
                continue
            
            # 필수 ARIA 속성 확인
            if role in self.required_aria_props:
                required_props = self.required_aria_props[role]
                for prop in required_props:
                    if not element.get(prop):
                        issues.append(AccessibilityIssue(
                            type=IssueType.ARIA,
                            severity=SeverityLevel.HIGH,
                            message=f"role='{role}'에 필수 속성 '{prop}'이 없습니다",
                            description=f"{role} role을 사용할 때는 {prop} 속성이 필요합니다",
                            element=str(element)[:200],
                            recommendation=f"{prop} 속성을 추가하세요",
                            wcag_reference="WCAG 2.1 - 4.1.2 Name, Role, Value"
                        ))
        
        return issues
    
    def _check_aria_properties(self, soup: BeautifulSoup, url: str) -> List[AccessibilityIssue]:
        """ARIA 속성의 올바른 사용을 검사합니다."""
        issues = []
        
        # aria-* 속성을 가진 모든 요소 찾기
        aria_elements = soup.find_all(attrs=lambda x: x and any(attr.startswith('aria-') for attr in x.keys()))
        
        for element in aria_elements:
            for attr_name, attr_value in element.attrs.items():
                if attr_name.startswith('aria-'):
                    # 속성 값 검증
                    if self._is_boolean_aria_property(attr_name):
                        if attr_value not in ['true', 'false']:
                            issues.append(AccessibilityIssue(
                                type=IssueType.ARIA,
                                severity=SeverityLevel.MEDIUM,
                                message=f"잘못된 ARIA 부울 값: {attr_name}='{attr_value}'",
                                description=f"{attr_name} 속성은 'true' 또는 'false' 값만 허용합니다",
                                element=str(element)[:200],
                                recommendation=f"{attr_name} 값을 'true' 또는 'false'로 수정하세요",
                                wcag_reference="WCAG 2.1 - 4.1.1 Parsing"
                            ))
                    
                    # 빈 값 확인
                    if not attr_value or attr_value.strip() == '':
                        issues.append(AccessibilityIssue(
                            type=IssueType.ARIA,
                            severity=SeverityLevel.MEDIUM,
                            message=f"빈 ARIA 속성: {attr_name}",
                            description=f"{attr_name} 속성에 의미 있는 값이 필요합니다",
                            element=str(element)[:200],
                            recommendation=f"{attr_name} 속성에 적절한 값을 설정하세요",
                            wcag_reference="WCAG 2.1 - 4.1.2 Name, Role, Value"
                        ))
        
        return issues
    
    def _check_landmark_roles(self, soup: BeautifulSoup, url: str) -> List[AccessibilityIssue]:
        """랜드마크 역할의 적절한 사용을 검사합니다."""
        issues = []
        
        # 기본 랜드마크 요소들
        main_elements = soup.find_all('main')
        nav_elements = soup.find_all('nav')
        header_elements = soup.find_all('header')
        footer_elements = soup.find_all('footer')
        
        # main 요소 검사
        if len(main_elements) == 0:
            # role="main"으로 대체되었는지 확인
            main_role_elements = soup.find_all(attrs={'role': 'main'})
            if len(main_role_elements) == 0:
                issues.append(AccessibilityIssue(
                    type=IssueType.ARIA,
                    severity=SeverityLevel.MEDIUM,
                    message="main 랜드마크가 없습니다",
                    description="페이지에 main 요소 또는 role='main'이 없습니다",
                    recommendation="페이지의 주요 콘텐츠를 <main> 요소로 감싸거나 role='main'을 추가하세요",
                    wcag_reference="WCAG 2.1 - 2.4.1 Bypass Blocks"
                ))
        elif len(main_elements) > 1:
            issues.append(AccessibilityIssue(
                type=IssueType.ARIA,
                severity=SeverityLevel.MEDIUM,
                message="main 요소가 여러 개 있습니다",
                description="페이지에는 하나의 main 요소만 있어야 합니다",
                recommendation="main 요소를 하나만 사용하세요",
                wcag_reference="WCAG 2.1 - 2.4.1 Bypass Blocks"
            ))
        
        # 네비게이션 요소 검사
        if len(nav_elements) == 0:
            nav_role_elements = soup.find_all(attrs={'role': 'navigation'})
            if len(nav_role_elements) == 0:
                issues.append(AccessibilityIssue(
                    type=IssueType.ARIA,
                    severity=SeverityLevel.LOW,
                    message="navigation 랜드마크가 없습니다",
                    description="페이지에 nav 요소 또는 role='navigation'이 없습니다",
                    recommendation="네비게이션 메뉴를 <nav> 요소로 감싸거나 role='navigation'을 추가하세요",
                    wcag_reference="WCAG 2.1 - 2.4.1 Bypass Blocks"
                ))
        
        return issues
    
    def _check_aria_hidden(self, soup: BeautifulSoup, url: str) -> List[AccessibilityIssue]:
        """aria-hidden 속성의 올바른 사용을 검사합니다."""
        issues = []
        
        hidden_elements = soup.find_all(attrs={'aria-hidden': 'true'})
        
        for element in hidden_elements:
            # 포커스 가능한 요소가 aria-hidden="true"인지 확인
            if self._is_focusable_element(element):
                issues.append(AccessibilityIssue(
                    type=IssueType.ARIA,
                    severity=SeverityLevel.HIGH,
                    message="포커스 가능한 요소에 aria-hidden='true'가 설정됨",
                    description="포커스를 받을 수 있는 요소는 aria-hidden='true'를 사용하면 안 됩니다",
                    element=str(element)[:200],
                    recommendation="aria-hidden='true'를 제거하거나 tabindex='-1'을 함께 사용하세요",
                    wcag_reference="WCAG 2.1 - 4.1.2 Name, Role, Value"
                ))
        
        return issues
    
    def _check_aria_live_regions(self, soup: BeautifulSoup, url: str) -> List[AccessibilityIssue]:
        """aria-live 영역의 적절한 사용을 검사합니다."""
        issues = []
        
        live_elements = soup.find_all(attrs={'aria-live': True})
        
        for element in live_elements:
            aria_live_value = element.get('aria-live')
            
            # 유효한 값인지 확인
            if aria_live_value not in ['off', 'polite', 'assertive']:
                issues.append(AccessibilityIssue(
                    type=IssueType.ARIA,
                    severity=SeverityLevel.MEDIUM,
                    message=f"잘못된 aria-live 값: '{aria_live_value}'",
                    description="aria-live 속성은 'off', 'polite', 'assertive' 값만 허용합니다",
                    element=str(element)[:200],
                    recommendation="aria-live 값을 'off', 'polite', 'assertive' 중 하나로 설정하세요",
                    wcag_reference="WCAG 2.1 - 4.1.3 Status Messages"
                ))
        
        return issues
    
    def _check_aria_describedby(self, soup: BeautifulSoup, url: str) -> List[AccessibilityIssue]:
        """aria-describedby 속성의 올바른 사용을 검사합니다."""
        issues = []
        
        describedby_elements = soup.find_all(attrs={'aria-describedby': True})
        
        for element in describedby_elements:
            describedby_ids = element.get('aria-describedby').split()
            
            for desc_id in describedby_ids:
                # 참조된 ID가 실제로 존재하는지 확인
                target_element = soup.find(id=desc_id)
                if not target_element:
                    issues.append(AccessibilityIssue(
                        type=IssueType.ARIA,
                        severity=SeverityLevel.MEDIUM,
                        message=f"aria-describedby가 존재하지 않는 ID를 참조: '{desc_id}'",
                        description=f"aria-describedby='{desc_id}'가 참조하는 요소가 페이지에 없습니다",
                        element=str(element)[:200],
                        recommendation=f"ID '{desc_id}'를 가진 요소를 추가하거나 aria-describedby 값을 수정하세요",
                        wcag_reference="WCAG 2.1 - 4.1.2 Name, Role, Value"
                    ))
        
        return issues
    
    def _check_tabindex_usage(self, soup: BeautifulSoup, url: str) -> List[AccessibilityIssue]:
        """tabindex 속성의 올바른 사용을 검사합니다."""
        issues = []
        
        tabindex_elements = soup.find_all(attrs={'tabindex': True})
        
        for element in tabindex_elements:
            tabindex_value = element.get('tabindex')
            
            try:
                tabindex_int = int(tabindex_value)
                
                # 양수 tabindex 사용 경고
                if tabindex_int > 0:
                    issues.append(AccessibilityIssue(
                        type=IssueType.ARIA,
                        severity=SeverityLevel.MEDIUM,
                        message=f"양수 tabindex 사용: {tabindex_value}",
                        description="양수 tabindex는 키보드 네비게이션 순서를 예측하기 어렵게 만듭니다",
                        element=str(element)[:200],
                        recommendation="tabindex='0' 또는 tabindex='-1'을 사용하세요",
                        wcag_reference="WCAG 2.1 - 2.4.3 Focus Order"
                    ))
                
            except ValueError:
                issues.append(AccessibilityIssue(
                    type=IssueType.ARIA,
                    severity=SeverityLevel.MEDIUM,
                    message=f"잘못된 tabindex 값: '{tabindex_value}'",
                    description="tabindex 값은 정수여야 합니다",
                    element=str(element)[:200],
                    recommendation="tabindex 값을 정수로 설정하세요",
                    wcag_reference="WCAG 2.1 - 4.1.1 Parsing"
                ))
        
        return issues
    
    def _check_focus_management(self, soup: BeautifulSoup, url: str) -> List[AccessibilityIssue]:
        """포커스 관리를 검사합니다."""
        issues = []
        
        # 건너뛰기 링크 확인
        skip_links = soup.find_all('a', href=re.compile(r'^#'))
        has_skip_link = any(
            'skip' in link.get_text().lower() or 
            'main' in link.get('href', '').lower()
            for link in skip_links
        )
        
        if not has_skip_link:
            issues.append(AccessibilityIssue(
                type=IssueType.ARIA,
                severity=SeverityLevel.LOW,
                message="건너뛰기 링크가 없습니다",
                description="페이지 시작 부분에 주요 콘텐츠로 건너뛸 수 있는 링크가 필요합니다",
                recommendation="페이지 시작 부분에 '메인 콘텐츠로 건너뛰기' 링크를 추가하세요",
                wcag_reference="WCAG 2.1 - 2.4.1 Bypass Blocks"
            ))
        
        return issues
    
    def _has_accessible_name(self, element: Tag) -> bool:
        """요소가 접근 가능한 이름을 가지고 있는지 확인합니다."""
        # aria-label 확인
        if element.get('aria-label'):
            return True
        
        # aria-labelledby 확인
        if element.get('aria-labelledby'):
            return True
        
        # label 요소 확인 (input의 경우)
        if element.name == 'input':
            input_id = element.get('id')
            if input_id:
                label = element.find_parent().find('label', attrs={'for': input_id})
                if label:
                    return True
        
        # 내부 텍스트 확인 (button의 경우)
        if element.name == 'button':
            text_content = element.get_text(strip=True)
            if text_content:
                return True
        
        return False
    
    def _is_valid_role(self, role: str) -> bool:
        """유효한 ARIA role인지 확인합니다."""
        # 간단한 유효성 검사 (실제로는 더 포괄적인 목록이 필요)
        valid_roles = self.interactive_roles | self.landmark_roles | {
            'alert', 'alertdialog', 'application', 'article', 'cell', 'columnheader',
            'definition', 'dialog', 'directory', 'document', 'figure', 'group',
            'heading', 'img', 'list', 'listitem', 'log', 'marquee', 'math',
            'note', 'presentation', 'progressbar', 'region', 'row', 'rowgroup',
            'rowheader', 'scrollbar', 'separator', 'status', 'table', 'tablist',
            'tabpanel', 'term', 'timer', 'toolbar', 'tooltip', 'tree', 'treegrid'
        }
        return role in valid_roles
    
    def _is_boolean_aria_property(self, prop_name: str) -> bool:
        """ARIA 속성이 부울 값을 가져야 하는지 확인합니다."""
        boolean_props = {
            'aria-checked', 'aria-disabled', 'aria-expanded', 'aria-hidden',
            'aria-invalid', 'aria-pressed', 'aria-readonly', 'aria-required',
            'aria-selected'
        }
        return prop_name in boolean_props
    
    def _is_focusable_element(self, element: Tag) -> bool:
        """요소가 포커스를 받을 수 있는지 확인합니다."""
        # 기본적으로 포커스 가능한 요소들
        focusable_tags = {'a', 'button', 'input', 'select', 'textarea'}
        
        if element.name in focusable_tags:
            return True
        
        # tabindex가 있는 요소
        if element.get('tabindex') is not None:
            try:
                tabindex = int(element.get('tabindex'))
                return tabindex >= 0
            except ValueError:
                return False
        
        return False
    
    def _calculate_score(self, issues: List[AccessibilityIssue], total_checks: int) -> float:
        """점수를 계산합니다."""
        if total_checks == 0:
            return 100.0
        
        # 심각도별 가중치
        severity_weights = {
            SeverityLevel.CRITICAL: 20,
            SeverityLevel.HIGH: 10,
            SeverityLevel.MEDIUM: 5,
            SeverityLevel.LOW: 2
        }
        
        # 총 감점 계산
        total_penalty = sum(severity_weights.get(issue.severity, 0) for issue in issues)
        
        # 기본 점수에서 감점
        base_score = 100.0
        final_score = max(0.0, base_score - total_penalty)
        
        return round(final_score, 1)