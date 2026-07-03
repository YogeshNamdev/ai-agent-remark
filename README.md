# Hugging Face Space API Deployment

The current Space is a Streamlit UI. PHP/cURL receives the Streamlit HTML shell, not the generated remark. Deploy this API version so the CRM can call:

`POST https://yogesh10101998-remarkupdate.hf.space/api/enhance`

Request:

```json
{"remark": "raw officer remark"}
```

Response:

```json
{"enhanced_remark": "professional official remark"}
```

Deployment steps:

1. Replace the Space files with `app.py`, `requirements.txt`, and `Dockerfile` from this folder.
2. Set `GROQ_API_KEY` in the Space secrets.
3. Keep the CRM config URL as `https://yogesh10101998-remarkupdate.hf.space/api/enhance`.
