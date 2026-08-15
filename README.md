# Garden Speaker

Home Assistant custom integration for operating the Garden Speaker Bluetooth
audio stack through its local Control API. Music playback remains in OwnTone
and Music Assistant; this integration diagnoses and repairs the supporting
Bluetooth, PulseAudio, OwnTone, and Docker chain.

## Features

- Polls `GET /api/v1/health/check` every 45 seconds.
- Health sensor with issue, Bluetooth, PulseAudio, OwnTone, and container details.
- Connectivity and OwnTone-output binary sensors.
- Services for a fresh health check, soft repair, full Bluetooth re-pair, and
  ordered stack restart.
- Optional `X-API-Key` authentication for mutating API routes.

## Install

### HACS

Add `https://github.com/zlatko-lakisic/hacs-garden-speaker` as a custom
integration repository, install **Garden Speaker**, and restart Home Assistant.

### Manual

Copy `custom_components/garden_speaker` into the Home Assistant
`custom_components` directory and restart Home Assistant.

Then open **Settings → Devices & services → Add integration → Garden Speaker**.
The defaults target `192.168.89.27:8090`.

## Services

- `garden_speaker.health_check`: immediately refresh the full diagnosis.
- `garden_speaker.repair`: perform safe repairs without deleting pairing data.
- `garden_speaker.repair_pairing`: remove and recreate Bluetooth pairing.
  Before calling it, hold the PartyBox Bluetooth button for 3–5 seconds until
  the LED blinks rapidly, turn off Bluetooth on nearby phones, and set
  `confirm_pairing_mode: true`. Home Assistant posts a persistent progress
  notification.
- `garden_speaker.restart_stack`: restart managed services in dependency order.
  `include_control_api` defaults to `false`.

When multiple Garden Speaker instances are configured, select
`config_entry_id` in the service call.

Example:

```yaml
action: garden_speaker.repair_pairing
data:
  confirm_pairing_mode: true
```

Full re-pair and restart operations can take up to three minutes.
