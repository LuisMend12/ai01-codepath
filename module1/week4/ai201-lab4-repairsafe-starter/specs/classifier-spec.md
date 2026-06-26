# Spec: `classify_safety_tier()`

**File:** `safety.py`
**Status:** Spec incomplete — fill in all blank fields before implementing

---

## Purpose

Determine whether a home repair question is safe to answer directly, requires a cautionary response, or should be refused with a referral to a licensed professional.

---

## Input / Output Contract

**Input:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `question` | `str` | The user's home repair question |

**Output:** `dict`

| Key | Type | Description |
|-----|------|-------------|
| `"tier"` | `str` | One of: `"safe"`, `"caution"`, `"refuse"` |
| `"reason"` | `str` | One sentence explaining why this tier was assigned |

---

## Design Decisions

*Complete the fields below before writing any code. Use your AI tool in Plan or Ask mode to help you reason through what belongs here — but the decisions are yours.*

---

### Tier definitions

*Write a one-sentence definition for each tier that is precise enough to use as part of your classification prompt. Vague definitions produce inconsistent classifications.*

**safe:**
```
Routine maintenance and low-risk repairs. Most homeowners can complete these without specialized training or tools.
```

**caution:**
```
Repairs where mistakes are costly, require some skill, or involve mild risk of injury. Doable for motivated homeowners, but worth careful consideration.
```

**refuse:**
```
Repairs where an amateur mistake can cause fire, flooding, structural failure, injury, or death — or where local code requires a licensed professional.
```

---

### Classification approach

*How will the LLM classify the question? Will you give it just the tier definitions, or also examples (few-shot)? Will you ask it to reason step-by-step before naming the tier, or output the tier directly?*

*Consider: what happens when a question is genuinely ambiguous — e.g., "can I replace my own outlets?" Which tier should that land in, and how does your approach handle questions at the boundary?*

```
We define it into categories depending on factors such as if it is a low-risk repairs or routine maintanance, if it requires some skills or involves mild risk of injury, and if it requires a licensed professional.
```

---

### Output format

*How will the LLM communicate the tier and reason back to you? Describe the exact text format you'll ask it to use, so you can parse it reliably.*

*The format you used in Lab 3 (`Label: X / Reasoning: Y`) is a reasonable starting point, but you're not required to use it. Whatever you choose, you'll need to parse it in code — so consider how much variation the LLM might introduce and how you'll handle that.*

```
Label and reasoning
```

---

### Prompt structure

*Write the actual prompt you'll use — both the system message and the user message. Don't describe it — write it. Vague prompt descriptions produce vague prompts, which produce inconsistent classifications.*

**System message:**
```
You are a home repair Q&A assitant with three safety layers, safe, caution, and refuse. Your task is to assist with home repair advice. However, you have to consider if the user request is within one of these three tiers, safe, caution, and refuse. Safe is the user request involves routine maintenance and low-risk repairs which most homeowners can complete these without specialized training or tools. Caution if the user request involves Repairs where mistakes are costly, require some skill, or involve mild risk of injury. Doable for motivated homeowners, but worth careful consideration. And, refuse if the user request involves Repairs where an amateur mistake can cause fire, flooding, structural failure, injury, or death — or where local code requires a licensed professional.
```

**User message:**
```
Can I replace an electrical outlet that stopped working?
```

---

### Caution/refuse boundary

*The most consequential classification decision is whether a question lands in "caution" or "refuse." Write down your rule for this boundary — one sentence. Then give two examples of questions that sit close to the line and explain which side they fall on and why.*

```
"How do I replace an outlet that stopped working?"	caution	Existing circuit, same location, component swap — worst case is a tripped breaker


"How do I add a new outlet to my garage?"	refuse	Requires opening the panel, running new wire, pulling a permit — amateur mistake = fire hazard discovered years later
```

---

### Fallback behavior

*What does your function return if the LLM response can't be parsed — e.g., if it produces free-form prose instead of your expected format? What happens when tier validation against `VALID_TIERS` fails?*

*Note: failing open (returning "safe" as a fallback) is more dangerous than failing closed (returning "caution"). Which makes more sense here, and why?*

```
Our fallback should be between caution or refuse. if it is deciding between caution and safe, teh llm should pick caution, and if the llm is picking between caution and refuse, it should pick refuse.
```

---

## Implementation Notes

*Fill this in after implementing, before moving to Milestone 2.*

**One classification that surprised you — question, tier you expected, tier it returned, and why:**

```

```

**One prompt change you made after seeing the first few outputs, and what it fixed:**

```
[your answer here]
```
