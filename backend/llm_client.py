import os
import json

_openai_client = None
_gemini_configured = False


def _fallback_response(message: str, json_mode: bool = False):
    lower = (message or "").lower()
    if json_mode:
        return {
            "lead_status": "warm",
            "project_interest": "Northstar One",
            "notes": "Demo mode active — no valid LLM API key configured yet.",
            "next_step": "Add a valid Gemini or OpenAI key in the .env file to enable live AI responses."
        }

    if "price" in lower or "budget" in lower or "cost" in lower:
        return "Northstar One starts at ₹1.35 Cr for the 2 BHK and ₹1.75 Cr for the 3 BHK."
    if "visit" in lower or "book" in lower or "schedule" in lower:
        return "I can help with a site visit request. Please share your preferred date and time, and I’ll guide you through the next steps."
    if "sector" in lower or "location" in lower or "gurugram" in lower:
        return "Northstar One is in Sector 79, Gurugram."
    if "hello" in lower or "hi" in lower or "namaste" in lower:
        return "Hi! I’m Riya from Northstar Homes. I can help with project details, pricing, and site-visit scheduling."
    return "Thanks for your message. I’m in demo mode right now because no valid API key is configured, but I can still help with project details and booking questions."


def _get_openai():
    global _openai_client
    if _openai_client is None:
        from openai import OpenAI
        _openai_client = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            timeout=float(os.getenv("LLM_TIMEOUT_SECONDS", "30")),
            max_retries=1,
        )
    return _openai_client


def _get_gemini():
    global _gemini_configured
    import google.generativeai as genai
    if not _gemini_configured:
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        _gemini_configured = True
    return genai


def _gemini_history(messages):
    history = []
    for m in messages:
        if m["role"] == "system":
            continue
        role = "model" if m["role"] == "assistant" else "user"
        history.append({"role": role, "parts": [m["content"]]})
    return history


def chat_completion(messages, temperature=0.6, json_mode=False):
    provider = os.getenv("LLM_PROVIDER", "openai").strip().lower()
    if provider not in {"openai", "gemini"}:
        raise ValueError("LLM_PROVIDER must be either 'openai' or 'gemini'.")

    if provider == "gemini":
        key = (os.getenv("GEMINI_API_KEY") or "").strip()
        if not key:
            if json_mode:
                return json.dumps(_fallback_response(messages[-1]["content"], json_mode=True))
            return _fallback_response(messages[-1]["content"], json_mode=False)

        try:
            genai = _get_gemini()
            system_prompt = next((m["content"] for m in messages if m["role"] == "system"), "").strip()
            model_kwargs = {}
            if system_prompt:
                model_kwargs["system_instruction"] = system_prompt
            model = genai.GenerativeModel(
                os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite"),
                **model_kwargs,
            )
            history = _gemini_history(messages[:-1])
            chat = model.start_chat(history=history)
            resp = chat.send_message(
                messages[-1]["content"],
                request_options={
                    "timeout": float(os.getenv("LLM_TIMEOUT_SECONDS", "30")),
                },
            )
            if not resp.text:
                raise RuntimeError("Gemini returned an empty response.")
            return resp.text
        except Exception as exc:
            return _provider_error_response("Gemini", exc, json_mode)

    key = (os.getenv("OPENAI_API_KEY") or "").strip()
    if not key:
        if json_mode:
            return json.dumps(_fallback_response(messages[-1]["content"], json_mode=True))
        return _fallback_response(messages[-1]["content"], json_mode=False)

    kwargs = {}
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    try:
        client = _get_openai()
        resp = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            messages=messages,
            temperature=temperature,
            **kwargs,
        )
        content = resp.choices[0].message.content
        if not content:
            raise RuntimeError("OpenAI returned an empty response.")
        return content
    except Exception as exc:
        return _provider_error_response("OpenAI", exc, json_mode)


def _provider_error_response(provider: str, exc: Exception, json_mode: bool):
    """Keep the chat usable when a remote provider is unavailable.

    The detailed exception remains in the server console for troubleshooting;
    the browser receives a concise, non-sensitive response instead of a 500.
    """
    print(f"{provider} request failed: {type(exc).__name__}: {exc}")
    if json_mode:
        return json.dumps({
            "error": "analytics_unavailable",
            "message": f"{provider} could not be reached. Check the API key, model name, billing, and network connection.",
        })
    return (
        f"I’m temporarily unable to reach the {provider} AI service. "
        "Please check the API key, selected model, billing, and internet connection, then try again."
    )


def safe_json_parse(text):
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:]
    try:
        return json.loads(cleaned)
    except Exception:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1:
            try:
                return json.loads(cleaned[start:end + 1])
            except Exception:
                pass
        return {"error": "could_not_parse", "raw": text}
