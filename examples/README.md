# Examples

## Before/After Comparisons

Three scenarios showing the same prompt answered by generic AI vs. a Digital Twin. Each file includes the prompt, both outputs, and a line-by-line breakdown of what changed.

All three use the same fictional Founder/CEO profile so you can see the voice hold across contexts (email, Slack, pitch).

- [Follow-up Email](before-after/follow-up-email.md): a retailer went quiet after a proposal
- [Slack Pushback](before-after/slack-pushback.md): keeping the written checklist
- [Project Proposal](before-after/project-proposal.md): opening message to a referral

## Sample Profiles

Complete Digital Twin profiles for three fictional people, one per role. They are written by hand as examples. No real person is described.

- [Founder/CEO](sample-profiles/founder-ceo.md)
- [Creative Director](sample-profiles/creative-director.md)
- [Technical Lead](sample-profiles/technical-lead.md)

## Synthetic data for the scripts

Everything in these three folders is made up: fictional writing by a
fictional operations lead at a made-up wholesaler. No real person, client
or company is described. The email address, phone number and money figures
are fake and exist to show redaction working.

- [sample-corpus/](sample-corpus/): seven short documents with a planted
  voice. `board-memo.md` is written in a different register on purpose, so
  the drift section has something to find.
- [drafts/](drafts/): a draft that fails `twins/example/twin.rules.json`
  and a fixed version that passes.
- [edit-pairs/](edit-pairs/): draft and edited pairs for `twin_diff.py`.
