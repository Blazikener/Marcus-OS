# main.py
import streamlit as st
from scrape import scrape_website, extract_website_intelligence, generate_test_cases

st.set_page_config(page_title="AI Webscraper Agent", layout="wide")
st.title("AI Webscraper Agent")

url = st.text_input("Enter the URL to scrape:")
coverage = st.selectbox(
    "Test Coverage Level",
    ["basic", "standard", "comprehensive"],
    index=1,
)


def ensure_https(u: str) -> str:
    if u and not u.startswith(("http://", "https://")):
        return "https://" + u
    return u


if st.button("Scrape & Generate Tests") and url:
    url = ensure_https(url)

    with st.spinner("Scraping website..."):
        html = scrape_website(url)

    with st.spinner("Extracting structure & features..."):
        extracted = extract_website_intelligence(html, url)

    with st.spinner("Generating test cases"):
        tests = generate_test_cases(extracted, coverage)

    st.success(f"Generated {len(tests)} test cases")

    pos = sum(1 for t in tests if t["type"] == "positive")
    neg = sum(1 for t in tests if t["type"] == "negative")
    edge = sum(1 for t in tests if t["type"] == "edge")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total", len(tests))
    c2.metric("Positive", pos)
    c3.metric("Negative", neg)
    c4.metric("Edge", edge)

    st.subheader("Test Cases")
    for tc in tests:
        with st.expander(f"TC{tc['id']:02d} - {tc['title']}"):
            st.markdown(f"**Type:** {tc['type'].upper()}")
            st.markdown(f"**Description:** {tc['description']}")
            st.markdown(f"**Expected:** {tc['expected_result']}")
            st.markdown("**Steps:**")
            for step in tc["steps"]:
                st.markdown(f"- {step}")
