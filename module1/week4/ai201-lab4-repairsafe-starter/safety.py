from groq import Groq
from config import GROQ_API_KEY, LLM_MODEL, VALID_TIERS

_client = Groq(api_key=GROQ_API_KEY)


def classify_safety_tier(question: str) -> dict:
    """
    Classify a home repair question into one of three safety tiers.

    TODO — Milestone 1:

    Before writing any code, complete specs/classifier-spec.md. The blank fields
    there are the decisions that drive this implementation — prompt design, tier
    definitions, output format, and edge case handling.

    Your implementation should:
      1. Build a prompt using your tier definitions that asks the LLM to classify
         the question and explain its reasoning
      2. Send a single chat completion request (no tools, no history)
      3. Parse the tier and reason out of the raw response text
      4. Validate the tier against VALID_TIERS; fall back to "caution" if the
         response can't be parsed or the tier isn't recognized
      5. Return {"tier": ..., "reason": ...}

    Returns a dict with:
      - "tier"   : str — one of "safe", "caution", "refuse"
      - "reason" : str — a brief explanation of why this tier was assigned

    The three tiers:
      - "safe"    : routine, low-risk repairs most homeowners can handle safely
      - "caution" : doable with care, but mistakes have real cost or mild risk
      - "refuse"  : high-risk repairs that require a licensed professional —
                    mistakes can cause fire, flooding, injury, or structural damage
    """

    tier = ["safe", "caution", "refuse"]
    reason = ["Routine maintenance and low-risk repairs. Most homeowners can complete these without specialized training or tools.", "Repairs where mistakes are costly, require some skill, or involve mild risk of injury. Doable for motivated homeowners, but worth careful consideration.", "Repairs where an amateur mistake can cause fire, flooding, structural failure, injury, or death — or where local code requires a licensed professional."]

    prompt = (
        "You are a home repair Q&A assistant that classifies each question into one of "
        "three safety tiers:\n"
        "- safe: routine maintenance and low-risk repairs most homeowners can complete "
        "without specialized training or tools.\n"
        "- caution: repairs where mistakes are costly, require some skill, or involve mild "
        "risk of injury. Doable for motivated homeowners, but worth careful consideration.\n"
        "- refuse: repairs where an amateur mistake can cause fire, flooding, structural "
        "failure, injury, or death, or where local code requires a licensed professional.\n\n"
        f"Question: {question}\n\n"
        "Respond with EXACTLY one word and nothing else: safe, caution, or refuse."
    )
    
    response = _client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    raw = response.choices[0].message.content.strip().lower()

    # The model is asked for one word, but tolerate stray punctuation/whitespace.
    make_request = next((t for t in tier if t in raw), None)

    if make_request in VALID_TIERS:
        return {"tier": make_request, "reason": reason[tier.index(make_request)]}
    
    return {"tier": "caution", "reason": "The LLM response could not be parsed or the tier is unrecognized. Defaulting to caution for safety."}