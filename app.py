import os
import re

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from groq import Groq
from pydantic import BaseModel


GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.1-8b-instant")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get("ALLOWED_ORIGINS", "*").split(",")
    if origin.strip()
]

client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None
app = FastAPI(title="CRM Remark Enhancement API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


class RemarkRequest(BaseModel):
    remark: str


HINGLISH_WORDS = {
    "hai", "hain", "ho", "raha", "rahi", "rahe", "hoga", "hogi", "kar", "karo",
    "ki", "ka", "ke", "ko", "se", "par", "mein", "me", "aur", "ya", "nahi",
    "log", "logon", "janata", "sadak", "road", "gaddha", "pani", "bijli",
    "samasya", "dikkat", "pareshani", "shikayat", "kripya", "jaldi"
}


def detect_language_style(text: str) -> str:
    if re.search(r"[\u0900-\u097F]", text):
        return "Hindi"

    words = re.findall(r"[A-Za-z]+", text.lower())
    hinglish_hits = sum(1 for word in words if word in HINGLISH_WORDS)
    if hinglish_hits >= 2:
        return "Hinglish"

    return "English"


def clean_model_output(text: str) -> str:
    text = (text or "").strip()
    text = re.sub(r"^\s*(\*\*)?\s*(enhanced\s+remark|final\s+remark|output)\s*:?\s*(\*\*)?\s*", "", text, flags=re.I)
    text = re.sub(r"^\s*[-:]+\s*", "", text)

    stop_markers = [
        "\n\nLanguage",
        "\n\n**Language",
        "\n\nTranslation",
        "\n\n**Translation",
        "\n\nNote:",
        "\n\n**Note",
        "\n\nChanges:",
        "\n\n**Changes",
        "\n\nPreservation",
        "\n\n**Preservation",
    ]
    lowered = text.lower()
    cut_at = len(text)
    for marker in stop_markers:
        index = lowered.find(marker.lower())
        if index != -1:
            cut_at = min(cut_at, index)
    text = text[:cut_at].strip()

    if text.startswith('"') and text.endswith('"'):
        text = text[1:-1].strip()

    return text


def enhance_remark(raw_remark: str) -> str:
    raw_remark = (raw_remark or "").strip()
    if not raw_remark:
        raise ValueError("Remark is required.")
    if client is None:
        raise RuntimeError("GROQ_API_KEY is not configured.")

    language_style = detect_language_style(raw_remark)
    prompt = f"""You are an AI Remark Enhancement Agent for a Government Complaint Management System.

Rewrite the given officer remark into a polished, professional, publication-ready official remark.

Detected input language/style: {language_style}

Language preservation rules:
- You must return the output in exactly this detected language/style: {language_style}.
- If detected style is Hindi, return Hindi in Devanagari script only.
- If detected style is English, return English only.
- If detected style is Hinglish, return Hinglish in Latin/Roman script only.
- Do not translate the remark into another language unless the user explicitly asks for translation.
- Do not convert Hindi to English, English to Hindi, or Hinglish to Devanagari.

Content rules:
- Preserve the exact meaning and intent.
- Do not change any factual information.
- Do not add assumptions, new facts, or extra details.
- Correct grammar, spelling, punctuation, and sentence structure.
- Improve clarity, readability, flow, and official tone.
- Keep names, complaint numbers, dates, departments, locations, and technical terms unchanged.
- Return only the final enhanced remark.
- Do not write labels, markdown, explanations, introductions, confirmations, notes, translations, or phrases such as "Enhanced Remark" or "The remark has been rewritten".

Remark:
{raw_remark}"""

    completion = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
    )
    return clean_model_output(completion.choices[0].message.content)


@app.get("/api/health")
def health():
    return {"status": "ok", "model": GROQ_MODEL}


@app.post("/api/enhance")
def enhance(payload: RemarkRequest):
    try:
        return {"enhanced_remark": enhance_remark(payload.remark)}
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/", response_class=HTMLResponse)
def home():
    return """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>AI CRM Remark Enhancer</title>
  <style>
    body { margin: 0; background: #f4f6f9; color: #1f2933; font-family: Arial, sans-serif; }
    main { max-width: 860px; margin: 48px auto; background: #fff; border: 1px solid #e5e7eb; border-radius: 8px; padding: 24px; }
    textarea { width: 100%; min-height: 150px; border: 1px solid #cfd6df; border-radius: 6px; padding: 12px; font-size: 15px; box-sizing: border-box; }
    button { margin-top: 12px; background: #1a5fa5; color: #fff; border: 0; border-radius: 6px; padding: 10px 16px; font-weight: 700; cursor: pointer; }
    pre { white-space: pre-wrap; background: #f4fbf4; border: 1px solid #d7e7d8; border-radius: 6px; padding: 16px; line-height: 1.6; }
    .error { background: #fff5f5; border-color: #f1c7c7; color: #8a1f1f; }
  </style>
</head>
<body>
<main>
  <h1>AI CRM Remark Enhancer</h1>
  <textarea id="remark" placeholder="Enter officer remark"></textarea>
  <button id="enhance">Enhance Remark</button>
  <pre id="result" hidden></pre>
</main>
<script>
document.getElementById('enhance').onclick = async function () {
  const result = document.getElementById('result');
  result.hidden = false;
  result.className = '';
  result.textContent = 'Processing...';
  try {
    const response = await fetch('/api/enhance', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({remark: document.getElementById('remark').value})
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || 'Request failed');
    result.textContent = data.enhanced_remark;
  } catch (error) {
    result.className = 'error';
    result.textContent = error.message;
  }
};
</script>
</body>
</html>
"""
