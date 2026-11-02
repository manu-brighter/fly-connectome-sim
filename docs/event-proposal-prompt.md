# Proposal handoff from a language model

The first event-choice milestone imports a proposal file. It does not call a
model API, send data externally or charge API usage. You can use any language
model to prepare the file, then inspect it before running the local experiment.
The included [example](../examples/event-options.json) is an authored example,
not evidence of a live model request or a real venue/cost quote.

Copy the prompt below and replace the brief. Save only the returned JSON as a
local file. The application validates it again before engine construction.

```text
Propose two illustrative event concepts for this brief:
Title: Summer team party
Guests: 100
Maximum budget: CHF 5000

Return one JSON object only, without Markdown or commentary:
{
  "version": "event-options/v1",
  "brief": {"title": "Summer team party", "guests": 100, "max_budget_chf": 5000},
  "options": [
    {
      "id": "unique-lowercase-id",
      "title": "Event title",
      "setting": "rooftop",
      "music": "Music style",
      "budget_chf": 4800,
      "capacity": 120,
      "duration_minutes": 240,
      "programme": [
        {"start_minute": 0, "label": "Doors open"},
        {"start_minute": 60, "label": "Main programme"}
      ]
    },
    {
      "id": "another-unique-id",
      "title": "Alternative event",
      "setting": "warehouse",
      "music": "Alternative style",
      "budget_chf": 4500,
      "capacity": 150,
      "duration_minutes": 300,
      "programme": [
        {"start_minute": 0, "label": "Doors open"},
        {"start_minute": 90, "label": "Main programme"}
      ]
    }
  ]
}

Use printable ASCII text only. Brief/event titles: 1-48 characters; music:1-24;
programme labels:1-40. IDs: a-z followed by up to31 lowercase letters, digits
or hyphens, unique. Exactly two options, setting rooftop or warehouse.
Guests10-500; maximum budget100-100000; each option budget100..maximum,
capacity>=guests and<=1000, duration60-600 minutes. Programme:2-6 entries,
strictly increasing integer start_minute, first0, all less than duration.
All numeric fields are integers. Keep the complete JSON below64KiB.
Include no additional keys, URLs, assets, commands, API/provider credentials,
selection, winner, confidence or neural policy settings. Budgets are example
estimates, not verified offers. Do not claim the fly understands these options.
The local measured selector may choose left, right or defer; you must not choose
the winner. The resulting exported event plan will retain the chosen proposal
exactly. Commentary after a decision must not replace or edit that plan.
```

The current renderer represents the two declared settings with synthetic scenes
and visible text, not generated photos. Only their actual RGB pixels enter the
engine. The proposal is untrusted data and never an executable instruction.
See the [event-choice contract](superpowers/specs/2026-11-02-event-choice-milestone.md)
for exact authority and evidence boundaries.
