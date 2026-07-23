# Claim ledger

Verified: 2026-07-23

This ledger separates source-backed facts from working interpretations. A
claim marked `inference` must not be restated as vendor-confirmed behavior.

| Claim | Status | Evidence / qualification |
|---|---|---|
| aegis-360 can operate from decoded monoscopic equirectangular video without proprietary camera files. | confirmed | This is the project's accepted input boundary, not a claim that every nominally 2:1 file is valid ERP. Input projection still requires validation. |
| Insta360 Deep Track, Auto Frame, and Auto Edit are the same feature. | disproven | Insta360 documents them as distinct workflows. Deep Track follows a selected target; Auto Frame proposes views; Auto Edit performs broader clip/framing/edit decisions. [Deep Track](https://onlinemanual.insta360.com/studio/en-us/operation-guide/edit-function/deep-tracking-function), [Auto Edit](https://onlinemanual.insta360.com/app/en-us/operation-tutorial/edit-function/auto-edit) |
| Importing a generic MP4 into Insta360 Studio proves that all AI editing features support it. | unknown | Studio documents MP4/MOV import, while Deep Track compatibility is described using supported Insta360 models/modes. Importability does not establish feature eligibility. [Import guide](https://onlinemanual.insta360.com/studio/zh-cn/operation_guide/file_management/import), [Deep Track](https://onlinemanual.insta360.com/studio/en-us/operation-guide/edit-function/deep-tracking-function) |
| Renaming or remuxing GoPro footage as Insta360 media should enable Insta360 one-click editing. | unsupported | Container, extension, 2:1 pixels, camera metadata, proxy/analysis files, and application-level feature gating are separate concerns. Which exact gate rejects a particular file remains an empirical question. |
| Insta360's public disclosures describe scene/object/action recognition, aesthetics/highlight analysis, interest trajectories, and viewpoint-path planning. | confirmed | These strategy-level statements appear in company disclosures and product documentation; they do not reveal a reproducible production model. [Auto Edit](https://onlinemanual.insta360.com/app/en-us/operation-tutorial/edit-function/auto-edit), [2025 interim report](https://dataclouds.cninfo.com.cn/shgonggao/2025/2025-08-29/e7e73ee0840811f0a00dfa163e957f7a.pdf) |
| Insta360 has published enough detail to reproduce its Auto Edit algorithm. | disproven | Public material omits model architecture, training data, losses, production thresholds, feature weights, and end-to-end evaluation. |
| Automatic 360-to-2D reframing predates aegis-360. | confirmed | Prior academic work includes *Making 360° Video Watchable in 2D* (2017). The novelty claim cannot be “automatic 360 reframing has no alternative.” [Paper](https://arxiv.org/abs/1703.00495) |
| The defensible product hypothesis is an offline, camera-agnostic auto-director that chooses subjects/events without requiring a user-selected target. | inference | This is the proposed differentiation to test against fixed-forward and simple saliency/motion baselines, not a proven market gap. |
| “Ordinary viewers find this interesting” has one objective ground truth. | disproven | Viewer preference can be multimodal. Evaluation should allow multiple acceptable viewpoints and use blind pairwise preference across viewers. |
| FFmpeg `v360` is sufficient for production performance. | unknown | It is the geometry reference path. Dynamic control semantics, throughput, quality, memory use, and A/V behavior require local measurement. |
| The three public benchmark files may be adapted and publicly shown without contacting their creators. | confirmed | Their Commons pages preserve CC BY 3.0 or CC BY-SA 3.0 grants. Attribution and, for Old Ghost Road derivatives, ShareAlike obligations still apply. See `benchmarks/manifest.toml`. |
| Those Creative Commons grants clear every face, trademark, location, music, and privacy right. | disproven | Copyright licensing does not automatically clear personality, privacy, trademark, publicity, or third-party audio rights. Public outputs require content review. |

## Open verification work

- Perform controlled Insta360 feature-gating tests only if native and exported
  comparison media can be obtained lawfully.
- Probe benchmark files locally and record exact projection/container/audio
  properties and checksums before use.
- Test whether viewer preference favors the global planner over fixed-forward
  and greedy-with-hysteresis baselines.
- Treat MAX2 native-format compatibility as unverified until a licensed native
  sample is inspected.
