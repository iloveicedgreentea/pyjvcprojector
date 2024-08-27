"""Device constants for a JVC Projector."""

from typing import Final

POWER: Final = "power"
OFF: Final = "off"
STANDBY: Final = "standby"
ON: Final = "on"
WARMING: Final = "warming"
COOLING: Final = "cooling"
ERROR: Final = "error"
NORMAL: Final = "normal"
LOW: Final = "low"
MEDIUM: Final = "medium"
HIGH: Final = "high"
AUTO: Final = "auto"

SIGNAL: Final = "signal"
NOSIGNAL: Final = "no_signal"

INPUT: Final = "input"
HDMI1 = "hdmi1"
HDMI2 = "hdmi2"

SOURCE: Final = "source"
NOSIGNAL: Final = "nosignal"
SIGNAL: Final = "signal"

REMOTE_MENU: Final = "732E"
REMOTE_UP: Final = "7301"
REMOTE_DOWN: Final = "7302"
REMOTE_LEFT: Final = "7336"
REMOTE_RIGHT: Final = "7334"
REMOTE_OK: Final = "732F"
REMOTE_BACK: Final = "7303"
REMOTE_MPC: Final = "73F0"
REMOTE_HIDE: Final = "731D"
REMOTE_INFO: Final = "7374"
REMOTE_INPUT: Final = "7308"
REMOTE_ADVANCED_MENU: Final = "7373"
REMOTE_PICTURE_MODE: Final = "73F4"
REMOTE_COLOR_PROFILE: Final = "7388"
REMOTE_LENS_CONTROL: Final = "7330"
REMOTE_SETTING_MEMORY: Final = "73D4"
REMOTE_GAMMA_SETTINGS: Final = "73F5"
REMOTE_CMD: Final = "738A"
REMOTE_MODE_1: Final = "73D8"
REMOTE_MODE_2: Final = "73D9"
REMOTE_MODE_3: Final = "73DA"
REMOTE_HDMI_1: Final = "7370"
REMOTE_HDMI_2: Final = "7371"
REMOTE_LENS_AP: Final = "7320"
REMOTE_ANAMO: Final = "73C5"
REMOTE_GAMMA: Final = "7375"
REMOTE_COLOR_TEMP: Final = "7376"
REMOTE_3D_FORMAT: Final = "73D6"
REMOTE_PIC_ADJ: Final = "7372"
REMOTE_NATURAL: Final = "736A"
REMOTE_CINEMA: Final = "7368"

# HDR Processing modes
HDR_10PLUS: Final = "hdr10_plus"
HDR_STATIC: Final = "static"
HDR_FRAME_BY_FRAME: Final = "frame_by_frame"
HDR_SCENE_BY_SCENE: Final = "scene_by_scene"

# HDR Content types
HDR_CONTENT_SDR: Final = "sdr"
HDR_CONTENT_HDR10: Final = "hdr10"
HDR_CONTENT_HDR10PLUS: Final = "hdr10_plus"
HDR_CONTENT_HLG: Final = "hlg"

# Anamorphic modes
ANAMORPHIC_A: Final = "a"
ANAMORPHIC_B: Final = "b"
ANAMORPHIC_C: Final = "c"
ANAMORPHIC_D: Final = "d"

# Laser dimming modes
LASER_DIMMING_AUTO1: Final = "auto1"
LASER_DIMMING_AUTO2: Final = "auto2"
LASER_DIMMING_AUTO3: Final = "auto3"

# Aspect Ratio
ASPECT_RATIO_ZOOM: Final = "zoom"
ASPECT_RATIO_NATIVE: Final = "native"

MODEL_MAP = {
    "B5A1": "NZ9",
    "B5A2": "NZ8",
    "B5A3": "NZ7",
    "A2B1": "NX9",
    "A2B2": "NX7",
    "A2B3": "NX5",
    "B2A1": "NX9",
    "B2A2": "NX7",
    "B2A3": "NX5",
    "B5B1": "NP5",
    "XHR1": "X570R",
    "XHR3": "X770R||X970R",
    "XHP1": "X5000",
    "XHP2": "XC6890",
    "XHP3": "X7000||X9000",
    "XHK1": "X500R",
    "XHK2": "RS4910",
    "XHK3": "X700R||X900R",
}

# Key names
KEY_MODEL: Final = "model"
KEY_MAC: Final = "mac"
KEY_VERSION: Final = "version"
KEY_POWER: Final = "power"
KEY_SIGNAL: Final = "signal"
KEY_SOURCE: Final = "source"
KEY_INPUT: Final = "input"
KEY_PICTURE_MODE: Final = "picture_mode"
KEY_LOW_LATENCY: Final = "low_latency"
KEY_INSTALLATION_MODE: Final = "installation_mode"
KEY_ANAMORPHIC: Final = "anamorphic"
KEY_HDR: Final = "hdr"
KEY_HDMI_INPUT_LEVEL: Final = "hdmi_input_level"
KEY_HDMI_COLOR_SPACE: Final = "hdmi_color_space"
KEY_COLOR_PROFILE: Final = "color_profile"
KEY_GRAPHICS_MODE: Final = "graphics_mode"
KEY_COLOR_SPACE: Final = "color_space"
KEY_ESHIFT: Final = "eshift"
KEY_LASER_MODE: Final = "laser_mode"
KEY_LASER_VALUE: Final = "laser_value"
KEY_LASER_POWER: Final = "laser_power"
KEY_LASER_TIME: Final = "laser_time"
KEY_MOTION_ENHANCE: Final = "motion_enhance"
KEY_CLEAR_MOTION_DRIVE: Final = "clear_motion_drive"
KEY_HDR_PROCESSING: Final = "hdr_processing"
KEY_HDR_CONTENT_TYPE: Final = "hdr_content_type"
KEY_LASER_DIMMING: Final = "laser_dimming"