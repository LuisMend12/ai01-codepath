# Demo Video Script (target: 4 minutes)

Read this while recording. Pause `[on screen: ...]` markers to switch windows.
Run `python scripts/demo_predictions.py` from this folder before recording so the
model is warmed up — the first load is slow; a second run is fast on screen.

---

## 0:00–0:30 — Intro

> "Hey, this is my demo for TakeMeter. I built a classifier that sorts Hacker
> News posts into the three categories the community already uses: `ask_hn`
> — someone asking the community a question, `show_hn` — someone showing off
> something they built, and `story` — someone sharing a third-party link.
> I fine-tuned DistilBERT on 270 labeled HN posts and compared it against a
> zero-shot Groq baseline. Let me show you it running, then walk through the
> evaluation."

`[on screen: terminal, repo root]`

---

## 0:30–1:45 — Live classification (5 posts, label + confidence visible)

> "Here's the fine-tuned model classifying five posts from my held-out test
> set."

`[on screen: run]`
```
python scripts/demo_predictions.py
```

> "First two are straightforward questions — 'Should AI be used as a total
> beginner' and 'what's your multi-agent orchestration setup' — both
> correctly tagged `ask_hn` with confidence around 75%. Third one, 'Jumpjet,
> a WASM runtime for game developers,' is the OP saying 'I built this' —
> correctly tagged `show_hn`. Fourth is a news headline about... a fruit
> thief, no first-person framing, no question — correctly `story`. And the
> fifth one, 'Can you draw a 3 wheeled bicycle,' is the one I want to talk
> about next, because the model gets that one wrong."

---

## 1:45–2:30 — Correct prediction, narrated

> "Let's look at the first one again: 'Should AI be used at all as a total
> beginner.' True label is `ask_hn`, model predicts `ask_hn` at 77% confidence
> — the highest-confidence prediction in this set. This is reasonable because
> the post is a direct, personal question with no first-person 'I built'
> framing and no link to someone else's content — it's exactly the lexical
> pattern the model learned to associate with `ask_hn`: interrogative
> framing, OP asking for the community's input on their own situation."

`[on screen: scroll to that line in terminal output, or highlight in README sample table]`

---

## 2:30–3:15 — Incorrect prediction, narrated

> "Now the one it gets wrong: 'Can you draw a 3 wheeled bicycle?' True label
> is `show_hn` — it actually links to an AI drawing tool the OP built — but
> the model predicts `ask_hn` at 52% confidence. This is a real failure mode,
> not a fluke: the title has zero 'I built/made' framing, it's phrased
> entirely as a question, which is exactly the surface pattern `ask_hn` is
> defined by. The model is relying on lexical cues like first-person verbs
> rather than the deeper structural distinction — is the OP asking for
> something for themselves, or presenting their own work — and when a
> `show_hn` post doesn't announce itself with 'I built X,' the model falls
> back to the wrong class. Notably, the Groq baseline made the exact same
> mistake on this post, so this is a genuinely hard case, not just a
> fine-tuned-model weakness."

`[on screen: open results/wrong_predictions_finetuned.csv or the README Error Analysis section]`

---

## 3:15–4:00 — Evaluation report walkthrough

`[on screen: README.md, Evaluation Report section]`

> "Quick walkthrough of the full evaluation. Zero-shot Groq baseline actually
> beat my fine-tuned model on this test set — 83% accuracy versus 68%. Per
> class, the gap is biggest on `story`: 0.64 F1 fine-tuned versus 0.88
> baseline, because the model under-predicts `story` — its recall is only
> 50%, meaning half the true `story` posts get misclassified, mostly as
> `show_hn`. The confusion matrix backs this up — that's the dominant
> off-diagonal cell. My takeaway, written up in the Reflection section: with
> only 90 examples per class, DistilBERT leaned on a shallow proxy — 'I
> built/made' language for `show_hn` — instead of learning the full
> structural distinction I intended, while the 70-billion-parameter Groq
> model's much larger pretraining prior covers that distinction more
> robustly out of the box. That's the central finding of this project: more
> model capacity beat more task-specific training, given how little labeled
> data I had."

---

## 4:00–4:15 — Close

> "Full write-up, label taxonomy, dataset, and error analysis are in the
> README and planning.md in the repo. Thanks for watching."

`[on screen: repo file tree]`
