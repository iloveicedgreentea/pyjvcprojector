"""Tests for projector module."""

from unittest.mock import AsyncMock

from unittest.mock import patch
import pytest

from jvcprojector import const
from jvcprojector.command import HEAD_ACK, HEAD_RES, JvcCommand
from jvcprojector.error import JvcProjectorError
from jvcprojector.projector import JvcProjector

from . import HOST, IP, MAC, MODEL, PORT, VERSION, cc


@pytest.mark.asyncio
async def test_init(dev: AsyncMock):
    """Test init succeeds."""
    p = JvcProjector(IP, port=PORT)
    assert p.host == IP
    assert p.port == PORT
    with pytest.raises(JvcProjectorError):
        assert p.ip
    with pytest.raises(JvcProjectorError):
        assert p.model
    with pytest.raises(JvcProjectorError):
        assert p.mac


@pytest.mark.asyncio
async def test_connect(dev: AsyncMock):
    """Test connect succeeds."""
    p = JvcProjector(IP, port=PORT)
    await p.connect()
    assert p.ip == IP
    await p.disconnect()
    assert dev.disconnect.call_count == 1


@pytest.mark.asyncio
async def test_connect_host(dev: AsyncMock):
    """Test connect succeeds."""
    p = JvcProjector(HOST, port=PORT)
    await p.connect()
    assert p.ip == IP
    await p.disconnect()
    assert dev.disconnect.call_count == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("dev", [{const.CMD_MODEL: None}], indirect=True)
async def test_unknown_model(dev: AsyncMock):
    """Test projector with unknown model succeeds."""
    p = JvcProjector(IP)
    await p.connect()
    await p.get_info()
    assert p.mac == MAC
    assert p.model == "(unknown): Unknown"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "dev", [{const.CMD_LAN_SETUP_MAC_ADDRESS: None}], indirect=True
)
async def test_unknown_mac(dev: AsyncMock):
    """Test projector with unknown mac uses model succeeds."""
    p = JvcProjector(IP)
    await p.connect()
    with pytest.raises(JvcProjectorError):
        assert p.mac == ""


@pytest.mark.asyncio
async def test_get_info(dev: AsyncMock):
    """Test get_info succeeds."""
    p = JvcProjector(IP)
    await p.connect()
    assert await p.get_info() == {"model": MODEL, "mac": MAC}
    # make sure model code is right
    assert p.model in const.MODEL_MAP.values()
    # make sure version is right
    assert p.version == "3.0.0"


@pytest.mark.asyncio
async def test_get_state(dev: AsyncMock):
    """Test get_state succeeds."""
    p = JvcProjector(IP)
    await p.connect()
    expected_dict = {
        "power": const.ON,
    }
    assert set(expected_dict.items()).issubset((await p.get_state()).items())


def test_version():
    """Test version processing."""

    p = JvcProjector(IP)
    assert p.process_version(VERSION) == "3.0.0"


def test_model():
    """Test model processing."""
    model = "B5A1"
    p = JvcProjector(IP)
    assert p.process_model_code(model) == "NZ9"


@pytest.mark.asyncio
async def test_send_command_success(dev: AsyncMock):
    """Test send_command succeeds."""
    p = JvcProjector(IP, port=PORT)
    await p.connect()

    with patch.object(p, "op", new=AsyncMock()) as mock_op:
        await p.send_command(const.KEY_LASER_POWER, const.HIGH)
        mock_op.assert_awaited_once_with(f"{const.CMD_PICTURE_MODE_LASER_POWER}1")


@pytest.mark.asyncio
async def test_send_command_invalid_value(dev: AsyncMock):
    """Test send_command fails with invalid value."""
    p = JvcProjector(IP, port=PORT)
    await p.connect()

    dev.send.reset_mock()
    with pytest.raises(
        ValueError,
        match=f"Invalid value for {const.KEY_LASER_POWER}: invalid_value",
    ):
        await p.send_command(const.KEY_LASER_POWER, "invalid_value")
    dev.send.assert_not_awaited()


@pytest.mark.asyncio
async def test_send_command_unknown_command(dev: AsyncMock):
    """Test send_command fails with unknown command."""
    p = JvcProjector(IP, port=PORT)
    await p.connect()

    dev.send.reset_mock()
    with pytest.raises(ValueError, match="Unknown command: unknown_command"):
        await p.send_command("unknown_command", "value")
    dev.send.assert_not_awaited()


@pytest.mark.asyncio
async def test_is_command_supported_before_connect(dev: AsyncMock):
    """Test is_command_supported returns True before connect."""
    p = JvcProjector(IP, port=PORT)
    assert p.is_command_supported(const.CMD_PICTURE_MODE_LOW_LATENCY)


@pytest.mark.asyncio
async def test_get_unsupported_commands_before_connect(dev: AsyncMock):
    """Test get_unsupported_commands returns empty set before connect."""
    p = JvcProjector(IP, port=PORT)
    assert p.get_unsupported_commands() == set()


@pytest.mark.asyncio
async def test_clear_unsupported_commands_before_connect(dev: AsyncMock):
    """Test clear_unsupported_commands works before connect."""
    p = JvcProjector(IP, port=PORT)
    p.clear_unsupported_commands()


@pytest.mark.asyncio
async def test_get_state_with_partial_response(dev: AsyncMock):
    """Test get_state handles missing command responses gracefully."""
    p = JvcProjector(IP, port=PORT)
    await p.connect()
    state = await p.get_state()
    assert const.KEY_POWER in state
    assert state[const.KEY_POWER] == const.ON


@pytest.mark.asyncio
async def test_failed_connect_can_be_retried(dev: AsyncMock):
    """A failed initial test must not leave a falsely connected projector."""
    p = JvcProjector(IP)
    with patch.object(p, "test", side_effect=[JvcProjectorError("offline"), True]):
        with pytest.raises(JvcProjectorError, match="offline"):
            await p.connect()
        await p.connect()
    assert dev.disconnect.await_count == 1
    assert p.ip == IP


@pytest.mark.asyncio
async def test_get_state_discards_stale_signal_and_power_data(dev: AsyncMock):
    """Snapshots must not retain HDR or input details from the previous poll."""
    p = JvcProjector(IP)
    await p.connect(get_info=True)
    first = await p.get_state()
    assert const.KEY_INPUT in first
    with patch.object(p, "_send", new=AsyncMock(return_value=[const.STANDBY])):
        second = await p.get_state()
    assert second[const.KEY_POWER] == const.STANDBY
    assert const.KEY_INPUT not in second
    assert first[const.KEY_POWER] == const.ON


@pytest.mark.parametrize("value", ["hdmi", "", "h", "hdmi1, hdmi2"])
def test_validate_command_rejects_partial_value(value):
    """A substring of a documented value must not be accepted."""
    with pytest.raises(ValueError, match="Invalid value"):
        JvcProjector.validate_command("input", value)


@pytest.mark.parametrize(
    ("cmd", "value"),
    [
        ("source", "signal"),
        ("power", "warming"),
        ("laser_time", "1"),
        ("hdr", "sdr"),
        ("hdr_processing", "hdr10_plus"),
    ],
)
def test_validate_command_rejects_read_only_state(cmd, value):
    """State values and decoders cannot become unsafe setter parameters."""
    with pytest.raises(ValueError):
        JvcProjector.validate_command(cmd, value)


def test_validate_command_normalizes_and_preserves_enum_names():
    """Validation exposes a pure preflight for callers that send batches."""
    assert JvcProjector.validate_command(" INPUT ", " HDMI1 ") == ("input", "hdmi1")
    assert JvcProjector.validate_command("picture_mode", "frameadapt_hdr") == (
        "picture_mode",
        "frameadapt_hdr",
    )


@pytest.mark.asyncio
async def test_remote_normalizes_code_and_rejects_injection(dev: AsyncMock):
    """Remote codes are exactly two hexadecimal bytes in ASCII form."""
    p = JvcProjector(IP)
    with patch.object(p, "op", new=AsyncMock()) as op:
        await p.remote("732e")
        op.assert_awaited_once_with("RC732E")
        for code in ("732E\n", "RC732E", "zzzz", "732", "732E00"):
            with pytest.raises(ValueError, match="four hexadecimal"):
                await p.remote(code)
        op.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("direction", "code"),
    [
        ("focus_near", "INFN"),
        ("focus_far", "INFF"),
        ("zoom_tele", "INZT"),
        ("zoom_wide", "INZW"),
        ("shift_left", "INSL"),
        ("shift_right", "INSR"),
        ("shift_up", "INSU"),
        ("shift_down", "INSD"),
    ],
)
@pytest.mark.parametrize("start", [False, True])
@pytest.mark.parametrize("dev", [{const.CMD_MODEL: "ILAFPJ-B5A3"}], indirect=True)
async def test_lens_move_encodes_continuous_start_and_stop(dev, direction, code, start):
    """Lens motion uses the directional start/stop codes, never remote repeats."""
    p = JvcProjector(IP)
    await p.connect(get_info=True)
    dev.send.reset_mock()
    await p.lens_move(direction, start=start)
    dev.send.assert_awaited_once()
    commands = dev.send.call_args.args[0]
    assert len(commands) == 1
    assert commands[0].code == code + ("1" if start else "0")
    assert commands[0].is_ref is False


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("direction", "code"),
    [
        ("focus_near", "IN1N"),
        ("focus_far", "IN1F"),
        ("zoom_tele", "IN1T"),
        ("zoom_wide", "IN1W"),
        ("shift_left", "IN1L"),
        ("shift_right", "IN1R"),
        ("shift_up", "IN1U"),
        ("shift_down", "IN1D"),
    ],
)
async def test_lens_step_encodes_one_parameterless_operation(
    conn, direction, code, monkeypatch
):
    """A fine adjustment sends one native single-shot command, without 1/0 data."""
    monkeypatch.setattr("jvcprojector.device.COMMAND_INTERVAL", 0)
    conn.readline.side_effect = [
        cc(HEAD_ACK, "\0\0"),
        cc(HEAD_ACK, "PW"),
        cc(HEAD_RES, "PW0"),
        cc(HEAD_ACK, "MD"),
        cc(HEAD_RES, "MDILAFPJ-B5A3"),
        cc(HEAD_ACK, "LS"),
        cc(HEAD_RES, "LS" + MAC),
        cc(HEAD_ACK, "IN"),
    ]
    p = JvcProjector(IP)
    await p.connect(get_info=True)
    conn.write.reset_mock()
    await p.lens_step(direction)
    conn.write.assert_awaited_once_with(b"!\x89\x01" + code.encode() + b"\n")
    await p.disconnect()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "dev",
    [
        {const.CMD_MODEL: code}
        for code in ("B5A3", "B5A2", "B5A1", "B5B1", "B8A2", "B8A1")
    ],
    indirect=True,
)
async def test_lens_step_supports_verified_model_families(dev):
    """All documented lens models accept the single-shot command family."""
    p = JvcProjector(IP)
    await p.connect(get_info=True)
    dev.send.reset_mock()
    await p.lens_step("focus_near")
    dev.send.assert_awaited_once()
    assert dev.send.call_args.args[0][0].code == "IN1N"


@pytest.mark.asyncio
@pytest.mark.parametrize("direction", [None, 1, [], "up", "SHIFT_UP", "shift_up\n"])
async def test_lens_step_rejects_invalid_direction_before_io(dev, direction):
    """Malformed single-shot requests cannot write anything."""
    p = JvcProjector(IP)
    with pytest.raises(ValueError, match="Unknown lens direction"):
        await p.lens_step(direction)
    dev.send.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "dev", [{const.CMD_MODEL: "A2B1"}, {const.CMD_MODEL: None}], indirect=True
)
async def test_lens_step_rejects_unverified_models_before_io(dev):
    """Unsupported and unknown projectors do not receive native lens steps."""
    p = JvcProjector(IP)
    await p.connect(get_info=True)
    dev.send.reset_mock()
    with pytest.raises(ValueError, match="not verified"):
        await p.lens_step("shift_up")
    dev.send.assert_not_awaited()


@pytest.mark.asyncio
async def test_lens_step_rejects_uninitialized_model_before_io(dev):
    """Single steps require model identification before writing."""
    p = JvcProjector(IP)
    with pytest.raises(ValueError, match="not verified"):
        await p.lens_step("shift_up")
    dev.send.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "command_name",
    ["IN1N", "in1n", "IN1F", "IN1T", "IN1W", "IN1L", "IN1R", "IN1U", "IN1D"],
)
async def test_named_commands_reject_raw_lens_step_codes(dev, command_name):
    """The named setting path cannot bypass the dedicated lens step API."""
    p = JvcProjector(IP)
    with pytest.raises(ValueError, match="Unknown command"):
        await p.send_command(command_name, "1")
    dev.send.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "dev",
    [
        {const.CMD_MODEL: code}
        for code in ("B5A3", "B5A2", "B5A1", "B5B1", "B8A2", "B8A1")
    ],
    indirect=True,
)
async def test_lens_move_supports_only_verified_model_families(dev):
    """All documented motor-capable model IDs accept the same start/stop API."""
    p = JvcProjector(IP)
    await p.connect(get_info=True)
    dev.send.reset_mock()
    await p.lens_move("shift_left", start=True)
    await p.lens_move("shift_left", start=False)
    assert [entry.args[0][0].code for entry in dev.send.call_args_list] == [
        "INSL1",
        "INSL0",
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize("direction", [None, 1, [], "up", "SHIFT_UP", "shift_up\n"])
async def test_lens_move_rejects_invalid_direction_before_io(dev, direction):
    """Invalid motor requests cannot write anything, including with no model."""
    p = JvcProjector(IP)
    with pytest.raises(ValueError, match="Unknown lens direction"):
        await p.lens_move(direction, start=True)
    dev.send.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("start", [None, 0, 1, "false", "true"])
async def test_lens_move_requires_explicit_boolean_before_io(dev, start):
    """Strings and integer flags cannot accidentally start a motor."""
    p = JvcProjector(IP)
    with pytest.raises(ValueError, match="must be a boolean"):
        await p.lens_move("shift_up", start=start)
    dev.send.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "dev", [{const.CMD_MODEL: "A2B1"}, {const.CMD_MODEL: None}], indirect=True
)
@pytest.mark.parametrize("start", [False, True])
async def test_lens_move_rejects_unverified_models_before_io(dev, start):
    """Unsupported or unidentified projectors cannot receive motor operations."""
    p = JvcProjector(IP)
    await p.connect(get_info=True)
    dev.send.reset_mock()
    with pytest.raises(ValueError, match="not verified"):
        await p.lens_move("shift_up", start=start)
    dev.send.assert_not_awaited()


@pytest.mark.asyncio
async def test_lens_move_rejects_uninitialized_model_before_io(dev):
    """Model verification is required even for a stop on a new object."""
    p = JvcProjector(IP)
    with pytest.raises(ValueError, match="not verified"):
        await p.lens_move("shift_up", start=False)
    dev.send.assert_not_awaited()


def test_lens_movement_is_not_available_as_an_unbounded_named_command():
    """Named setting calls cannot bypass the caller's dedicated motor safeguards."""
    for direction in const.LENS_COMMANDS:
        with pytest.raises(ValueError, match="Unknown command"):
            JvcProjector.validate_command(direction, "start", model="NZ7")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "command_name", ["lens_control", "INLC", "inlc", "INFN", "infn", "INSL1"]
)
async def test_named_commands_reject_unverified_or_raw_lens_codes(dev, command_name):
    """Raw motor opcodes and the old undocumented INLC alias cannot be setters."""
    p = JvcProjector(IP)
    with pytest.raises(ValueError, match="Unknown command"):
        await p.send_command(command_name, "start")
    dev.send.assert_not_awaited()
    assert const.CMD_INSTALLATION_LENS_CONTROL not in JvcCommand.command_map


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("", "(unknown)"),
        ("(unknown)", "(unknown)"),
        ("0300PJ", "3.0.0"),
        ("garbage", "garbage"),
        ("03-005", "3.005"),
        ("0300  ", "3.0.0"),
    ],
)
def test_version_handles_missing_or_unrecognized_version(raw, expected):
    """Unknown firmware formats should remain visible without crashing a poll."""
    assert JvcProjector(IP).process_version(raw) == expected


@pytest.mark.asyncio
async def test_firmware_populates_after_standby_startup(dev: AsyncMock):
    """Version initially unavailable in standby should be populated on power-on."""
    p = JvcProjector(IP)
    await p.connect()
    assert (await p.get_state())[const.KEY_VERSION] == "3.0.0"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "dev",
    [
        {
            const.CMD_MODEL: "ILAFPJ-B8A1",
            const.CMD_INPUT_SIGNAL_ALLM: "1",
            const.CMD_PICTURE_MODE_DEEP_BLACK: "1",
            const.CMD_FUNCTION_DEEP_COLOR: "2",
            const.CMD_FUNCTION_COLORIMETRY: "B",
        }
    ],
    indirect=True,
)
async def test_optional_latest_telemetry_is_only_polled_when_requested(dev):
    """Disabled sensors add no requests; enabled sensors use verified tables."""
    p = JvcProjector(IP)
    await p.connect(get_info=True)
    assert p.model == "NZ900"
    await p.get_state()
    sent = [cmd.code for entry in dev.send.call_args_list for cmd in entry.args[0]]
    assert const.CMD_INPUT_SIGNAL_ALLM not in sent
    assert const.CMD_FUNCTION_DEEP_COLOR not in sent
    assert const.CMD_INSTALLATION_MODE not in sent  # Operation-only on latest models.
    state = await p.get_state(
        requested_keys={
            const.KEY_ALLM,
            const.KEY_DEEP_BLACK,
            const.KEY_DEEP_COLOR,
            const.KEY_COLORIMETRY,
        }
    )
    assert state[const.KEY_ALLM] == const.ON
    assert state[const.KEY_DEEP_BLACK] == const.ON
    assert state[const.KEY_DEEP_COLOR] == "12bit"
    assert state[const.KEY_COLORIMETRY] == "dci_p3_d65"


@pytest.mark.asyncio
@pytest.mark.parametrize("dev", [{const.CMD_MODEL: "ILAFPJ-B8A2"}], indirect=True)
async def test_latest_model_setters_use_model_specific_values(dev):
    """Modern dimming and motion settings encode the model's wire values."""
    p = JvcProjector(IP)
    await p.connect(get_info=True)
    with patch.object(p, "op", new=AsyncMock()) as op:
        await p.send_command(const.KEY_LASER_DIMMING, "balanced")
        op.assert_awaited_with("PMDC3")
        await p.send_command(const.KEY_CLEAR_MOTION_DRIVE, const.LOW)
        op.assert_awaited_with("PMCM3")
    with pytest.raises(ValueError, match="Invalid value"):
        p.validate_command("picture_mode", "animation", model="NZ800")
    with pytest.raises(ValueError, match="Invalid value"):
        p.validate_command("graphics_mode", "off", model="NZ800")


@pytest.mark.asyncio
async def test_requested_keys_excludes_disabled_base_telemetry(dev):
    """HA entity subscriptions should remove disabled legacy polling as well."""
    p = JvcProjector(IP)
    await p.connect(get_info=True)
    dev.send.reset_mock()
    state = await p.get_state(requested_keys={const.KEY_INPUT})
    sent = {cmd.code for entry in dev.send.call_args_list for cmd in entry.args[0]}
    assert const.CMD_INPUT in sent
    assert const.CMD_POWER in sent
    assert const.CMD_PICTURE_MODE_LASER_VALUE not in sent
    assert const.CMD_FUNCTION_LASER_TIME not in sent
    assert const.CMD_PICTURE_MODE not in sent
    assert const.KEY_PICTURE_MODE not in state
    assert state[const.KEY_INPUT] == const.HDMI1


@pytest.mark.asyncio
async def test_default_state_reader_preserves_reference_batches(dev):
    """Callers without a reader retain whole-group reference exchanges."""
    p = JvcProjector(IP)
    await p.connect(get_info=True)
    dev.send.reset_mock()
    await p.get_state()
    groups = [entry.args[0] for entry in dev.send.call_args_list]
    assert any(len(group) > 1 for group in groups)
    assert all(cmd.is_ref for group in groups for cmd in group)


@pytest.mark.asyncio
@pytest.mark.parametrize("dev", [{const.CMD_MODEL: "ILAFPJ-B5A1"}], indirect=True)
async def test_state_reference_reader_owns_each_ordered_exchange(dev):
    """Dependency reads stay ordered and complete through the supplied reader."""
    p = JvcProjector(IP)
    await p.connect(get_info=True)
    dev.send.reset_mock()
    responses = {
        const.CMD_POWER: const.ON,
        const.CMD_INPUT: const.HDMI1,
        const.CMD_SOURCE: const.SIGNAL,
        const.CMD_PICTURE_MODE: "frameadapt_hdr",
        const.CMD_FUNCTION_HDR: "hdr10",
        const.CMD_PICTURE_MODE_LASER_VALUE: "75",
        const.CMD_PICTURE_MODE_HDR_CONTENT_TYPE: "hdr10",
    }
    reader = AsyncMock(side_effect=lambda code: responses.get(code))
    state = await p.get_state(
        requested_keys={
            const.KEY_INPUT,
            const.KEY_PICTURE_MODE,
            const.KEY_LASER_VALUE,
            const.KEY_HDR_CONTENT_TYPE,
        },
        reference_reader=reader,
    )
    assert [entry.args[0] for entry in reader.await_args_list] == list(responses)
    assert state[const.KEY_INPUT] == const.HDMI1
    assert state[const.KEY_LASER_VALUE] == "75"
    assert state[const.KEY_HDR_CONTENT_TYPE] == "hdr10"
    dev.send.assert_not_awaited()


@pytest.mark.asyncio
async def test_state_reference_reader_owns_lazy_firmware_request(dev):
    """Missing firmware cannot bypass the caller's per-reference scheduler."""
    p = JvcProjector(IP)
    await p.connect()
    dev.send.reset_mock()
    reader = AsyncMock(
        side_effect=lambda code: {
            const.CMD_POWER: const.ON,
            const.CMD_VERSION: "03-005",
        }.get(code)
    )
    state = await p.get_state(requested_keys=set(), reference_reader=reader)
    assert [entry.args[0] for entry in reader.await_args_list] == [
        const.CMD_POWER,
        const.CMD_VERSION,
        const.CMD_SOURCE,
    ]
    assert state[const.KEY_VERSION] == "3.005"
    dev.send.assert_not_awaited()


@pytest.mark.asyncio
async def test_aborted_state_reader_does_not_publish_partial_snapshot(dev):
    """Yielding to a control leaves the last complete cached snapshot intact."""
    p = JvcProjector(IP)
    await p.connect(get_info=True)
    previous = await p.get_state(requested_keys={const.KEY_INPUT})
    dev.send.reset_mock()
    reader = AsyncMock(side_effect=[const.ON, RuntimeError("control pending")])
    with pytest.raises(RuntimeError, match="control pending"):
        await p.get_state(requested_keys={const.KEY_INPUT}, reference_reader=reader)
    assert p._dict == previous  # noqa: SLF001
    assert [entry.args[0] for entry in reader.await_args_list] == [
        const.CMD_POWER,
        const.CMD_INPUT,
    ]
    dev.send.assert_not_awaited()


@pytest.mark.asyncio
async def test_disconnected_state_reader_can_connect_before_its_reference(dev):
    """The supplied reader owns reconnects after a previous transport failure."""
    p = JvcProjector(IP)
    await p.connect(get_info=True)
    await p.disconnect()
    dev.send.reset_mock()

    async def read_reference(code):
        await p.connect()
        return await p.ref(code)

    state = await p.get_state(
        requested_keys={const.KEY_INPUT}, reference_reader=read_reference
    )
    assert state[const.KEY_INPUT] == const.HDMI1
    groups = [entry.args[0] for entry in dev.send.call_args_list]
    assert [group[0].code for group in groups] == [
        "\0\0",
        const.CMD_POWER,
        const.CMD_INPUT,
        const.CMD_SOURCE,
        const.CMD_FUNCTION_HDR,
    ]
    assert all(len(group) == 1 for group in groups)
    assert all(group[0].is_ref for group in groups[1:])
    await p.disconnect()


@pytest.mark.asyncio
async def test_disconnected_default_state_reader_still_requires_connection(dev):
    """Only callers that supply a reader may delegate connecting."""
    p = JvcProjector(IP)
    with pytest.raises(JvcProjectorError, match="Must call connect"):
        await p.get_state()
    dev.send.assert_not_awaited()
