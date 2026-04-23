# IBL Science: Fiber Photometry Dataset

This document provides scientific context for the IBL fiber photometry dataset converted by this pipeline.

## Experiment Overview

This experiment investigates the distinct roles of key neuromodulators — dopamine, serotonin, norepinephrine, and acetylcholine — in shaping decision-making and adaptive behavior. Using the International Brain Laboratory's standardized decision-making task (validated for reproducibility across behavior and neural recordings), neuromodulatory activity is systematically examined across multiple brain regions and task events.

The scientific goals are to:
- Link neuromodulatory dynamics to learning and behavioral strategy shifts
- Connect observed dynamics to theoretical models of decision making
- Develop integrated hardware for high-throughput fiber photometry acquisition compatible with the IBL behavioral platform

## Fiber Photometry Recording

Fiber photometry is an optical technique for monitoring neural activity in freely moving animals. In this dataset:

- **GCaMP signal** (470 nm excitation): Calcium-dependent fluorescence that reflects neural activity in the targeted brain region
- **Isosbestic signal** (415 nm excitation): Calcium-independent control signal used to correct for motion artifacts and bleaching

Each session records from one or more brain areas simultaneously, with one optical fiber implanted per target region.

## Behavioral Task

The primary task is the IBL decision-making task (biasedChoiceWorld / advancedChoiceWorld):

- A Gabor patch appears at +/-35 degrees azimuth
- The mouse turns a steering wheel to bring it to the center of the screen
- Correct responses earn a water reward (~1.5 uL)
- Incorrect responses trigger white noise and a 2s timeout
- Stimulus probability alternates between 80/20 and 20/80 blocks
- Contrast levels: 100%, 25%, 12.5%, 6.25%, 0%

Sessions may also include passive replay periods (passiveChoiceWorld) where the same stimuli are presented without behavioral contingency.

## Task Protocols

The `task_protocol` field in the session metadata identifies which protocol was run. Fiber photometry sessions commonly use:

| Protocol | Type | Description |
|----------|------|-------------|
| `cuedBiasedChoiceWorld` | Active | Biased choice world with added visual cues |
| `biasedChoiceWorld` | Active | Standard IBL data-collection task |
| `advancedChoiceWorld` | Active | iblrig v8+ replacement for biasedChoiceWorld |
| `passiveChoiceWorld` | Passive | Replay of choice world stimuli without behavioral contingency |
| `spontaneous` | Passive | Gray screen, no stimuli or task |

A single session may contain multiple tasks (e.g. `task_00` = active, `task_01` = passive), each stored in its own ALF collection directory.

## Recorded Data Modalities

Each NWB file can contain the following data, depending on session availability:

| Modality | Description |
|----------|-------------|
| **GCaMP fluorescence** | Calcium-dependent signal from each recorded brain area |
| **Isosbestic control** | Motion/bleaching control signal from each area |
| **Fiber photometry hardware metadata** | Optical fiber, LED, photodetector, filter specifications |
| **Fiber tip coordinates** | Anatomical location of each fiber tip (placeholder until histology data available) |
| **Wheel position and movements** | Rotary encoder data from the steering wheel |
| **Behavioral trials** | Trial-by-trial outcomes, timings, contrasts, and choices |
| **Session epochs** | High-level task vs passive phase boundaries |
| **Passive stimuli** | Replay stimuli timing and parameters |
| **Lick times** | Lick detection events |
| **Pose estimation** | Body part tracking from video (Lightning Pose or DeepLabCut) |
| **Pupil tracking** | Pupil diameter from left/right camera video |
| **ROI motion energy** | Motion energy from video regions of interest |
| **Raw behavioral video** | Camera recordings (left, right, body) |

## Related Resources

- [IBL website](https://www.internationalbrainlab.com/)
- [IBL data architecture paper](https://doi.org/10.1101/2023.07.26.550704)
- [Brain Wide Map dataset (DANDI:000409)](https://dandiarchive.org/dandiset/000409) — The Neuropixels counterpart
- [ONE API documentation](https://int-brain-lab.github.io/ONE/)
