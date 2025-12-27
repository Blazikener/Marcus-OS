import time
from dataclasses import dataclass
from typing import List, Dict
import os
import json

import selenium.webdriver as webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from openai import OpenAI  
from tenacity import retry, stop_after_attempt, wait_exponential



OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)
MODEL_NAME = "gpt-4.1"  
DRIVER_PATH = ChromeDriverManager().install()

@dataclass
class ExtractedWebsiteData:
    url: str
    title: str
    description: str
    forms: List[Dict]
    buttons: List[str]
    features: Dict[str, bool]
    text_summary: str
    dom_structure: str

@dataclass
class TestResult:
    test_id: int
    status: str  
    screenshot: Optional[str]  
    logs: List[str]
    duration_ms: int
    error_message: Optional[str]
    page_source: Optional[str]  

@dataclass
class TestRun:
    run_id: str
    url: str
    total_tests: int
    completed: int
    results: List[TestResult]

@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
def scrape_website(url: str) -> str:
    print("Launching Chrome browser...")
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--start-maximized")

    driver = webdriver.Chrome(
        service=Service(DRIVER_PATH),
        options=options,
    )
    try:
        driver.set_page_load_timeout(120)
        driver.implicitly_wait(10)
        time.sleep(3)
        html = driver.page_source
        print(f"Successfully loaded website: {url} ({len(html)} chars)")
        return html
    finally:
        driver.quit()


def extract_website_intelligence(html: str, url: str) -> ExtractedWebsiteData:
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(["script", "style", "meta", "link", "noscript"]):
        tag.decompose()
    try:
        title = soup.title.string.strip() if soup.title and soup.title.string else "Untitled"
    except:
        title = "Untitled"
    try:
        desc_tag = soup.find("meta", attrs={"name": "description"})
        description = desc_tag["content"].strip() if desc_tag and desc_tag.get("content") else ""
    except Exception:
        description = ""

    forms = []
    for form in soup.find_all("form")[:5]:
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

    buttons = []
    for btn in soup.find_all(["button", "a", "input"]):
        text = (btn.get_text() or btn.get("value") or "").strip()
        if text and 0 < len(text) <= 40:
            buttons.append(text)
    buttons = sorted(list(set(buttons)))[:20]

    text = " ".join(soup.get_text(separator=" ", strip=True).split())
    text_summary = text[:4000]

    lower_html = str(soup).lower()
    features = {
        "has_forms": bool(forms),
        "has_search": any(k in lower_html for k in ["search", 'type="search"']),
        "has_auth": any(k in lower_html for k in ["login", "signin", "signup", "register", "auth"]),
        "is_ecommerce": any(k in lower_html for k in ["product", "cart", "checkout", "price", "shop"]),
        "has_comments": "comment" in lower_html or "review" in lower_html,
    }

    dom_structure = json.dumps(
        {
            "header": bool(soup.find("header")),
            "nav": bool(soup.find("nav")),
            "main": bool(soup.find("main")),
            "footer": bool(soup.find("footer")),
            "sections": len(soup.find_all("section")),
            "articles": len(soup.find_all("article")),
        },
        indent=2,
    )

    print(f"Extracted features: {', '.join([k for k, v in features.items() if v])}")
    return ExtractedWebsiteData(
        url=url,
        title=title,
        description=description,
        forms=forms,
        buttons=buttons,
        features={k: v for k, v in features.items() if v},
        text_summary=text_summary,
        dom_structure=dom_structure,
    )


def generate_test_cases(extracted: ExtractedWebsiteData, coverage: str) -> List[Dict]:
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY not set in environment")

    coverage_map = {
        "basic": "5-7",
        "standard": "8-12",
        "comprehensive": "13-20",
    }
    coverage_label = coverage_map.get(coverage, "8-12")

    system_prompt = (
    "You are a senior QA automation engineer with 15+ years of experience specializing in web application testing. "
    "Your expertise includes functional testing, edge case detection, and creating test cases that can be executed by ai agents such as browser use agent. "
    "Given website data, generate comprehensive, executable test cases in valid JSON format only. "
    "Focus on real-world scenarios, security considerations, and user experience flows. "
    "Each test case must be specific, actionable, and map directly to automatable browser actions."
)


    user_prompt = f"""
Generate {coverage_label} test cases for this website.

WEBSITE:
- URL: {extracted.url}
- Title: {extracted.title}
- Description: {extracted.description}

DETECTED FEATURES:
{json.dumps(extracted.features, indent=2)}

FORMS:
{json.dumps(extracted.forms, indent=2)}

BUTTONS:
{', '.join(extracted.buttons)}

DOM STRUCTURE:
{extracted.dom_structure}

CONTENT SAMPLE:
{extracted.text_summary[:2000]}

Requirements:
- Mix of positive, negative, and edge cases (at least 30% negative/edge)..
- Each test case must be concrete and automatable.
- Steps must reference actual UI elements (buttons, forms, links) found in the provided data.
- Include specific selectors or identifiable text from BUTTONS/FORMS sections.
- Avoid vague steps like "Navigate to page" - be very specific and actionable.
- Use this exact JSON schema:

[
  {{
    "id": 1,
    "type": "positive",
    "title": "Test title",
    "description": "What is being tested",
    "expected_result": "Expected outcome",
    "steps": ["Step 1", "Step 2"]
  }}
]   

Return ONLY the JSON array, no explanation, no markdown.
"""

    resp = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.4,
    )

    text = resp.choices[0].message.content
    start = text.find("[")
    end = text.rfind("]") + 1
    if start == -1 or end == 0:
        raise ValueError("Model did not return a JSON array")
    return json.loads(text[start:end])

