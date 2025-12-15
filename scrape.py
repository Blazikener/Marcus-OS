import selenium.webdriver as webdriver
from selenium.webdriver.chrome.service import Service
import time
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service

def scrape_website(url: str) -> str:
    print("Launching Chrome browser...")

    chrome_driver_path = "./chromedriver.exe"
    options = webdriver.ChromeOptions()
    driver = webdriver.Chrome(
    service=Service(ChromeDriverManager().install()),
    options=options)
    try:
        driver.get(url)
        print(f"Successfully loaded website: {url}")
        html = driver.page_source
        time.sleep(10)

        return html

    finally:
        driver.quit()
