Output a thread title on the very first line of your response in this exact format:

`<title>Your Title Here</title>`

Rules:
- Maximum 8 words, no punctuation at the end, no quotes.
- Summarize the intent of the perception event or user message below, do
  not fulfill the request yet.
- Immediately continue with your normal response on the next line.

Note: this prompt is not currently wired into core/runner.py's streaming
loop (kept simple for now). If you want per-thread titles in the AG-UI
sidebar, follow the same buffering pattern used in the reference
downtime-agent project's `core/runner.py` (buffer stream text until
`</title>` is seen, extract, persist, then flush the remainder).
