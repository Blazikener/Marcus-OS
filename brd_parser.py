import PyPDF2  
from docx import Document  
from openai import OpenAI

def extract_brd_requirements(file, instructions=""):
    """Extract features/stories from BRD."""
    text = ""
    if file.name.endswith('.pdf'):
        reader = PyPDF2.PdfReader(file)
        text = " ".join(page.extract_text() for page in reader.pages)
    elif file.name.endswith('.docx'):
        doc = Document(file)
        text = " ".join(p.text for p in doc.paragraphs)
    else:
        text = file.read().decode()
    
    client = OpenAI()
    prompt = f"""
    Extract test-relevant info from BRD:
    - User stories/features
    - UI elements/flows
    - Edge cases/security
    
    Instructions: {instructions}
    
    Return JSON: {{"features": [...], "flows": [...], "ui_elements": [...]}}
    """
    resp = client.chat.completions.create(model="gpt-4.1-nano", messages=[{"role":"user", "content":prompt}])
    return json.loads(resp.choices[0].message.content)
