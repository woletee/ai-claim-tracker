# AI Claim Tracker

Big AI claims, and whether they held up. Every verdict links to its evidence.

Sister site to [Fast, With AI](https://woletee.github.io/fast-with-ai/).

## Verdicts

| Verdict | Meaning |
|---|---|
| Confirmed | Independent evidence supports it. |
| Partly true | True in part, or overstated. |
| Unverified | Only the claimant's own numbers so far. |
| Disputed | Credible experts challenge it. |
| Walked back | The claimant retracted or corrected it. |
| False | Evidence shows it wasn't true. |

## Submitting a claim

1. Anyone opens **[Submit a claim](https://github.com/woletee/ai-claims-tracker/issues/new?template=new-claim.yml)** and fills in the short form (about 3 minutes).
2. A bot checks the form and the links, then comments on the issue.
3. A maintainer reads the evidence, adds a verdict label (`confirmed`, `partly-true`, `unverified`, `disputed`, `walked-back` or `false`), then adds `approved`.
4. The bot adds the claim to `data/claims.json`, saves the source's preview image as the card image, credits it, and closes the issue. The site updates in a minute or two.

Card images are each source's own preview image and belong to their owners.
