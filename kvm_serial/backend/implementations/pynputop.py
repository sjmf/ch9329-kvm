# pynput implementation
import logging
from pynput.keyboard import Key, KeyCode, Listener
from utils.communication import DataComm
from utils.utils import ascii_to_scancode, merge_scancodes
from .baseop import KeyboardOp

logger = logging.getLogger(__name__)

# fmt: off
MODIFIER_TO_VALUE = {
    Key.alt: 0x04, Key.alt_l: 0x04, Key.alt_r: 0x40, Key.alt_gr: 0x40,
    Key.shift: 0x02, Key.shift_l: 0x02, Key.shift_r: 0x20,
    Key.cmd: 0x08, Key.cmd_l: 0x08, Key.cmd_r: 0x80,
    Key.ctrl: 0x01, Key.ctrl_l: 0x01, Key.ctrl_r: 0x10,
}

KEYS_WITH_CODES = {
    Key.up: 0x52, Key.down: 0x51, Key.left: 0x50, Key.right: 0x4f,
    Key.delete: 0x4c, Key.backspace: 0x2a,
    Key.f1: 0x3b, Key.f2: 0x3c, Key.f3: 0x3d, Key.f4: 0x3e,
    Key.f5: 0x3f, Key.f6: 0x40, Key.f7: 0x41, Key.f8: 0x42,
    Key.f9: 0x43, Key.f10: 0x44, Key.f11: 0x57, Key.f12: 0x58,
    Key.home: 0x4a, Key.end: 0x4d, Key.page_down: 0x4e, Key.page_up: 0x4b,
    Key.space: 0x2C, Key.tab: 0x2B, Key.enter: 0x28,
    Key.caps_lock: 0x39,
    Key.media_play_pause: None, Key.media_volume_mute: None,
    Key.media_volume_down: None, Key.media_volume_up: None,
    Key.media_previous: None, Key.media_next: None,
    Key.esc: 0x29,
}
# fmt: on


class PynputOp(KeyboardOp):
    @property
    def name(self):
        return "pynput"

    def __init__(self, serial_port):
        super().__init__(serial_port)
        self.modifier_map = {}

    def run(self):
        """
        Main method for control using pynput
        Starting point: https://stackoverflow.com/a/53210441/1681205
        :param serial_port:
        :return:
        """
        logging.info(
            "Using pynput operation mode.\n"
            "Can run as standard user, but Accessibility "
            "permission for input capture is required in Mac OSX.\n"
            "Paste not supported. Modifier keys supported.\n"
            "Input will continue in background without terminal focus.\n"
            "Press Ctrl+ESC or Ctrl+C to exit."
        )

        # Collect events until released
        with Listener(on_press=self.on_press, on_release=self.on_release) as listener:
            listener.join()

    def on_press(self, key):
        """
        Function which runs when a key is pressed down
        :param key:
        :return:
        """
        scancode = [b for b in b"\x00" * 8]

        try:
            # Collect modifiers
            if isinstance(key, Key):
                if key in MODIFIER_TO_VALUE:
                    value = MODIFIER_TO_VALUE[key]
                    scancode[0] = value
                else:
                    value = KEYS_WITH_CODES[key]
                    scancode[2] = value

                self.modifier_map[key] = scancode

            scancode = merge_scancodes(self.modifier_map.values())

            # Merge alphanumerics in with the modifiers
            if isinstance(key, KeyCode):
                scancode[2] = ascii_to_scancode(key.char)[2]

        except KeyError as e:
            logging.error("Key not found: " + str(e))

        # Merge keys in the modifier_keys_map and send over serial
        logging.debug(f"{scancode}\t({', '.join([hex(i) for i in scancode])})")
        self.hid_serial_out.send_scancode(bytes(scancode))

    def on_release(self, key):
        """
        Function which runs when a key is released
        :param key:
        :return:
        """
        # Send key release (null scancode)
        self.hid_serial_out.release()

        # Ctrl + ESC escape sequence
        if key == Key.esc and Key.ctrl in self.modifier_map:
            # Stop listener
            from pynput.keyboard import Listener as PynputListener

            raise PynputListener.StopException()

        try:
            self.modifier_map.pop(key)
        except KeyError:
            pass  # It might not be a modifier. Ask forgiveness, not permission


def main_pynput(serial_port):
    # For backwards compatibility
    return PynputOp(serial_port).run()
