from bs4 import BeautifulSoup, Tag
from typing import List, Dict, Any, Set
import re
import requests
from urllib.parse import urljoin, urlparse
import logging
from PIL import Image
import io

from models.report_models import AccessibilityIssue, SeverityLevel, IssueType

logger = logging.getLogger(__name__)

class CheckerResult:
    def __init__(self):
        self.score = 0.0
        self.issues: List[AccessibilityIssue] = []
        self.passed_checks = 0
        self.total_checks = 0

class ImageChecker:
    """이미지 접근성을 검사하는 클래스"""
    
    def __init__(self):
        self.decorative_indicators = {
            'decoration', 'decorative', 'ornament', 'ornamental', 'bg', 'background',
            'spacer', 'divider', 'separator', 'bullet', 'icon-bg', 'pattern'
        }
        
        self.informative_indicators = {
            'logo', 'chart', 'graph', 'diagram', 'infographic', 'map', 'photo',
            'screenshot', 'illustration', 'artwork', 'product', 'profile'
        }
        
        # 의미 없는 alt 텍스트 패턴
        self.meaningless_alt_patterns = {
            'image', 'img', 'picture', 'pic', 'photo', 'graphic', 'untitled',
            'no title', 'no name', 'default', 'placeholder', 'temp', 'test'
        }
    
    async def check(self, html_content: str, url: str, page_info: Dict[str, Any]) -> CheckerResult:
        """이미지 접근성 검사를 수행합니다."""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            result = CheckerResult()
            
            # 각 검사 수행
            checks = [
                self._check_img_alt_attributes,
                self._check_alt_text_quality,
                self._check_decorative_images,
                self._check_complex_images,
                self._check_background_images,
                self._check_image_links,
                self._check_figure_captions,
                self._check_svg_accessibility
            ]
            
            for check_func in checks:
                issues = check_func(soup, url)
                result.issues.extend(issues)
                result.total_checks += 1
                if not issues:
                    result.passed_checks += 1
            
            # 점수 계산
            result.score = self._calculate_score(result.issues, result.total_checks)
            
            logger.info(f"이미지 접근성 검사 완료: {len(result.issues)}개 이슈 발견")
            return result
            
        except Exception as e:
            logger.error(f"이미지 접근성 검사 중 오류 발생: {str(e)}")
            result = CheckerResult()
            result.issues.append(AccessibilityIssue(
                type=IssueType.IMAGE,
                severity=SeverityLevel.HIGH,
                message="이미지 접근성 검사 실행 오류",
                description=f"검사 중 오류가 발생했습니다: {str(e)}",
                recommendation="개발자에게 문의하세요."
            ))
            return result
    
    def _check_img_alt_attributes(self, soup: BeautifulSoup, url: str) -> List[AccessibilityIssue]:
        """img 태그의 alt 속성을 검사합니다."""
        issues = []
        
        img_tags = soup.find_all('img')
        
        for img in img_tags:
            src = img.get('src', '')
            alt = img.get('alt')
            
            # alt 속성이 없는 경우
            if alt is None:
                issues.append(AccessibilityIssue(
                    type=IssueType.IMAGE,
                    severity=SeverityLevel.HIGH,
                    message="img 태그에 alt 속성이 없습니다",
                    description=f"이미지 '{src}'에 alt 속성이 없습니다",
                    element=str(img)[:200],
                    recommendation="모든 이미지에 alt 속성을 추가하세요. 장식용 이미지는 alt=''를 사용하세요",
                    wcag_reference="WCAG 2.1 - 1.1.1 Non-text Content"
                ))
                continue
            
            # role="presentation" 또는 alt=""인 경우는 장식용으로 간주
            if alt == '' or img.get('role') == 'presentation':
                continue
            
            # alt 텍스트가 있지만 의미 없는 경우
            if self._is_meaningless_alt(alt, src):
                issues.append(AccessibilityIssue(
                    type=IssueType.IMAGE,
                    severity=SeverityLevel.MEDIUM,
                    message=f"의미 없는 alt 텍스트: '{alt}'",
                    description="alt 텍스트가 이미지의 내용이나 목적을 설명하지 않습니다",
                    element=str(img)[:200],
                    recommendation="이미지의 내용이나 목적을 명확히 설명하는 alt 텍스트를 작성하세요",
                    wcag_reference="WCAG 2.1 - 1.1.1 Non-text Content"
                ))
            
            # alt 텍스트가 너무 긴 경우
            if len(alt) > 125:
                issues.append(AccessibilityIssue(
                    type=IssueType.IMAGE,
                    severity=SeverityLevel.LOW,
                    message=f"alt 텍스트가 너무 깁니다 ({len(alt)}글자)",
                    description="alt 텍스트가 125글자를 초과합니다",
                    element=str(img)[:200],
                    recommendation="alt 텍스트를 간결하게 작성하고, 자세한 설명이 필요한 경우 longdesc나 주변 텍스트를 활용하세요",
                    wcag_reference="WCAG 2.1 - 1.1.1 Non-text Content"
                ))
            
            # 파일 확장자가 alt 텍스트에 포함된 경우
            file_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg']
            if any(ext in alt.lower() for ext in file_extensions):
                issues.append(AccessibilityIssue(
                    type=IssueType.IMAGE,
                    severity=SeverityLevel.LOW,
                    message="alt 텍스트에 파일 확장자가 포함됨",
                    description="alt 텍스트에 이미지 파일 확장자가 포함되어 있습니다",
                    element=str(img)[:200],
                    recommendation="alt 텍스트에서 파일 확장자를 제거하세요",
                    wcag_reference="WCAG 2.1 - 1.1.1 Non-text Content"
                ))
        
        return issues
    
    def _check_alt_text_quality(self, soup: BeautifulSoup, url: str) -> List[AccessibilityIssue]:
        """alt 텍스트의 품질을 검사합니다."""
        issues = []
        
        img_tags = soup.find_all('img', alt=True)
        
        for img in img_tags:
            alt = img.get('alt', '').strip()
            src = img.get('src', '')
            
            if alt == '':
                continue  # 장식용 이미지
            
            # "image of", "picture of" 등의 불필요한 접두사
            redundant_prefixes = [
                'image of', 'picture of', 'photo of', 'graphic of', 'illustration of',
                '이미지', '사진', '그래픽', '일러스트', '그림'
            ]
            
            for prefix in redundant_prefixes:
                if alt.lower().startswith(prefix.lower()):
                    issues.append(AccessibilityIssue(
                        type=IssueType.IMAGE,
                        severity=SeverityLevel.LOW,
                        message=f"alt 텍스트에 불필요한 접두사: '{prefix}'",
                        description="alt 텍스트에 '이미지', '사진' 등의 불필요한 접두사가 있습니다",
                        element=str(img)[:200],
                        recommendation="불필요한 접두사를 제거하고 이미지의 내용을 직접 설명하세요",
                        wcag_reference="WCAG 2.1 - 1.1.1 Non-text Content"
                    ))
                    break
            
            # alt 텍스트와 파일명이 비슷한 경우
            if src:
                filename = src.split('/')[-1].split('.')[0]
                if filename.lower().replace('-', ' ').replace('_', ' ') in alt.lower():
                    issues.append(AccessibilityIssue(
                        type=IssueType.IMAGE,
                        severity=SeverityLevel.MEDIUM,
                        message="alt 텍스트가 파일명과 유사합니다",
                        description="alt 텍스트가 파일명을 그대로 사용하는 것으로 보입니다",
                        element=str(img)[:200],
                        recommendation="파일명 대신 이미지의 내용이나 목적을 설명하는 텍스트를 사용하세요",
                        wcag_reference="WCAG 2.1 - 1.1.1 Non-text Content"
                    ))
        
        return issues
    
    def _check_decorative_images(self, soup: BeautifulSoup, url: str) -> List[AccessibilityIssue]:
        """장식용 이미지의 적절한 처리를 검사합니다."""
        issues = []
        
        img_tags = soup.find_all('img')
        
        for img in img_tags:
            src = img.get('src', '')
            alt = img.get('alt')
            role = img.get('role')
            
            # 장식용 이미지로 추정되는 경우
            if self._is_likely_decorative(img, src):
                if alt is not None and alt != '':
                    if role != 'presentation':
                        issues.append(AccessibilityIssue(
                            type=IssueType.IMAGE,
                            severity=SeverityLevel.MEDIUM,
                            message="장식용 이미지에 alt 텍스트가 있습니다",
                            description="장식용으로 보이는 이미지에 alt 텍스트가 설정되어 있습니다",
                            element=str(img)[:200],
                            recommendation="장식용 이미지는 alt='' 또는 role='presentation'을 사용하세요",
                            wcag_reference="WCAG 2.1 - 1.1.1 Non-text Content"
                        ))
        
        return issues
    
    def _check_complex_images(self, soup: BeautifulSoup, url: str) -> List[AccessibilityIssue]:
        """복잡한 이미지(차트, 그래프 등)의 접근성을 검사합니다."""
        issues = []
        
        img_tags = soup.find_all('img')
        
        for img in img_tags:
            src = img.get('src', '')
            alt = img.get('alt', '')
            
            # 복잡한 이미지로 추정되는 경우
            if self._is_complex_image(img, src, alt):
                # longdesc 속성 확인 (deprecated이지만 여전히 사용)
                longdesc = img.get('longdesc')
                
                # aria-describedby 확인
                aria_describedby = img.get('aria-describedby')
                
                # 주변에 상세 설명이 있는지 확인
                has_detailed_description = self._has_nearby_description(img)
                
                if not longdesc and not aria_describedby and not has_detailed_description:
                    issues.append(AccessibilityIssue(
                        type=IssueType.IMAGE,
                        severity=SeverityLevel.MEDIUM,
                        message="복잡한 이미지에 상세 설명이 없습니다",
                        description="차트, 그래프, 복잡한 이미지에 상세 설명이 제공되지 않았습니다",
                        element=str(img)[:200],
                        recommendation="aria-describedby로 상세 설명을 연결하거나 이미지 근처에 텍스트 설명을 추가하세요",
                        wcag_reference="WCAG 2.1 - 1.1.1 Non-text Content"
                    ))
        
        return issues
    
    def _check_background_images(self, soup: BeautifulSoup, url: str) -> List[AccessibilityIssue]:
        """CSS 배경 이미지의 접근성을 검사합니다."""
        issues = []
        
        # style 속성에서 background-image 찾기
        elements_with_bg = soup.find_all(attrs={'style': re.compile(r'background-image', re.I)})
        
        for element in elements_with_bg:
            style = element.get('style', '')
            
            # 정보를 전달하는 배경 이미지인지 확인
            if self._is_informative_background(element, style):
                # 대체 텍스트가 있는지 확인
                has_alt_text = (
                    element.get('aria-label') or
                    element.get('aria-labelledby') or
                    element.get_text(strip=True)
                )
                
                if not has_alt_text:
                    issues.append(AccessibilityIssue(
                        type=IssueType.IMAGE,
                        severity=SeverityLevel.MEDIUM,
                        message="정보를 전달하는 배경 이미지에 대체 텍스트가 없습니다",
                        description="의미 있는 내용을 포함한 CSS 배경 이미지에 대체 텍스트가 없습니다",
                        element=str(element)[:200],
                        recommendation="aria-label을 추가하거나 이미지의 내용을 텍스트로 제공하세요",
                        wcag_reference="WCAG 2.1 - 1.1.1 Non-text Content"
                    ))
        
        return issues
    
    def _check_image_links(self, soup: BeautifulSoup, url: str) -> List[AccessibilityIssue]:
        """이미지가 포함된 링크의 접근성을 검사합니다."""
        issues = []
        
        # 이미지만 포함한 링크 찾기
        img_links = soup.find_all('a', href=True)
        
        for link in img_links:
            imgs = link.find_all('img')
            link_text = link.get_text(strip=True)
            
            # 텍스트 없이 이미지만 있는 링크
            if imgs and not link_text:
                has_accessible_name = False
                
                # 이미지의 alt 텍스트 확인
                for img in imgs:
                    alt = img.get('alt')
                    if alt and alt.strip():
                        has_accessible_name = True
                        break
                
                # 링크 자체의 aria-label 확인
                if not has_accessible_name:
                    if link.get('aria-label') or link.get('aria-labelledby'):
                        has_accessible_name = True
                
                if not has_accessible_name:
                    issues.append(AccessibilityIssue(
                        type=IssueType.IMAGE,
                        severity=SeverityLevel.HIGH,
                        message="이미지 링크에 접근 가능한 이름이 없습니다",
                        description="이미지만 포함한 링크에 접근 가능한 이름이 없습니다",
                        element=str(link)[:200],
                        recommendation="이미지에 의미 있는 alt 텍스트를 추가하거나 링크에 aria-label을 설정하세요",
                        wcag_reference="WCAG 2.1 - 2.4.4 Link Purpose"
                    ))
        
        return issues
    
    def _check_figure_captions(self, soup: BeautifulSoup, url: str) -> List[AccessibilityIssue]:
        """figure 요소와 figcaption의 적절한 사용을 검사합니다."""
        issues = []
        
        figures = soup.find_all('figure')
        
        for figure in figures:
            figcaption = figure.find('figcaption')
            
            if not figcaption:
                issues.append(AccessibilityIssue(
                    type=IssueType.IMAGE,
                    severity=SeverityLevel.LOW,
                    message="figure 요소에 figcaption이 없습니다",
                    description="figure 요소에 캡션을 제공하는 figcaption이 없습니다",
                    element=str(figure)[:200],
                    recommendation="figure 요소에 figcaption을 추가하여 이미지나 콘텐츠를 설명하세요",
                    wcag_reference="WCAG 2.1 - 1.1.1 Non-text Content"
                ))
            else:
                caption_text = figcaption.get_text(strip=True)
                if not caption_text:
                    issues.append(AccessibilityIssue(
                        type=IssueType.IMAGE,
                        severity=SeverityLevel.LOW,
                        message="빈 figcaption 요소",
                        description="figcaption 요소에 텍스트 내용이 없습니다",
                        element=str(figcaption)[:200],
                        recommendation="figcaption에 이미지나 콘텐츠를 설명하는 텍스트를 추가하세요",
                        wcag_reference="WCAG 2.1 - 1.1.1 Non-text Content"
                    ))
        
        return issues
    
    def _check_svg_accessibility(self, soup: BeautifulSoup, url: str) -> List[AccessibilityIssue]:
        """SVG 요소의 접근성을 검사합니다."""
        issues = []
        
        svgs = soup.find_all('svg')
        
        for svg in svgs:
            # role="img" 확인
            role = svg.get('role')
            
            # 제목과 설명 확인
            title = svg.find('title')
            desc = svg.find('desc')
            
            # aria-label 또는 aria-labelledby 확인
            aria_label = svg.get('aria-label')
            aria_labelledby = svg.get('aria-labelledby')
            
            # 장식용 SVG인지 확인
            is_decorative = (
                role == 'presentation' or
                svg.get('aria-hidden') == 'true'
            )
            
            if not is_decorative:
                has_accessible_name = (
                    title or aria_label or aria_labelledby
                )
                
                if not has_accessible_name:
                    issues.append(AccessibilityIssue(
                        type=IssueType.IMAGE,
                        severity=SeverityLevel.MEDIUM,
                        message="SVG 요소에 접근 가능한 이름이 없습니다",
                        description="정보를 전달하는 SVG에 제목이나 레이블이 없습니다",
                        element=str(svg)[:200],
                        recommendation="SVG에 <title> 요소나 aria-label을 추가하고 role='img'를 설정하세요",
                        wcag_reference="WCAG 2.1 - 1.1.1 Non-text Content"
                    ))
        
        return issues
    
    def _is_meaningless_alt(self, alt: str, src: str) -> bool:
        """alt 텍스트가 의미 없는지 확인합니다."""
        alt_lower = alt.lower().strip()
        
        # 의미 없는 패턴과 일치하는지 확인
        for pattern in self.meaningless_alt_patterns:
            if pattern in alt_lower:
                return True
        
        # 파일명과 비슷한지 확인
        if src:
            filename = src.split('/')[-1].split('.')[0].lower()
            if filename.replace('-', ' ').replace('_', ' ') in alt_lower:
                return True
        
        return False
    
    def _is_likely_decorative(self, img: Tag, src: str) -> bool:
        """이미지가 장식용일 가능성이 높은지 확인합니다."""
        # 파일명으로 판단
        if src:
            filename = src.lower()
            for indicator in self.decorative_indicators:
                if indicator in filename:
                    return True
        
        # CSS 클래스로 판단
        css_classes = img.get('class', [])
        if isinstance(css_classes, str):
            css_classes = [css_classes]
        
        for class_name in css_classes:
            class_lower = class_name.lower()
            for indicator in self.decorative_indicators:
                if indicator in class_lower:
                    return True
        
        # 크기가 매우 작은 경우 (스페이서 이미지 등)
        width = img.get('width')
        height = img.get('height')
        if width and height:
            try:
                w, h = int(width), int(height)
                if w <= 5 or h <= 5:
                    return True
            except ValueError:
                pass
        
        return False
    
    def _is_complex_image(self, img: Tag, src: str, alt: str) -> bool:
        """복잡한 이미지인지 확인합니다."""
        # 파일명으로 판단
        if src:
            filename = src.lower()
            complex_indicators = ['chart', 'graph', 'diagram', 'infographic', 'map']
            for indicator in complex_indicators:
                if indicator in filename:
                    return True
        
        # alt 텍스트로 판단
        alt_lower = alt.lower()
        complex_keywords = ['차트', '그래프', '도표', '지도', '다이어그램', 'chart', 'graph', 'diagram', 'map']
        for keyword in complex_keywords:
            if keyword in alt_lower:
                return True
        
        return False
    
    def _has_nearby_description(self, img: Tag) -> bool:
        """이미지 근처에 상세 설명이 있는지 확인합니다."""
        # 부모 요소에서 텍스트 찾기
        parent = img.find_parent()
        if parent:
            siblings = parent.find_next_siblings()[:3]  # 다음 3개 형제 요소 확인
            for sibling in siblings:
                text = sibling.get_text(strip=True)
                if len(text) > 50:  # 충분히 긴 설명이 있는 경우
                    return True
        
        return False
    
    def _is_informative_background(self, element: Tag, style: str) -> bool:
        """배경 이미지가 정보를 전달하는지 확인합니다."""
        # 간단한 휴리스틱 - 실제로는 더 정교한 분석 필요
        
        # 요소에 텍스트가 없는 경우
        text_content = element.get_text(strip=True)
        if not text_content:
            return True
        
        # 특정 클래스나 역할을 가진 경우
        css_classes = element.get('class', [])
        if isinstance(css_classes, str):
            css_classes = [css_classes]
        
        informative_classes = ['logo', 'banner', 'hero', 'chart', 'graph']
        for class_name in css_classes:
            for info_class in informative_classes:
                if info_class in class_name.lower():
                    return True
        
        return False
    
    def _calculate_score(self, issues: List[AccessibilityIssue], total_checks: int) -> float:
        """점수를 계산합니다."""
        if total_checks == 0:
            return 100.0
        
        # 심각도별 가중치
        severity_weights = {
            SeverityLevel.CRITICAL: 12,
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