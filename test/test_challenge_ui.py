import os
import tempfile
import threading
import time
import unittest
from urllib.request import urlopen

from unittest.mock import patch

from bdnex.ui.challenge import ChallengeUI


class TestChallengeUI(unittest.TestCase):
    def test_manual_search_exits_without_hang(self):
        """Clicking "Chercher Manuellement" should return -1 and not hang."""
        with tempfile.TemporaryDirectory() as tmp:
            local_cover = os.path.join(tmp, 'local.jpg')
            candidate_cover = os.path.join(tmp, 'cand.jpg')

            # Create tiny placeholder files
            with open(local_cover, 'wb') as f:
                f.write(b'\x00')
            with open(candidate_cover, 'wb') as f:
                f.write(b'\x00')

            ui = ChallengeUI()

            # Use a fixed port to avoid races; if it's taken, the test will fail fast.
            fixed_port = 8765

            def fake_open(url: str):
                # Fire the /select?idx=-1 request in a background thread.
                def send():
                    # Give the server a brief moment to start.
                    time.sleep(0.05)
                    urlopen(f"{url}select?idx=-1").read()

                threading.Thread(target=send, daemon=True).start()
                return True

            candidates = [({'title': 'X'}, 0.5, candidate_cover)]

            with patch.object(ChallengeUI, '_find_free_port', return_value=fixed_port), patch('webbrowser.open', side_effect=fake_open):
                selected = ui.show_challenge_interactive(local_cover, candidates, 'file.cbz')

            self.assertEqual(selected, -1)


if __name__ == '__main__':
    unittest.main()
