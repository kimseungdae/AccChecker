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

class MediaChecker:
    """미디어(동영상, 오디오) 접근성을 검사하는 클래스"""
    
    def __init__(self):
        self.supported_caption_formats = {'.vtt', '.srt', '.webvtt'}
        self.media_elements = {'video', 'audio', 'embed', 'object', 'iframe'}
    
    async def check(self, html_content: str, url: str, page_info: Dict[str, Any]) -> CheckerResult:
        """미디어 접근성 검사를 수행합니다."""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            result = CheckerResult()
            
            # 각 검사 수행
            checks = [
                self._check_video_captions,
                self._check_audio_transcripts,
                self._check_autoplay_settings,
                self._check_media_controls,
                self._check_media_descriptions,
                self._check_embedded_media,
                self._check_media_alternatives,
                self._check_live_captions
            ]
            
            for check_func in checks:
                issues = check_func(soup, url)
                result.issues.extend(issues)
                result.total_checks += 1
                if not issues:
                    result.passed_checks += 1
            
            # 점수 계산
            result.score = self._calculate_score(result.issues, result.total_checks)
            
            logger.info(f"미디어 접근성 검사 완료: {len(result.issues)}개 이슈 발견")
            return result
            
        except Exception as e:
            logger.error(f"미디어 접근성 검사 중 오류 발생: {str(e)}")
            result = CheckerResult()
            result.issues.append(AccessibilityIssue(
                type=IssueType.MEDIA,
                severity=SeverityLevel.HIGH,
                message="미디어 접근성 검사 실행 오류",
                description=f"검사 중 오류가 발생했습니다: {str(e)}",
                recommendation="개발자에게 문의하세요."
            ))
            return result
    
    def _check_video_captions(self, soup: BeautifulSoup, url: str) -> List[AccessibilityIssue]:
        """비디오 자막 제공 여부를 검사합니다."""
        issues = []
        
        videos = soup.find_all('video')
        
        for video in videos:
            # track 요소 확인
            tracks = video.find_all('track')
            caption_tracks = [track for track in tracks if track.get('kind') in ['captions', 'subtitles']]
            
            if not caption_tracks:
                issues.append(AccessibilityIssue(
                    type=IssueType.MEDIA,
                    severity=SeverityLevel.HIGH,
                    message="비디오에 자막이 없습니다",
                    description="video 요소에 자막을 제공하는 track 요소가 없습니다",
                    element=str(video)[:200],
                    recommendation="<track kind='captions' src='captions.vtt'> 요소를 추가하여 자막을 제공하세요",
                    wcag_reference="WCAG 2.1 - 1.2.2 Captions (Prerecorded)"
                ))
            else:
                # 자막 파일 형식 확인
                for track in caption_tracks:
                    src = track.get('src', '')
                    if src:
                        file_ext = '.' + src.split('.')[-1].lower() if '.' in src else ''
                        if file_ext not in self.supported_caption_formats:
                            issues.append(AccessibilityIssue(
                                type=IssueType.MEDIA,
                                severity=SeverityLevel.MEDIUM,
                                message=f"지원되지 않는 자막 형식: {file_ext}",
                                description="WebVTT(.vtt) 형식의 자막 파일을 사용하는 것이 권장됩니다",
                                element=str(track)[:200],
                                recommendation="자막 파일을 WebVTT(.vtt) 형식으로 변환하세요",
                                wcag_reference="WCAG 2.1 - 1.2.2 Captions (Prerecorded)"
                            ))
                    
                    # srclang 속성 확인
                    if not track.get('srclang'):
                        issues.append(AccessibilityIssue(
                            type=IssueType.MEDIA,
                            severity=SeverityLevel.MEDIUM,
                            message="track 요소에 srclang 속성이 없습니다",
                            description="자막의 언어를 명시하는 srclang 속성이 없습니다",
                            element=str(track)[:200],
                            recommendation="track 요소에 srclang 속성을 추가하세요 (예: srclang='ko')",
                            wcag_reference="WCAG 2.1 - 1.2.2 Captions (Prerecorded)"
                        ))
                    
                    # label 속성 확인
                    if not track.get('label'):
                        issues.append(AccessibilityIssue(
                            type=IssueType.MEDIA,
                            severity=SeverityLevel.LOW,
                            message="track 요소에 label 속성이 없습니다",
                            description="자막 트랙의 설명을 제공하는 label 속성이 없습니다",
                            element=str(track)[:200],
                            recommendation="track 요소에 label 속성을 추가하세요 (예: label='한국어 자막')",
                            wcag_reference="WCAG 2.1 - 1.2.2 Captions (Prerecorded)"
                        ))
        
        return issues
    
    def _check_audio_transcripts(self, soup: BeautifulSoup, url: str) -> List[AccessibilityIssue]:
        """오디오 대본 제공 여부를 검사합니다."""
        issues = []
        
        audios = soup.find_all('audio')
        
        for audio in audios:
            # 대본 링크나 텍스트 확인
            has_transcript = self._has_transcript_nearby(audio)
            
            if not has_transcript:
                issues.append(AccessibilityIssue(
                    type=IssueType.MEDIA,
                    severity=SeverityLevel.HIGH,
                    message="오디오에 대본이 없습니다",
                    description="audio 요소에 대본이나 텍스트 대안이 제공되지 않았습니다",
                    element=str(audio)[:200],
                    recommendation="오디오 내용의 대본을 텍스트로 제공하거나 대본 링크를 추가하세요",
                    wcag_reference="WCAG 2.1 - 1.2.1 Audio-only and Video-only (Prerecorded)"
                ))
        
        return issues
    
    def _check_autoplay_settings(self, soup: BeautifulSoup, url: str) -> List[AccessibilityIssue]:
        """자동재생 설정을 검사합니다."""
        issues = []
        
        media_elements = soup.find_all(['video', 'audio'])
        
        for media in media_elements:
            autoplay = media.get('autoplay')
            muted = media.get('muted')
            
            if autoplay is not None:
                # 음성이 있는 미디어의 자동재생
                if media.name == 'video' or (media.name == 'audio'):
                    if muted is None:
                        issues.append(AccessibilityIssue(
                            type=IssueType.MEDIA,
                            severity=SeverityLevel.HIGH,
                            message="소리가 있는 미디어가 자동재생됩니다",
                            description="음성이 포함된 미디어가 자동으로 재생되어 사용자를 방해할 수 있습니다",
                            element=str(media)[:200],
                            recommendation="autoplay를 제거하거나 muted 속성을 추가하고 사용자 컨트롤을 제공하세요",
                            wcag_reference="WCAG 2.1 - 1.4.2 Audio Control"
                        ))
                
                # 3초 이상 재생되는 미디어
                duration = self._estimate_duration(media)
                if duration is None or duration > 3:
                    issues.append(AccessibilityIssue(
                        type=IssueType.MEDIA,
                        severity=SeverityLevel.MEDIUM,
                        message="3초 이상 자동재생되는 미디어",
                        description="3초 이상 자동재생되는 미디어는 정지 버튼이 필요합니다",
                        element=str(media)[:200],
                        recommendation="미디어 컨트롤을 제공하거나 자동재생을 비활성화하세요",
                        wcag_reference="WCAG 2.1 - 1.4.2 Audio Control"
                    ))
        
        return issues
    
    def _check_media_controls(self, soup: BeautifulSoup, url: str) -> List[AccessibilityIssue]:
        """미디어 컨트롤의 접근성을 검사합니다."""
        issues = []
        
        media_elements = soup.find_all(['video', 'audio'])
        
        for media in media_elements:
            controls = media.get('controls')
            
            if controls is None:
                # 커스텀 컨트롤이 있는지 확인
                has_custom_controls = self._has_custom_controls(media)
                
                if not has_custom_controls:
                    issues.append(AccessibilityIssue(
                        type=IssueType.MEDIA,
                        severity=SeverityLevel.HIGH,
                        message="미디어 컨트롤이 없습니다",
                        description="미디어 요소에 컨트롤이나 사용자 인터페이스가 제공되지 않았습니다",
                        element=str(media)[:200],
                        recommendation="controls 속성을 추가하거나 키보드로 접근 가능한 커스텀 컨트롤을 제공하세요",
                        wcag_reference="WCAG 2.1 - 2.1.1 Keyboard"
                    ))
            
            # 키보드 접근성 확인
            if controls is not None:
                # 브라우저 기본 컨트롤은 일반적으로 키보드 접근 가능
                pass
            else:
                # 커스텀 컨트롤의 키보드 접근성은 별도 검사 필요
                pass
        
        return issues
    
    def _check_media_descriptions(self, soup: BeautifulSoup, url: str) -> List[AccessibilityIssue]:
        """미디어 설명(audio description) 제공 여부를 검사합니다."""
        issues = []
        
        videos = soup.find_all('video')
        
        for video in videos:
            # 음성 해설 트랙 확인
            tracks = video.find_all('track')
            description_tracks = [track for track in tracks if track.get('kind') == 'descriptions']
            
            # 비디오가 시각적 정보를 포함하는지 추정
            if self._likely_contains_visual_info(video):
                if not description_tracks:
                    issues.append(AccessibilityIssue(
                        type=IssueType.MEDIA,
                        severity=SeverityLevel.MEDIUM,
                        message="비디오에 음성 해설이 없습니다",
                        description="시각적 정보가 포함된 비디오에 음성 해설 트랙이 없습니다",
                        element=str(video)[:200],
                        recommendation="<track kind='descriptions'> 요소를 추가하여 음성 해설을 제공하세요",
                        wcag_reference="WCAG 2.1 - 1.2.5 Audio Description (Prerecorded)"
                    ))
        
        return issues
    
    def _check_embedded_media(self, soup: BeautifulSoup, url: str) -> List[AccessibilityIssue]:
        """임베디드 미디어(YouTube, Vimeo 등)의 접근성을 검사합니다."""
        issues = []
        
        iframes = soup.find_all('iframe')
        
        for iframe in iframes:
            src = iframe.get('src', '')
            
            # 미디어 플랫폼 확인
            if self._is_media_iframe(src):
                # title 속성 확인
                title = iframe.get('title')
                if not title:
                    issues.append(AccessibilityIssue(
                        type=IssueType.MEDIA,
                        severity=SeverityLevel.MEDIUM,
                        message="임베디드 미디어에 title이 없습니다",
                        description="iframe으로 임베디드된 미디어에 설명적인 title이 없습니다",
                        element=str(iframe)[:200],
                        recommendation="iframe에 미디어 내용을 설명하는 title 속성을 추가하세요",
                        wcag_reference="WCAG 2.1 - 2.4.1 Bypass Blocks"
                    ))
                
                # 대체 콘텐츠 확인
                iframe_text = iframe.get_text(strip=True)
                if not iframe_text:
                    issues.append(AccessibilityIssue(
                        type=IssueType.MEDIA,
                        severity=SeverityLevel.LOW,
                        message="임베디드 미디어에 대체 콘텐츠가 없습니다",
                        description="iframe이 지원되지 않을 때 표시할 대체 콘텐츠가 없습니다",
                        element=str(iframe)[:200],
                        recommendation="iframe 태그 내부에 대체 콘텐츠나 링크를 제공하세요",
                        wcag_reference="WCAG 2.1 - 1.1.1 Non-text Content"
                    ))
        
        # embed, object 태그 확인
        embeds = soup.find_all(['embed', 'object'])
        for embed in embeds:
            if self._is_media_embed(embed):
                # 대체 텍스트나 콘텐츠 확인
                has_alternative = (
                    embed.get('alt') or
                    embed.get('title') or
                    embed.get_text(strip=True)
                )
                
                if not has_alternative:
                    issues.append(AccessibilityIssue(
                        type=IssueType.MEDIA,
                        severity=SeverityLevel.MEDIUM,
                        message="임베디드 미디어에 대체 텍스트가 없습니다",
                        description="embed/object 요소에 대체 텍스트나 설명이 없습니다",
                        element=str(embed)[:200],
                        recommendation="대체 텍스트나 미디어 설명을 제공하세요",
                        wcag_reference="WCAG 2.1 - 1.1.1 Non-text Content"
                    ))
        
        return issues
    
    def _check_media_alternatives(self, soup: BeautifulSoup, url: str) -> List[AccessibilityIssue]:
        """미디어 대안 제공 여부를 검사합니다."""
        issues = []
        
        all_media = soup.find_all(['video', 'audio', 'iframe'])
        
        for media in all_media:
            # 텍스트 대안이나 링크 확인
            has_text_alternative = self._has_text_alternative_nearby(media)
            
            # 동영상의 경우 썸네일이나 스크린샷 확인
            if media.name == 'video':
                poster = media.get('poster')
                if not poster and not has_text_alternative:
                    issues.append(AccessibilityIssue(
                        type=IssueType.MEDIA,
                        severity=SeverityLevel.LOW,
                        message="비디오에 포스터 이미지가 없습니다",
                        description="비디오에 미리보기 이미지(포스터)가 제공되지 않았습니다",
                        element=str(media)[:200],
                        recommendation="poster 속성을 추가하여 비디오 미리보기 이미지를 제공하세요",
                        wcag_reference="WCAG 2.1 - 1.1.1 Non-text Content"
                    ))
        
        return issues
    
    def _check_live_captions(self, soup: BeautifulSoup, url: str) -> List[AccessibilityIssue]:
        """라이브 미디어의 자막 제공 여부를 검사합니다."""
        issues = []
        
        # 라이브 스트리밍 관련 요소나 속성 확인
        live_indicators = soup.find_all(attrs={'class': re.compile(r'live|stream', re.I)})
        
        for element in live_indicators:
            media = element.find(['video', 'audio', 'iframe'])
            if media:
                # 라이브 자막 제공 여부 확인 (실제로는 더 정교한 검사 필요)
                has_live_captions = self._has_live_captions(element)
                
                if not has_live_captions:
                    issues.append(AccessibilityIssue(
                        type=IssueType.MEDIA,
                        severity=SeverityLevel.MEDIUM,
                        message="라이브 미디어에 실시간 자막이 없을 수 있습니다",
                        description="라이브 스트리밍 콘텐츠에 실시간 자막 제공이 확인되지 않았습니다",
                        element=str(element)[:200],
                        recommendation="라이브 콘텐츠에 실시간 자막을 제공하세요",
                        wcag_reference="WCAG 2.1 - 1.2.4 Captions (Live)"
                    ))
        
        return issues
    
    def _has_transcript_nearby(self, audio: Tag) -> bool:
        """오디오 근처에 대본이 있는지 확인합니다."""
        # 부모 요소나 형제 요소에서 대본 관련 텍스트 찾기
        parent = audio.find_parent()
        if parent:
            text_content = parent.get_text().lower()
            transcript_keywords = ['transcript', '대본', '스크립트', 'script']
            
            for keyword in transcript_keywords:
                if keyword in text_content:
                    return True
            
            # 대본 링크 확인
            links = parent.find_all('a', href=True)
            for link in links:
                link_text = link.get_text().lower()
                href = link.get('href', '').lower()
                
                for keyword in transcript_keywords:
                    if keyword in link_text or keyword in href:
                        return True
        
        return False
    
    def _estimate_duration(self, media: Tag) -> float:
        """미디어의 재생 시간을 추정합니다."""
        # duration 속성이 있는 경우
        duration = media.get('duration')
        if duration:
            try:
                return float(duration)
            except ValueError:
                pass
        
        # 실제로는 미디어 파일을 분석해야 하지만, 
        # 여기서는 추정 불가로 처리
        return None
    
    def _has_custom_controls(self, media: Tag) -> bool:
        """커스텀 미디어 컨트롤이 있는지 확인합니다."""
        # 부모나 형제 요소에서 컨트롤 버튼 찾기
        parent = media.find_parent()
        if parent:
            buttons = parent.find_all('button')
            control_keywords = ['play', 'pause', 'stop', 'volume', '재생', '정지', '볼륨']
            
            for button in buttons:
                button_text = button.get_text().lower()
                for keyword in control_keywords:
                    if keyword in button_text:
                        return True
                
                # aria-label이나 title 확인
                aria_label = (button.get('aria-label', '') + ' ' + button.get('title', '')).lower()
                for keyword in control_keywords:
                    if keyword in aria_label:
                        return True
        
        return False
    
    def _likely_contains_visual_info(self, video: Tag) -> bool:
        """비디오가 시각적 정보를 포함할 가능성이 높은지 확인합니다."""
        # 간단한 휴리스틱 - 실제로는 더 정교한 분석 필요
        
        # 비디오 소스나 제목에서 키워드 확인
        src = video.get('src', '')
        title = video.get('title', '')
        
        visual_keywords = [
            'tutorial', 'demo', 'presentation', 'lecture', 'documentary',
            '튜토리얼', '데모', '발표', '강의', '다큐멘터리'
        ]
        
        content = (src + ' ' + title).lower()
        for keyword in visual_keywords:
            if keyword in content:
                return True
        
        # 기본적으로 시각적 정보가 있다고 가정
        return True
    
    def _is_media_iframe(self, src: str) -> bool:
        """iframe이 미디어 콘텐츠인지 확인합니다."""
        media_domains = [
            'youtube.com', 'youtu.be', 'vimeo.com', 'dailymotion.com',
            'twitch.tv', 'soundcloud.com', 'spotify.com'
        ]
        
        src_lower = src.lower()
        return any(domain in src_lower for domain in media_domains)
    
    def _is_media_embed(self, embed: Tag) -> bool:
        """embed/object 요소가 미디어인지 확인합니다."""
        # type 속성 확인
        type_attr = embed.get('type', '')
        if any(media_type in type_attr for media_type in ['video', 'audio']):
            return True
        
        # src나 data 속성에서 미디어 파일 확장자 확인
        src = embed.get('src', '') + embed.get('data', '')
        media_extensions = ['.mp4', '.avi', '.mov', '.wmv', '.mp3', '.wav', '.ogg']
        
        return any(ext in src.lower() for ext in media_extensions)
    
    def _has_text_alternative_nearby(self, media: Tag) -> bool:
        """미디어 근처에 텍스트 대안이 있는지 확인합니다."""
        parent = media.find_parent()
        if parent:
            # 형제 요소들에서 대안 콘텐츠 찾기
            siblings = list(parent.children)
            for sibling in siblings:
                if hasattr(sibling, 'get_text'):
                    text = sibling.get_text(strip=True)
                    if len(text) > 50:  # 충분한 길이의 텍스트
                        return True
        
        return False
    
    def _has_live_captions(self, element: Tag) -> bool:
        """라이브 자막 제공 여부를 확인합니다."""
        # 라이브 자막 관련 키워드나 클래스 확인
        text_content = element.get_text().lower()
        css_classes = ' '.join(element.get('class', [])).lower()
        
        live_caption_keywords = [
            'live caption', 'real-time caption', 'closed caption',
            '실시간 자막', '라이브 자막', '동시 자막'
        ]
        
        content = text_content + ' ' + css_classes
        return any(keyword in content for keyword in live_caption_keywords)
    
    def _calculate_score(self, issues: List[AccessibilityIssue], total_checks: int) -> float:
        """점수를 계산합니다."""
        if total_checks == 0:
            return 100.0
        
        # 심각도별 가중치
        severity_weights = {
            SeverityLevel.CRITICAL: 15,
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