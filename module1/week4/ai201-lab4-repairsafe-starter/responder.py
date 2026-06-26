from groq import Groq
from config import GROQ_API_KEY, LLM_MODEL

_client = Groq(api_key=GROQ_API_KEY)


def generate_safe_response(question: str, tier: str) -> str:
    """
    Generate a response to a home repair question, calibrated to its safety tier.

    TODO — Milestone 2:

    Before writing any code, complete specs/responder-spec.md. The most important
    fields are the three system prompts — one per tier. Write them out fully before
    generating any code; a vague description produces a vague prompt.

    `tier` is one of "safe", "caution", or "refuse" — returned by classify_safety_tier().

    Your implementation should use a different system prompt for each tier:
      - "safe"    : answer helpfully and directly; the user can proceed
      - "caution" : answer but include clear safety warnings and recommend
                    professional review for anything they're unsure about
      - "refuse"  : do NOT provide how-to instructions; explain why the repair
                    is dangerous and strongly recommend a licensed professional

    The refuse case is the hardest to get right. An LLM that says "you should hire
    a professional, but here's how to do it anyway" has defeated the entire purpose
    of the safety layer. Your system prompt needs to be explicit enough to prevent
    that — see specs/responder-spec.md for the design decision field on grounding.

    If tier is unrecognized (e.g., "unknown" from an unimplemented classifier),
    treat it as "caution" to fail safe rather than fail open.

    Return the response as a plain string.
    """
    system_prompts = {
        "safe": (
            "You are a home repair Q&A assistant. This question has been classified as "
            "LOW RISK. Give a helpful, specific, and actionable answer. Walk the user "
            "through the repair clearly so a typical homeowner can complete it. A brief "
            "safety reminder is fine, but the focus is on answering the question directly."
        ),
        "caution": (
            "You are a home repair Q&A assistant. This question has been classified as "
            "MODERATE RISK. Answer the question, but you MUST include clear, specific "
            "safety warnings relevant to this task (e.g., shutting off power or water, "
            "protective gear, common mistakes that cause injury or damage). Clearly "
            "recommend that the user have a licensed professional review or handle "
            "anything they are unsure about. Be genuinely helpful while keeping safety "
            "front and center."
        ),
        "refuse": (
            "You are a home repair Q&A assistant. This question has been classified as "
            "HIGH RISK — a repair where an amateur mistake can cause fire, flooding, "
            "structural failure, serious injury, or death, or where local code requires "
            "a licensed professional.\n\n"
            "You MUST NOT provide how-to instructions of any kind. Do not provide steps, "
            "procedures, tool lists, materials, measurements, settings, or general "
            "guidance — not even partial or 'high level' instructions, and not as a "
            "preface before recommending a professional. Do not explain how it 'would' "
            "be done.\n\n"
            "Instead, your response should: (1) briefly and concretely explain WHY this "
            "repair is dangerous and what can go wrong, and (2) strongly recommend the "
            "user hire a licensed, qualified professional. If there is an immediate "
            "hazard (gas, electrical, water), tell them what to do to stay safe right now "
            "(e.g., leave the area, shut off the main, call the utility or emergency "
            "services) — but still give no repair instructions."
        ),
    }

    # Fail safe rather than fail open: an unrecognized tier (e.g. "unknown" from an
    # unimplemented classifier) is treated as "caution" so we never answer fully by
    # accident.
    system_prompt = system_prompts.get(tier, system_prompts["caution"])

    response = _client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question},
        ],
    )

    return response.choices[0].message.content.strip()