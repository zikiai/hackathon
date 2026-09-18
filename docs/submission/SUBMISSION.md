# rookies — submission links and checklist

## Portal links

- **Team:** rookies
- **Problem statement:** PS3 — Train Condition Monitoring
- **GitHub:** https://github.com/zikiai/hackathon
- **README:** https://github.com/zikiai/hackathon/blob/main/README.md
- **Prototype:** https://nebulax-workspace-1029817906638.asia-southeast1.run.app/
- **Write-up:** https://github.com/zikiai/hackathon/blob/main/docs/submission/write_up.md
- **Video:** not included, as requested. Add the required 2–3 minute demo separately.

## Package structure

```text
rookies/
├── predictions.zip
├── app/                   Runtime code, models, Dockerfile and README
└── Optional_Items/
    ├── write_up.md
    ├── SUBMISSION.md
    ├── prediction_validation.json
    └── package_manifest.json
```

The app includes the inference code and trusted model bundles needed by its
Dockerfile. No raw datasets, credentials, local environments or organiser sample
prediction files are packaged. Hosted deployment instructions are in its README.

Keep `predictions.zip` zipped directly under `rookies`, even when zipping the whole
team folder. Its top level contains exactly these four files and no subfolders:

| Filename | Header | Coverage |
|---|---|---|
| rail_predictions.csv | file_id,prediction | Test1.csv–Test68.csv; 68 rows |
| door_predictions.csv | start_time,end_time,prediction | 38 predicted movements from Test.csv; no file_id |
| acv_predictions.csv | file_id,ranked_cars | One workbook; eight exact two-digit car IDs separated by `\|` |
| shm_predictions.csv | file_id,prediction | test01.csv–test16.csv; 16 numeric damage estimates |

Door timestamps use the accepted native hyphen-separated format. The archive has
no confidence columns, explanations or manifests. Those checks and checksums are
stored separately in `Optional_Items/prediction_validation.json`.

## Before pressing Submit

1. Add `demo_video.mp4` (or another accepted format) at the `rookies` root, or supply
   the accessible video link if requested by the portal. Show real uploads,
   results and downloads. The PS3 specification limits the demo to three minutes.
2. Check prototype and repository access as a signed-out judge.
3. Keep the temporary Google Cloud project active throughout judging.
4. Upload the package, complete portal fields and confirm its receipt.

No video has been produced and no competition submission has been sent by this
preparation task. Member names were not supplied; no personal contribution claims
are invented.

## Official references checked

- [PS3 deliverables, schemas, packaging and grading](https://github.com/aochinwen/NebulaX-Hackathon-ProblemStatement/blob/966c976005db2e3e40a691cff268fdb8f396a5df/PS3/01_Problem_Statement_3_Specifications.md)
- [Door timestamp and segment requirements](https://github.com/aochinwen/NebulaX-Hackathon-ProblemStatement/blob/966c976005db2e3e40a691cff268fdb8f396a5df/PS3/03_References/Door/Door_Subsystem_Info_Kit.md)

The participant slide additionally requests GitHub/README, the hosted link and a
short write-up; these are supplied here. The GitHub specification accepts Markdown
for the write-up, so a separate PDF or Word file is not required.
