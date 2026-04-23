import base64
import tempfile
import os
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage
from dotenv import load_dotenv
from services.image_utils import compress_image

load_dotenv()

def _get_llm():
    return ChatGroq(
        model_name="meta-llama/llama-4-scout-17b-16e-instruct",
        temperature=0,
        api_key=os.getenv("GROQ_API_KEY")
    )

def _image_content(image_path: str) -> dict:
    if os.getenv("GCS_BUCKET_NAME"):
        from services.gcs_storage import upload_to_gcs
        return {"type": "image_url", "image_url": {"url": upload_to_gcs(image_path)}}
    with open(image_path, "rb") as f:
        data = base64.b64encode(f.read()).decode("utf-8")
    return {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{data}"}}

def _invoke(llm, prompt: str, img_content: dict) -> str:
    msg = HumanMessage(content=[{"type": "text", "text": prompt}, img_content])
    response = llm.invoke([msg])
    usage = response.response_metadata.get("token_usage", {})
    print(f"[TOKEN USAGE] Input: {usage.get('prompt_tokens', 0)}, Output: {usage.get('completion_tokens', 0)}, Total: {usage.get('total_tokens', 0)}")
    return response.content

CLASSIFY_PROMPT = (
    "Classify this image into exactly one category:\n"
    "- prescription: doctor's prescription or medical document listing medicines\n"
    "- medicine: photo of a tablet, capsule, strip, or medicine bottle\n"
    "- lab_report: blood test, urine test, scan report, or any lab result document\n"
    "- condition: visible physical condition — wound, scar, rash, swelling, skin issue, injury\n"
    "- other: not related to healthcare\n\n"
    "Reply with ONE word only: prescription, medicine, lab_report, condition, or other."
)

PRESCRIPTION_PROMPT = (
    "This is a medical prescription. List only the medicines you can clearly read."
    " List maximum 5 medicines. If none are readable, reply exactly: 'No clear medicines detected. Please upload a clearer image.'"
    "\n\nIf medicines are found, use this format strictly:\n\n"
    "🧾 Prescription Detected\n\n"
    "Medicines:\n"
    "• [Medicine name]\n"
    "→ Used for: [one-line general use]\n"
    "→ General use: [simple safe intake tip, e.g. 'Typically taken after food']\n"
    "(repeat for each medicine, max 5)\n\n"
    "⚠ This is not a diagnosis. Follow your doctor's instructions.\n\n"
    "Rules:\n"
    "- ONLY include actual medicine names (e.g. Paracetamol, Amoxicillin, Omeprazole)\n"
    "- SKIP: dosage numbers, frequency (bd/od/sos), alcohol, flavoring, instructions, brand slogans\n"
    "- SKIP anything you are not 100% sure is a medicine\n"
    "- No exact dosage or frequency\n"
    "- No paragraphs\n"
    "- No invented medicines\n"
    "- Keep each line under 10 words"
)

MEDICINE_PROMPT = (
    "Identify the medicine in this image.\n"
    "If not identifiable, say: 'Medicine not clearly visible. Please upload a clearer image.'\n\n"
    "If identified, use this format strictly:\n\n"
    "💊 Medicine Identified\n\n"
    "• Name: [medicine name]\n"
    "• Used for: [one-line use]\n"
    "• General guidance: [one-line]\n\n"
    "💡 For exact dosage, share your prescription.\n\n"
    "⚠ This is not a diagnosis.\n\n"
    "Rules:\n"
    "- No paragraphs\n"
    "- No diagnosis\n"
    "- Keep it short"
)

LAB_REPORT_PROMPT = (
    "This is a lab report. Extract only the key values that are abnormal or noteworthy.\n"
    "If values are not readable, say: 'Lab values not clearly visible. Please upload a clearer image.'\n\n"
    "If readable, use this format strictly:\n\n"
    "🧾 Lab Report Detected\n\n"
    "Key Observations:\n"
    "• [Test name] – [Normal / Slightly low / High / etc.]\n"
    "(only list abnormal or important values)\n\n"
    "💡 What it means:\n"
    "• [One-line simple explanation per abnormal value]\n\n"
    "⚠ This is not a diagnosis. Please consult a doctor.\n\n"
    "Rules:\n"
    "- No paragraphs\n"
    "- Do NOT suggest medicines\n"
    "- Do NOT invent values\n"
    "- Only flag abnormal values\n"
    "- Keep each bullet under 12 words"
)

CONDITION_PROMPT = (
    "This image shows a visible physical condition.\n"
    "Use this format strictly:\n\n"
    "🩺 Condition Observed\n\n"
    "• Observation: [one-line description of what is visible]\n"
    "• Care tip: [one general first-aid or care suggestion]\n"
    "• Consult: [type of doctor to see]\n\n"
    "💡 If prescribed medication for this, share your prescription for more guidance.\n\n"
    "⚠ This is not a diagnosis.\n\n"
    "Rules:\n"
    "- No paragraphs\n"
    "- No diagnosis\n"
    "- Keep it short"
)

NON_MEDICAL_MSG = (
    "❌ Not a medical image\n\n"
    "Please upload one of the following:\n"
    "• Prescription\n"
    "• Medicine photo\n"
    "• Lab report\n"
    "• Skin / visible condition"
)

def verify_image(image_path: str) -> dict:
    if not os.path.exists(image_path):
        raise ValueError("Invalid file path")
    temp_dir = os.path.abspath(tempfile.gettempdir())
    if os.path.commonpath([os.path.abspath(image_path), temp_dir]) != temp_dir:
        raise ValueError("Access denied: invalid file location")

    compressed_path = compress_image(image_path)
    try:
        llm = _get_llm()
        img = _image_content(compressed_path)

        raw_type = _invoke(llm, CLASSIFY_PROMPT, img).strip().lower()

        if "prescription" in raw_type:
            image_type = "prescription"
            prompt = PRESCRIPTION_PROMPT
        elif "medicine" in raw_type:
            image_type = "medicine"
            prompt = MEDICINE_PROMPT
        elif "lab_report" in raw_type or "lab" in raw_type:
            image_type = "lab_report"
            prompt = LAB_REPORT_PROMPT
        elif "condition" in raw_type:
            image_type = "condition"
            prompt = CONDITION_PROMPT
        else:
            return {
                "type": "image_analysis",
                "message": NON_MEDICAL_MSG,
                "data": {"is_medical": False}
            }

        analysis = _invoke(llm, prompt, img)
        return {
            "type": "image_analysis",
            "message": analysis,
            "data": {"is_medical": True, "image_type": image_type}
        }

    except Exception as e:
        err = str(e)
        if "429" in err or "rate_limit" in err.lower() or "quota" in err.lower():
            return {
                "type": "image_analysis",
                "message": "AI quota limit reached. Please wait a moment and try again.",
                "data": {"is_medical": None}
            }
        raise
    finally:
        if compressed_path != image_path and os.path.exists(compressed_path):
            os.remove(compressed_path)
