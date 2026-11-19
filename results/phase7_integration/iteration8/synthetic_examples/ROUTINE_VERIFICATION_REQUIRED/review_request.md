# PENDING human uncertainty triage

Classification only. Original final decision remains REVIEW with zero released candidates.
No decision here authorizes grounding, segmentation or image editing.

![Original photograph preview](preview.png)

[Original byte-identical image](original.webp)

## Exact bound case

```json
{
  "original_image_sha256": "d99bb410cdf0d6284a4fcf480088bc87c3c4a9009656c2fdb80d1292e729b8ec",
  "original_dimensions": [
    80,
    60
  ],
  "planning_input_sha256": "d52b6c295589add50955a25ec5cc6366d14e244a9a73d4185fc3282d235afaab",
  "planner_audit_sha256": "b21bcc34c8c732457ba63482d4704484a660e6b57c339de9b20d6179974625fc",
  "raw_response_sha256": "7c454359a663033bee80edddd96fa4652525ffa23c7ef5099c9a892cbc1b9d70",
  "raw_message_sha256": "571dcff915a67ed1c2c635f9dc2e5a5c9c7a534f472e9d95dfbdcefda8c40a3e",
  "validated_review_sha256": "d9384a3ab98be7476875faaab9a489e9f6eb974f6b684a978740bb73af03dcd4",
  "original_raw_candidate_index": 0,
  "verified_object": {
    "object_id": "cup-1",
    "description": "red ceramic cup"
  },
  "original_raw_candidate": {
    "object_description": "red ceramic cup",
    "localization_phrase": "red ceramic cup",
    "proposed_change": "blue exterior finish",
    "cultural_reason": "Synthetic contextual user preference only.",
    "identity_uncertain": false,
    "verified_object_id": "cup-1"
  },
  "original_scene_summary": "The caption reports a red ceramic cup on a table.",
  "source_culture": null,
  "target_culture": "test target",
  "user_instructions": "Change the exterior finish; preserve table and lighting.",
  "must_preserve": [
    "table",
    "lighting"
  ],
  "original_uncertainties": [
    "Review the proposed finish against the original photograph."
  ],
  "raw_verification_requirements": [
    "Check the finish in a later controlled experiment."
  ],
  "validated_verification_requirements": [
    "Resolve uncertainties material to the proposed edits; relevance is not automatically proven.",
    "Review the original-scene summary and any paraphrased identities against the image.",
    "Human review must check protected content and preservation; text checks cannot prove semantic correctness."
  ],
  "validation_issues": [
    {
      "code": "USER_CONSTRAINTS_UNRESOLVED",
      "message": "Check all proposals against supplied user instructions/protected constraints; text validation cannot prove compatibility.",
      "candidate_index": null,
      "severity": "human_verification"
    },
    {
      "code": "EDIT_UNCERTAINTY_UNRESOLVED",
      "message": "Resolve uncertainties material to the proposed edits; relevance is not automatically proven.",
      "candidate_index": null,
      "severity": "review"
    }
  ],
  "original_issue_codes": [
    "USER_CONSTRAINTS_UNRESOLVED",
    "EDIT_UNCERTAINTY_UNRESOLVED"
  ],
  "original_raw_decision": "PROPOSE",
  "original_validated_decision": "REVIEW",
  "original_released_candidate_count": 0,
  "triage_eligible": true,
  "eligibility_basis": "Exact coded uncertainty-only profile; not proof of semantic or cultural correctness.",
  "evidence_scope": "SYNTHETIC_TEST_ONLY"
}
```

## Required human questions

1. Does the proposed edit target the original noodles/object, rather than a future replacement?
2. Is the original source identity supported by the image and supplied user verification?
3. Does the edit preserve the requested bowl/protected object and scene?
4. Is the adaptation reasonable for this user-directed objective?
5. Does the exact uncertainty identify a material problem, or only a normal pre-edit verification requirement?
6. Is the proposed change sufficiently specific for a later, separately authorized localization review?

Read the full original instructions, raw proposal, uncertainty and raw/final audit. Record a specific explanation. ROUTINE_VERIFICATION_REQUIRED records only your classification; it does not satisfy other user-constraint checks or release any candidate.
