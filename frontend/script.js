let sessionId = null;

const messagesEl = document.getElementById("messages");
const form = document.getElementById("chatForm");
const input = document.getElementById("msgInput");
const endBtn = document.getElementById("endBtn");
const analyticsModal = document.getElementById("analyticsModal");
const analyticsContent = document.getElementById("analyticsContent");
const analyticsSubtitle = document.getElementById("analyticsSubtitle");
const analyticsClose = document.getElementById("analyticsClose");
const sendBtn = form.querySelector("button[type='submit']");
const micBtn = document.getElementById("micBtn");
const defaultPlaceholder = input.placeholder;
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
let recognition = null;
let isListening = false;

function addMessage(text, who) {
  const div = document.createElement("div");
  div.className = `msg ${who}`;
  div.textContent = text;
  messagesEl.appendChild(div);
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function addTypingIndicator() {
  const div = document.createElement("div");
  div.className = "msg bot typing";
  div.id = "typingIndicator";
  div.textContent = "Riya is typing...";
  messagesEl.appendChild(div);
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function removeTypingIndicator() {
  document.getElementById("typingIndicator")?.remove();
}

function showChatError(error) {
  console.error(error);
  if (window.location.protocol === "file:") {
    addMessage("Please do not open index.html directly. Start the FastAPI server and open http://localhost:8000.", "bot");
    return;
  }
  if (error.name === "AbortError") {
    addMessage("The request took too long. Check that the backend is running and try again.", "bot");
    return;
  }
  if (error.message?.includes("Request failed with 5")) {
    addMessage("The backend returned an error. Check the VS Code terminal for the provider details, then restart the server.", "bot");
    return;
  }
  addMessage("The backend is not reachable. Start it with: cd backend, then uvicorn main:app --reload --port 8000.", "bot");
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>'"]/g, (character) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    "'": "&#39;",
    '"': "&quot;",
  })[character]);
}

function readableValue(value, fallback = "Not provided") {
  if (value === null || value === undefined || value === "" || value === "unknown" || value === "undecided") {
    return fallback;
  }
  return escapeHtml(value);
}

function badgeTone(value) {
  const status = String(value || "").toLowerCase();
  if (["booked", "yes", "hot", "completed"].some((word) => status.includes(word))) return "badge-positive";
  if (["failed", "declined", "cold", "no"].some((word) => status.includes(word))) return "badge-negative";
  if (["requested", "warm", "follow"].some((word) => status.includes(word))) return "badge-warning";
  return "badge-neutral";
}

function scoreTone(score) {
  const normalized = String(score || "").toLowerCase();
  if (normalized === "hot") return "score-hot";
  if (normalized === "warm") return "score-warm";
  if (normalized === "cold") return "score-cold";
  return "score-neutral";
}

function openAnalyticsModal() {
  analyticsModal.classList.remove("hidden");
}

function closeAnalyticsModal() {
  analyticsModal.classList.add("hidden");
}

function renderAnalytics(report, sessionId) {
  if (!report || typeof report !== "object" || report.error || report.lead_status) {
    const message = report?.message || report?.notes || "Analytics are not available for this conversation yet.";
    analyticsContent.innerHTML = `
      <div class="analytics-empty">
        <h3>Insights are unavailable</h3>
        <p>${escapeHtml(message)}</p>
      </div>`;
    return;
  }

  const score = readableValue(report.interest_level, "Not scored");
  const objections = Array.isArray(report.objections_raised) ? report.objections_raised.filter(Boolean) : [];
  const visitStatus = readableValue(report.site_visit_status, "Not discussed");
  const followUp = report.follow_up_required ? "Follow-up needed" : "No follow-up needed";
  const signals = [
    ["Human handoff", report.escalated_to_human],
    ["Do-not-contact", report.do_not_contact],
    ["Follow-up", report.follow_up_required],
  ];

  analyticsSubtitle.textContent = sessionId ? `Session ${sessionId.slice(0, 8)} · Generated from this conversation` : "Generated from this conversation";
  analyticsContent.innerHTML = `
    <div class="analytics-overview">
      <section class="lead-hero">
        <div>
          <p class="report-kicker">Customer profile</p>
          <p class="lead-name">${readableValue(report.customer_name, "Unnamed customer")}</p>
          <p class="lead-caption">${readableValue(report.configuration_interest, "Configuration not discussed")} · ${readableValue(report.purpose, "Purpose not discussed")}</p>
        </div>
        <div class="lead-score ${scoreTone(report.interest_level)}">LEAD SCORE<strong>${score}</strong></div>
      </section>
      <section class="report-card contact-card">
        <div class="contact-row"><span class="contact-label">Contact number</span><span class="contact-value">${readableValue(report.contact_number)}</span></div>
        <div class="contact-row"><span class="contact-label">Language</span><span class="contact-value">${readableValue(report.language_used)}</span></div>
      </section>
    </div>

    <div class="metric-grid">
      <section class="report-card metric"><p class="metric-label">Budget</p><p class="metric-value">${readableValue(report.budget_mentioned)}</p></section>
      <section class="report-card metric"><p class="metric-label">Buying timeline</p><p class="metric-value">${readableValue(report.timeline)}</p></section>
      <section class="report-card metric"><p class="metric-label">Visit status</p><span class="report-badge ${badgeTone(visitStatus)}">${visitStatus}</span></section>
      <section class="report-card metric"><p class="metric-label">Next step</p><p class="metric-value">${followUp}</p></section>
    </div>

    <div class="report-grid">
      <section class="report-card">
        <h3>Site visit</h3>
        <div class="detail-list">
          <div class="detail-item"><span>Status</span><strong>${visitStatus}</strong></div>
          <div class="detail-item"><span>Date & time</span><strong>${readableValue(report.site_visit_datetime, "Not scheduled")}</strong></div>
          <div class="detail-item"><span>Follow-up note</span><strong>${readableValue(report.follow_up_notes, "No action recorded")}</strong></div>
        </div>
      </section>
      <section class="report-card">
        <h3>Conversation signals</h3>
        <div class="signal-list">
          ${signals.map(([label, active]) => `<div class="signal"><span class="signal-dot ${active ? "yes" : ""}"></span>${label}: <strong>${active ? "Yes" : "No"}</strong></div>`).join("")}
        </div>
        <div class="tag-list">
          ${objections.length ? objections.map((item) => `<span class="tag">${escapeHtml(item)}</span>`).join("") : '<span class="tag">No objections recorded</span>'}
        </div>
      </section>
      <section class="report-card summary-card">
        <h3>Conversation summary</h3>
        <p class="summary-text">${readableValue(report.conversation_summary, "No summary was generated.")}</p>
      </section>
    </div>`;
}

function setMicListening(listening) {
  isListening = listening;
  micBtn.classList.toggle("listening", listening);
  micBtn.textContent = listening ? "■" : "🎙";
  micBtn.title = listening ? "Stop listening" : "Speak your message";
  input.placeholder = listening ? "Listening... speak now" : defaultPlaceholder;
}

if (SpeechRecognition) {
  recognition = new SpeechRecognition();
  recognition.lang = "en-IN";
  recognition.continuous = false;
  recognition.interimResults = true;

  recognition.onstart = () => setMicListening(true);
  recognition.onresult = (event) => {
    let transcript = "";
    for (let index = event.resultIndex; index < event.results.length; index += 1) {
      transcript += event.results[index][0].transcript;
    }
    input.value = transcript.trim();
  };
  recognition.onerror = (event) => {
    if (event.error !== "aborted") {
      addMessage("Microphone access failed. Please allow microphone permission and try again.", "bot");
    }
  };
  recognition.onend = () => setMicListening(false);

  micBtn.addEventListener("click", () => {
    if (isListening) {
      recognition.stop();
      return;
    }
    try {
      recognition.start();
    } catch (error) {
      console.error(error);
    }
  });
} else {
  micBtn.disabled = true;
  micBtn.title = "Voice input is not supported in this browser";
}

addMessage(
  "Hi! I'm Riya from Northstar Homes. Aap Northstar One, Sector 79 Gurugram ke baare mein jaanna chahenge? Ask me anything in English, Hindi, or Hinglish.",
  "bot"
);

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const text = input.value.trim();
  if (!text) return;
  addMessage(text, "user");
  input.value = "";
  input.disabled = true;
  sendBtn.disabled = true;
  micBtn.disabled = true;
  addTypingIndicator();
  const controller = new AbortController();
  const requestTimeout = window.setTimeout(() => controller.abort(), 40000);

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId, message: text }),
      signal: controller.signal,
    });

    if (!res.ok) {
      throw new Error(`Request failed with ${res.status}`);
    }

    const data = await res.json();
    sessionId = data.session_id;
    addMessage(data.reply || "I couldn’t generate a reply. Please try again.", "bot");
    if (data.whatsapp_confirmation_queued) {
      addMessage("Your site-visit details are being sent to your WhatsApp number.", "bot");
    }
  } catch (error) {
    showChatError(error);
  } finally {
    window.clearTimeout(requestTimeout);
    removeTypingIndicator();
    input.disabled = false;
    sendBtn.disabled = false;
    micBtn.disabled = !SpeechRecognition;
    input.focus();
  }
});

endBtn.addEventListener("click", async () => {
  if (!sessionId) {
    alert("Start a conversation first.");
    return;
  }
  endBtn.textContent = "Generating insights...";
  endBtn.disabled = true;
  analyticsSubtitle.textContent = "Reviewing this conversation and preparing your report";
  analyticsContent.innerHTML = '<div class="analytics-empty"><h3>Creating your report</h3><p>Riya is summarising the customer conversation now.</p></div>';
  openAnalyticsModal();
  try {
    const res = await fetch("/api/end", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId }),
    });

    if (!res.ok) {
      throw new Error(`Request failed with ${res.status}`);
    }

    const data = await res.json();
    renderAnalytics(data.analytics, data.session_id);
  } catch (error) {
    console.error(error);
    renderAnalytics({ error: "analytics_unavailable", message: "Analytics could not be generated. Please check the AI provider and try again." });
  } finally {
    endBtn.textContent = "View Conversation Insights";
    endBtn.disabled = false;
  }
});

analyticsClose.addEventListener("click", closeAnalyticsModal);
analyticsModal.addEventListener("click", (event) => {
  if (event.target === analyticsModal) closeAnalyticsModal();
});
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") closeAnalyticsModal();
});
