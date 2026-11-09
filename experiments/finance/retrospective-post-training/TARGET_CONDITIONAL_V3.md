# Target-conditional finance transfer representation

The source-level SNFinLLM audit exposes a limitation in the earlier semantic
mapping. A training stage can improve one target while reducing another, so a
candidate cannot receive one target-independent quality score. FEVO provides the
complementary case: finance- and mathematics-aligned RL improves every reported
target over its SFT checkpoint, while the full staged pipeline outperforms direct
RL from an instruction model.

Version 3 therefore represents each candidate relative to the target being
predicted. It uses five coordinates:

- **domain-content alignment:** overlap between the training content and the
  target's domain knowledge
- **supervision alignment:** overlap between demonstrations or preference pairs
  and the capability measured by the target
- **verifier alignment:** whether the training reward directly checks the target
  behavior
- **prerequisite coverage:** whether a later stage inherits the knowledge and
  behavior required to use its feedback
- **retention control:** an explicit mechanism or data mixture intended to
  preserve capabilities outside the current objective.

Stage labels receive no direct credit. SFT, DPO, and RL contribute only through
their reported data, feedback, prerequisites, and retention contract. Data
filtering remains a curation measurement and is no longer inferred from the
presence of preference optimization.

The initial decision rule is deliberately ordinal:

1. score every candidate separately for each target family
2. prefer stronger content alignment for knowledge targets
3. prefer stronger supervision or verifier alignment for reasoning and agentic
   targets
4. prefer a staged candidate when the later objective depends on capabilities
   established by earlier stages
5. preserve ties when a later stage has no reported connection to the target or
   no retention evidence.

SNFinLLM and FEVO are development evidence for this revision and cannot test it.
The first source-level test is frozen on a separate Japanese financial-document
adaptation study before its result table is inspected.
