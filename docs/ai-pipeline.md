# AI Pipeline

## Pipeline
Audio upload
→ transcription
→ transcript cleanup
→ speech segmentation
→ argument extraction
→ flow construction
→ rubric evaluation
→ judge-perspective feedback
→ drill generation
→ storage

## Structured Outputs Required
Use JSON/Pydantic-style schemas wherever possible.

## Argument Extraction Fields
- claim
- warrant
- evidence
- impact
- weighing
- response/refutation
- issue flags
- component status: explicit, implied, missing

## Feedback Priorities
The AI should identify:
- Missing warrants
- Weak weighing
- Dropped responses
- Unclear impacts
- Unsupported evidence claims
- New arguments in later speeches
- Weak extensions
- Lack of clash

## Avoid
Do not produce generic public speaking comments unless delivery affects debate performance.