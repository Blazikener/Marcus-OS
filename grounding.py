import torch
from PIL import Image
from transformers import Qwen2VLForConditionalGeneration, AutoProcessor
import re

# 3B model 
model_id = "qianhuiwu/GUI-Actor-3B-Qwen2.5-VL-LiteTrain"
processor = AutoProcessor.from_pretrained(model_id, trust_remote_code=True)
model = Qwen2VLForConditionalGeneration.from_pretrained(
    model_id, 
    torch_dtype=torch.float16,
    device_map="auto",
    trust_remote_code=True
).eval()

print("GUI-Actor-3B loaded!")

# Load png
image = Image.open("ss.png")

# Analyze YOUR screenshot
messages = [
    {
        "role": "user",
        "content": [
            {"type": "image", "image": image},
            {"type": "text", "text": "Find the web browser icon/button. Output ONLY coordinates x1,y1,x2,y2"}
        ]
    }
]

# Generate
text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
inputs = processor(text=[text], images=[image], padding=True, return_tensors="pt")
inputs = inputs.to("cuda" if torch.cuda.is_available() else "cpu")

with torch.no_grad():
    generated_ids = model.generate(**inputs, max_new_tokens=50)
    generated_ids_trimmed = [
        out_ids[len(in_ids):] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
    ]
    
response = processor.batch_decode(generated_ids_trimmed, skip_special_tokens=True)[0]

# Extract coordinates
coords = re.search(r'(\d+),(\d+),(\d+),(\d+)', response)
if coords:
    x1, y1, x2, y2 = map(int, coords.groups())
    center_x, center_y = (x1 + x2) // 2, (y1 + y2) // 2
    print(f"**CLICK HERE**: ({center_x}, {center_y})")
    print(f"Full bbox: {x1},{y1},{x2},{y2}")
    print(f"Model said: {response}")
else:
    print(" No coordinates found. Response:", response)
