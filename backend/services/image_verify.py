import base64
import tempfile
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage
import os
from dotenv import load_dotenv

load_dotenv()

def verify_image(image_path: str) -> dict:
    if not os.path.exists(image_path):
        raise ValueError("Invalid file path")
    temp_dir = os.path.abspath(tempfile.gettempdir())
    if os.path.commonpath([os.path.abspath(image_path), temp_dir]) != temp_dir:
        raise ValueError("Access denied: invalid file location")

    llm = ChatGroq(
        model_name="meta-llama/llama-4-scout-17b-16e-instruct",
        temperature=0,
        api_key=os.getenv("GROQ_API_KEY")
    )

    if os.getenv("GCS_BUCKET_NAME"):
        from services.gcs_storage import upload_to_gcs
        image_content = {"type": "image_url", "image_url": {"url": upload_to_gcs(image_path)}}
    else:
        with open(image_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")
        image_content = {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}}

    message = HumanMessage(
        content=[
            {
                "type": "text",
                "text": (
                    "You are a medical image classifier. Analyze this image carefully.\n"
                    "Answer YES if the image contains ANY of: medical report, lab result, blood test, clinic document, prescription, X-ray, MRI, scan, skin condition, wound, or any health-related document.\n"
                    "Answer NO only if the image is clearly unrelated to healthcare (e.g. food, landscape, selfie).\n"
                    "Start your response with YES or NO, then briefly explain. Do NOT provide diagnosis."
                )
            },
            image_content
        ]
    )

    try:
        response = llm.invoke([message])
        text = response.content
        text_lower = text.lower().strip()
        is_medical = text_lower.startswith("yes") or ("yes" in text_lower[:20])

        # Log token usage
        usage = response.response_metadata.get("token_usage", {})
        print(f"[TOKEN USAGE] Input: {usage.get('prompt_tokens', 0)}, Output: {usage.get('completion_tokens', 0)}, Total: {usage.get('total_tokens', 0)}")

        return {
            "type": "image_verification",
            "message": text,
            "data": {"is_medical": is_medical}
        }
    except Exception as e:
        err = str(e)
        if "429" in err or "rate_limit" in err.lower() or "quota" in err.lower():
            return {
                "type": "image_verification",
                "message": "AI quota limit reached. Please wait a moment and try again.",
                "data": {"is_medical": None}
            }
        raise
