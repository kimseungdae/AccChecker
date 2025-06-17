from bs4 import BeautifulSoup, Tag
from typing import List, Dict, Any, Set
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

class SemanticChecker:
    """HTML 시멘틱 구조와 코딩 컨벤션을 검사하는 클래스"""
    
    def __init__(self):
        self.semantic_tags = {
            'header', 'nav', 'main', 'section', 'article', 'aside', 'footer',
            'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'figure', 'figcaption',
            'time', 'mark', 'details', 'summary'
        }
        
        self.form_elements = {
            'form', 'fieldset', 'legend', 'label', 'input', 'textarea',
            'select', 'option', 'optgroup', 'button'
        }
    
    async def check(self, html_content: str, url: str, page_info: Dict[str, Any]) -> CheckerResult:
        """시멘틱 HTML 검사를 수행합니다."""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            result = CheckerResult()
            
            # 각 검사 수행
            checks = [
                self._check_document_structure,
                self._check_heading_hierarchy,
                self._check_semantic_tags_usage,
                self._check_list_structures,
                self._check_table_structures,
                self._check_form_structures,
                self._check_link_purposes,
                self._check_language_attributes,
                self._check_page_title
            ]
            
            for check_func in checks:
                issues = check_func(soup, url)
                result.issues.extend(issues)
                result.total_checks += 1
                if not issues:
                    result.passed_checks += 1
            
            # 점수 계산
            result.score = self._calculate_score(result.issues, result.total_checks)
            
            logger.info(f"시멘틱 검사 완료: {len(result.issues)}개 이슈 발견")
            return result
            
        except Exception as e:
            logger.error(f"시멘틱 검사 중 오류 발생: {str(e)}")
            result = CheckerResult()
            result.issues.append(AccessibilityIssue(
                type=IssueType.SEMANTIC,
                severity=SeverityLevel.HIGH,
                message="시멘틱 검사 실행 오류",
                description=f"검사 중 오류가 발생했습니다: {str(e)}",
                recommendation="개발자에게 문의하세요."
            ))
            return result
    
    def _check_document_structure(self, soup: BeautifulSoup, url: str) -> List[AccessibilityIssue]:
        """문서의 기본 구조를 검사합니다."""
        issues = []
        
        # DOCTYPE 확인
        if not soup.find('html'):
            issues.append(AccessibilityIssue(
                type=IssueType.SEMANTIC,
                severity=SeverityLevel.HIGH,
                message="HTML 요소가 없습니다",
                description="문서에 <html> 요소가 없습니다",
                recommendation="문서를 <html> 요소로 감싸세요",
                wcag_reference="WCAG 2.1 - 4.1.1 Parsing"
            ))
        
        # head 요소 확인
        head = soup.find('head')
        if not head:
            issues.append(AccessibilityIssue(
                type=IssueType.SEMANTIC,
                severity=SeverityLevel.HIGH,
                message="head 요소가 없습니다",
                description="문서에 <head> 요소가 없습니다",
                recommendation="<head> 요소를 추가하세요",
                wcag_reference="WCAG 2.1 - 4.1.1 Parsing"
            ))
        
        # body 요소 확인
        body = soup.find('body')
        if not body:
            issues.append(AccessibilityIssue(
                type=IssueType.SEMANTIC,
                severity=SeverityLevel.HIGH,
                message="body 요소가 없습니다",
                description="문서에 <body> 요소가 없습니다",
                recommendation="<body> 요소를 추가하세요",
                wcag_reference="WCAG 2.1 - 4.1.1 Parsing"
            ))
        
        return issues
    
    def _check_heading_hierarchy(self, soup: BeautifulSoup, url: str) -> List[AccessibilityIssue]:
        """제목 태그의 계층 구조를 검사합니다."""
        issues = []
        
        headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
        
        if not headings:
            issues.append(AccessibilityIssue(
                type=IssueType.SEMANTIC,
                severity=SeverityLevel.MEDIUM,
                message="제목 태그가 없습니다",
                description="페이지에 제목 태그(h1-h6)가 없습니다",
                recommendation="콘텐츠 구조를 나타내는 제목 태그를 추가하세요",
                wcag_reference="WCAG 2.1 - 2.4.6 Headings and Labels"
            ))
            return issues
        
        # h1 태그 확인
        h1_tags = soup.find_all('h1')
        if len(h1_tags) == 0:
            issues.append(AccessibilityIssue(
                type=IssueType.SEMANTIC,
                severity=SeverityLevel.MEDIUM,
                message="h1 태그가 없습니다",
                description="페이지에 h1 태그가 없습니다",
                recommendation="페이지의 주요 제목으로 h1 태그를 추가하세요",
                wcag_reference="WCAG 2.1 - 2.4.6 Headings and Labels"
            ))
        elif len(h1_tags) > 1:
            issues.append(AccessibilityIssue(
                type=IssueType.SEMANTIC,
                severity=SeverityLevel.LOW,
                message="h1 태그가 여러 개 있습니다",
                description=f"페이지에 h1 태그가 {len(h1_tags)}개 있습니다",
                recommendation="h1 태그는 페이지당 하나만 사용하는 것이 좋습니다",
                wcag_reference="WCAG 2.1 - 2.4.6 Headings and Labels"
            ))
        
        # 제목 계층 구조 확인
        prev_level = 0
        for heading in headings:
            current_level = int(heading.name[1])  # h1 -> 1, h2 -> 2, ...
            
            # 빈 제목 확인
            text_content = heading.get_text(strip=True)
            if not text_content:
                issues.append(AccessibilityIssue(
                    type=IssueType.SEMANTIC,
                    severity=SeverityLevel.MEDIUM,
                    message=f"빈 제목 태그: {heading.name}",
                    description=f"{heading.name} 태그에 텍스트 내용이 없습니다",
                    element=str(heading)[:200],
                    recommendation="제목 태그에 의미 있는 텍스트를 추가하세요",
                    wcag_reference="WCAG 2.1 - 2.4.6 Headings and Labels"
                ))
            
            # 계층 구조 확인 (첫 번째 제목이 아닌 경우)
            if prev_level > 0:
                if current_level > prev_level + 1:
                    issues.append(AccessibilityIssue(
                        type=IssueType.SEMANTIC,
                        severity=SeverityLevel.LOW,
                        message=f"제목 계층 구조 오류: h{prev_level} 다음에 h{current_level}",
                        description="제목 태그는 순차적으로 사용해야 합니다",
                        element=str(heading)[:200],
                        recommendation=f"h{prev_level + 1}을 사용하거나 이전 제목 수준을 조정하세요",
                        wcag_reference="WCAG 2.1 - 2.4.6 Headings and Labels"
                    ))
            
            prev_level = current_level
        
        return issues
    
    def _check_semantic_tags_usage(self, soup: BeautifulSoup, url: str) -> List[AccessibilityIssue]:
        """시멘틱 태그의 적절한 사용을 검사합니다."""
        issues = []
        
        # 필수 시멘틱 태그 확인
        required_tags = ['main']
        for tag in required_tags:
            if not soup.find(tag):
                issues.append(AccessibilityIssue(
                    type=IssueType.SEMANTIC,
                    severity=SeverityLevel.MEDIUM,
                    message=f"{tag} 태그가 없습니다",
                    description=f"페이지에 <{tag}> 태그가 없습니다",
                    recommendation=f"주요 콘텐츠를 <{tag}> 태그로 감싸세요",
                    wcag_reference="WCAG 2.1 - 2.4.1 Bypass Blocks"
                ))
        
        # 시멘틱 태그 중복 확인
        single_use_tags = ['main', 'header', 'footer']
        for tag in single_use_tags:
            elements = soup.find_all(tag)
            if len(elements) > 1:
                # 중첩된 경우는 허용 (예: article 내부의 header)
                root_elements = [elem for elem in elements if not elem.find_parent(single_use_tags)]
                if len(root_elements) > 1:
                    issues.append(AccessibilityIssue(
                        type=IssueType.SEMANTIC,
                        severity=SeverityLevel.LOW,
                        message=f"{tag} 태그가 여러 개 있습니다",
                        description=f"페이지 레벨에서 <{tag}> 태그가 {len(root_elements)}개 있습니다",
                        recommendation=f"페이지 레벨에서는 <{tag}> 태그를 하나만 사용하세요",
                        wcag_reference="WCAG 2.1 - 4.1.1 Parsing"
                    ))
        
        # 의미 없는 div 남용 확인
        divs = soup.find_all('div')
        semantic_replaceable_divs = 0
        
        for div in divs:
            class_names = div.get('class', [])
            if isinstance(class_names, str):
                class_names = [class_names]
            
            # 클래스명으로 시멘틱 의미 추측
            semantic_indicators = {
                'header': 'header',
                'nav': 'nav',
                'main': 'main',
                'section': 'section',
                'article': 'article',
                'aside': 'aside',
                'footer': 'footer'
            }
            
            for class_name in class_names:
                for indicator, tag in semantic_indicators.items():
                    if indicator in class_name.lower():
                        semantic_replaceable_divs += 1
                        break
        
        if semantic_replaceable_divs > 0:
            issues.append(AccessibilityIssue(
                type=IssueType.SEMANTIC,
                severity=SeverityLevel.LOW,
                message=f"시멘틱 태그로 대체 가능한 div가 {semantic_replaceable_divs}개 발견됨",
                description="의미를 나타내는 클래스명을 가진 div 요소들이 있습니다",
                recommendation="적절한 시멘틱 태그로 대체하세요 (header, nav, main, section, article, aside, footer)",
                wcag_reference="WCAG 2.1 - 4.1.2 Name, Role, Value"
            ))
        
        return issues
    
    def _check_list_structures(self, soup: BeautifulSoup, url: str) -> List[AccessibilityIssue]:
        """리스트 구조의 적절한 사용을 검사합니다."""
        issues = []
        
        # ul, ol 요소 검사
        lists = soup.find_all(['ul', 'ol'])
        for list_elem in lists:
            # 직접 자식 요소 중 li가 아닌 것 확인
            direct_children = [child for child in list_elem.children if child.name]
            non_li_children = [child for child in direct_children if child.name != 'li']
            
            if non_li_children:
                issues.append(AccessibilityIssue(
                    type=IssueType.SEMANTIC,
                    severity=SeverityLevel.MEDIUM,
                    message=f"{list_elem.name} 요소에 li가 아닌 직접 자식 요소가 있습니다",
                    description=f"<{list_elem.name}> 요소의 직접 자식은 <li> 요소만 가능합니다",
                    element=str(list_elem)[:200],
                    recommendation="li 요소만을 직접 자식으로 사용하세요",
                    wcag_reference="WCAG 2.1 - 4.1.1 Parsing"
                ))
            
            # 빈 리스트 확인
            li_items = list_elem.find_all('li')
            if not li_items:
                issues.append(AccessibilityIssue(
                    type=IssueType.SEMANTIC,
                    severity=SeverityLevel.LOW,
                    message=f"빈 {list_elem.name} 요소",
                    description=f"<{list_elem.name}> 요소에 li 항목이 없습니다",
                    element=str(list_elem)[:200],
                    recommendation="li 항목을 추가하거나 리스트 요소를 제거하세요",
                    wcag_reference="WCAG 2.1 - 4.1.1 Parsing"
                ))
        
        # dl 요소 검사
        dl_lists = soup.find_all('dl')
        for dl in dl_lists:
            dt_elements = dl.find_all('dt')
            dd_elements = dl.find_all('dd')
            
            if not dt_elements or not dd_elements:
                issues.append(AccessibilityIssue(
                    type=IssueType.SEMANTIC,
                    severity=SeverityLevel.MEDIUM,
                    message="dl 요소에 dt 또는 dd가 없습니다",
                    description="<dl> 요소는 dt와 dd 요소를 함께 사용해야 합니다",
                    element=str(dl)[:200],
                    recommendation="dt와 dd 요소를 쌍으로 사용하세요",
                    wcag_reference="WCAG 2.1 - 4.1.1 Parsing"
                ))
        
        return issues
    
    def _check_table_structures(self, soup: BeautifulSoup, url: str) -> List[AccessibilityIssue]:
        """테이블 구조의 적절한 사용을 검사합니다."""
        issues = []
        
        tables = soup.find_all('table')
        
        for table in tables:
            # caption 확인
            caption = table.find('caption')
            if not caption:
                issues.append(AccessibilityIssue(
                    type=IssueType.SEMANTIC,
                    severity=SeverityLevel.MEDIUM,
                    message="table에 caption이 없습니다",
                    description="테이블에 제목을 설명하는 caption 요소가 없습니다",
                    element=str(table)[:200],
                    recommendation="테이블에 <caption> 요소를 추가하여 테이블의 목적을 설명하세요",
                    wcag_reference="WCAG 2.1 - 1.3.1 Info and Relationships"
                ))
            
            # th 요소 확인
            th_elements = table.find_all('th')
            if not th_elements:
                issues.append(AccessibilityIssue(
                    type=IssueType.SEMANTIC,
                    severity=SeverityLevel.HIGH,
                    message="table에 th 요소가 없습니다",
                    description="테이블에 헤더 셀(th)이 없습니다",
                    element=str(table)[:200],
                    recommendation="테이블 헤더에 <th> 요소를 사용하세요",
                    wcag_reference="WCAG 2.1 - 1.3.1 Info and Relationships"
                ))
            else:
                # th 요소의 scope 속성 확인
                for th in th_elements:
                    if not th.get('scope'):
                        issues.append(AccessibilityIssue(
                            type=IssueType.SEMANTIC,
                            severity=SeverityLevel.MEDIUM,
                            message="th 요소에 scope 속성이 없습니다",
                            description="테이블 헤더 셀에 scope 속성이 없습니다",
                            element=str(th)[:200],
                            recommendation="th 요소에 scope='col' 또는 scope='row' 속성을 추가하세요",
                            wcag_reference="WCAG 2.1 - 1.3.1 Info and Relationships"
                        ))
            
            # 레이아웃 목적의 테이블 확인
            if self._is_layout_table(table):
                issues.append(AccessibilityIssue(
                    type=IssueType.SEMANTIC,
                    severity=SeverityLevel.LOW,
                    message="레이아웃 목적으로 table 사용",
                    description="레이아웃을 위해 테이블을 사용하는 것으로 보입니다",
                    element=str(table)[:200],
                    recommendation="레이아웃을 위해서는 CSS를 사용하고, 테이블은 표 형태의 데이터에만 사용하세요",
                    wcag_reference="WCAG 2.1 - 1.3.1 Info and Relationships"
                ))
        
        return issues
    
    def _check_form_structures(self, soup: BeautifulSoup, url: str) -> List[AccessibilityIssue]:
        """폼 구조의 적절한 사용을 검사합니다."""
        issues = []
        
        # form 요소 검사
        forms = soup.find_all('form')
        for form in forms:
            # fieldset과 legend 확인 (여러 관련 필드가 있는 경우)
            inputs = form.find_all(['input', 'select', 'textarea'])
            if len(inputs) > 3:  # 필드가 많은 경우
                fieldsets = form.find_all('fieldset')
                if not fieldsets:
                    issues.append(AccessibilityIssue(
                        type=IssueType.SEMANTIC,
                        severity=SeverityLevel.LOW,
                        message="복잡한 폼에 fieldset이 없습니다",
                        description="관련 필드가 많은 폼에 fieldset으로 그룹화되지 않았습니다",
                        element=str(form)[:200],
                        recommendation="관련된 필드들을 <fieldset>과 <legend>로 그룹화하세요",
                        wcag_reference="WCAG 2.1 - 1.3.1 Info and Relationships"
                    ))
        
        # input 요소 검사
        inputs = soup.find_all('input')
        for input_elem in inputs:
            input_type = input_elem.get('type', 'text')
            input_id = input_elem.get('id')
            
            # 숨겨진 필드는 제외
            if input_type in ['hidden', 'submit', 'button', 'reset']:
                continue
            
            # label 연결 확인
            has_label = False
            
            # id로 연결된 label 확인
            if input_id:
                label = soup.find('label', attrs={'for': input_id})
                if label:
                    has_label = True
            
            # 부모 label 확인
            if not has_label:
                parent_label = input_elem.find_parent('label')
                if parent_label:
                    has_label = True
            
            # aria-label 또는 aria-labelledby 확인
            if not has_label:
                if input_elem.get('aria-label') or input_elem.get('aria-labelledby'):
                    has_label = True
            
            if not has_label:
                issues.append(AccessibilityIssue(
                    type=IssueType.SEMANTIC,
                    severity=SeverityLevel.HIGH,
                    message=f"input 요소에 연결된 label이 없습니다",
                    description=f"type='{input_type}' input 요소에 레이블이 없습니다",
                    element=str(input_elem)[:200],
                    recommendation="<label> 요소를 사용하여 input과 연결하거나 aria-label을 추가하세요",
                    wcag_reference="WCAG 2.1 - 1.3.1 Info and Relationships"
                ))
            
            # 필수 필드 표시 확인
            if input_elem.get('required'):
                # 시각적 표시 또는 aria-required 확인
                parent_text = input_elem.find_parent().get_text() if input_elem.find_parent() else ''
                has_required_indicator = (
                    '*' in parent_text or
                    '필수' in parent_text or
                    'required' in parent_text.lower() or
                    input_elem.get('aria-required') == 'true'
                )
                
                if not has_required_indicator:
                    issues.append(AccessibilityIssue(
                        type=IssueType.SEMANTIC,
                        severity=SeverityLevel.MEDIUM,
                        message="필수 필드 표시가 명확하지 않습니다",
                        description="required 속성이 있는 필드에 명확한 필수 표시가 없습니다",
                        element=str(input_elem)[:200],
                        recommendation="필수 필드에 시각적 표시(*)를 추가하고 aria-required='true'를 설정하세요",
                        wcag_reference="WCAG 2.1 - 3.3.2 Labels or Instructions"
                    ))
        
        return issues
    
    def _check_link_purposes(self, soup: BeautifulSoup, url: str) -> List[AccessibilityIssue]:
        """링크의 목적이 명확한지 검사합니다."""
        issues = []
        
        links = soup.find_all('a', href=True)
        
        for link in links:
            link_text = link.get_text(strip=True)
            
            # 빈 링크 텍스트
            if not link_text:
                # 이미지가 있는지 확인
                img = link.find('img')
                if img and img.get('alt'):
                    continue  # 이미지의 alt 텍스트가 링크 텍스트 역할
                
                issues.append(AccessibilityIssue(
                    type=IssueType.SEMANTIC,
                    severity=SeverityLevel.HIGH,
                    message="빈 링크 텍스트",
                    description="링크에 텍스트 내용이 없습니다",
                    element=str(link)[:200],
                    recommendation="링크의 목적을 설명하는 텍스트를 추가하세요",
                    wcag_reference="WCAG 2.1 - 2.4.4 Link Purpose"
                ))
                continue
            
            # 모호한 링크 텍스트 확인
            vague_texts = {
                '여기', '클릭', 'click', 'here', '더보기', 'more', '자세히', 'read more',
                '바로가기', '링크', 'link', '확인', '보기', 'view'
            }
            
            if link_text.lower() in vague_texts:
                issues.append(AccessibilityIssue(
                    type=IssueType.SEMANTIC,
                    severity=SeverityLevel.MEDIUM,
                    message=f"모호한 링크 텍스트: '{link_text}'",
                    description="링크의 목적이 명확하지 않은 텍스트를 사용합니다",
                    element=str(link)[:200],
                    recommendation="링크의 목적을 명확히 설명하는 텍스트를 사용하세요",
                    wcag_reference="WCAG 2.1 - 2.4.4 Link Purpose"
                ))
        
        return issues
    
    def _check_language_attributes(self, soup: BeautifulSoup, url: str) -> List[AccessibilityIssue]:
        """언어 속성의 적절한 사용을 검사합니다."""
        issues = []
        
        # html 요소의 lang 속성 확인
        html_elem = soup.find('html')
        if html_elem:
            lang_attr = html_elem.get('lang')
            if not lang_attr:
                issues.append(AccessibilityIssue(
                    type=IssueType.SEMANTIC,
                    severity=SeverityLevel.MEDIUM,
                    message="html 요소에 lang 속성이 없습니다",
                    description="문서의 주 언어가 지정되지 않았습니다",
                    recommendation="<html> 요소에 lang 속성을 추가하세요 (예: lang='ko')",
                    wcag_reference="WCAG 2.1 - 3.1.1 Language of Page"
                ))
            elif len(lang_attr) < 2:
                issues.append(AccessibilityIssue(
                    type=IssueType.SEMANTIC,
                    severity=SeverityLevel.MEDIUM,
                    message=f"잘못된 lang 속성 값: '{lang_attr}'",
                    description="lang 속성 값이 유효한 언어 코드가 아닙니다",
                    recommendation="유효한 언어 코드를 사용하세요 (예: 'ko', 'en', 'ko-KR')",
                    wcag_reference="WCAG 2.1 - 3.1.1 Language of Page"
                ))
        
        return issues
    
    def _check_page_title(self, soup: BeautifulSoup, url: str) -> List[AccessibilityIssue]:
        """페이지 제목의 적절성을 검사합니다."""
        issues = []
        
        title_elem = soup.find('title')
        
        if not title_elem:
            issues.append(AccessibilityIssue(
                type=IssueType.SEMANTIC,
                severity=SeverityLevel.HIGH,
                message="title 요소가 없습니다",
                description="문서에 <title> 요소가 없습니다",
                recommendation="<head> 섹션에 <title> 요소를 추가하세요",
                wcag_reference="WCAG 2.1 - 2.4.2 Page Titled"
            ))
        else:
            title_text = title_elem.get_text(strip=True)
            
            if not title_text:
                issues.append(AccessibilityIssue(
                    type=IssueType.SEMANTIC,
                    severity=SeverityLevel.HIGH,
                    message="빈 title 요소",
                    description="title 요소에 텍스트가 없습니다",
                    recommendation="페이지의 목적을 설명하는 제목을 추가하세요",
                    wcag_reference="WCAG 2.1 - 2.4.2 Page Titled"
                ))
            elif len(title_text) < 10:
                issues.append(AccessibilityIssue(
                    type=IssueType.SEMANTIC,
                    severity=SeverityLevel.LOW,
                    message="title이 너무 짧습니다",
                    description=f"title이 {len(title_text)}글자로 너무 짧습니다",
                    recommendation="페이지의 내용과 목적을 충분히 설명하는 제목을 사용하세요",
                    wcag_reference="WCAG 2.1 - 2.4.2 Page Titled"
                ))
        
        return issues
    
    def _is_layout_table(self, table: Tag) -> bool:
        """테이블이 레이아웃 목적으로 사용되는지 확인합니다."""
        # 간단한 휴리스틱 검사
        # 실제로는 더 정교한 분석이 필요
        
        # th가 없거나 매우 적은 경우
        th_count = len(table.find_all('th'))
        td_count = len(table.find_all('td'))
        
        if th_count == 0 or (td_count > 0 and th_count / td_count < 0.1):
            return True
        
        # border, cellpadding, cellspacing 등의 속성이 있는 경우
        layout_attributes = ['border', 'cellpadding', 'cellspacing']
        for attr in layout_attributes:
            if table.get(attr) == '0':
                return True
        
        return False
    
    def _calculate_score(self, issues: List[AccessibilityIssue], total_checks: int) -> float:
        """점수를 계산합니다."""
        if total_checks == 0:
            return 100.0
        
        # 심각도별 가중치
        severity_weights = {
            SeverityLevel.CRITICAL: 15,
            SeverityLevel.HIGH: 8,
            SeverityLevel.MEDIUM: 4,
            SeverityLevel.LOW: 1
        }
        
        # 총 감점 계산
        total_penalty = sum(severity_weights.get(issue.severity, 0) for issue in issues)
        
        # 기본 점수에서 감점
        base_score = 100.0
        final_score = max(0.0, base_score - total_penalty)
        
        return round(final_score, 1)