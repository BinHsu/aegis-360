import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_ffmpeg_frame_difference.py"
CONFIG = ROOT / "config" / "skiing-continuous-onset-acquisition-v2.json"


class RunFfmpegFrameDifferenceTests(unittest.TestCase):
    def test_fake_ffmpeg_contract_absolute_pts_sha_and_refuse_overwrite(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source.webm"
            source.write_bytes(b"complete-source-bytes")
            output = root / "artifact.json"
            argv_log = root / "argv.json"
            fake = root / "ffmpeg"
            fake.write_text(
                "#!/usr/bin/env python3\n"
                "import json, os, sys\n"
                "open(os.environ['FAKE_FFMPEG_ARGV'], 'w').write(json.dumps(sys.argv[1:]))\n"
                "print('frame:0 pts:0 pts_time:0.25')\n"
                "print('lavfi.signalstats.YAVG=25.5')\n"
                "print('frame:1 pts:1 pts_time:0.5')\n"
                "print('lavfi.signalstats.YAVG=127.5')\n",
                encoding="utf-8",
            )
            fake.chmod(0o755)
            env = dict(os.environ)
            env["PATH"] = f"{root}:{env['PATH']}"
            env["FAKE_FFMPEG_ARGV"] = str(argv_log)
            command = [sys.executable, str(SCRIPT), str(source), "skiing:probe",
                       str(CONFIG), str(output), "--start", "385.0",
                       "--duration", "2.0"]
            completed = subprocess.run(command, env=env, capture_output=True,
                                       text=True)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            artifact = json.loads(output.read_text())
            self.assertEqual(artifact["schema_version"],
                             "aegis360.frame-difference-samples.v2")
            self.assertEqual([item["pts_seconds"] for item in artifact["samples"]],
                             [385.25, 385.5])
            self.assertEqual(artifact["inputs"]["source_sha256"],
                             hashlib.sha256(source.read_bytes()).hexdigest())
            self.assertNotIn(str(source), output.read_text())
            argv = json.loads(argv_log.read_text())
            self.assertIn("-nostdin", argv)
            self.assertEqual(argv[argv.index("-threads") + 1], "2")
            self.assertEqual(argv[argv.index("-ss") + 1], "385.0")
            self.assertEqual(argv[argv.index("-t") + 1], "2.0")
            graph = argv[argv.index("-vf") + 1]
            expected = ("fps=fps=4.0,scale=w=320:h=-2,format=pix_fmts=gray,"
                        "tblend=all_mode=difference,signalstats,"
                        "metadata=mode=print:key=lavfi.signalstats.YAVG:file=-")
            self.assertEqual(graph, expected)
            repeated = subprocess.run(command, env=env, capture_output=True,
                                      text=True)
            self.assertNotEqual(repeated.returncode, 0)
            self.assertIn("refusing to overwrite", repeated.stderr)


if __name__ == "__main__":
    unittest.main()
