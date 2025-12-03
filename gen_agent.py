import os
from dotenv import load_dotenv
from e2b_desktop import Sandbox
from io import BytesIO
from PIL import Image as PILImage
import subprocess
import time
from openai import OpenAI
import base64

load_dotenv()

def main():
    api_key = os.getenv("E2B_API_KEY")
    print(f"API Key loaded: {'Yes' if api_key else 'No'}")
    
    desktop = Sandbox.create(api_key=api_key)
    desktop.launch('chromium')
    desktop.wait(10000)  

    screenshot_bytes = desktop.screenshot()
    
    img = PILImage.open(BytesIO(screenshot_bytes))
    width, height = img.size
    new_width, new_height = int(width * 0.5), int(height * 0.5)
    small_img = img.resize((new_width, new_height))
    
    # Save full size first, then display
    img.save("screenshot1.png")
    
    # For Jupyter/VSCode display (non-blocking)

    from IPython.display import display
    display(small_img)
    
    print("Screenshot1 captured successfully!")
    
    desktop.wait(10000)  
    desktop.move_mouse(100, 200)
    screenshot_bytes = desktop.screenshot()
    img = PILImage.open(BytesIO(screenshot_bytes))
    width, height = img.size
    new_width, new_height = int(width * 0.5), int(height * 0.5)
    small_img = img.resize((new_width, new_height))
    
    # Save full size first, then display
    img.save("screenshot2.png")
    
    # For Jupyter/VSCode display (non-blocking)

    from IPython.display import display
    display(small_img)
    
    print("Screenshot2 captured successfully!")


    client = OpenAI()
    def encode_image(image_path):
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")
        
    image_path = "screenshot2.png"

    base64_image = encode_image(image_path)
    response = client.responses.create(
        model="gpt-4o-mini",
        input=[{
            "role": "user",
            "content": [
                {"type": "input_text", "text": "I want to enter internet and search some stuff up. So what should I click on this image?"},
                {
                    "type": "input_image",
                    "image_url": f"data:image/jpeg;base64,{base64_image}",
                },
            ],
        }],
    )

    print(response.output_text)
        

if __name__ == "__main__":
    main()
