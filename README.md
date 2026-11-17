# pyjvcprojector

An asynchronous Python library for controlling network-connected JVC D-ILA projectors. Requires Python 3.10 or newer and has no third-party runtime dependencies.

Forked from [SteveEasley/pyjvcprojector](https://github.com/SteveEasley/pyjvcprojector).

## Installation

```sh
pip install pyjvcprojector_test
```

The distribution is named `pyjvcprojector_test`; its import package is `jvcprojector`. The [Home Assistant integration](https://github.com/iloveicedgreentea/jvc_homeassistant) bundles a private copy, so it does not need a separate pip installation.

## Usage

```python
import asyncio

from jvcprojector import const
from jvcprojector.projector import JvcProjector


async def main():
    projector = JvcProjector("192.168.1.100", password="your-password")
    try:
        await projector.connect(get_info=True)
        print(projector.model, projector.version)
        print(await projector.get_state())
        if await projector.is_on():
            await projector.remote(const.REMOTE_INFO)
            await projector.send_command("input", "hdmi1")
    finally:
        await projector.disconnect()


asyncio.run(main())
```

Omit `password` for models configured without one. Legacy and SHA-256 authentication are supported. Change the default TCP port with `port=20554` and the transport timeout with `timeout=15.0`.

## Commands

- `power_on()` and `power_off()` change power; `get_power()` reads `standby`, `on`, `cooling`, `warming`, or `error`. `is_on()` checks whether the projector is ready.
- `get_info()` reads model, MAC address, and available firmware information.
- `send_command(name, value)` accepts named settings such as `("input", "hdmi1")` or `("laser_power", "high")`. `validate_command(name, value, model=projector.model)` validates and normalizes a setting without sending it.
- `remote(code)` accepts exactly four hexadecimal characters, such as `const.REMOTE_UP`. Generic remote commands have no separate key-down/key-up message; repeated presses do not reproduce every physical remote hold action.
- `ref(code)` sends a raw reference and returns its decoded value. `op(code)` sends a raw operation including its data parameter. These low-level methods require the correct model-specific command format.

`JvcCommandHelpers` in `jvcprojector.command` provides `get_available_commands()` and `get_command_help("picture_mode")`. Its help describes the general command vocabulary; model-specific values can differ. Read-only references and response decoders cannot be used as named setters.

A failed operation or critical reference raises an error. Do not automatically retry operations: a lost acknowledgement can follow a successful keypress. Optional references that time out are skipped for five minutes, and their TCP stream is discarded before another exchange. `clear_unsupported_commands()` clears that backoff.

Commands return after their final acknowledgement. A 200 ms recovery interval remains between exchanges, including separate calls. Calls on one projector must be serialized; lens lifecycle and cooperative polling also require caller coordination.

## State polling

`get_state()` returns a fresh mapping of available state. Missing or no-longer-applicable values are omitted rather than retained from a previous signal.

Pass `requested_keys` to limit polling:

```python
state = await projector.get_state(requested_keys={"picture_mode", "laser_time"})
```

Power and source/HDR dependencies remain automatic. Omitting `requested_keys` preserves the base query set. Additional HDMI diagnostics (`deep_color`, `colorimetry`) require explicit requests. NZ800/NZ900 also support optional ALLM, Deep Black, Filmmaker auto, Highlight Color, and Smoother state. Commands and valid values depend on the model, firmware, power, and signal.

For controllers that prioritize input over polling, `get_state(reference_reader=reader)` delegates each complete reference to an async callback:

```python
async def reader(code):
    async with io_lock:  # Use the same lock for foreground commands.
        await projector.connect()
        return await projector.ref(code)

state = await projector.get_state(reference_reader=reader)
```

The callback owns connection setup and serialization and must return the decoded result of `ref(code)`. It may yield to controls or abort before starting the next reference. Exceptions discard the partial snapshot; firmware lookup also uses the callback. Do not cancel an exchange midway to prioritize another command. Without a callback, references retain their batched behavior.

## Lens adjustment

`lens_step(direction)` performs one native finite adjustment. `lens_move(direction, start=True)` starts continuous movement; `start=False` stops it. Supported directions are `focus_near`, `focus_far`, `zoom_tele`, `zoom_wide`, `shift_left`, `shift_right`, `shift_up`, and `shift_down`. These APIs require an identified NZ7/NZ8/NZ9/NP5 or NZ800/NZ900 model.

The caller must serialize motor operations, enforce a time limit, and attempt a matching stop even when the start acknowledgement is lost:

```python
try:
    await projector.lens_move("shift_left", start=True)
    await asyncio.sleep(0.5)
finally:
    await projector.lens_move("shift_left", start=False)
```

Only one motor may run at a time. Closing TCP is not a motor-stop command, and a network outage can prevent delivery of a stop. The Home Assistant integration provides bounded lens services with stop handling.

## Protocol references

[JVC's installer documentation](https://www.jvc.com/usa/projectors/installers-calibrators/) provides the model-specific command tables. NZ800/NZ900 mappings follow External Command Communication Specification Ver. 2.0 (8 October 2025), LAN connection specification (9 December 2024), and remote-code table Ver. 2.1. Older model tables remain separate where values differ. Numeric laser writes and multi-stage calibration operations require dedicated implementations; their write formats are not inferred from response decoders.

## Development

```sh
python -m pip install -e . pytest pytest-asyncio build
python -m pytest
python -m build
```

Tests use simulated projectors by default. To run the read-only hardware check, set `RUN_INTEGRATION=true`, `JVC_IP`, and, if needed, `JVC_PASSWORD`. This check does not change power or picture settings.
