from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class SemanticDetectorBatchContractTests(unittest.TestCase):
    def test_child_processes_cannot_consume_timestamp_stream(self):
        script = (
            ROOT / "scripts/run_semantic_detector_batch.sh"
        ).read_text()
        self.assertIn('read -r timestamp <&3', script)
        self.assertIn('done 3< "$timestamps_file"', script)
        self.assertIn("ffmpeg -nostdin", script)
        self.assertIn('"$sample_count" -eq "$expected_count"', script)

    def test_repository_timestamp_sets_have_five_unique_samples(self):
        directory = ROOT / "benchmarks/semantic-gate-timestamps"
        for path in sorted(directory.glob("*.txt")):
            values = [
                float(line)
                for line in path.read_text().splitlines()
                if line and not line.startswith("#")
            ]
            self.assertEqual(len(values), 5, path.name)
            self.assertEqual(len(set(values)), 5, path.name)
            self.assertEqual(values, sorted(values), path.name)


if __name__ == "__main__":
    unittest.main()
