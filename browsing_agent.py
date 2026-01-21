from browser_use import Agent, ChatOpenAI, sandbox, Browser
from dotenv import load_dotenv
import asyncio
import json
import os

load_dotenv()

from e2b_desktop import Sandbox

async def main():

    if not os.path.exists("tests.json"):
        print("tests.json not found!")
        return
    
    try:
        with open("tests.json", "r", encoding='utf-8') as f:
            tests = json.load(f)
        print(f"Loaded {len(tests)} tests")
    except Exception as e:
        print(f"Error loading tests: {e}")
        return
    
    for i, test in enumerate(tests):
        # Extract task description as STRING for browser-use Agent
        task_description = test.get("description", "Navigate and test website functionality")
        task_prompt = f"""
Test Case: {test.get('title', 'Unknown')}
Type: {test.get('type', 'positive').upper()}
Expected: {test.get('expected_result', 'Success')}
Description: {task_description}

Execute these steps:
{chr(10).join([f"- {step}" for step in test.get('steps', [])])}

Report PASS/FAIL with screenshots.
"""
        
        print(f"Running test {i+1}/{len(tests)}: {test.get('title', 'Unknown')}")
        
        llm = ChatOpenAI(model="gpt-4.1-mini")
        agent = Agent(task=task_prompt, llm=llm) 
        await agent.run()

if __name__ == "__main__":
    asyncio.run(main())
