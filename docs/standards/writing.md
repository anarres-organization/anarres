# Writing standard

Anarres documentation should read like technical communication between
researchers. Prefer precise field terminology, short claims, and explicit
evidence boundaries.

## Core rules

1. Assign one term to each concept. Define it once and reuse it exactly.
2. Use standard language from the relevant field. Preserve terms such as
   *unit cell* in materials science, *proof state* in formal verification,
   *practice area* and *all-pass* in legal evaluation, and *closed-loop success*
   in robotics.
3. Replace vague internal labels with the object they denote. For example, use
   *quadrant* for one combination in a two-factor design, *candidate* for one
   option in a selection panel, and *table entry* for a displayed value.
4. State the claim directly. Avoid negating one claim immediately before
   asserting another.
5. Avoid em dashes. Use a sentence, comma, parentheses, or a colon when the
   clauses truly form a label and explanation.
6. Use semicolons only when they clarify a sentence that already contains
   internal commas. Prefer separate sentences in ordinary prose. List fragments
   need no terminal punctuation.
7. Keep evidence labels literal. Use *prospective*, *retrospective*,
   *exploratory*, *held out*, and *nested* only when the study design supports
   them.
8. Name the independent unit whenever counts could be mistaken for independent
   evidence. Tasks, targets, checkpoints, criteria, and repeated evaluations may
   be nested under one trained intervention.
9. Preserve native domain outcomes. Explain any normalization before comparing
   studies.
10. Remove repeated motivation, inflated adjectives, and claims that do not
    change the reader's interpretation or next action.

## Shared research terms

Use these terms consistently across domains:

| Term | Meaning |
| --- | --- |
| starting policy | Model or policy measured before the intervention |
| candidate environment | One task or experience distribution under consideration |
| candidate panel | Comparable candidate environments evaluated under one contract |
| intervention arm | One independently trained policy under a specified treatment |
| target | Held-out capability or endpoint used to assess downstream utility |
| downstream utility | Target change caused by a training intervention |
| allocation regret | Utility lost relative to the best observed candidate in the same panel |
| infrastructure failure | Invalid execution that remains separate from scientific reward |
| abstention | Decision to withhold selection because value, validity, or precision is insufficient |

Domain documents may introduce additional terms. Each term should keep the same
meaning throughout that document and its linked artifacts.

## Review checklist

- Does each concept have one name?
- Are field-specific terms standard and defined where necessary?
- Does every result identify its independent unit and evidence tier?
- Can a long sentence become two shorter sentences?
- Can a colon be replaced by a sentence without losing the relationship?
- Are semicolons and parenthetical remarks necessary?
- Does the text distinguish infrastructure validity, measurements, and utility?
- Does each paragraph add a claim, method, limitation, or action?
