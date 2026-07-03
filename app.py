import os

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


def enhance_remark(raw_remark: str) -> str:
    raw_remark = (raw_remark or "").strip()
    if not raw_remark:
        raise ValueError("Remark is required.")
    if client is None:
        raise RuntimeError("GROQ_API_KEY is not configured.")

    prompt = f"""You are an AI Remark Enhancement Agent for a Government Complaint Management System.

Rewrite the given officer remark into professional official English.

Instructions:
- Preserve the exact meaning.
- Do not change any factual information.
- Do not add assumptions or new content.
- Correct grammar, spelling, punctuation, and sentence structure.
- Keep names, complaint numbers, dates, departments, locations, and technical terms unchanged.
- If the input is in Hindi or mixed Hindi-English, translate it into fluent professional English while preserving the original intent.
- Maintain an official government communication tone.
- Return only the final enhanced remark.

Remark:
{raw_remark}"""

    completion = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )
    return completion.choices[0].message.content.strip()


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
