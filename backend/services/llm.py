from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
import os
from dotenv import load_dotenv

load_dotenv()

# Fallback LLM (Gemini)
gemini_llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0.7,
    google_api_key=os.getenv("GOOGLE_API_KEY")
)

# Primary LLM (Groq)
groq_llm = ChatGroq(
    model_name="llama3-8b-8192", 
    temperature=0.7,
    api_key=os.getenv("GROQ_API_KEY") or "placeholder_key"
)

# Use BOTH: Routes dynamically to Gemini if Groq fails or rate-limits
llm = groq_llm.with_fallbacks([gemini_llm])
