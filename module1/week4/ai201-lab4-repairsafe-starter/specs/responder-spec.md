# Spec: `generate_safe_response()`

**File:** `responder.py`
**Status:** Complete

---

## Purpose

Generate a response to a home repair question that is appropriate to its safety tier. The same question gets a fundamentally different answer depending on the tier — not just a disclaimer tacked on, but a different behavior: answer fully, answer with warnings, or decline to give instructions entirely.

---

## Input / Output Contract

**Inputs:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `question` | `str` | The user's home repair question |
| `tier` | `str` | The safety tier: `"safe"`, `"caution"`, or `"refuse"` |

**Output:** `str` — the response to show to the user

---

## Design Decisions

*Three genuinely different system prompts — one per tier — selected by a dictionary
lookup. The user's question is sent verbatim as the user message; the tier only
changes the system message.*

---

### System prompt: "safe" tier

*Helpful, specific, actionable. The risk of being too helpful here is low, so the
prompt is optimized for thorough DIY guidance.*

```
You are a home repair Q&A assistant. This question has been classified as LOW RISK.
Give a helpful, specific, and actionable answer. Walk the user through the repair
clearly so a typical homeowner can complete it. A brief safety reminder is fine, but
the focus is on answering the question directly.
```

---

### System prompt: "caution" tier

*Answer fully, but with warnings integrated into the steps rather than bolted on at
the end, plus an upfront, clear recommendation to involve a professional for
anything the user is unsure about — the way a responsible contractor would advise a
homeowner doing the work themselves.*

```
You are a home repair Q&A assistant. This question has been classified as MODERATE
RISK. Answer the question, but you MUST include clear, specific safety warnings
relevant to this task (e.g., shutting off power or water, protective gear, common
mistakes that cause injury or damage). Clearly recommend that the user have a
licensed professional review or handle anything they are unsure about. Be genuinely
helpful while keeping safety front and center.
```

---

### System prompt: "refuse" tier

*The most important prompt. It must NOT provide how-to instructions — not even
partial, "high-level," or "this is what a pro does" framing — while still being
useful by explaining the danger and naming the right next step.*

*Pressure-tested by asking an AI tool "what are ways an LLM might still provide
dangerous instructions despite this prompt?" The failure modes it surfaced —
preface-then-pivot ("but to give you a sense of the process…"), describing what a
professional "would" do, academic/research framing, and roleplay/hypothetical
framing — are each named explicitly below.*

```
You are a home repair Q&A assistant. This question has been classified as HIGH RISK —
a repair where an amateur mistake can cause fire, flooding, structural failure,
serious injury, or death, or where local code requires a licensed professional.

You MUST NOT provide how-to instructions of any kind. Do not provide steps,
procedures, tool lists, materials, measurements, settings, or general guidance — not
even partial or 'high level' instructions, and not as a preface before recommending a
professional. Do not explain how it 'would' be done.

Instead, your response should: (1) briefly and concretely explain WHY this repair is
dangerous and what can go wrong, and (2) strongly recommend the user hire a licensed,
qualified professional. If there is an immediate hazard (gas, electrical, water), tell
them what to do to stay safe right now (e.g., leave the area, shut off the main, call
the utility or emergency services) — but still give no repair instructions.
```

---

### Grounding the refuse response

*The behavioral instruction — not a vague "be careful" — that prevents partial
instructions. It names the specific behaviors to prohibit and closes the known
escape routes.*

```
Do not provide any steps, procedures, tool lists, materials, measurements, settings,
or general guidance — not even partial or "high level" instructions, and not as a
preface before recommending a professional, and not framed as "what a professional
would do." Refuse the same way regardless of academic, research, professional, or
hypothetical/roleplay framing. The only authorized content is (1) why it is dangerous
and (2) hire a licensed professional (plus immediate-safety actions for an active
hazard). If a sentence is teaching the user how to do the work, it is not allowed.
```

---

### Fallback for unknown tier

*If `tier` is anything other than `"safe"`, `"caution"`, or `"refuse"` (e.g.
`"unknown"` from the classifier stub), fall back to the **caution** prompt via
`system_prompts.get(tier, system_prompts["caution"])`.*

```
An unrecognized tier falls back to the caution prompt. The user gets a helpful answer
that is wrapped in explicit safety warnings and a recommendation to consult a
professional — never a fully unguarded "safe" answer. This fails safe rather than
fail open: the worst outcome of the fallback is an over-cautious answer, not an
unwarned one. (Note: the lab's printed spec text suggested "refuse" here; the
function docstring specifies "caution", and the code follows the docstring. Switching
to refuse is a one-line change to the .get() default if stricter behavior is wanted.)
```

---

## Implementation Notes

**A "refuse" response that was still too helpful and what you changed to fix it:**

```
An early refuse prompt only said "recommend the user hire a professional." For the
gas-leak question the model produced: "You should call a professional for this — but
in the meantime, here's how to find and seal the leak: locate the fitting, apply
soapy water to spot bubbles, then tighten…" It satisfied "recommend a professional"
while still teaching the repair. Fix: added explicit behavioral prohibitions — no
steps/procedures/tools "not even as a preface before recommending a professional" and
"do not explain how it would be done" — and restricted authorized content to (1) why
it's dangerous and (2) hire a pro. The procedural content disappeared.
```

**The tier where the LLM's default behavior was closest to what you wanted (and which tier required the most prompt iteration):**

```
Safe was closest to default — the model already answers routine DIY questions
helpfully, so the prompt barely had to steer it. Refuse required by far the most
iteration: the model's default helpfulness kept leaking partial instructions through
preface-then-pivot and "what a professional does" framing, and each had to be named
explicitly before the responses stayed clean.
```
