from playwright.async_api import async_playwright, Browser, BrowserContext, Page, Playwright


class AsyncBrowserManager:
    def __init__(self, headless=True, navigation_timeout: int = 60000, action_timeout: int = 30000):
        self.headless = headless
        self.navigation_timeout = navigation_timeout
        self.action_timeout = action_timeout
        self.playwright: Playwright | None = None
        self.browser: Browser | None = None
        self.context: BrowserContext | None = None

    async def start(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=self.headless)
        self.context = await self.browser.new_context()

    async def new_page(self) -> Page:
        if self.context is None:
            raise RuntimeError('Browser context no iniciado')
        try:
            page = await self.context.new_page()
            page.set_default_navigation_timeout(self.navigation_timeout)
            page.set_default_timeout(self.action_timeout)
            return page
        except Exception as exc:
            # Si el contexto se cerró, marcar como None para que se recree
            if 'closed' in str(exc).lower() or 'target' in str(exc).lower():
                self.context = None
            raise
    
    async def is_context_alive(self) -> bool:
        """Check if browser context is still alive."""
        if self.context is None:
            return False
        try:
            # Try to create a test page to verify context is alive
            page = await self.context.new_page()
            await page.close()
            return True
        except Exception:
            self.context = None
            return False

    async def close(self):
        try:
            if self.context:
                await self.context.close()
                self.context = None
        except Exception:
            self.context = None
        try:
            if self.browser:
                await self.browser.close()
                self.browser = None
        except Exception:
            self.browser = None
        try:
            if self.playwright:
                await self.playwright.stop()
                self.playwright = None
        except Exception:
            self.playwright = None
