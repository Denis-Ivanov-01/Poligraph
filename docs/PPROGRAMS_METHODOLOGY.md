# Political Programs Methodology

This document points to the methodology used for political program and commitment analysis.

Political program analysis is separate from statement analysis. It focuses on commitments inside a program: what was promised, whether the subject had authority to act, what evidence exists about implementation, and how confidently the current status can be described.

The current detailed workflow lives in:

- [`docs/program_commitment_analysis_v6.md`](./program_commitment_analysis_v6.md)

The program methodology covers:

- extracting program sections, subsections, and commitments;
- analyzing each commitment independently;
- checking implementation evidence, contradictory evidence, and attribution;
- handling section-sized batches through tranche-based AI runs;
- validating AI JSON before import;
- preserving prompt, model, schema, and methodology provenance through `AiRun`;
- publishing reviewed commitments to the public program pages.

Program methodology should remain auditable and operational. The app may automate more of the execution later, but the current boundary keeps prompts, raw JSON imports, validation, review, and publication explicit.
