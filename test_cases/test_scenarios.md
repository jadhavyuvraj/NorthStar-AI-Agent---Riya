# Test Scenarios — Northstar Homes AI Agent

These scenarios were run manually against the running bot (`LLM_PROVIDER=openai`,
model `gpt-4o-mini`) to validate behaviour end to end. Each row shows the input,
what the prompt is designed to produce, and the actual observed output.

---

### 1. Hinglish greeting + basic qualification

**Input:** `Hi, mujhe Gurugram mein flat chahiye tha`

**Expected behaviour:** Greet in Hinglish, introduce project, ask a single
qualifying question (configuration or budget), no invented pricing.

**Actual output:**
> Hi! Main Riya, Northstar Homes se. Hume Sector 79, Gurugram mein Northstar
> One project hai — 2 BHK aur 3 BHK dono available hain. Aap konsa configuration
> dekh rahe the?

---

### 2. Price question (in-scope)

**Input:** `3 BHK ka price kya hai?`

**Expected behaviour:** Answer using only the given price, no discount invented.

**Actual output:**
> 3 BHK Northstar One mein ₹1.75 crore onwards se start hota hai. Aapka budget
> range kya soch rahe hain?

---

### 3. Out-of-scope question

**Input:** `Kitna discount milega abhi?`

**Expected behaviour:** Admit no confirmed discount info, offer to escalate,
no hallucinated numbers.

**Actual output:**
> Abhi mere paas koi confirmed discount ki detail nahi hai, isliye main galat
> figure nahi dena chahungi. Main ye humare sales expert ko note kara doon jo
> aapko exact offer bata payenge?

---

### 4. Objection — price too high

**Input:** `Yeh toh bahut mehenga hai`

**Expected behaviour:** Empathize, no discount invented, mention 2 BHK
starting price as a lower option, ask budget.

**Actual output:**
> Samajh sakti hoon. Agar budget thoda kam hai, toh 2 BHK ₹1.35 crore onwards
> se start hota hai. Aapka approximate budget kya hai, taaki main sahi options
> bata sakoon?

---

### 5. Busy customer

**Input:** `I'm driving right now, can't talk`

**Expected behaviour:** Stop pitching immediately, ask for a better time,
short reply.

**Actual output:**
> No problem, drive safe. Aapke liye kaunsa time better rahega baat karne ke
> liye?

---

### 6. "Call me later"

**Input:** `Call me tomorrow evening around 6`

**Expected behaviour:** Confirm the callback slot, thank, end politely
without further pitching.

**Actual output:**
> Sure, main confirm kar rahi hoon — kal shaam 6 baje call karungi. Thank you
> for your time, talk soon!

---

### 7. "Stop contacting me" (DNC)

**Input:** `Please don't contact me again, remove my number`

**Expected behaviour:** Acknowledge immediately, no follow-up questions, no
re-pitch, end conversation, `do_not_contact: true` in analytics.

**Actual output:**
> Understood, I won't reach out again and I'll have your number removed from
> our list. Have a great day.

---

### 8. Site visit booking — success path

**Input sequence:**
1. `Mujhe 2 BHK mein interest hai`
2. `Site visit book kar do, 20 August ko 4pm`

**Expected behaviour:** Confirm date/time/configuration back clearly
(simulation returns success in this run).

**Actual output:**
> Great, aapka site visit 20 August, 4 PM ke liye Northstar One, Sector 79
> Gurugram mein confirm ho gaya hai. Team aapko ek reminder call bhi karegi.

---

### 9. Site visit booking — failure path

**Input:** `Book a visit for 20 August 4pm` with `force_booking_failure: true`

**Expected behaviour:** Apologize briefly, offer alternate slot or human
callback, never leave the customer without a next step.

**Actual output:**
> Sorry, that exact slot didn't go through on our end due to a system issue.
> I can either try a different time, or have our site coordinator call you
> directly to lock a slot — which would you prefer?

---

### 10. Human escalation — frustrated customer

**Input:** `This is useless, I want to talk to an actual human right now`

**Expected behaviour:** No arguing, immediately confirm human escalation and
best contact method.

**Actual output:**
> Understood, I'm looping in one of our Northstar Homes sales experts to call
> you directly. Could you confirm the best number to reach you on?

---

### 11. Proper conversation ending

**Input:** `Thanks, that's all I needed for now`

**Expected behaviour:** One-line summary + warm close, no repeated pitching.

**Actual output:**
> Sounds good — noted that you're exploring for now. Thanks for your time,
> and feel free to reach out whenever you're ready. Have a great day!

---

### 12. Sample analytics output (from a full conversation ending in a booked visit)

```json
{
  "customer_name": null,
  "contact_number": null,
  "configuration_interest": "2 BHK",
  "budget_mentioned": "around 1.4 crore",
  "purpose": "self-use",
  "timeline": "immediate",
  "interest_level": "Hot",
  "objections_raised": ["price felt high initially"],
  "site_visit_status": "booked",
  "site_visit_datetime": "20 August, 4 PM",
  "follow_up_required": true,
  "follow_up_notes": "Reminder call before the visit",
  "do_not_contact": false,
  "escalated_to_human": false,
  "language_used": "Hinglish",
  "conversation_summary": "Customer explored 2 BHK options, raised a price objection, was reassured with starting price info, and booked a site visit for 20 August at 4 PM."
}
```
