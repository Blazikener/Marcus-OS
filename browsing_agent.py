from browser_use import Agent, ChatOpenAI
from dotenv import load_dotenv
import asyncio

load_dotenv()

async def main():
    llm = ChatOpenAI(model="gpt-4.1-mini")
    task = "just open the browser and go to the website https://www.google.com, its a trail run"
    agent = Agent(task=task, llm=llm)
    await agent.run()

if __name__ == "__main__":
    asyncio.run(main())
