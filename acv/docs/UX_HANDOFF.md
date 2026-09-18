# Shared screen pattern — recommendation

This is a UX recommendation, not an additional competition requirement.
The ACV prototype implements upload → summary → comparison → evidence → download.
It has not yet been launched or visually verified.

Use the same section order in the shared application, adapting the result:

| Subsystem | Summary | Evidence |
| --- | --- | --- |
| ACV | Suggested car inspection order | Temperature comparison and eligible reading count |
| Doors | Door-cycle classifications | Cycle timeline and relevant signals |
| Rail | Normal / Side I / Side II | Recording and corresponding signals |
| SHM | Estimated cumulative fatigue damage | Estimate and documented interpretation |

Keep data coverage separate from findings. Missing evidence is not a healthy
result. Avoid shared fault percentages or severity thresholds unless validated
for the relevant subsystem. Do not combine unrelated recordings into a single
train inspection without supported identifiers and time alignment.

For ACV, the first ranked car is selected automatically in Evidence. Exact top
score ties are explained. Unscored cars are marked Not assessed in the display;
the official export still includes every car, placing unscored cars last by ID.
Rich-layout assumptions are visible for the selected recording. Raw chart data
includes all modes; the score uses the existing baseline eligibility rules.

The shared app should call each subsystem pipeline and preserve its official
export format. The ACV prototype exposes render_acv() as its page body; its
standalone page configuration stays in the main guard. Its imports and Streamlit
dependencies need checking in the shared app's launch environment.
