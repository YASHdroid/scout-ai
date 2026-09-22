from groq import Groq
from app.core.config import GROQ_API_KEY, LLM_MODEL

groq = Groq(api_key=GROQ_API_KEY)

def chat_completion(messages, reasoning_effort="low"):
    response = groq.chat.completions.create(
        model=LLM_MODEL,
        messages=messages,
        reasoning_effort=reasoning_effort
    )

    return response.choices[0].message.content

def chat_completion_with_tools(messages, tools):
    return groq.chat.completions.create(
        model=LLM_MODEL,
        messages=messages,
        tools=tools,
        tool_choice="auto",
        reasoning_effort="low"
    )
