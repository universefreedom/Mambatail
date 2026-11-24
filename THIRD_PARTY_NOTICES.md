# Third-party notices

This file records third-party material referenced or bundled by the MambaTail public portfolio. It does not select or grant a project-wide MambaTail license. The project source remains `LICENSE_UNDECIDED`; each third-party item remains governed by its own terms.

## Bundled public demonstration images

The following photographs are bundled only for the separate `PUBLIC_VISUAL_REFERENCE` similarity demonstration. They are not behavior ground truth and are not frames from the protected research video.

| Local file | Creator | Source | Declared license | SHA-256 |
|---|---|---|---|---|
| `app/static/demo/public-gallery/gallery-dog-forest.jpg` | Ssroldan | [Dog in forest.jpg](https://commons.wikimedia.org/wiki/File:Dog_in_forest.jpg) | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) | `648FB3FF269970C8308373B8CC831BF6916D71A6A8B71C2300CCCF53AD4FC830` |
| `app/static/demo/public-gallery/gallery-dirt-road.jpg` | Arlo Barnes | [Dog on dirt road.jpg](https://commons.wikimedia.org/wiki/File:Dog_on_dirt_road.jpg) | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) | `15E9C6497A5A7C34CACD02D6033923B8A0839973EF6E480EC9A186AF773F2603` |
| `app/static/demo/public-gallery/gallery-warm-cloth.jpg` | Savexig63 | [Dog wearing warm cloth.jpg](https://commons.wikimedia.org/wiki/File:Dog_wearing_warm_cloth.jpg) | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) | `3678D3441970C4849722E041B27E0E8340C81CFA383856B53A466A932700A475` |
| `app/static/demo/public-gallery/gallery-sitting-forest.jpg` | Hamoma30 | [Cute dog sitting in forest.jpg](https://commons.wikimedia.org/wiki/File:Cute_dog_sitting_in_forest.jpg) | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) | `69DEBA54A3349DF72657BF7248D0C617AFFD6305DE1F97D7C6914F735A9E5383` |

Wikimedia Commons and the uploaders do not warrant privacy, personality, trademark, or other third-party rights.

## Legacy derived pose coordinates

An older, non-default pose-coordinate bundle retained for provenance was derived from [Batumi2025dog-laying-relax.webm](https://commons.wikimedia.org/wiki/File:Batumi2025dog-laying-relax.webm), created by Vitaly Zdanevich and licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). The public route excludes this legacy lying-video demonstration. The repository does not redistribute its raw RGB video or audio.

## Model and implementation references

| Component | Upstream implementation | Upstream code license | Checkpoint/data boundary |
|---|---|---|---|
| OpenAI CLIP RN50 | [openai/CLIP](https://github.com/openai/CLIP) | [MIT](https://github.com/openai/CLIP/blob/main/LICENSE) | Exact weights are identified by SHA in the model ledger and are not redistributed. The upstream repository does not state a separate weight-specific grant in its MIT license file. |
| RTMDet-M | [open-mmlab/mmdetection](https://github.com/open-mmlab/mmdetection) | [Apache-2.0](https://github.com/open-mmlab/mmdetection/blob/main/LICENSE) | Checkpoint is referenced by filename and SHA only; it is not redistributed. |
| RTMPose-M AP-10K native17 | [open-mmlab/mmpose](https://github.com/open-mmlab/mmpose) | [Apache-2.0](https://github.com/open-mmlab/mmpose/blob/main/LICENSE) | Checkpoint is referenced by filename and SHA only. AP-10K declares [CC BY 4.0](https://github.com/AlexTheBad/AP-10K/blob/main/LICENSE); code and training-data terms are recorded separately. |
| reveal.js 6.0.2 | [hakimel/reveal.js](https://github.com/hakimel/reveal.js) | [MIT](presentation/vendor/reveal.js/LICENSE) | Vendored presentation runtime; its upstream license is bundled unchanged. |

Exact checkpoint identifiers, hashes, papers, and use boundaries are listed in [MODEL_AND_CHECKPOINT_REFERENCES.md](MODEL_AND_CHECKPOINT_REFERENCES.md).

## Redistribution boundary

This repository does not redistribute the referenced model checkpoints, training datasets, private embeddings, raw protected research videos, or local databases. A code license does not automatically determine the license of a trained checkpoint or its training data. Nothing in this notice expands upstream rights.
