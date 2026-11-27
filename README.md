# AI Claim Tracker

Viral AI discoveries and creations, checked against the evidence. Every verdict links to its sources.

Sister site to [Fast, With AI](https://woletee.github.io/fast-with-ai/).

## Verdicts

| Verdict | Meaning |
|---|---|
| Confirmed | Independent evidence supports it. |
| Unverified | Only the creator's own numbers so far. |
| Disputed | Credible experts challenge it. |

## Submitting a claim

1. Anyone opens **[Submit a claim](https://github.com/woletee/ai-claim-tracker/issues/new?template=new-claim.yml)** and fills in the short form (about 3 minutes).
2. A bot checks the form and the links, then comments on the issue.
3. A maintainer reads the evidence, adds a verdict label (`confirmed`, `unverified`, or `disputed`), then adds `approved`.
4. The bot adds the claim to `data/claims.json`, saves the source's preview image as the card image, credits it, and closes the issue. The site updates in a minute or two.

Card images are each source's own preview image and belong to their owners.
