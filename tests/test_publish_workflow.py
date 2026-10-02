"""Check publishing gates without writing to a registry. [AI-Codex]"""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = yaml.safe_load((ROOT / '.github/workflows/docker-publish.yml').read_text())
JOBS = WORKFLOW['jobs']


class PublishWorkflowTests(unittest.TestCase):
    def test_builds_use_only_run_tags(self):
        self.assertEqual(WORKFLOW['env']['BUILD_TAG'],
                         'build-${{ github.run_id }}-${{ github.run_attempt }}')
        for name, job in JOBS.items():
            if not name.startswith('build-'):
                continue
            meta = next(s for s in job['steps'] if s.get('id') == 'meta')['with']
            self.assertEqual(meta['tags'], 'type=raw,value=${{ env.BUILD_TAG }}')
            self.assertEqual(meta['flavor'], 'latest=false')
            for step in job['steps']:
                for arg in step.get('with', {}).get('build-args', '').splitlines():
                    self.assertNotIn(':main', arg)
                    self.assertIn('env.BUILD_TAG', arg)

    def test_promotion_waits_for_all_builds(self):
        self.assertEqual(set(JOBS['promote']['needs']),
                         {name for name in JOBS if name.startswith('build-')})
        self.assertIn("github.event_name != 'pull_request'", JOBS['promote']['if'])
        self.assertIn("github.ref == 'refs/heads/main'", JOBS['promote']['if'])
        self.assertFalse(WORKFLOW['concurrency']['cancel-in-progress'])
        self.assertIn("'publish'", WORKFLOW['concurrency']['group'])
        tags = next(s for s in JOBS['promote']['steps'] if s.get('id') == 'meta')['with']['tags']
        self.assertIn('value=clang19', tags)
        self.assertIn("startsWith(matrix.image, 'adaptivecpp-')", tags)
        self.assertNotIn('clang18', tags)
        for name in ('build-runtime', 'build-hpc', 'build-alias'):
            self.assertEqual(JOBS[name]['if'], "github.event_name != 'pull_request'")

    def test_published_digest_is_tested_before_signing(self):
        for name in ('build-base', 'build-hpc'):
            steps = JOBS[name]['steps']
            push = next(i for i, s in enumerate(steps) if s.get('id') == 'push')
            test = next(i for i, s in enumerate(steps) if s['name'] == 'Run tests')
            sign = next(i for i, s in enumerate(steps) if s['name'].startswith('Sign '))
            self.assertLess(push, test)
            self.assertLess(test, sign)
            self.assertIn('steps.push.outputs.digest', steps[test]['env']['IMAGE_REF'])
            self.assertIn('"$IMAGE_REF"', steps[test]['run'])

    def run_promotion(self, digest, tags):
        script = JOBS['promote']['steps'][-1]['run']
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            docker = directory / 'docker'
            docker.write_text('''#!/usr/bin/env python3
import json, os, sys
with open(os.environ['CALL_LOG'], 'a') as f:
    f.write(json.dumps(sys.argv[1:]) + '\\n')
if sys.argv[1:4] == ['buildx', 'imagetools', 'inspect']:
    print(os.environ['TEST_DIGEST'])
    sys.exit(int(os.environ.get('INSPECT_EXIT', '0')))
''')
            docker.chmod(0o755)
            log = directory / 'calls.jsonl'
            env = dict(os.environ, PATH=tmp + os.pathsep + os.environ['PATH'],
                       CALL_LOG=str(log), TEST_DIGEST=digest, TAGS=tags,
                       IMAGE='example.invalid/adaptivecpp-base', BUILD_TAG='build-123-1')
            result = subprocess.run(['bash', '-c', script], env=env,
                                    capture_output=True, text=True)
            calls = [json.loads(line) for line in log.read_text().splitlines()]
            return result, calls

    def test_promotion_keeps_digest_and_requested_tags(self):
        digest = 'sha256:' + 'a' * 64
        tags = ['example.invalid/adaptivecpp-base:main',
                'example.invalid/adaptivecpp-base:clang19']
        result, calls = self.run_promotion(digest, '\n'.join(tags) + '\n')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(calls[-1], ['buildx', 'imagetools', 'create', '--prefer-index=false',
                                    '--tag', tags[0], '--tag', tags[1],
                                    'example.invalid/adaptivecpp-base@' + digest])
        self.assertEqual(len(calls), 2)

    def test_invalid_digest_or_empty_tags_never_promotes(self):
        for digest, tags in [('invalid', 'example.invalid/adaptivecpp-base:main'),
                             ('sha256:' + 'a' * 64, '')]:
            with self.subTest(digest=digest, tags=tags):
                result, calls = self.run_promotion(digest, tags)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(len(calls), 1)


if __name__ == '__main__':
    unittest.main()
