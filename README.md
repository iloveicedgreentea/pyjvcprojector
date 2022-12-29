# pyjvcprojector

A python library for controlling a JVC Projector over a network connection.

https://pypi.org/project/pyjvcprojector/

## Features

### Key wrapper functions:
* `JvcProjector::get_power()` gets power state (standby, on, cooling, warming, error)
* `JvcProjector::power_on()` turns on power.
* `JvcProjector::power_off()` turns off power.
* `JvcProjector::get_input()` get current input (hdmi1, hdmi2, etc).
* `JvcProjector::get_signal()` get signal state (signal, nosignal).
* `JvcProjector::get_info()` returns {power state, current input, and signal status}.
* `JvcProjector::get_status()` returns {projector model, mac address}.

### Send remote control codes
* `JvcProjector::remote(code)` sends remote control command

### Send raw command codes
* `JvcProjector::ref(code)` sends reference commands (read data)
* `JvcProjector::op(code)` sends operation commands (write data)

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

    if await jp.get_power() == const.STANDBY:
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
