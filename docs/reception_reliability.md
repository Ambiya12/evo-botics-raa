# Reception Reliability Validation

This milestone defines repeatable measurements; it does not claim robot
performance. Laptop/mock checks and robot acoustic checks must be recorded
separately.

## Acceptance targets

| Measure | Laptop/mock target | Robot target |
| --- | ---: | ---: |
| Recognition success, quiet | >= 95% | >= 90% |
| Recognition success, noisy lobby | Fixture baseline only | >= 80% |
| STT latency, audio start to transcript, p95 | <= 2.0 s | <= 2.5 s |
| End-to-end decision latency, approach to navigation request, p95 | <= 6.0 s | <= 8.0 s |
| False usable transcripts from silence/noise | 0 per 20 trials | <= 1 per 50 trials |

A recognition succeeds when normalized word error rate is at most 0.20.
Navigation travel time is excluded from decision latency because it depends on
the map and destination.

## Measurement record

Store one JSON object per line. Use monotonic seconds from one clock:

```json
{"environment":"mock","noise":"quiet","expected_transcript":"Yes, I do","actual_transcript":"Yes, I do","audio_started_at":10.0,"transcript_published_at":10.8,"approach_at":8.0,"navigation_requested_at":13.2}
```

Required recognition fields are `expected_transcript` and
`actual_transcript`. Latency pairs are optional, but both fields in a pair
must be recorded. Keep raw JSONL files outside the repository if they contain
visitor audio or personal data.

Summarize a recording with:

```bash
cd evo_ws/src/evo_voice
python3 -m evo_voice.reliability_metrics measurements.jsonl
```

## Laptop and fixture procedure

1. Prepare at least 20 English reception utterances, covering every supported
   intent and natural synonyms.
2. Replay each quiet fixture through `/voice/stt/mock_audio_path`; record the
   expected and published transcript.
3. Create noisy copies at fixed signal-to-noise ratios, for example 20, 10,
   and 5 dB, using an offline audio editor. Preserve the clean fixtures.
4. Repeat each set with the same model and parameters. Record the model,
   device, `vad_rms_threshold`, and `minimum_confidence` beside the JSONL file.
5. Run the metrics tool separately for each noise level. Do not combine quiet
   and noisy results into one success rate.
6. Run the complete mock launch at least 20 times and record timestamps from
   `PersonApproach`, `Transcript`, and `WorkflowStatus` messages using the same
   ROS clock.

Mock transcripts test workflow timing but do not measure Faster Whisper
accuracy. Prerecorded microphone-like WAV fixtures measure STT repeatability,
not the robot microphone or lobby acoustics.

## Robot noisy-room procedure — pending robot validation

1. Measure from the intended visitor position with the deployed microphone.
2. Record 20 utterances in quiet conditions and 50 with representative lobby
   noise and TTS volume.
3. Include different speakers, speaking rates, and distances without storing
   identities.
4. Record silence/noise-only trials and count any published usable transcript.
5. Repeat after changing microphone placement, gain, model, VAD, or confidence
   settings. Change one variable per run.
6. Mark the targets above verified only after preserving the parameter set and
   anonymized metrics output.

## VAD and STT configuration

Supported ROS parameters are:

- `vad_rms_threshold` (`0.0`–`1.0`, default `0.01`): raises the minimum WAV
  energy accepted by the local pre-filter.
- `minimum_confidence` (`0.0`–`1.0`, default `0.4`): rejects low-confidence
  transcription results when Faster Whisper supplies confidence.
- `language`: keep `en` for English reliability runs; `auto` adds language
  detection variability.

Start with existing defaults. Sweep `vad_rms_threshold` through `0.005`,
`0.01`, and `0.02`, then sweep `minimum_confidence` through `0.4`, `0.5`, and
`0.6` only if the fixture results justify tuning. Select the lowest settings
that meet both recognition and false-transcript targets. Do not tune from mock
text input.

Acoustic echo cancellation is not added: STT already pauses while TTS speaks,
and no measured residual echo failure exists. Reconsider AEC only if robot
tests show transcripts after the pause boundary or unavoidable simultaneous
listening.

## Offline operation checklist

- [ ] Disconnect network access before launch.
- [ ] Confirm the configured Whisper and Piper model paths already exist.
- [ ] Launch without downloads, package installation, or cloud credentials.
- [ ] Complete the mock happy path and one failure path.
- [ ] Replay a local WAV fixture and observe a local transcript.
- [ ] Confirm QR mock verification and mock navigation work offline.
- [ ] Record the result as laptop-verified or robot-verified, with date and
      configuration.

## Node restart recovery checklist

Run each check in mock mode first. Robot execution remains pending validation.

- [ ] Restart STT while idle; it resumes publishing only new transcripts.
- [ ] Restart TTS while idle; status returns to `idle` and the queue is empty.
- [ ] Restart intent detection; subsequent transcripts produce one result.
- [ ] Restart the QR bridge; unavailable verification fails safely until ready.
- [ ] Restart navigation; readiness gates reject requests until it is ready.
- [ ] Restart the dialogue manager; transient state returns to `IDLE`, no
      previous destination is resumed, and a new visitor starts a new session.
- [ ] Restart the complete mock launch and complete a fresh happy path.
- [ ] Confirm no restart produces movement without a new verified request.

## Multilingual gate

French and translation remain disabled in the reception workflow. Enable a
French experiment only after English meets every robot target in this document
across two repeat runs. Any later implementation must remain offline, use
language-specific intent phrases and TTS voices, and keep translation isolated
from STT and dialogue state.
