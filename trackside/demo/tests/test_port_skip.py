"""
Trackside — the port finder never opens (and so never resets) a port the user asked it to skip.
"""

import os
import sys
import unittest
from unittest.mock import patch

demo_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if demo_dir not in sys.path:
    sys.path.insert(0, demo_dir)

import sim_port_finder as finder


def listed(*names):
    """Port facts for the given names, as the system would list them."""
    return [{"port": n, "description": "USB Serial", "vid_pid": "1A86:7523", "serial_number": ""} for n in names]


class PortSkipTests(unittest.TestCase):

    def test_skipped_ports_are_not_candidates(self):
        """A port named in TRACKSIDE_PORT_SKIP is dropped, whatever its letter case."""
        with patch.dict(os.environ, {finder.SKIP_ENV: "com3, COM9"}, clear=False), \
                patch.object(finder, "all_listed_ports", return_value=listed("COM3", "COM6", "COM7", "COM9")):
            names = [p["port"] for p in finder.system_ports()]
        self.assertEqual(names, ["COM6", "COM7"])

    def test_without_the_setting_nothing_is_dropped(self):
        """No setting: every listed port stays (the search behaves as before)."""
        env = {k: v for k, v in os.environ.items() if k != finder.SKIP_ENV}
        with patch.dict(os.environ, env, clear=True), \
                patch.object(finder, "all_listed_ports", return_value=listed("COM3", "COM6")):
            self.assertEqual([p["port"] for p in finder.system_ports()], ["COM3", "COM6"])

    def test_a_port_named_on_purpose_is_still_tried(self):
        """Choosing a port explicitly overrides the skip list: the user asked for exactly that one."""
        with patch.dict(os.environ, {finder.SKIP_ENV: "COM3"}, clear=False):
            ordered = finder.order_candidates("COM3", "", listed("COM6"))
        self.assertEqual([p["port"] for p in ordered][0], "COM3")

    def test_skipped_ports_are_also_left_out_of_the_list_everything_probe(self):
        """The 'probe all ports' diagnostic uses the same list, so it leaves skipped ports alone too."""
        probed = []
        with patch.dict(os.environ, {finder.SKIP_ENV: "COM3"}, clear=False), \
                patch.object(finder, "all_listed_ports", return_value=listed("COM3", "COM6")), \
                patch.object(finder, "probe_port", side_effect=lambda port, baud, *a: probed.append(port) or ("unknown", "x")):
            finder.probe_all_ports(115200)
        self.assertEqual(probed, ["COM6"])


if __name__ == "__main__":
    unittest.main()
