# Frozen target-conditional holdout: Japanese financial documents

This audit tests the target-conditional representation on an independently
reported staged adaptation study for Japanese financial documents. The study is
absent from the fitted bridge and from the SNFinLLM and FEVO development audits.

The freeze uses only the public method description: a base checkpoint, a
financial text-adaptation stage, a subsequent visual financial-document stage,
and an ablation that removes an earlier prerequisite stage. It records three
predictions before result-table extraction:

1. financial text adaptation improves the text-finance target family over the
   unadapted checkpoint
2. visual financial adaptation improves the visual-document target family over
   the text-only checkpoint
3. the full staged path improves the combined financial-document target over the
   skip-stage ablation.

The representation abstains on general capabilities because the public method
description does not establish a retention comparison. Exact candidate names,
target names, and every comparable regression will be recovered after this
freeze. The audit remains a retrospective source-level holdout because the paper
was already public.
