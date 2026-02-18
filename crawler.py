"""
Multi-page Playwright-based website crawler with login support.
Renders JS-heavy SPAs and maintains auth cookies across pages.
Integrates with scrape.py for per-page intelligence extraction.
"""

import asyncio
import concurrent.futures
import os
import sys
import time
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Callable, Set, Tuple
from urllib.parse import urlparse, urljoin, urldefrag

from playwright.async_api import async_playwright, Page, Browser
from dotenv import load_dotenv

from scrape import validate_and_normalize_url
from logger import get_logger

load_dotenv()

log = get_logger("crawler")

# Hard limits
MAX_PAGES = 50
MAX_DEPTH = 3
DEFAULT_CRAWL_TIMEOUT = int(os.getenv("MARCUS_CRAWL_TIMEOUT", "300"))
PAGE_LOAD_TIMEOUT = 15    # 15 seconds per page
LOGIN_TIMEOUT = 30        # 30 seconds for login flow

# File extensions to skip (non-HTML resources)
_SKIP_EXTENSIONS = frozenset((
    '.pdf', '.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.bmp',
    '.css', '.js', '.ico', '.woff', '.woff2', '.ttf', '.eot',
    '.mp4', '.mp3', '.avi', '.mov', '.webm', '.ogg',
    '.zip', '.tar', '.gz', '.rar', '.7z',
    '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
))


@dataclass
class CrawlProgress:
    """Crawl progress state for UI callback."""
    pages_discovered: int = 0
    pages_scraped: int = 0
    pages_failed: int = 0
    current_url: str = ""
    status: str = "starting"  # starting | logging_in | crawling | done | error
    errors: List[str] = field(default_factory=list)


@dataclass
class CrawlResult:
    """Result of a complete site crawl."""
    pages: List[Dict] = field(default_factory=list)
    site_map: Dict[str, List[str]] = field(default_factory=dict)
    login_success: bool = False
    errors: List[str] = field(default_factory=list)


class SiteCrawler:
    """
    BFS website crawler using Playwright (Chromium).

    Crawls a website starting from start_url, optionally logging in first.
    Stays within the same domain, respects max_pages and max_depth limits,
    and SSRF-validates every discovered URL.
    """

    def __init__(
        self,
        start_url: str,
        max_pages: int = 20,
        max_depth: int = 2,
        login_url: Optional[str] = None,
        login_username: Optional[str] = None,
        login_password: Optional[str] = None,
        crawl_timeout: int = DEFAULT_CRAWL_TIMEOUT,
        progress_callback: Optional[Callable] = None,
    ):
        self.start_url = start_url
        self.max_pages = min(max_pages, MAX_PAGES)
        self.max_depth = min(max_depth, MAX_DEPTH)
        self.login_url = login_url
        self.login_username = login_username
        self.login_password = login_password
        self.crawl_timeout = crawl_timeout
        self._progress_cb = progress_callback

        # Derive allowed domain from start URL
        parsed = urlparse(start_url)
        self._allowed_domain = parsed.hostname
        # Base domain for subdomain matching (e.g. www.example.com → example.com)
        parts = self._allowed_domain.rsplit(".", 2) if self._allowed_domain else []
        self._base_domain = ".".join(parts[-2:]) if len(parts) >= 2 else self._allowed_domain

        # State
        self._visited: Set[str] = set()
        self._site_map: Dict[str, List[str]] = {}
        self._progress = CrawlProgress()

    def _is_same_site(self, hostname: Optional[str]) -> bool:
        """Check if hostname belongs to the same site (allows subdomains)."""
        if not hostname:
            return False
        if hostname == self._allowed_domain:
            return True
        if self._base_domain and (
            hostname == self._base_domain
            or hostname.endswith("." + self._base_domain)
        ):
            return True
        return False

    # ─── Login ────────────────────────────────────────────────────────────

    async def _perform_login(self, page: Page) -> bool:
        """
        Navigate to login URL, detect form fields, fill credentials, submit.
        Returns True if login appears successful.

        Strategy:
        1. Find input[type="password"]
        2. Find username field via priority selectors
        3. Fill both, click submit or press Enter
        4. Verify: URL changed or password field disappeared
        """
        self._update_progress(status="logging_in", current_url=self.login_url)

        try:
            await page.goto(self.login_url, timeout=PAGE_LOAD_TIMEOUT * 1000, wait_until="domcontentloaded")
            await asyncio.sleep(2)  # Allow page to settle

            # Find password field — main frame first, then iframes
            password_field = None
            login_frame = page
            try:
                password_field = await page.wait_for_selector(
                    'input[type="password"]', timeout=PAGE_LOAD_TIMEOUT * 1000
                )
            except Exception:
                password_field = None

            # Fallback: search iframes
            if password_field is None:
                try:
                    await asyncio.sleep(1)
                    for frame in page.frames:
                        if frame == page.main_frame:
                            continue
                        try:
                            pw_field = await frame.wait_for_selector(
                                'input[type="password"]', timeout=3000
                            )
                            if pw_field:
                                password_field = pw_field
                                login_frame = frame
                                log.info("Found password field inside iframe")
                                break
                        except Exception:
                            continue
                except Exception:
                    pass

            if password_field is None:
                title = ""
                try:
                    title = await page.title() or ""
                except Exception:
                    pass
                input_count = 0
                try:
                    inputs = await page.query_selector_all("input")
                    input_count = len(inputs) if inputs else 0
                except Exception:
                    pass
                self._progress.errors.append(
                    "No password field found on login page (title='{}', inputs={})".format(
                        title[:60], input_count
                    )
                )
                log.warning(
                    "No password field. title='%s', inputs=%d, url=%s",
                    title, input_count, self.login_url,
                )
                return False

            # Find username/email field via JS querySelectorAll
            username_field = None
            username_js = """
            (() => {
                const selectors = [
                    'input[type="email"]',
                    'input[name*="email" i]',
                    'input[name*="user" i]',
                    'input[name*="login" i]',
                    'input[autocomplete="username"]',
                    'input[autocomplete="email"]',
                ];
                for (const sel of selectors) {
                    const el = document.querySelector(sel);
                    if (el && el.offsetParent !== null) return sel;
                }
                // Fallback: first visible text/email input that isn't password
                const inputs = document.querySelectorAll(
                    'input[type="text"], input[type="email"], input:not([type])'
                );
                for (const inp of inputs) {
                    if (inp.type !== 'password' && inp.offsetParent !== null) {
                        return '__fallback__';
                    }
                }
                return null;
            })()
            """
            try:
                if login_frame == page:
                    found_selector = await page.evaluate(username_js)
                else:
                    found_selector = await login_frame.evaluate(username_js)

                if found_selector == '__fallback__':
                    all_inputs = await login_frame.query_selector_all(
                        'input[type="text"], input[type="email"], input:not([type])'
                    )
                    if all_inputs:
                        for inp in all_inputs:
                            try:
                                inp_type = await inp.get_attribute("type") or ""
                                if inp_type != "password":
                                    username_field = inp
                                    break
                            except Exception:
                                continue
                elif found_selector:
                    username_field = await login_frame.wait_for_selector(
                        found_selector, timeout=5000
                    )
            except Exception as e:
                log.warning("Username field JS detection failed: %s", e)

            if username_field is None:
                self._progress.errors.append("No username/email field found on login page")
                log.warning("Login page has no visible username field: %s", self.login_url)
                return False

            # Fill credentials
            await username_field.fill(self.login_username)
            await password_field.fill(self.login_password)

            # Submit: try button[type=submit] first, then Enter
            pre_login_url = page.url

            try:
                submit_btn = await login_frame.query_selector(
                    'button[type="submit"], input[type="submit"]'
                )
                if submit_btn:
                    await submit_btn.click()
                else:
                    await password_field.press("Enter")
            except Exception:
                try:
                    await password_field.press("Enter")
                except Exception:
                    pass

            # Wait for navigation away from login page (polling)
            deadline = time.monotonic() + LOGIN_TIMEOUT
            while time.monotonic() < deadline:
                await asyncio.sleep(0.5)
                try:
                    current_url = page.url
                    if current_url != pre_login_url:
                        break
                except Exception:
                    break

            # Let SPA settle after login redirect before checking
            await asyncio.sleep(2)

            # Verify: URL changed OR password field disappeared
            post_login_url = page.url

            password_still_visible = False
            try:
                pw_check = await page.query_selector('input[type="password"]')
                password_still_visible = pw_check is not None
            except Exception:
                password_still_visible = False

            if post_login_url != pre_login_url or not password_still_visible:
                log.info("Login successful. Redirected to: %s", post_login_url)
                return True

            # Check for error messages on the page
            try:
                error_el = await page.query_selector(
                    '[class*="error"], [class*="alert-danger"], [role="alert"]'
                )
                if error_el:
                    error_text = await error_el.text_content() or ""
                    self._progress.errors.append(
                        "Login failed: {}".format(str(error_text)[:200])
                    )
                else:
                    self._progress.errors.append(
                        "Login may have failed: still on login page"
                    )
            except Exception:
                self._progress.errors.append("Login may have failed: still on login page")

            return False

        except Exception as e:
            self._progress.errors.append("Login error: {}".format(str(e)[:200]))
            log.error("Login failed with exception: %s", e)
            return False

    # ─── Link Extraction ──────────────────────────────────────────────────

    async def _extract_links(self, page: Page, current_url: str) -> List[str]:
        """
        Extract all <a href> links from page, filter to same domain,
        normalize, deduplicate, and SSRF-check each one.
        """
        try:
            raw_hrefs = await page.evaluate(
                "Array.from(document.querySelectorAll('a[href]')).map(e => e.href)"
            )
        except Exception:
            return []

        if not raw_hrefs or not isinstance(raw_hrefs, list):
            return []

        valid_links = []
        seen: Set[str] = set()
        skipped_scheme = 0
        skipped_domain = 0
        skipped_dedup = 0
        skipped_ext = 0
        skipped_ssrf = 0

        for href in raw_hrefs:
            # Resolve relative URLs
            absolute = urljoin(current_url, href)

            # Remove fragment
            absolute, _ = urldefrag(absolute)

            # Skip non-http schemes
            parsed = urlparse(absolute)
            if parsed.scheme not in ("http", "https"):
                skipped_scheme += 1
                continue

            # Domain scope check (allows subdomains)
            if not self._is_same_site(parsed.hostname):
                skipped_domain += 1
                continue

            # Deduplicate
            if absolute in seen or absolute in self._visited:
                skipped_dedup += 1
                continue
            seen.add(absolute)

            # Skip non-page file extensions
            path_lower = parsed.path.lower()
            if any(path_lower.endswith(ext) for ext in _SKIP_EXTENSIONS):
                skipped_ext += 1
                continue

            # SSRF check every discovered URL
            is_valid, normalized = validate_and_normalize_url(absolute)
            if is_valid:
                valid_links.append(normalized)
            else:
                skipped_ssrf += 1

        log.info(
            "Links from %s: %d valid, %d total | filtered: %d domain, %d ssrf, %d dedup, %d ext, %d scheme",
            current_url[:80], len(valid_links), len(raw_hrefs),
            skipped_domain, skipped_ssrf, skipped_dedup, skipped_ext, skipped_scheme,
        )

        return valid_links

    # ─── Core Crawl ───────────────────────────────────────────────────────

    async def crawl(self) -> CrawlResult:
        """
        Execute BFS crawl. Returns CrawlResult with pages and site map.
        Uses Playwright Chromium in headless mode.
        """
        result = CrawlResult()
        playwright = None
        browser = None
        context = None

        try:
            playwright = await async_playwright().start()
            browser = await playwright.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled"],
            )
            context = await browser.new_context(ignore_https_errors=True)
            page = await context.new_page()
            log.info("Launched Chromium via Playwright")

            try:
                # Login if credentials provided
                if self.login_url and self.login_username and self.login_password:
                    result.login_success = await self._perform_login(page)
                    if not result.login_success:
                        log.warning("Login failed — will crawl as unauthenticated user")

                    # Navigate to start URL after login attempt
                    try:
                        await page.goto(self.start_url, timeout=PAGE_LOAD_TIMEOUT * 1000, wait_until="domcontentloaded")
                        await asyncio.sleep(2)
                    except Exception:
                        pass  # BFS loop will retry start_url from queue

                # BFS crawl
                queue: List[Tuple[str, int]] = [(self.start_url, 0)]
                crawl_start = time.monotonic()

                while queue and len(self._visited) < self.max_pages:
                    # Check total crawl timeout
                    elapsed = time.monotonic() - crawl_start
                    if elapsed > self.crawl_timeout:
                        result.errors.append(
                            "Crawl timeout ({}s) reached after {} pages".format(
                                self.crawl_timeout, len(self._visited)
                            )
                        )
                        log.warning(
                            "Crawl timeout after %.0fs, %d pages",
                            elapsed, len(self._visited),
                        )
                        break

                    url, depth = queue.pop(0)

                    if url in self._visited:
                        continue
                    if depth > self.max_depth:
                        continue
                    self._visited.add(url)

                    self._update_progress(
                        status="crawling",
                        current_url=url,
                        pages_scraped=len(result.pages),
                        pages_discovered=len(self._visited) + len(queue),
                    )

                    try:
                        response = await page.goto(url, timeout=PAGE_LOAD_TIMEOUT * 1000, wait_until="domcontentloaded")
                        await asyncio.sleep(1)  # Allow page to settle

                        # Skip non-HTML responses
                        content_type = ""
                        if response:
                            content_type = response.headers.get("content-type", "")
                        if content_type and "text/html" not in content_type \
                                and "application/xhtml" not in content_type:
                            log.info("Skipping non-HTML: %s (%s)", url, content_type[:50])
                            continue

                        # Get fully rendered HTML
                        html = await page.content()

                        result.pages.append({
                            "url": url,
                            "html": html,
                            "depth": depth,
                        })

                        # Discover and queue links (only if under max depth)
                        if depth < self.max_depth:
                            links = await self._extract_links(page, url)
                            self._site_map[url] = links

                            for link in links:
                                if link not in self._visited:
                                    queue.append((link, depth + 1))

                    except Exception as e:
                        error_msg = "Failed to load {}: {}".format(url, str(e)[:150])
                        log.warning(error_msg)
                        result.errors.append(error_msg)
                        self._progress.pages_failed += 1
                        # Reset page to clean state
                        try:
                            await page.goto("about:blank", timeout=5000)
                        except Exception:
                            try:
                                await page.close()
                                page = await context.new_page()
                            except Exception:
                                pass
                        continue

                result.site_map = self._site_map

            finally:
                self._update_progress(
                    status="done",
                    pages_scraped=len(result.pages),
                )

        except Exception as e:
            log.error("Crawl failed to start: %s", e)
            result.errors.append("Crawl failed: {}".format(str(e)[:200]))
            self._update_progress(status="error")

        finally:
            if context:
                try:
                    await context.close()
                except Exception:
                    pass
            if browser:
                try:
                    await browser.close()
                except Exception:
                    pass
            if playwright:
                try:
                    await playwright.stop()
                except Exception:
                    pass

        # Merge progress errors (e.g. login details) without duplicates
        existing = set(result.errors)
        for err in self._progress.errors:
            if err not in existing:
                result.errors.append(err)
                existing.add(err)
        log.info(
            "Crawl complete: %d pages scraped, %d failed, %d errors",
            len(result.pages), self._progress.pages_failed, len(result.errors),
        )
        return result

    # ─── Progress ─────────────────────────────────────────────────────────

    def _update_progress(self, **kwargs):
        """Update progress state and invoke callback if set."""
        for k, v in kwargs.items():
            if hasattr(self._progress, k):
                setattr(self._progress, k, v)
        if self._progress_cb:
            try:
                self._progress_cb(self._progress)
            except Exception:
                pass  # Never let callback errors break the crawl


# ─── Sync Entry Point ────────────────────────────────────────────────────────

def _run_crawl_in_thread(crawler):
    """Run the async crawl in a dedicated thread.

    Running in a dedicated thread avoids nested event loop errors when called
    from Streamlit's synchronous context.
    """
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    return asyncio.run(crawler.crawl())


def crawl_website(
    start_url: str,
    max_pages: int = 20,
    max_depth: int = 2,
    login_url: Optional[str] = None,
    login_username: Optional[str] = None,
    login_password: Optional[str] = None,
    crawl_timeout: int = DEFAULT_CRAWL_TIMEOUT,
    progress_callback: Optional[Callable] = None,
) -> CrawlResult:
    """
    Synchronous wrapper for SiteCrawler.crawl().
    Safe to call from Streamlit's synchronous context.
    Always runs in a dedicated thread to avoid nested-loop errors.
    """
    crawler = SiteCrawler(
        start_url=start_url,
        max_pages=max_pages,
        max_depth=max_depth,
        login_url=login_url,
        login_username=login_username,
        login_password=login_password,
        crawl_timeout=crawl_timeout,
        progress_callback=progress_callback,
    )

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(_run_crawl_in_thread, crawler)
        try:
            return future.result(timeout=crawl_timeout + 30)
        except concurrent.futures.TimeoutError:
            pool.shutdown(wait=False, cancel_futures=True)
            raise TimeoutError(f"Crawl exceeded {crawl_timeout}s timeout")
