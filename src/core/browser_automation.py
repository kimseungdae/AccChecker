import asyncio
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class BrowserManager:
    def __init__(self):
        self.driver: Optional[webdriver.Chrome] = None
        self.options = self._setup_chrome_options()
    
    def _setup_chrome_options(self) -> Options:
        """Chrome 브라우저 옵션을 설정합니다."""
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--disable-web-security')
        options.add_argument('--disable-features=VizDisplayCompositor')
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        return options
    
    async def get_driver(self) -> webdriver.Chrome:
        """WebDriver 인스턴스를 생성하고 반환합니다."""
        if self.driver is None:
            try:
                service = Service(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=self.options)
                logger.info("Chrome WebDriver 초기화 완료")
            except Exception as e:
                logger.error(f"WebDriver 초기화 실패: {str(e)}")
                raise
        
        return self.driver
    
    async def load_page(self, driver: webdriver.Chrome, url: str, wait_time: int = 5) -> None:
        """지정된 URL의 페이지를 로드합니다."""
        try:
            driver.get(url)
            
            # 페이지 로딩 대기
            WebDriverWait(driver, wait_time).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # 추가 대기 시간 (JavaScript 실행 완료 대기)
            await asyncio.sleep(2)
            
            logger.info(f"페이지 로드 완료: {url}")
            
        except Exception as e:
            logger.error(f"페이지 로드 실패: {url} - {str(e)}")
            raise
    
    async def get_page_info(self, driver: webdriver.Chrome) -> Dict[str, Any]:
        """페이지의 기본 정보를 수집합니다."""
        try:
            return {
                'title': driver.title,
                'url': driver.current_url,
                'viewport_size': driver.get_window_size(),
                'page_source_length': len(driver.page_source),
                'has_javascript': self._check_javascript_enabled(driver),
                'language': driver.execute_script("return document.documentElement.lang || 'unknown'"),
                'charset': driver.execute_script("return document.characterSet || 'unknown'")
            }
        except Exception as e:
            logger.error(f"페이지 정보 수집 실패: {str(e)}")
            return {}
    
    def _check_javascript_enabled(self, driver: webdriver.Chrome) -> bool:
        """JavaScript가 활성화되어 있는지 확인합니다."""
        try:
            return driver.execute_script("return true")
        except:
            return False
    
    async def take_screenshot(self, driver: webdriver.Chrome, filename: str) -> bool:
        """페이지 스크린샷을 캡처합니다."""
        try:
            driver.save_screenshot(filename)
            logger.info(f"스크린샷 저장 완료: {filename}")
            return True
        except Exception as e:
            logger.error(f"스크린샷 저장 실패: {str(e)}")
            return False
    
    async def get_element_screenshot(self, driver: webdriver.Chrome, element, filename: str) -> bool:
        """특정 요소의 스크린샷을 캡처합니다."""
        try:
            element.screenshot(filename)
            logger.info(f"요소 스크린샷 저장 완료: {filename}")
            return True
        except Exception as e:
            logger.error(f"요소 스크린샷 저장 실패: {str(e)}")
            return False
    
    async def cleanup(self) -> None:
        """WebDriver를 정리합니다."""
        if self.driver:
            try:
                self.driver.quit()
                self.driver = None
                logger.info("WebDriver 정리 완료")
            except Exception as e:
                logger.error(f"WebDriver 정리 실패: {str(e)}")
    
    def __del__(self):
        """소멸자에서 정리 작업을 수행합니다."""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass