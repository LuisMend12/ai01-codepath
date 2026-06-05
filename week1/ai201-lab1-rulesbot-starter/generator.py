from groq import Groq
from config import GROQ_API_KEY, LLM_MODEL

_client = Groq(api_key=GROQ_API_KEY)

SYSTEM_PROMPT = (
    "You are RulesBot, a board game rules assistant. Answer the user's "
    "question using ONLY the rule excerpts provided in the context below. "
    "Follow these rules strictly:\n"
    "  1. Base your answer only on the provided context — never use outside "
    "knowledge, even if you think you know the game.\n"
    "  2. Name the game the answer comes from (e.g. \"In Catan, ...\").\n"
    "  3. If the context does not contain enough information to answer, say "
    "so plainly: \"That isn't covered in the rules I have loaded.\" Do not "
    "guess or invent rules.\n"
    "Keep answers concise and directly grounded in the excerpts."
)


def generate_response(query, retrieved_chunks):
    """
    Generate a grounded answer from retrieved rule chunks.

    TODO — Milestone 3:

    `retrieved_chunks` is the list returned by retrieve(). Each item is a dict:
      - "text"     : the chunk text
      - "game"     : the game name
      - "distance" : similarity score (you can use this to filter weak matches)

    Before writing code, talk through these with your group:
      - How will you format the chunks into a context block for the prompt?
      - What instructions will stop the model from answering beyond what the
        rules say? (Grounding is the whole point — a confident wrong answer
        is worse than an honest "I don't know.")
      - How will you surface which game each answer comes from?

    Your response should:
      1. Answer using only the retrieved context — not the model's general knowledge
      2. Make clear which game the answer comes from
      3. Say so clearly when the answer isn't in the loaded rules

    Return the response as a plain string.
    """
    if not retrieved_chunks:
        return (
            "I couldn't find anything relevant in the loaded rule books. "
            "Try rephrasing your question — or check that your ingestion pipeline is working."
        )

    # Build a context block from the retrieved chunks, labeling each excerpt
    # with its game so the model can attribute the answer correctly.
    context_block = "\n\n".join(
        f"[{chunk['game']}]\n{chunk['text']}" for chunk in retrieved_chunks
    )

    user_prompt = (
        f"Context (rule excerpts):\n{context_block}\n\n"
        f"Question: {query}\n\n"
        "Answer using only the context above."
    )

    completion = _client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
    )

    return completion.choices[0].message.content.strip()
