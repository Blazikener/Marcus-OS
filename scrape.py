"""
Website scraping and test case generation for Marcus Intelligence.
Uses requests for fast, reliable HTTP scraping.
Supports Web URL + BRD documents + Custom Instructions.
"""


import time
import re
import json
import socket
import ipaddress
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
from urllib.parse import urlparse
import os


import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from bs4 import BeautifulSoup
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential
from dotenv import load_dotenv
import pypdf

from logger import get_logger

load_dotenv()

logger = get_logger(__name__)


OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4o-mini")


@dataclass
class ExtractedWebsiteData:
    """Structured data extracted from website."""
    url: str
    title: str
    description: str
    forms: List[Dict]
    buttons: List[str]
    features: Dict[str, bool]
    text_summary: str
    dom_structure: str
    errors: List[str] = field(default_factory=list)


def validate_and_normalize_url(url: str) -> Tuple[bool, str]:
    """
    Validate and normalize URL. Blocks private/reserved/loopback IPs (SSRF protection).

    Args:
        url: Input URL string

    Returns:
        (is_valid, normalized_url) tuple
    """
    if not url or not url.strip():
        return False, ""

    url = url.strip()

    # Add https:// if no protocol
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    # Validate URL format
    try:
        parsed = urlparse(url)
        if not parsed.netloc:
            return False, ""
    except Exception:
        return False, ""

    # Resolve hostname and block private/reserved IPs
    try:
        hostname = parsed.hostname
        if not hostname:
            return False, ""
        for info in socket.getaddrinfo(hostname, None):
            ip = ipaddress.ip_address(info[4][0])
            if ip.is_private or ip.is_reserved or ip.is_loopback or ip.is_link_local:
                logger.warning("SSRF blocked: %s resolves to private/reserved IP %s", url, ip)
                return False, ""
    except (socket.gaierror, ValueError):
        return False, ""

    return True, url


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
def scrape_website(url: str) -> str:
    """
    Scrape website using requests (simple HTTP).
    
    Args:
        url: Website URL to scrape
        
    Returns:
        HTML content as string
        
    Raises:
        requests.Timeout: If request times out
        requests.RequestException: If request fails
    """
    logger.info("Loading website: %s", url)
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }
    
    try:
        response = requests.get(
            url, 
            headers=headers, 
            timeout=30,
            allow_redirects=True,
            verify=True
        )
        response.raise_for_status()
        
        html = response.text
        
        logger.info("Successfully loaded %s characters", f"{len(html):,}")
        return html
        
    except requests.Timeout:
        logger.warning("Timeout loading %s", url)
        raise
    except requests.HTTPError as e:
        logger.warning("HTTP error %d: %s", e.response.status_code, url)
        raise
    except requests.exceptions.SSLError:
        logger.warning("SSL error for %s, retrying without verification", url)
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=InsecureRequestWarning)
            response = requests.get(
                url,
                headers=headers,
                timeout=30,
                allow_redirects=True,
                verify=False
            )
        response.raise_for_status()
        html = response.text
        logger.info("Loaded %s chars (SSL verification disabled)", f"{len(html):,}")
        return html
    except Exception as e:
        logger.error("Error scraping %s: %s", url, e)
        raise


def extract_website_intelligence(html: str, url: str) -> ExtractedWebsiteData:
    """
    Extract structured data from HTML.
    
    Args:
        html: Raw HTML content
        url: Website URL
        
    Returns:
        ExtractedWebsiteData with all extracted information
    """
    errors = []
    soup = BeautifulSoup(html, "html.parser")
    
    # Remove noise
    for tag in soup(["script", "style", "meta", "link", "noscript"]):
        tag.decompose()
    
    # Extract title
    try:
        title = soup.title.string.strip() if soup.title and soup.title.string else "Untitled"
    except Exception as e:
        title = "Untitled"
        errors.append(f"Title extraction: {e}")
    
    # Extract description
    try:
        desc_tag = soup.find("meta", attrs={"name": "description"})
        description = desc_tag["content"].strip() if desc_tag and desc_tag.get("content") else ""
    except Exception as e:
        description = ""
        errors.append(f"Description extraction: {e}")
    
    # Extract forms
    forms = []
    try:
        for form in soup.find_all("form")[:10]:
            form_data = {
                "method": (form.get("method") or "GET").upper(),
                "action": form.get("action") or "",
                "inputs": [],
            }
            for inp in form.find_all(["input", "textarea", "select"])[:15]:
                form_data["inputs"].append({
                    "type": inp.get("type") or inp.name,
                    "name": inp.get("name") or "",
                    "placeholder": inp.get("placeholder") or "",
                    "required": inp.has_attr("required"),
                })
            forms.append(form_data)
    except Exception as e:
        errors.append(f"Form extraction: {e}")
    
    # Extract buttons
    buttons = []
    try:
        for btn in soup.find_all(["button", "a", "input"]):
            text = (btn.get_text() or btn.get("value") or "").strip()
            if text and 0 < len(text) <= 40:
                buttons.append(text)
        buttons = sorted(list(set(buttons)))[:30]
    except Exception as e:
        errors.append(f"Button extraction: {e}")
    
    # Extract text content
    try:
        text = " ".join(soup.get_text(separator=" ", strip=True).split())
        text_summary = text[:16000]
    except Exception as e:
        text_summary = ""
        errors.append(f"Text extraction: {e}")
    
    # Detect features
    try:
        lower_html = str(soup).lower()
        features = {
            "has_forms": bool(forms),
            "has_search": any(k in lower_html for k in ["search", 'type="search"']),
            "has_auth": any(k in lower_html for k in ["login", "signin", "signup", "register", "auth"]),
            "is_ecommerce": any(k in lower_html for k in ["product", "cart", "checkout", "price", "shop"]),
            "has_comments": "comment" in lower_html or "review" in lower_html,
        }
    except Exception as e:
        features = {}
        errors.append(f"Feature detection: {e}")
    
    # Extract DOM structure
    try:
        dom_structure = json.dumps({
            "header": bool(soup.find("header")),
            "nav": bool(soup.find("nav")),
            "main": bool(soup.find("main")),
            "footer": bool(soup.find("footer")),
            "sections": len(soup.find_all("section")),
            "articles": len(soup.find_all("article")),
        }, indent=2)
    except Exception as e:
        dom_structure = "{}"
        errors.append(f"DOM structure: {e}")
    
    logger.info("Extracted: %d forms, %d buttons, %d features", len(forms), len(buttons), len(features))
    
    return ExtractedWebsiteData(
        url=url,
        title=title,
        description=description,
        forms=forms,
        buttons=buttons,
        features={k: v for k, v in features.items() if v},
        text_summary=text_summary,
        dom_structure=dom_structure,
        errors=errors
    )


def aggregate_crawl_data(pages: List[Dict], token_budget: int = 12000) -> str:
    """
    Merge HTML from multiple crawled pages into a single string within a token budget.

    Args:
        pages: List of dicts with 'url' and 'html' keys from CrawlResult.pages
        token_budget: Approximate max tokens (~4 chars/token) for the combined output

    Returns:
        Combined HTML string with page separators
    """
    char_budget = token_budget * 4
    combined = []
    used = 0

    for page in pages:
        url = page.get("url", "")
        html = page.get("html", "")
        header = f"\n<!-- PAGE: {url} -->\n"
        available = char_budget - used - len(header)
        if available <= 0:
            break
        chunk = html[:available]
        combined.append(header + chunk)
        used += len(header) + len(chunk)

    return "".join(combined)


def generate_test_cases(source: Dict, instruction: str, extracted: ExtractedWebsiteData, coverage: str, site_map: Optional[Dict[str, List[str]]] = None) -> List[Dict]:
    """
    Generate test cases using OpenAI from Web + BRD + Instructions.
    
    Args:
        source: Dict with BRD content or other sources {"brd_content": "..."}
        instruction: Custom test generation instructions
        extracted: Extracted website data (optional if source provided)
        coverage: basic/standard/comprehensive
        
    Returns:
        List of test case dictionaries
        
    Raises:
        RuntimeError: If OPENAI_API_KEY not set
        ValueError: If LLM doesn't return valid JSON
    """
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY not set in environment")
    
    # Thread-safe client initialization
    client = OpenAI(api_key=OPENAI_API_KEY)
    
    coverage_map = {
        "basic": "3-4",
        "standard": "8-12", 
        "comprehensive": "40-60",
    }
    coverage_label = coverage_map.get(coverage, "20-30")
    
    system_prompt = '''You are a senior QA automation engineer with 15+ years of experience specializing in web application testing. 
Your expertise includes functional testing, edge case detection, and creating test cases that can be executed by AI agents such as browser-use agent.
Given website data AND/OR BRD requirements, generate comprehensive, executable test cases in valid JSON format only.
Focus on real-world scenarios, security considerations, and user experience flows.
Give high importance to the UI and UX and buttons of the website especially if the website is a web application.
Each test case must be specific, actionable, and map directly to automatable browser actions.
Try to cover all the possible scenarios and edge cases.

CRITICAL SAFETY RULES:
- NEVER generate tests for payment, checkout, billing, or transaction flows
- Skip any buttons/forms with text: 'Pay', 'Purchase', 'Checkout', 'Buy Now'
- Do NOT test credit card fields, CVV, expiry dates, or billing info
- Focus ONLY on: navigation, search, login (without payment), content display
- If payment elements detected, test ONLY page load + basic navigation
'''
    
    user_prompt = f"""Generate {coverage_label} test cases.

WEBSITE DATA (if available):
- URL: {extracted.url}
- Title: {extracted.title}
- Description: {extracted.description}

DETECTED FEATURES:
{json.dumps(extracted.features, indent=2)}

FORMS:
{json.dumps(extracted.forms, indent=2)}

BUTTONS:
{', '.join(extracted.buttons[:20])}

DOM STRUCTURE:
{extracted.dom_structure}

CONTENT SAMPLE:
{extracted.text_summary[:2000]}

"""

    # CRITICAL: ACTIVATE source + instruction params (3 lines added)
    if source:
        user_prompt += f"\n\nADDITIONAL SOURCES (BRD/Requirements):\n{json.dumps(source, indent=2)}"
    if instruction:
        user_prompt += f"\n\nCUSTOM PRIORITIES:\n{instruction}"
    if site_map:
        user_prompt += "\n\nSITE MAP (page → linked pages):\n"
        for parent, children in list(site_map.items())[:30]:
            user_prompt += f"  {parent} → {', '.join(children[:10])}\n"
        user_prompt += "\nGenerate cross-page navigation tests that verify links between these pages work correctly."
    user_prompt += "\n\n"

    user_prompt += """
Requirements:
- Mix of positive, negative, and edge cases (at least 30% negative/edge)
- Each test case must be concrete and automatable
- Steps must reference actual UI elements (buttons, forms, links) from data above
- Include specific selectors or identifiable text from BUTTONS/FORMS sections
- Avoid vague steps like "Navigate to page" - be very specific and actionable

Use this exact JSON schema:

[
  {
    "id": 1,
    "type": "positive",
    "title": "Test title",
    "description": "What is being tested",
    "expected_result": "Expected outcome",
    "steps": ["Step 1", "Step 2"]
  }
]

Return ONLY the JSON array, no explanation, no markdown.
"""
    
    min_tests = int(coverage_label.split("-")[0])

    try:
        logger.info("Generating %s test cases with %s...", coverage_label, MODEL_NAME)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        # Allow up to 2 attempts: retry if model returns too few tests
        for attempt in range(2):
            resp = client.chat.completions.create(
                model=MODEL_NAME,
                messages=messages,
                temperature=0.4,
            )

            text = resp.choices[0].message.content

            # Extract JSON from response
            start = text.find("[")
            end = text.rfind("]") + 1

            if start == -1 or end == 0:
                raise ValueError("Model did not return a JSON array")

            test_cases = json.loads(text[start:end])

            if len(test_cases) >= min_tests:
                break

            if attempt == 0:
                logger.info("Got %d tests, need at least %d. Retrying...", len(test_cases), min_tests)
                messages.append({"role": "assistant", "content": text})
                messages.append({"role": "user", "content": (
                    f"You returned only {len(test_cases)} test cases but I need at least {min_tests}. "
                    "Even for a simple website, generate tests for: page load, title check, "
                    "link navigation, responsive layout, broken links, 404 handling, meta tags, "
                    "accessibility basics, and basic content verification. "
                    "Return the FULL JSON array with at least {} test cases.".format(min_tests)
                )})

        logger.info("Generated %d test cases", len(test_cases))
        return test_cases

    except json.JSONDecodeError as e:
        logger.error("Failed to parse LLM response as JSON: %s", e)
        raise ValueError(f"Invalid JSON from LLM: {e}")
    except Exception as e:
        logger.error("Test generation failed: %s", e)
        raise