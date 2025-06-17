from bs4 import BeautifulSoup, Tag
from typing import List, Dict, Any, Tuple
import re
import logging
import colorsys

from models.report_models import AccessibilityIssue, SeverityLevel, IssueType

logger = logging.getLogger(__name__)

class CheckerResult:
    def __init__(self):
        self.score = 0.0
        self.issues: List[AccessibilityIssue] = []
        self.passed_checks = 0
        self.total_checks = 0

class VisualChecker:
    """시각적 접근성을 검사하는 클래스"""
    
    def __init__(self):
        # WCAG 대비율 기준
        self.contrast_ratios = {
            'normal_aa': 4.5,
            'large_aa': 3.0,
            'normal_aaa': 7.0,
            'large_aaa': 4.5
        }
        
        # 큰 텍스트 기준 (18pt 이상 또는 14pt 이상 bold)
        self.large_text_size_pt = 18
        self.large_text_size_px = 24  # 대략적 변환
        
        # 색상 키워드
        self.color_keywords = {
            'red': '#ff0000', 'green': '#008000', 'blue': '#0000ff',
            'yellow': '#ffff00', 'orange': '#ffa500', 'purple': '#800080',
            'pink': '#ffc0cb', 'brown': '#a52a2a', 'gray': '#808080',
            'grey': '#808080', 'black': '#000000', 'white': '#ffffff',
            'transparent': 'rgba(0,0,0,0)'
        }
    
    async def check(self, html_content: str, url: str, page_info: Dict[str, Any]) -> CheckerResult:
        """시각적 접근성 검사를 수행합니다."""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            result = CheckerResult()
            
            # 각 검사 수행
            checks = [
                self._check_color_contrast,
                self._check_color_only_information,
                self._check_text_spacing,
                self._check_resize_compatibility,
                self._check_focus_indicators,
                self._check_motion_animation,
                self._check_flashing_content,
                self._check_visual_layout
            ]
            
            for check_func in checks:
                issues = check_func(soup, url)
                result.issues.extend(issues)
                result.total_checks += 1
                if not issues:
                    result.passed_checks += 1
            
            # 점수 계산
            result.score = self._calculate_score(result.issues, result.total_checks)
            
            logger.info(f"시각적 접근성 검사 완료: {len(result.issues)}개 이슈 발견")
            return result
            
        except Exception as e:
            logger.error(f"시각적 접근성 검사 중 오류 발생: {str(e)}")
            result = CheckerResult()
            result.issues.append(AccessibilityIssue(
                type=IssueType.VISUAL,
                severity=SeverityLevel.HIGH,
                message="시각적 접근성 검사 실행 오류",
                description=f"검사 중 오류가 발생했습니다: {str(e)}",
                recommendation="개발자에게 문의하세요."
            ))
            return result
    
    def _check_color_contrast(self, soup: BeautifulSoup, url: str) -> List[AccessibilityIssue]:
        """색상 대비를 검사합니다."""
        issues = []
        
        # 인라인 스타일에서 색상 정보 추출
        elements_with_style = soup.find_all(attrs={'style': True})
        
        for element in elements_with_style:
            style = element.get('style', '')
            colors = self._extract_colors_from_style(style)
            
            if colors['color'] and colors['background']:
                contrast_ratio = self._calculate_contrast_ratio(colors['color'], colors['background'])
                
                if contrast_ratio is not None:
                    # 텍스트 크기 확인
                    is_large_text = self._is_large_text(element, style)
                    
                    # 적절한 기준 선택
                    if is_large_text:
                        min_ratio = self.contrast_ratios['large_aa']
                        level = "대형 텍스트 AA"
                    else:
                        min_ratio = self.contrast_ratios['normal_aa']
                        level = "일반 텍스트 AA"
                    
                    if contrast_ratio < min_ratio:
                        issues.append(AccessibilityIssue(
                            type=IssueType.VISUAL,
                            severity=SeverityLevel.MEDIUM,
                            message=f"색상 대비 부족: {contrast_ratio:.1f}:1 ({level} 기준: {min_ratio}:1)",
                            description=f"텍스트와 배경색의 대비가 WCAG {level} 기준을 충족하지 않습니다",
                            element=str(element)[:200],
                            recommendation=f"색상 대비를 {min_ratio}:1 이상으로 조정하세요",
                            wcag_reference="WCAG 2.1 - 1.4.3 Contrast (Minimum)"
                        ))
        
        # 링크 색상 대비 확인
        links = soup.find_all('a', href=True)
        for link in links:
            # 링크가 주변 텍스트와 구분되는지 확인
            if not self._has_non_color_distinction(link):
                issues.append(AccessibilityIssue(
                    type=IssueType.VISUAL,
                    severity=SeverityLevel.LOW,
                    message="링크가 색상으로만 구분됩니다",
                    description="링크가 주변 텍스트와 색상으로만 구분되어 색각 이상자가 인식하기 어려울 수 있습니다",
                    element=str(link)[:200],
                    recommendation="밑줄, 굵기, 테두리 등 색상 외의 시각적 구분 요소를 추가하세요",
                    wcag_reference="WCAG 2.1 - 1.4.1 Use of Color"
                ))
        
        return issues
    
    def _check_color_only_information(self, soup: BeautifulSoup, url: str) -> List[AccessibilityIssue]:
        """색상만으로 정보를 전달하는지 검사합니다."""
        issues = []
        
        # 일반적인 색상 의존 패턴 찾기
        color_dependent_patterns = [
            (r'빨간색.*필수', '필수 필드 표시'),
            (r'red.*required', '필수 필드 표시'),
            (r'녹색.*성공', '성공 상태 표시'),
            (r'green.*success', '성공 상태 표시'),
            (r'빨간색.*오류', '오류 상태 표시'),
            (r'red.*error', '오류 상태 표시')
        ]
        
        page_text = soup.get_text().lower()
        
        for pattern, description in color_dependent_patterns:
            if re.search(pattern, page_text, re.IGNORECASE):
                issues.append(AccessibilityIssue(
                    type=IssueType.VISUAL,
                    severity=SeverityLevel.MEDIUM,
                    message=f"색상에만 의존하는 정보 전달: {description}",
                    description="정보가 색상에만 의존하여 전달되고 있습니다",
                    recommendation="색상과 함께 텍스트, 아이콘, 패턴 등을 사용하여 정보를 전달하세요",
                    wcag_reference="WCAG 2.1 - 1.4.1 Use of Color"
                ))
        
        # 차트나 그래프 요소 확인
        chart_elements = soup.find_all(attrs={'class': re.compile(r'chart|graph', re.I)})
        for chart in chart_elements:
            # 범례나 레이블이 있는지 확인
            has_text_labels = self._has_text_labels(chart)
            if not has_text_labels:
                issues.append(AccessibilityIssue(
                    type=IssueType.VISUAL,
                    severity=SeverityLevel.MEDIUM,
                    message="차트/그래프에 텍스트 레이블이 없습니다",
                    description="차트나 그래프가 색상만으로 정보를 전달하고 있습니다",
                    element=str(chart)[:200],
                    recommendation="차트에 텍스트 레이블, 패턴, 또는 상세한 데이터 테이블을 추가하세요",
                    wcag_reference="WCAG 2.1 - 1.4.1 Use of Color"
                ))
        
        return issues
    
    def _check_text_spacing(self, soup: BeautifulSoup, url: str) -> List[AccessibilityIssue]:
        """텍스트 간격을 검사합니다."""
        issues = []
        
        # 인라인 스타일에서 간격 관련 속성 확인
        elements_with_style = soup.find_all(attrs={'style': True})
        
        for element in elements_with_style:
            style = element.get('style', '').lower()
            
            # line-height 확인
            line_height_match = re.search(r'line-height\s*:\s*([^;]+)', style)
            if line_height_match:
                line_height = line_height_match.group(1).strip()
                if self._is_insufficient_line_height(line_height):
                    issues.append(AccessibilityIssue(
                        type=IssueType.VISUAL,
                        severity=SeverityLevel.LOW,
                        message=f"줄 간격이 부족합니다: {line_height}",
                        description="줄 간격이 1.5배 미만으로 설정되어 있습니다",
                        element=str(element)[:200],
                        recommendation="line-height를 1.5 이상으로 설정하세요",
                        wcag_reference="WCAG 2.1 - 1.4.12 Text Spacing"
                    ))
            
            # letter-spacing 확인
            letter_spacing_match = re.search(r'letter-spacing\s*:\s*([^;]+)', style)
            if letter_spacing_match:
                letter_spacing = letter_spacing_match.group(1).strip()
                if 'negative' in letter_spacing or letter_spacing.startswith('-'):
                    issues.append(AccessibilityIssue(
                        type=IssueType.VISUAL,
                        severity=SeverityLevel.LOW,
                        message="자간이 음수로 설정되었습니다",
                        description="negative letter-spacing은 가독성을 해칠 수 있습니다",
                        element=str(element)[:200],
                        recommendation="letter-spacing을 0 이상으로 설정하세요",
                        wcag_reference="WCAG 2.1 - 1.4.12 Text Spacing"
                    ))
        
        return issues
    
    def _check_resize_compatibility(self, soup: BeautifulSoup, url: str) -> List[AccessibilityIssue]:
        """확대/축소 호환성을 검사합니다."""
        issues = []
        
        # viewport meta 태그 확인
        viewport_meta = soup.find('meta', attrs={'name': 'viewport'})
        if viewport_meta:
            content = viewport_meta.get('content', '').lower()
            
            # user-scalable=no 확인
            if 'user-scalable=no' in content or 'user-scalable=0' in content:
                issues.append(AccessibilityIssue(
                    type=IssueType.VISUAL,
                    severity=SeverityLevel.HIGH,
                    message="사용자 확대/축소가 비활성화되었습니다",
                    description="viewport meta 태그에서 사용자 확대/축소를 막고 있습니다",
                    element=str(viewport_meta),
                    recommendation="user-scalable=no를 제거하거나 user-scalable=yes로 변경하세요",
                    wcag_reference="WCAG 2.1 - 1.4.4 Resize text"
                ))
            
            # maximum-scale 확인
            max_scale_match = re.search(r'maximum-scale\s*=\s*([0-9.]+)', content)
            if max_scale_match:
                max_scale = float(max_scale_match.group(1))
                if max_scale < 2.0:
                    issues.append(AccessibilityIssue(
                        type=IssueType.VISUAL,
                        severity=SeverityLevel.MEDIUM,
                        message=f"최대 확대 비율이 제한됨: {max_scale}",
                        description="maximum-scale이 2.0 미만으로 설정되어 충분한 확대가 불가능합니다",
                        element=str(viewport_meta),
                        recommendation="maximum-scale을 2.0 이상으로 설정하거나 제거하세요",
                        wcag_reference="WCAG 2.1 - 1.4.4 Resize text"
                    ))
        
        # 고정 크기 텍스트 확인
        elements_with_style = soup.find_all(attrs={'style': True})
        for element in elements_with_style:
            style = element.get('style', '')
            if self._has_fixed_font_size(style):
                issues.append(AccessibilityIssue(
                    type=IssueType.VISUAL,
                    severity=SeverityLevel.LOW,
                    message="픽셀 단위 고정 폰트 크기 사용",
                    description="px 단위로 폰트 크기가 고정되어 있어 확대 시 가독성이 떨어질 수 있습니다",
                    element=str(element)[:200],
                    recommendation="em, rem, % 등 상대적 단위를 사용하세요",
                    wcag_reference="WCAG 2.1 - 1.4.4 Resize text"
                ))
        
        return issues
    
    def _check_focus_indicators(self, soup: BeautifulSoup, url: str) -> List[AccessibilityIssue]:
        """포커스 표시를 검사합니다."""
        issues = []
        
        # CSS에서 outline: none 사용 확인
        style_tags = soup.find_all('style')
        for style_tag in style_tags:
            css_content = style_tag.get_text()
            if 'outline:none' in css_content.replace(' ', '') or 'outline:0' in css_content.replace(' ', ''):
                issues.append(AccessibilityIssue(
                    type=IssueType.VISUAL,
                    severity=SeverityLevel.MEDIUM,
                    message="CSS에서 outline이 제거되었습니다",
                    description="포커스 표시가 제거되어 키보드 사용자가 현재 위치를 파악하기 어려울 수 있습니다",
                    element=str(style_tag)[:200],
                    recommendation="outline을 제거하는 대신 커스텀 포커스 스타일을 제공하세요",
                    wcag_reference="WCAG 2.1 - 2.4.7 Focus Visible"
                ))
        
        # 인터랙티브 요소의 포커스 스타일 확인
        interactive_elements = soup.find_all(['a', 'button', 'input', 'select', 'textarea'])
        for element in interactive_elements:
            style = element.get('style', '')
            if 'outline:none' in style.replace(' ', '') or 'outline:0' in style.replace(' ', ''):
                # 대체 포커스 스타일이 있는지 확인
                has_custom_focus = self._has_custom_focus_style(element, style)
                if not has_custom_focus:
                    issues.append(AccessibilityIssue(
                        type=IssueType.VISUAL,
                        severity=SeverityLevel.MEDIUM,
                        message="포커스 표시가 제거되었습니다",
                        description="인터랙티브 요소에서 포커스 표시가 제거되었습니다",
                        element=str(element)[:200],
                        recommendation="커스텀 포커스 스타일을 제공하세요",
                        wcag_reference="WCAG 2.1 - 2.4.7 Focus Visible"
                    ))
        
        return issues
    
    def _check_motion_animation(self, soup: BeautifulSoup, url: str) -> List[AccessibilityIssue]:
        """모션과 애니메이션을 검사합니다."""
        issues = []
        
        # CSS 애니메이션 확인
        style_tags = soup.find_all('style')
        for style_tag in style_tags:
            css_content = style_tag.get_text().lower()
            
            # @keyframes 확인
            if '@keyframes' in css_content or 'animation:' in css_content:
                # prefers-reduced-motion 대응 확인
                if 'prefers-reduced-motion' not in css_content:
                    issues.append(AccessibilityIssue(
                        type=IssueType.VISUAL,
                        severity=SeverityLevel.LOW,
                        message="애니메이션에 모션 감소 선호 설정이 적용되지 않았습니다",
                        description="CSS 애니메이션이 prefers-reduced-motion 미디어 쿼리를 고려하지 않습니다",
                        element=str(style_tag)[:200],
                        recommendation="@media (prefers-reduced-motion: reduce) 쿼리를 추가하여 애니메이션을 비활성화하세요",
                        wcag_reference="WCAG 2.1 - 2.3.3 Animation from Interactions"
                    ))
        
        # 자동 슬라이드쇼나 회전 콘텐츠 확인
        carousel_elements = soup.find_all(attrs={'class': re.compile(r'carousel|slider|slideshow', re.I)})
        for carousel in carousel_elements:
            # 정지 버튼이나 컨트롤이 있는지 확인
            has_controls = self._has_carousel_controls(carousel)
            if not has_controls:
                issues.append(AccessibilityIssue(
                    type=IssueType.VISUAL,
                    severity=SeverityLevel.MEDIUM,
                    message="자동 회전 콘텐츠에 컨트롤이 없습니다",
                    description="자동으로 변경되는 콘텐츠에 일시정지나 제어 수단이 없습니다",
                    element=str(carousel)[:200],
                    recommendation="일시정지, 정지, 숨기기 버튼을 제공하세요",
                    wcag_reference="WCAG 2.1 - 2.2.2 Pause, Stop, Hide"
                ))
        
        return issues
    
    def _check_flashing_content(self, soup: BeautifulSoup, url: str) -> List[AccessibilityIssue]:
        """깜박이는 콘텐츠를 검사합니다."""
        issues = []
        
        # blink 태그 확인 (deprecated)
        blink_elements = soup.find_all('blink')
        if blink_elements:
            issues.append(AccessibilityIssue(
                type=IssueType.VISUAL,
                severity=SeverityLevel.HIGH,
                message="blink 태그 사용",
                description="깜박이는 blink 태그는 발작을 유발할 수 있습니다",
                element=str(blink_elements[0])[:200],
                recommendation="blink 태그를 제거하고 다른 방법으로 주의를 끌어보세요",
                wcag_reference="WCAG 2.1 - 2.3.1 Three Flashes or Below Threshold"
            ))
        
        # marquee 태그 확인 (deprecated)
        marquee_elements = soup.find_all('marquee')
        if marquee_elements:
            issues.append(AccessibilityIssue(
                type=IssueType.VISUAL,
                severity=SeverityLevel.MEDIUM,
                message="marquee 태그 사용",
                description="움직이는 marquee 태그는 접근성 문제를 일으킬 수 있습니다",
                element=str(marquee_elements[0])[:200],
                recommendation="marquee 태그를 제거하고 CSS 애니메이션을 사용하되 prefers-reduced-motion을 고려하세요",
                wcag_reference="WCAG 2.1 - 2.2.2 Pause, Stop, Hide"
            ))
        
        # CSS에서 빠른 깜박임 확인
        style_tags = soup.find_all('style')
        for style_tag in style_tags:
            css_content = style_tag.get_text()
            # 매우 빠른 애니메이션 (0.5초 미만) 확인
            fast_animation_pattern = r'animation-duration\s*:\s*0\.[0-4]s'
            if re.search(fast_animation_pattern, css_content):
                issues.append(AccessibilityIssue(
                    type=IssueType.VISUAL,
                    severity=SeverityLevel.MEDIUM,
                    message="매우 빠른 애니메이션",
                    description="0.5초 미만의 빠른 애니메이션은 발작을 유발할 수 있습니다",
                    element=str(style_tag)[:200],
                    recommendation="애니메이션 속도를 늦추거나 prefers-reduced-motion을 고려하세요",
                    wcag_reference="WCAG 2.1 - 2.3.1 Three Flashes or Below Threshold"
                ))
        
        return issues
    
    def _check_visual_layout(self, soup: BeautifulSoup, url: str) -> List[AccessibilityIssue]:
        """시각적 레이아웃을 검사합니다."""
        issues = []
        
        # 매우 긴 줄 길이 확인
        elements_with_style = soup.find_all(attrs={'style': True})
        for element in elements_with_style:
            style = element.get('style', '')
            width_match = re.search(r'width\s*:\s*([^;]+)', style)
            if width_match:
                width = width_match.group(1).strip()
                if self._is_excessive_width(width):
                    text_content = element.get_text(strip=True)
                    if len(text_content) > 100:  # 충분한 텍스트가 있는 경우만
                        issues.append(AccessibilityIssue(
                            type=IssueType.VISUAL,
                            severity=SeverityLevel.LOW,
                            message=f"텍스트 줄이 너무 깁니다: {width}",
                            description="긴 텍스트 줄은 가독성을 떨어뜨릴 수 있습니다",
                            element=str(element)[:200],
                            recommendation="텍스트 컨테이너의 최대 너비를 80자 정도로 제한하세요",
                            wcag_reference="WCAG 2.1 - 1.4.8 Visual Presentation"
                        ))
        
        # 양쪽 정렬 텍스트 확인
        for element in elements_with_style:
            style = element.get('style', '')
            if 'text-align:justify' in style.replace(' ', ''):
                issues.append(AccessibilityIssue(
                    type=IssueType.VISUAL,
                    severity=SeverityLevel.LOW,
                    message="양쪽 정렬 텍스트 사용",
                    description="양쪽 정렬은 단어 간격을 불규칙하게 만들어 가독성을 해칠 수 있습니다",
                    element=str(element)[:200],
                    recommendation="왼쪽 정렬을 사용하는 것이 좋습니다",
                    wcag_reference="WCAG 2.1 - 1.4.8 Visual Presentation"
                ))
        
        return issues
    
    def _extract_colors_from_style(self, style: str) -> Dict[str, str]:
        """스타일에서 색상 정보를 추출합니다."""
        colors = {'color': None, 'background': None}
        
        # color 속성
        color_match = re.search(r'color\s*:\s*([^;]+)', style, re.IGNORECASE)
        if color_match:
            colors['color'] = color_match.group(1).strip()
        
        # background-color 속성
        bg_match = re.search(r'background-color\s*:\s*([^;]+)', style, re.IGNORECASE)
        if bg_match:
            colors['background'] = bg_match.group(1).strip()
        
        # background 단축 속성에서 색상 추출
        elif 'background:' in style.lower():
            bg_match = re.search(r'background\s*:\s*([^;]+)', style, re.IGNORECASE)
            if bg_match:
                bg_value = bg_match.group(1).strip()
                # 색상 값만 추출 (간단한 휴리스틱)
                color_in_bg = self._extract_color_from_background(bg_value)
                if color_in_bg:
                    colors['background'] = color_in_bg
        
        return colors
    
    def _extract_color_from_background(self, bg_value: str) -> str:
        """background 속성에서 색상만 추출합니다."""
        # 간단한 색상 패턴 찾기
        color_patterns = [
            r'#[0-9a-fA-F]{3,6}',  # hex
            r'rgb\([^)]+\)',       # rgb
            r'rgba\([^)]+\)',      # rgba
            r'hsl\([^)]+\)',       # hsl
            r'hsla\([^)]+\)'       # hsla
        ]
        
        for pattern in color_patterns:
            match = re.search(pattern, bg_value)
            if match:
                return match.group(0)
        
        # 색상 키워드 확인
        for keyword in self.color_keywords:
            if keyword in bg_value.lower():
                return self.color_keywords[keyword]
        
        return None
    
    def _calculate_contrast_ratio(self, color1: str, color2: str) -> float:
        """두 색상 간의 대비율을 계산합니다."""
        try:
            rgb1 = self._parse_color(color1)
            rgb2 = self._parse_color(color2)
            
            if rgb1 and rgb2:
                luminance1 = self._calculate_luminance(rgb1)
                luminance2 = self._calculate_luminance(rgb2)
                
                lighter = max(luminance1, luminance2)
                darker = min(luminance1, luminance2)
                
                return (lighter + 0.05) / (darker + 0.05)
        except:
            pass
        
        return None
    
    def _parse_color(self, color: str) -> Tuple[int, int, int]:
        """색상 문자열을 RGB 값으로 변환합니다."""
        color = color.strip().lower()
        
        # 키워드 색상
        if color in self.color_keywords:
            hex_color = self.color_keywords[color]
            if hex_color.startswith('#'):
                return self._hex_to_rgb(hex_color)
        
        # hex 색상
        if color.startswith('#'):
            return self._hex_to_rgb(color)
        
        # rgb 색상
        rgb_match = re.match(r'rgb\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)', color)
        if rgb_match:
            return (int(rgb_match.group(1)), int(rgb_match.group(2)), int(rgb_match.group(3)))
        
        return None
    
    def _hex_to_rgb(self, hex_color: str) -> Tuple[int, int, int]:
        """hex 색상을 RGB로 변환합니다."""
        hex_color = hex_color.lstrip('#')
        
        if len(hex_color) == 3:
            hex_color = ''.join([c*2 for c in hex_color])
        
        if len(hex_color) == 6:
            return (
                int(hex_color[0:2], 16),
                int(hex_color[2:4], 16),
                int(hex_color[4:6], 16)
            )
        
        return None
    
    def _calculate_luminance(self, rgb: Tuple[int, int, int]) -> float:
        """RGB 값으로부터 상대 휘도를 계산합니다."""
        def normalize_component(c):
            c = c / 255.0
            if c <= 0.03928:
                return c / 12.92
            else:
                return pow((c + 0.055) / 1.055, 2.4)
        
        r, g, b = rgb
        return 0.2126 * normalize_component(r) + 0.7152 * normalize_component(g) + 0.0722 * normalize_component(b)
    
    def _is_large_text(self, element: Tag, style: str) -> bool:
        """큰 텍스트인지 확인합니다."""
        # font-size 확인
        font_size_match = re.search(r'font-size\s*:\s*([^;]+)', style)
        if font_size_match:
            size = font_size_match.group(1).strip()
            if 'px' in size:
                px_value = float(size.replace('px', ''))
                return px_value >= self.large_text_size_px
            elif 'pt' in size:
                pt_value = float(size.replace('pt', ''))
                return pt_value >= self.large_text_size_pt
        
        # font-weight 확인
        font_weight_match = re.search(r'font-weight\s*:\s*([^;]+)', style)
        if font_weight_match:
            weight = font_weight_match.group(1).strip().lower()
            if weight in ['bold', '700', '800', '900']:
                # bold이면서 14pt 이상이면 큰 텍스트
                if font_size_match:
                    size = font_size_match.group(1).strip()
                    if 'pt' in size:
                        pt_value = float(size.replace('pt', ''))
                        return pt_value >= 14
                    elif 'px' in size:
                        px_value = float(size.replace('px', ''))
                        return px_value >= 18  # 대략 14pt
        
        return False
    
    def _has_non_color_distinction(self, link: Tag) -> bool:
        """링크가 색상 외의 구분 요소를 가지는지 확인합니다."""
        style = link.get('style', '').lower()
        
        # text-decoration 확인
        if 'text-decoration' in style and 'none' not in style:
            return True
        
        # font-weight 확인
        if 'font-weight' in style and any(weight in style for weight in ['bold', '700', '800', '900']):
            return True
        
        # border 확인
        if 'border' in style and 'none' not in style:
            return True
        
        return False
    
    def _has_text_labels(self, chart: Tag) -> bool:
        """차트에 텍스트 레이블이 있는지 확인합니다."""
        # 차트 내부나 근처에 텍스트 설명이 있는지 확인
        text_content = chart.get_text(strip=True)
        if len(text_content) > 20:  # 충분한 텍스트가 있는 경우
            return True
        
        # 형제 요소에서 테이블이나 목록 확인
        parent = chart.find_parent()
        if parent:
            tables = parent.find_all('table')
            lists = parent.find_all(['ul', 'ol', 'dl'])
            if tables or lists:
                return True
        
        return False
    
    def _is_insufficient_line_height(self, line_height: str) -> bool:
        """줄 간격이 부족한지 확인합니다."""
        try:
            # 숫자만 있는 경우 (배수)
            if line_height.replace('.', '').isdigit():
                return float(line_height) < 1.5
            
            # % 단위
            if line_height.endswith('%'):
                return float(line_height.rstrip('%')) < 150
            
            # 기타 단위는 판단하기 어려우므로 false 반환
            return False
        except:
            return False
    
    def _has_fixed_font_size(self, style: str) -> bool:
        """고정 픽셀 폰트 크기를 사용하는지 확인합니다."""
        font_size_match = re.search(r'font-size\s*:\s*([^;]+)', style)
        if font_size_match:
            size = font_size_match.group(1).strip()
            return size.endswith('px')
        return False
    
    def _has_custom_focus_style(self, element: Tag, style: str) -> bool:
        """커스텀 포커스 스타일이 있는지 확인합니다."""
        # border, box-shadow, background 등의 포커스 스타일 확인
        focus_properties = ['border', 'box-shadow', 'background']
        return any(prop in style.lower() for prop in focus_properties)
    
    def _has_carousel_controls(self, carousel: Tag) -> bool:
        """캐러셀에 컨트롤이 있는지 확인합니다."""
        # 정지, 일시정지 버튼 찾기
        control_keywords = ['pause', 'stop', 'play', 'prev', 'next', '정지', '일시정지', '재생']
        
        buttons = carousel.find_all('button')
        for button in buttons:
            button_text = button.get_text().lower()
            aria_label = button.get('aria-label', '').lower()
            title = button.get('title', '').lower()
            
            all_text = f"{button_text} {aria_label} {title}"
            if any(keyword in all_text for keyword in control_keywords):
                return True
        
        return False
    
    def _is_excessive_width(self, width: str) -> bool:
        """과도한 너비인지 확인합니다."""
        try:
            # 절대 단위 확인
            if width.endswith('px'):
                px_value = float(width.rstrip('px'))
                return px_value > 1200  # 80자 * 15px 대략
            
            # 퍼센트 확인
            if width.endswith('%'):
                percent_value = float(width.rstrip('%'))
                return percent_value > 80
            
            # vw 단위 확인
            if width.endswith('vw'):
                vw_value = float(width.rstrip('vw'))
                return vw_value > 80
        except:
            pass
        
        return False
    
    def _calculate_score(self, issues: List[AccessibilityIssue], total_checks: int) -> float:
        """점수를 계산합니다."""
        if total_checks == 0:
            return 100.0
        
        # 심각도별 가중치
        severity_weights = {
            SeverityLevel.CRITICAL: 10,
            SeverityLevel.HIGH: 6,
            SeverityLevel.MEDIUM: 3,
            SeverityLevel.LOW: 1
        }
        
        # 총 감점 계산
        total_penalty = sum(severity_weights.get(issue.severity, 0) for issue in issues)
        
        # 기본 점수에서 감점
        base_score = 100.0
        final_score = max(0.0, base_score - total_penalty)
        
        return round(final_score, 1)