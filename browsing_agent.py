import asyncio
import json
from e2b import Sandbox
from browser_use import Agent, ChatOpenAI
from dotenv import load_dotenv

load_dotenv()

async def main():
    # E2B sandbox creates successfully
    sandbox = await Sandbox.create(template="browser-chromium")
    
    try:
        # Get Chrome CDP endpoint 
        chrome_host = await sandbox.get_host(9222)
        cdp_url = f"wss://{chrome_host}"
        print(f"CDP URL: {cdp_url}")  # Prints: wss://sandbox-abc123.e2b.dev
        
        # Agent ignores remote browser - spawns LOCAL Chrome
        llm = ChatOpenAI(model="gpt-4o-mini")
        agent = Agent(
            task="Go to google.com and search 'test'",
            llm=llm,
            browser_url=cdp_url  
        )
        
        result = await agent.run()  # Local Chrome opens instead of E2B
        print(result)
        
    finally:
        await sandbox.close()

if __name__ == "__main__":
    asyncio.run(main())
