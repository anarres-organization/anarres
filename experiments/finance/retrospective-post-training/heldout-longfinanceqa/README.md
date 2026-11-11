# LongFinanceQA component freeze

This record freezes component-level predictions before opening the paper PDF,
ablation tables, or subset results. The EMNLP abstract was visible before the
freeze. It discloses the overall gains from PAI and LongFinanceQA fine-tuning,
so those headline comparisons are excluded from scoring.

The unseen test concerns matched components. The capability-contract
representation predicts that intermediate reasoning supervision improves
financial and multi-source long-context targets, while property extraction,
property-based retrieval, and intermediate summarization each improve the full
agentic inference pipeline when directly ablated. Simpler-context retention is
scored separately if the paper reports the required control.

Every reported comparison matching a frozen prediction will be scored. Missing
comparisons remain unscored rather than being replaced by looser contrasts.
The source did not appear in the finance evidence map or repository history
before this freeze.

Source: [Lin et al., EMNLP 2025](https://aclanthology.org/2025.emnlp-main.615/).
