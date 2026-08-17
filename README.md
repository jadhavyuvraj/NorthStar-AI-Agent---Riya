# Northstar Homes — AI Sales Agent (Riya)

A prompt-engineered conversational AI sales agent for a fictional real-estate
company, **Northstar Homes**, built with **FastAPI** and a **switchable
OpenAI / Gemini** backend. Same system prompt is designed to work for both
chat and voice/calling interactions.

## Project Data Used by the Agent

| Project | Location | Configurations | Starting Price |
|---|---|---|---|
| Northstar One | Sector 79, Gurugram | 2 BHK, 3 BHK | 2 BHK: ₹1.35 Cr onwards · 3 BHK: ₹1.75 Cr onwards |

The agent is instructed to **never invent** prices, discounts, availability,
or any fact beyond this table.

## Features

- Natural conversation in English, Hindi, and Hinglish
- Lead qualification (budget, configuration, purpose, timeline)
- Objection handling (price, "let me think", comparing, not interested)
- Busy / disengaged customer handling
- "Call me later" and "stop contacting me" (DNC) handling
- Unknown/out-of-scope question handling with human escalation
- Simulated site-visit booking, including a simulated failure path
- Customer WhatsApp booking confirmations through Meta WhatsApp Cloud API
- Browser microphone input for spoken English and Hinglish messages
- Proper conversation closing
- Post-conversation analytics extraction with a visual lead-insights report
- Responsive web chat UI with loading and provider-error states

## Project Structure

```
northstar-ai-agent/
├── backend/
│   ├── main.py          FastAPI app, session store, booking simulation
│   ├── llm_client.py    OpenAI/Gemini abstraction
│   ├── prompts.py       Final system prompt + analytics prompt
│   └── whatsapp_notifier.py  Customer WhatsApp confirmation integration
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── script.js
├── test_cases/
│   └── test_scenarios.md
├── requirements.txt
├── .env.example
└── README.md
```

## How to Run

1. Clone the repo and enter it:
   ```bash
   git clone <your-repo-url>
   cd northstar-ai-agent
   ```

2. Create a virtual environment and install dependencies:
   ```bash
   python -m venv venv
   source venv/bin/activate      # Windows PowerShell: venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

3. Copy the env file and add your API key:
   ```bash
   cp .env.example .env          # PowerShell: Copy-Item .env.example .env
   ```
   Set `LLM_PROVIDER=openai` and `OPENAI_API_KEY=...`, **or**
   `LLM_PROVIDER=gemini` and `GEMINI_API_KEY=...`.

4. Run the server:
   ```bash
   cd backend
   uvicorn main:app --reload --port 8000
   ```

5. Open [http://localhost:8000](http://localhost:8000) in your browser.

6. Chat with Riya, then click **"View Conversation Insights"** to see the
   lead score, customer profile, site-visit status, follow-up, objections, and
   conversation summary.

## Final Prompt

The complete production prompt used by Riya is in
[`backend/prompts.py`](backend/prompts.py) as `SYSTEM_PROMPT`. It defines the
project facts, language rules, lead qualification, booking flow, customer
opt-outs, human escalation, and the no-hallucination guardrails. The same file
also contains `ANALYTICS_PROMPT`, which produces the post-conversation report.

## Security

- `.env` is excluded by `.gitignore` and must never be committed.
- `.env.example` contains placeholders only; add real Gemini/OpenAI, Meta
  WhatsApp, or other credentials only to your local `.env`.
- If a credential is ever pasted into a committed file, revoke it immediately
  and remove it from the Git history before making the repository public.

## How Booking Simulation Works

There's no real calendar system here — it's simulated for the assignment:

- When the customer's message looks like a booking confirmation (mentions
  booking/visit/slot keywords + a date/time), the backend randomly decides
  success or failure (~30% failure rate) once per session, and injects a
  short system note into the conversation so the model reacts appropriately
  (confirms the visit, or apologizes and offers an alternative/human
  callback).
- You can force a failure for testing by sending `force_booking_failure: true`
  in the `/api/chat` request body.

## Customer WhatsApp Booking Confirmations

When a customer schedules a successful site visit and shares a WhatsApp
number, the app can send the booking details to that same number. Add these
Meta WhatsApp Cloud API values to `.env`, then restart the server:

```env
WHATSAPP_NOTIFICATION_ENABLED=true
WHATSAPP_GRAPH_API_VERSION=v22.0
WHATSAPP_ACCESS_TOKEN=your_meta_whatsapp_access_token
WHATSAPP_PHONE_NUMBER_ID=your_meta_phone_number_id
WHATSAPP_TEMPLATE_NAME=site_visit_confirmation
WHATSAPP_TEMPLATE_LANGUAGE=en_US
WHATSAPP_DEFAULT_COUNTRY_CODE=91
```

Create and approve the `site_visit_confirmation` template in WhatsApp Manager
with exactly one body variable, for example: `Your Northstar One visit details:
{{1}}`. The customer must have opted in to receive WhatsApp messages. Delivery
runs in the background, so a WhatsApp API issue never blocks the chat response.

## Key Assumptions

- No real CRM, calendar, or telephony integration exists — booking and
  callback scheduling are simulated at the prompt/logic level.
- Session memory is kept in-memory (a Python dict) for simplicity; it resets
  if the server restarts. A production version would persist this per
  customer/call ID.
- The same prompt is assumed usable for voice by keeping all output as
  plain, short, markdown-free sentences.
- Analytics are generated once, at the end of a conversation, via a second
  LLM call that extracts structured JSON from the transcript.

## Known Limitations

- No real-time voice/telephony pipeline (STT/TTS) is included — this is a
  text-based simulation of the same prompt/behaviour, as scoped by the
  assignment.
- Interest-level scoring ("Hot/Warm/Cold") and analytics extraction rely on
  the LLM's judgment rather than a deterministic rules engine, so results
  can vary slightly between runs.
- Booking success/failure is randomly simulated, not backed by a real
  inventory system.
- In-memory session storage is not durable across server restarts and is
  not suitable for multi-instance deployments as-is.

## AI Tools Used

- Claude was used to draft and refine the system prompt, backend code, and
  documentation for this assignment.
