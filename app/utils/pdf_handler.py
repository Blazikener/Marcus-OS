# app/utils/pdf_handler.py
import pypdf
import json
import re
import io
from typing import List, Dict

def extract_json_from_text(text: str) -> List[Dict]:
    """
    Extracts JSON-like objects from raw text.
    Handles potential PDF extraction artifacts.
    """
    items = []
    # Replace smart quotes often found in PDFs
    text = text.replace('“', '"').replace('”', '"').replace('‘', "'").replace('’', "'")
    
    # Find all starting positions of potential JSON objects
    start_indices = [m.start() for m in re.finditer(r'\{', text)]
    
    processed_until = 0
    for start in start_indices:
        if start < processed_until:
            continue
            
        stack = 0
        end = -1
        for i in range(start, len(text)):
            if text[i] == '{':
                stack += 1
            elif text[i] == '}':
                stack -= 1
                if stack == 0:
                    end = i + 1
                    break
        
        if end != -1:
            potential_json = text[start:end]
            try:
                # Clean up interior newlines and extra spaces that might break json.loads
                # This is risky but often necessary for PDF text
                data = json.loads(potential_json)
                if isinstance(data, dict) and "title" in data:
                    items.append(data)
                    processed_until = end
            except json.JSONDecodeError:
                # Try a more aggressive cleanup if simple load fails
                try:
                    # Remove trailing commas before closing braces/brackets
                    cleaned = re.sub(r',\s*([\]}])', r'\1', potential_json)
                    data = json.loads(cleaned)
                    if isinstance(data, dict) and "title" in data:
                        items.append(data)
                        processed_until = end
                except json.JSONDecodeError:
                    continue
    return items

def classify_test_case(item: Dict) -> str:
    """
    Classifies a test case as 'positive' or 'negative' based on content 
    if the 'type' field is missing or generic.
    """
    current_type = item.get("type", "").lower()
    if current_type in ["positive", "negative"]:
        return current_type
        
    # Heuristic classification
    content = f"{item.get('title', '')} {item.get('description', '')} {item.get('expected_result', '')}".lower()
    negative_indicators = [
        "error", "fail", "invalid", "negative", "404", "500", 
        "exception", "unauthorized", "malformed", "wrong", "broken"
    ]
    
    if any(indicator in content for indicator in negative_indicators):
        return "negative"
    return "positive"

def parse_pdf_test_cases(file_bytes: bytes) -> List[Dict]:
    """
    Reads a PDF, extracts text, finds JSON test cases, and classifies them.
    """
    reader = pypdf.PdfReader(io.BytesIO(file_bytes))
    full_text = ""
    for page in reader.pages:
        text = page.extract_text()
        if text:
            full_text += text + "\n"
            
    raw_items = extract_json_from_text(full_text)
    
    final_items = []
    for item in raw_items:
        item["type"] = classify_test_case(item)
        final_items.append(item)
        
    return final_items
