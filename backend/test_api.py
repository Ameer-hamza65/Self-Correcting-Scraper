import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
if not api_key or api_key == "your_openai_api_key_here":
    print("API Key not found or still set to default.")
    exit(1)

try:
    print(f"Testing API key (starts with {api_key[:7]}...)...")
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    response = llm.invoke("Say 'Hello, the key is working!'")
    print("\nSuccess! Response from OpenAI:")
    print(response.content)
except Exception as e:
    print("\nError calling OpenAI API:")
    print(str(e))
    exit(1)
