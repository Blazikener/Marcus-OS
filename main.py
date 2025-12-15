import streamlit as st
from scrape import scrape_website

st.title("AI Webscraper Agent")
url = st.text_input("Enter the URL to scrape: ")

def ensure_https(url: str) -> str:
    if not url.startswith(("http://", "https://")):
        return "https://" + url
    return url

url = ensure_https(url)

if st.button("Scrape"):
    st.write("Scraping the URL...")
    result = scrape_website(url)
    print(result)
