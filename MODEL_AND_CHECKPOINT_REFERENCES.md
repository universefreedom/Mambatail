# Model and checkpoint references

This ledger identifies the frozen model artifacts used to generate the portfolio evidence. It is a provenance and citation record, not a redistribution of the artifacts and not a legal conclusion about checkpoint rights.

## Frozen artifact ledger

| Role | Exact artifact identifier | SHA-256 | Implementation and code license | Training-data or weight note | Redistributed here |
|---|---|---|---|---|---|
| Visual embedding | OpenAI CLIP `RN50` | `AFEB0E10F9E5A86DA6080E35CF09123ACA3B358A0C3E3B6C78A7B63BC04B6762` | [openai/CLIP](https://github.com/openai/CLIP), [MIT](https://github.com/openai/CLIP/blob/main/LICENSE) | Upstream MIT file covers the repository code but does not state a separate weight-specific license. No additional right to the weight is claimed here. | No; SHA reference only |
| Dog detector | `rtmdet_m_8xb32-300e_coco_20220719_112220-229f527c.pth` | `229F527CA88498E8894A778A62A878A322B4A3EA2CAE09EA537D34B7E907792B` | [open-mmlab/mmdetection](https://github.com/open-mmlab/mmdetection), [Apache-2.0](https://github.com/open-mmlab/mmdetection/blob/main/LICENSE) | Upstream checkpoint referenced by exact filename; checkpoint terms are not inferred solely from the code license. | No; SHA reference only |
| Animal pose | `rtmpose-m_simcc-ap10k_pt-aic-coco_210e-256x256-7a041aa1_20230206/end2end.onnx` | `1CFD1C86E0D9E5D5F95178BCD95EE9A4E8386A624CD3C57519F27FF58CAC7F28` | [open-mmlab/mmpose](https://github.com/open-mmlab/mmpose), [Apache-2.0](https://github.com/open-mmlab/mmpose/blob/main/LICENSE) | Model name declares AP-10K training; [AP-10K](https://github.com/AlexTheBad/AP-10K) declares [CC BY 4.0](https://github.com/AlexTheBad/AP-10K/blob/main/LICENSE). Dataset and implementation licenses remain distinct. | No; SHA reference only |

## Code and paper citations

- Radford, A. et al. “Learning Transferable Visual Models From Natural Language Supervision.” ICML 2021. [Paper](https://proceedings.mlr.press/v139/radford21a.html); [implementation](https://github.com/openai/CLIP).
- Lyu, P. et al. “RTMDet: An Empirical Study of Designing Real-Time Object Detectors.” 2022. [Paper](https://arxiv.org/abs/2212.07784); [implementation](https://github.com/open-mmlab/mmdetection).
- Jiang, T. et al. “RTMPose: Real-Time Multi-Person Pose Estimation based on MMPose.” 2023. [Paper](https://arxiv.org/abs/2303.07399); [implementation](https://github.com/open-mmlab/mmpose).
- Yu, H. et al. “AP-10K: A Benchmark for Animal Pose Estimation in the Wild.” NeurIPS 2021 Datasets and Benchmarks. [Dataset repository](https://github.com/AlexTheBad/AP-10K); [license](https://github.com/AlexTheBad/AP-10K/blob/main/LICENSE).

## Interpretation boundary

- SHA-256 values bind reported evidence to exact local artifacts; they do not grant redistribution rights.
- Implementation code licenses, checkpoint terms, and dataset licenses are separate layers.
- The portfolio reports pose observations and uncalibrated similarity for `LIMITED_EXPERT_ASSISTED_RECOMMENDATION`; it does not claim clinical or definitive expert judgment.
