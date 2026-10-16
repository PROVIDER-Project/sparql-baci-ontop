"""Atomic downloads, explicit year selection and cache behavior without network."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

FETCH = Path(__file__).resolve().parents[1] / 'loader/fetch.sh'


class FetchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.data = self.root / 'data with spaces'
        self.jdbc = self.root / 'jdbc'
        fake = self.root / 'curl'
        fake.write_text('''#!/bin/sh
while [ "$#" -gt 0 ]; do
    case "$1" in
        -o) shift; output=$1 ;;
        https://*) url=$1 ;;
    esac
    shift
done
printf '%s\\n' "$url" >> "$TEST_CALLS"
printf 'downloaded bytes\\n' > "$output"
case "$url" in *"${TEST_FAIL:-never-fail}"*) exit 22 ;; esac
''')
        fake.chmod(0o755)
        self.calls = self.root / 'calls'
        self.env = dict(os.environ, PATH=str(self.root)+os.pathsep+os.environ['PATH'],
                        TEST_CALLS=str(self.calls), DATA_DIR=str(self.data), JDBC_DIR=str(self.jdbc))
        self.env.pop('BACI_YEARS', None)
        self.env.pop('BACI_BASE_URL', None)

    def fetch(self, **env):
        return subprocess.run(['sh', str(FETCH)], env=dict(self.env, **env), capture_output=True, text=True)

    def test_default_urls_and_completed_cache(self):
        result = self.fetch()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.data/'years.csv').read_text(), 'year\n2024\n')
        urls = self.calls.read_text().splitlines()
        self.assertEqual(len(urls), 5)
        self.assertTrue(urls[0].endswith('/HS92_V202601/1/HS92_V202601-1-BACI_HS92_Y2024_V202601.csv.zst'))
        self.assertTrue(urls[3].endswith('/HS92_V202601-1-readme.txt'))
        self.assertEqual(self.fetch().returncode, 0)
        self.assertEqual(self.calls.read_text().splitlines(), urls)

    def test_invalid_or_empty_year_selection_does_not_download(self):
        for years in ['2025', '1994', '2024;echo', '*', '2024 2025', '   ']:
            with self.subTest(years=years):
                self.assertNotEqual(self.fetch(BACI_YEARS=years).returncode, 0)
                self.assertFalse(self.calls.exists())
                self.assertFalse((self.data/'years.csv').exists())

    def test_selection_and_mirror_override(self):
        self.assertEqual(self.fetch(BACI_YEARS='1995 2024 1995', BACI_BASE_URL='https://mirror.test/base/').returncode, 0)
        self.assertEqual((self.data/'years.csv').read_text(), 'year\n1995\n2024\n1995\n')
        self.assertEqual(len(self.calls.read_text().splitlines()), 6)
        self.assertTrue(self.calls.read_text().startswith('https://mirror.test/base/HS92_V202601-1-'))

    def test_partial_failure_preserves_previous_manifest_and_retries(self):
        self.assertEqual(self.fetch().returncode, 0)
        previous = (self.data/'years.csv').read_text()
        result = self.fetch(BACI_YEARS='2023', TEST_FAIL='Y2023')
        self.assertNotEqual(result.returncode, 0)
        target = self.data/'BACI_HS92_Y2023_V202601.csv.zst'
        self.assertFalse(target.exists())
        self.assertTrue(Path(str(target)+'.part').exists())
        self.assertEqual((self.data/'years.csv').read_text(), previous)
        self.assertEqual(self.fetch(BACI_YEARS='2023').returncode, 0)
        self.assertTrue(target.exists())
        self.assertEqual((self.data/'years.csv').read_text(), 'year\n2023\n')


if __name__ == '__main__':
    unittest.main()
