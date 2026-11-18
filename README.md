<!-- generated-by: gemini-ultra -->
# oddly-paradox-engine

> **"Every fact in this video has a receipt."**

`oddly-paradox-engine` (`paradox` CLI) is a local-first source-grounding verifier, mandatory human-editorial gate, and native `oddly-shorts` (`9:16` Remotion) bundle exporter for historical paradox explainers.

Unlike automated "faceless short" scripts that hallucinate dates, invent numbers, and trigger YouTube's **inauthentic / mass-produced / repetitive content** policy, `oddly-paradox-engine` enforces four deterministic gates before a single frame renders:

1. **Verbatim Character-Offset Claim Verification**: Parses pinned Wikipedia MediaWiki snapshots (`oldid` + `#section_anchor`), extracts atomic factual claims, and verifies that every `exact_quote` matches `paragraph.text[start:end]` character-for-character—or hard-fails.
2. **Mandatory Human-Review Gate (`paradox approve`)**: Generates a `claims_review.json` checklist requiring a human editor to choose the narrative angle, write original non-copied commentary (`>= 40` characters), and sign a SHA-256 `review_token` over `revision_id + approved_claims + human_editorial_take`. `paradox export` refuses to run without a valid token.
3. **Native `oddly-shorts` 9:16 Bundle Export (`paradox export`)**: Emits `episodes/<slug>/voice/script.txt` (with `*asterisk*` subtitle highlights), `say.json` spoken number map, `SCRIPT.md` (with 3 A/B hook variants), `copy.txt` (Wikipedia CC BY-SA 4.0 attribution + `AI-assisted animation` disclosure), `receipts.json`, and `src/videos/<slug>/plan.json` placing citation lower-thirds strictly inside vertical safe zones (`[12%..80%]` height).
4. **Fact-Number & OPSEC QA Gate (`paradox qa`)**: Scans `script.txt`, `plan.json`, and `copy.txt` to reject any unverified number absent from approved claims, PII/credential leaks, off-palette hex codes, or safe-zone violations.

---

## Quickstart (Zero External Runtime Dependencies)

Requires Python `3.11+` standard library only.

```console
lab@mac-studio ~ % PYTHONPATH=src python3 -m paradox_engine.cli extract \
  --snapshot fixtures/cobra_effect_wiki.json \
  --out out/claims_review.json
[paradox] Extracted 5 verbatim-aligned claims (oldid=1254091820) -> claims_review.json
  c01 | p0[0:152] | nums=[2001] | #The_original_cobra_effect
  c02 | p1[169:310] | nums=[-] | #The_original_cobra_effect
  c03 | p2[0:222] | nums=[0] | #The_original_cobra_effect
  c04 | p3[0:154] | nums=[1902,1] | #The_great_Hanoi_rat_massacre
  c05 | p4[0:215] | nums=[1902,20112] | #The_great_Hanoi_rat_massacre

lab@mac-studio ~ % PYTHONPATH=src python3 -m paradox_engine.cli approve \
  --snapshot fixtures/cobra_effect_wiki.json \
  --review out/claims_review.json \
  --angle "Paying per dead tail turns urban pest control into a breeding business" \
  --take "Whenever an institution pays for a proxy metric instead of the real outcome, rational actors farm the metric." \
  --claims c01,c02,c03,c04,c05
[paradox] Approved 5 claims for 'Perverse incentive' (token=98e4efeb684c14f1...)

lab@mac-studio ~ % PYTHONPATH=src python3 -m paradox_engine.cli export \
  --snapshot fixtures/cobra_effect_wiki.json \
  --review out/claims_review.json \
  --out-dir out/cobra-bundle
[paradox] Exported oddly-shorts 9:16 bundle for 'cobra-effect' -> cobra-bundle/

lab@mac-studio ~ % PYTHONPATH=src python3 -m paradox_engine.cli qa \
  --bundle out/cobra-bundle \
  --snapshot fixtures/cobra_effect_wiki.json \
  --review out/cobra-bundle/../claims_review.json
[paradox QA PASS] 4 files verified · 0 unverified numbers · 0 PII/OPSEC leaks · safe zones [12%..80%] OK
```

---

## Exported `oddly-shorts` Bundle Layout

```text
cobra-bundle/
├── episodes/
│   └── cobra-effect/
│       ├── SCRIPT.md          # 3 hook variants + human take + pinpointed Wikipedia receipts
│       ├── copy.txt           # Title <= 60 chars, CC BY-SA 4.0 oldid link, AI-assisted label
│       ├── receipts.json      # Cryptographic mapping of approved claims & verified numbers
│       └── voice/
│           ├── script.txt     # Narration with *asterisk* emphasis words
│           └── say.json       # Spoken pronunciation map for years & quantities
└── src/
    └── videos/
        └── cobra-effect/
            └── plan.json      # oddly-shorts 9:16 camera segments, expressions, screens & overlays
```

---

## Running Tests

```console
lab@mac-studio ~ % PYTHONPATH=src python3 -m pytest -v
```

---

## Fixtures & Attribution Notice

Files under `fixtures/` (`cobra_effect_wiki.json`, `vasa_ship_wiki.json`) are synthetic non-training unit-test snapshots summarizing historical Wikipedia facts under **CC BY-SA 4.0** with pinned revision IDs. Never use `fixtures/` for model training.

## License

Apache-2.0 (`LICENSE`). Built by **Oddly Proven**.
