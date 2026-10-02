"""Exercise deletion boundaries with synthetic package inventories. [AI-Codex]"""
from datetime import datetime, timedelta, timezone
import importlib.util
import io
from pathlib import Path
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location(
    'retention', Path(__file__).resolve().parents[1] / 'scripts/retain_container_builds.py')
r = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(r)
NOW = datetime(2026, 10, 2, tzinfo=timezone.utc)


def info(days, success=False, completed=True):
    return dict(time=NOW - timedelta(days=days), success=success, completed=completed)


def version(ident, refs, days=20):
    return dict(id=ident, name=f'sha256:{ident:064x}',
                updated_at=(NOW - timedelta(days=days)).isoformat(),
                metadata={'container': {'tags': refs}})


class RetentionTests(unittest.TestCase):
    def test_three_successful_sets_across_all_packages(self):
        attempts = {f'build-{i}-1': info(i, success=True) for i in range(1, 6)}
        inventory = {p: [version(i, [f'build-{i}-1']) for i in range(1, 6)]
                     for p in r.PACKAGES}
        result = r.plan(inventory, attempts, NOW)
        self.assertEqual({(p, v['id']) for p, v in result},
                         {(p, i) for p in r.PACKAGES for i in (4, 5)})

    def test_protected_and_untagged_versions_survive(self):
        attempts = {'build-1-1': info(20)}
        versions = [version(i, ['build-1-1', tag]) for i, tag in enumerate(
            ['main', 'clang19', 'clang18-frozen', 'latest', '1.2.3', 'custom'])]
        versions += [version(10, []), version(11, ['sha256-abc.sig']),
                     version(12, ['build-invalid'])]
        self.assertEqual(r.plan({'p': versions}, attempts, NOW), [])

    def test_failed_grace_period_and_active_attempts(self):
        attempts = {'build-1-1': info(8), 'build-2-1': info(6),
                    'build-3-1': info(20, completed=False), 'build-4-1': info(7)}
        versions = [version(i, [f'build-{i}-1']) for i in range(1, 5)]
        result = r.plan({'p': versions}, attempts, NOW)
        self.assertEqual([v['id'] for _, v in result], [1])
        self.assertEqual(r.plan({'p': [version(1, ['build-1-1'], days=2)]}, attempts, NOW), [])

    def test_shared_digest_kept_if_any_build_is_retained(self):
        attempts = {'build-1-1': info(20), 'build-2-1': info(1, success=True)}
        self.assertEqual(r.plan({'p': [version(1, list(attempts))]}, attempts, NOW), [])

    def test_failed_promotion_is_not_a_successful_set(self):
        data = {'path': '.github/workflows/docker-publish.yml',
                'status': 'completed', 'updated_at': NOW.isoformat()}
        jobs = [{'name': f'promote ({p})', 'conclusion': 'success'} for p in r.PACKAGES]
        with patch.object(r, 'api', return_value=data), patch.object(r, 'pages', return_value=jobs):
            self.assertTrue(r.attempt('owner/repo', 'build-1-1')['success'])
            jobs[-1]['conclusion'] = 'failure'
            self.assertFalse(r.attempt('owner/repo', 'build-1-1')['success'])
            jobs.pop()
            self.assertFalse(r.attempt('owner/repo', 'build-1-1')['success'])

    def test_pagination_collects_all_versions(self):
        with patch.object(r, 'api', side_effect=[list(range(100)), [100]]) as api:
            self.assertEqual(r.pages('endpoint'), list(range(101)))
            self.assertIn('page=2', api.call_args.args[0])

    def test_manual_apply_rejected_before_api_access(self):
        with patch('sys.argv', ['retention', '--repository', 'owner/repo', '--apply']), \
             patch.dict(r.os.environ, {}, clear=True), patch.object(r, 'api') as api, \
             patch('sys.stderr', new_callable=io.StringIO):
            with self.assertRaises(SystemExit):
                r.main()
            api.assert_not_called()

    def test_changed_version_aborts_before_delete(self):
        old = version(1, ['build-1-1'])
        changed = version(1, ['build-1-1', 'clang18-frozen'])
        env = {'GITHUB_ACTIONS': 'true', 'GITHUB_REPOSITORY': 'owner/repo',
               'GITHUB_REF': 'refs/heads/main'}
        with patch('sys.argv', ['retention', '--repository', 'owner/repo', '--apply']), \
             patch.dict(r.os.environ, env), \
             patch.object(r, 'pages', return_value=[old]), \
             patch.object(r, 'attempt', return_value=info(20)), \
             patch.object(r, 'api', side_effect=[{'type': 'Organization'}, changed]) as api, \
             patch('sys.stdout', new_callable=io.StringIO):
            with self.assertRaisesRegex(RuntimeError, 'changed'):
                r.main()
            self.assertFalse(any(c.args[-1] == 'DELETE' for c in api.call_args_list))


    def test_missing_history_aborts_before_any_delete(self):
        old = version(1, ['build-1-1'])
        env = {'GITHUB_ACTIONS': 'true', 'GITHUB_REPOSITORY': 'owner/repo',
               'GITHUB_REF': 'refs/heads/main'}
        with patch('sys.argv', ['retention', '--repository', 'owner/repo', '--apply']), \
             patch.dict(r.os.environ, env), patch.object(r, 'pages', return_value=[old]), \
             patch.object(r, 'attempt', side_effect=RuntimeError('missing history')), \
             patch.object(r, 'api', return_value={'type': 'Organization'}) as api:
            with self.assertRaisesRegex(RuntimeError, 'missing history'):
                r.main()
            self.assertEqual(api.call_count, 1)

    def test_cleanup_packages_match_promotion_matrix(self):
        import yaml
        workflow = yaml.safe_load((Path(__file__).resolve().parents[1] /
                                   '.github/workflows/docker-publish.yml').read_text())
        self.assertEqual(set(r.PACKAGES),
                         set(workflow['jobs']['promote']['strategy']['matrix']['image']))
        cleanup = workflow['jobs']['cleanup']
        self.assertIn('promote', cleanup['needs'])
        self.assertIn('always()', cleanup['if'])
        self.assertIn("github.ref == 'refs/heads/main'", cleanup['if'])


if __name__ == '__main__':
    unittest.main()
