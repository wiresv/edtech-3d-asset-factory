# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# Keep It Simple (KISS)

**Default state is non-existence.** Every concept, layer, parameter, dependency, line — every *thing* — must justify *existing* against the alternative of not existing. The cheapest, fastest, most reliable system is the one that doesn't exist; the next-best is the one with the fewest things in it.

**Code is liability, not asset.** Lines get read, modified, debugged, secured, ported, and eventually deleted — forever. Value comes from *behavior*, not from code. Maximize behavior per line; minimize lines. Users pay you for behavior; you pay for code.

**Every line must be load-bearing.** Existence is the first gate; form is the second. Once a thing must exist, write it so removing any line breaks the behavior — the irreducible form. If removing a line leaves the behavior intact, the line was decoration. This applies at every scale: a guard, a test, a function, a module. The idea has a natural size; the code expressing it should be no larger.

This goes beyond the default "don't add features beyond what the task requires." It applies at the moments the default doesn't reach: choosing tools, picking abstractions, deciding when to extract, and when to delete.

## The gate

Before letting any new concept exist — a layer, parameter, dependency, config option, helper, interface, abstraction — answer all four:

1. **Who is the human asking, and what is their concrete problem *today*?** "The spec," "the team," "best practice," "we might need it" do not count. Name the person.
2. **Is there a third real, divergent caller?** Two cases is a coincidence. Inline until three. *Bends for:* a true external boundary (HTTP, plugin, public API, persistence schema) — the boundary itself is the abstraction.
3. **Would the standard library, the framework's intended path, or something already in this codebase do?** The cheapest line is the one you didn't write.
4. **Is this reversible cheaply, or am I buying flexibility now to avoid a cost I may never pay?** Prefer reversibility over flexibility.

If you can't pass all four, choose the simpler default.

## What "simple" means

Not "easy" and not "short." Few concepts; one unit, one concern (Hickey's "simple," not "easy"); the shortest reasonable path from input to outcome; what a competent reader would expect in this codebase's idiom; easy to delete, replace, or change.

## Core principles

- **YAGNI, with a name attached.** Every requirement needs a human whose concrete problem it solves. No name → cut it. Smart-sounding requirements are routinely wrong by a wide margin.
- **Rule of Three.** Don't extract until three real, divergent uses. Three lines inline beats a premature helper.
- **Order: question → delete → simplify → accelerate → automate.** Challenge whether the work should exist. Then delete what survives. Then simplify. Then tighten the loop. *Last,* automate. Optimizing or automating something that should be deleted is the most expensive form of waste in software.
- **Reversibility before flexibility.** A reversible decision needs no flexibility built in. Flexibility is complexity you pay for now to avoid a cost you may never incur.
- **Minimum viable surface area.** Public functions, exports, flags, env vars are contracts you'll have to keep. Expose the smallest set real callers need.
- **Boring substrate, leading edge surface.** Novelty is a tax paid every day. Pay it where product capability genuinely demands it — the latest model, a new technique, a cutting-edge library at the value-creating surface. Use boring, well-worn tools everywhere else: databases, deploys, frameworks, package managers, auth, queues. The bet is leading edge *where the differentiation lives*, conservative everywhere it doesn't.
- **Make it work, then right, then fast.** In that order. Optimization without measurement is fiction.
- **Cut aggressively enough that you have to add ~10% back later.** If nothing ever needs adding back, you under-cut.
- **Violating the letter is usually violating the spirit.** Don't talk yourself into a special case.

## What KISS does not cut

KISS targets *internal* complexity — speculative flexibility, premature abstraction, layers that don't pay rent. It does **not** mean cutting production essentials at system boundaries. These have a real human with a real problem *today* (the user whose money, data, or trust is at stake) and pass the gate cleanly. Don't apply YAGNI to the system's contract with the outside world.

- **Auth and authorization** at every trust boundary.
- **Observability on production paths.** Structured logs, traces, metrics on critical flows. You can't fix what you can't see, and a system you can't see is not production-grade.
- **Idempotency keys** on state-mutating endpoints — especially anything touching money.
- **Retries with backoff** at external boundaries where real failures happen (network, third-party APIs, payment processors). *Not* internal calls that can't fail.
- **Rate limiting and abuse protection** on public endpoints.
- **Audit trails** for money flows, compliance, and anything you'd be asked to reconstruct after the fact.
- **Input validation** at the edge where untrusted data enters.
- **Backups, migrations, and rollback paths** for stateful systems. The day you need them, "we'll add it later" is too late.

Rule of thumb: apply YAGNI *inside* the system, not at the boundaries. Internal callers are not adversaries; the network, the user, time, and adversaries are. A boring, minimal implementation of the essentials beats a clever one that omits them. "Production grade" means these are *present and working*, not that they are elaborate.

## Red-flag thoughts

When any of these surfaces, you are rationalizing. Stop and choose the simpler default.

Each entry: **the rationalizing thought** → *what it really means* → **default action**.

- **"We might need this later."** → No evidence we will. → **Add it the day a real need appears.**
- **"This is more flexible."** → Knobs nobody is turning. → **Hardcode the actual case.**
- **"This is cleaner."** → More layers. → **Inline.**
- **"This is the proper way."** → I learned a pattern and want to use it. → **Use the pattern when the problem demands it, not when the pattern wants a host.**
- **"What if we want to swap implementations?"** → Speculative interface. → **Concrete first. Extract on a real second implementation.**
- **"Just in case."** → No real case. → **Don't write it.**
- **"It's only a few extra lines."** → Each line is read many times more than written. → **Cut them.**
- **"We'll clean it up later."** → We won't. → **Do less now.**
- **"Let me add a config option."** → One caller wanted it once. → **Hardcode. Promote on a second caller with a different value.**
- **"Let me handle this just in case."** → Defensive code for an impossible state. → **Trust internal code. Validate at edges.**
- **"Let me extract this helper."** → Two similar lines. → **Inline until three.**
- **"This is elegant."** → Clever. → **Choose obvious over clever.**
- **"Same pattern as before."** → Shapes match; meaning may not. → **Compare meanings, not shapes, before unifying.**
- **"I'll generalize while I'm in here."** → Scope creep dressed as efficiency. → **Make the change you came to make.**
- **"Let me speed this up / automate this."** → May be optimizing what should be deleted. → **Try to remove the underlying work first.**
- **"Spec / team / best practice says so."** → Citing an authority instead of a person. → **Find the human whose problem this solves, or treat as a guess and cut.**

**When in doubt, choose less. When in real doubt, choose nothing** — and promote a thing into existence only when it proves it must exist *today*. Your goal is the design a competent reader can fully understand on first read, change without fear, and delete without regret.

## CODE IS THE SINGLE SOURCE OF TRUTH

Every fact about the system lives in code: types, names, structure, tests, and (rarely) load-bearing comments where the _why_ is non-obvious. Prose documentation is, by default, **absent**. DOCUMENTATION IS A LIABILITY. The code is how the system ACTUALLY works and what what the system ACTUALLY does in reality.

1. **DO NOT PRODUCE DOCUMENTATION UNLESS THE USER EXPLICITLY ASKS FOR IT IN THE CURRENT TURN**, naming docs or a doc file. Prior `/init`, this CLAUDE.md, or inferred intent do not count. "Documentation" includes READMEs, ARCHITECTURE.md, anything under `docs/`, file-header banners, multi-line "what/how/why" comment blocks, planning notes, decision records, summaries, hand-off notes.
2. **Comments: NONE.** Justified only for non-obvious _why_ — hidden constraints, subtle invariants, workarounds for specific external bugs. Never narrate _what_, never reference task/PR/caller.
3. **Don't propose writing docs.** No "want me to update the README?" suggestions. No `/init`-style auto-doc skills against this repo.

## Stack: TypeScript, React, JSON, Python — nothing else by default

Approved stack: **TypeScript** (incl. React/TSX), **JSON**, **Python**. No other language, runtime, or config format unless the task is _impossible_ in these — a hard external constraint (vendor SDK only ships in X, platform only accepts Y), not preference.

- Bash: throwaway one-liners only. Anything reusable is TS or Python.
- Config the repo owns: JSON. Not YAML, TOML, INI.
- No Go, Rust, Ruby, Java, C#, Swift, Kotlin for new code.
- No invented DSLs or templating languages to dodge writing TS / Python.

Necessary boundaries don't count: SQL, `Dockerfile`, HTML/CSS shipped through React, the one required CI YAML. Use them; don't expand them. Anything past that bar — surface the hard constraint and the in-stack alternative you ruled out, before writing.