# TODO (50.data)

- [Deferred] Session resume for DWG/CV
  - Design per-folder hidden session files storing processed items.
  - Ensure no double credit deduction; per-file deduction only.
  - Add resume UI affordance and recovery prompts.

- [Policy] Upfront credit check
  - Implemented in DWG and CV: block start when credits insufficient.
  - Show messagebox prompting purchase; do not begin processing.

- [Follow-ups]
  - Verify prompts copy and consistency across apps.
  - Add unit tests around credit gating where feasible.
