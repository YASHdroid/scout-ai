import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

groq = Groq(
    api_key=os.getenv("GROQ_API_KEY")
)

response = groq.chat.completions.create(
    model="openai/gpt-oss-20b",
    messages=[
        {
            "role": "user",
            "content": "Explain what an LLM is in one sentence."
        }
    ]
)

print(response.choices[0].message.content)