"""Tests for command module."""

from jvcprojector import const
from jvcprojector.command import JvcCommand, JvcCommandHelpers


def test_build_command():
    """Test build command succeeds."""
    a = JvcCommandHelpers.get_available_commands()
    assert len(a) > 1


def test_list_values_encode_hexadecimal_indices():
    """List-backed setters use the same hexadecimal indices as responses."""
    result = JvcCommand._build_command_map({"XX(.)": [str(i) for i in range(13)]})  # noqa: SLF001
    assert result["XX"]["inverse"]["12"] == "C"


def test_help_lists_whole_values_and_callable_is_read_only():
    """Generated help must describe usable API values, not individual letters."""
    help_text = JvcCommandHelpers.get_command_help("input")
    assert "  - hdmi1" in help_text
    assert "  - h\n" not in help_text
    assert (
        JvcCommandHelpers.get_available_commands()["laser_value"]["type"] == "read_only"
    )


def test_hdr_mappings_match_jvc_tables():
    """HDR10+ occupies index zero for processing and two for content type."""
    processing = JvcCommand(const.CMD_PICTURE_MODE_HDR_PROCESSING, True)
    processing.response = "0"
    assert processing.response == const.HDR_CONTENT_HDR10PLUS
    processing.response = "1"
    assert processing.response == "static"
    processing.response = "3"
    assert processing.response == "scene"
    content = JvcCommand(const.CMD_PICTURE_MODE_HDR_CONTENT_TYPE, True)
    content.response = "2"
    assert content.response == const.HDR_CONTENT_HDR10PLUS


def test_latest_model_decoders_preserve_older_model_tables():
    """Latest wire values must not change meanings on older projectors."""
    legacy = JvcCommand(const.CMD_LASER_DIMMING, True, model="NZ9")
    modern = JvcCommand(const.CMD_LASER_DIMMING, True, model="NZ900")
    legacy.response = modern.response = "1"
    assert legacy.response == const.AUTO1
    assert modern.response == const.LOW
    color = JvcCommand(const.CMD_FUNCTION_COLOR_SPACE, True, model="NZ800")
    color.response = "2"
    assert color.response == "ycbcr444"
    motion = JvcCommand(const.CMD_PICTURE_MODE_CLEAR_MOTION_DRIVE, True, model="NZ800")
    motion.response = "3"
    assert motion.response == const.LOW
    hdr = JvcCommand(const.CMD_FUNCTION_HDR, True)
    hdr.response = "4"
    assert hdr.response == const.HDR_CONTENT_HDR10PLUS
