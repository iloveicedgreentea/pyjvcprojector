# pyjvcprojector

A python library for controlling a JVC Projector over a network connection.

https://pypi.org/project/pyjvcprojector/

## Features

### Convenience functions:
* `JvcProjector::power_on()` turns on power.
* `JvcProjector::power_off()` turns off power.
* `JvcProjector::get_power()` gets power state (_standby, on, cooling, warming, error_)
* `JvcProjector::get_input()` get current input (_hdmi1, hdmi2_).
* `JvcProjector::get_signal()` get signal state (_signal, nosignal_).
* `JvcProjector::get_state()` returns {_power, input, signal_}.
* `JvcProjector::get_info()` returns {_model, mac address_}.

### Send remote control codes
A wrapper for calling `JvcProjector::op(f"RC{code}")`
* `JvcProjector::remote(code)` sends remote control command.

### Send raw command codes
* `JvcProjector::ref(code)` sends reference commands to read data. `code` is formatted `f"{cmd}"`.
* `JvcProjector::op(code)` sends operation commands to write data. `code` is formatted `f"{cmd}{val}"`.

## Installation

```
pip install pyjvcprojector
```

## Usage

```python
import asyncio

from jvcprojector.projector import JvcProjector
from jvcprojector import const


async def main():
    jp = JvcProjector("127.0.0.1")
    await jp.connect()

    print("Projector info:")
    print(await jp.get_info())

    if await jp.get_power() != const.ON:
        await jp.power_on()
        print("Waiting for projector to warmup...")
        while await jp.get_power() != const.ON:
            await asyncio.sleep(3)

    print("Current state:")
    print(await jp.get_state())

    #
    # Example sending remote code
    #
    print("Showing info window")
    await jp.remote(const.REMOTE_INFO)
    await asyncio.sleep(5)

    print("Hiding info window")
    await jp.remote(const.REMOTE_BACK)

    #
    # Example sending reference command (reads value from function)
    #
    print("Picture mode info:")
    print(await jp.ref("PMPM"))

    #
    # Example sending operation command (writes value to function)
    #
    # await jp.ref("PMPM01")  # Sets picture mode to Film

    await jp.disconnect()
```
