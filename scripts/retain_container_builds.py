"""Retain complete build sets; delete only expendable build-tagged versions. [AI-Codex]"""
import argparse
from datetime import datetime, timedelta, timezone
import json
import os
import re
import subprocess

PACKAGES = ('adaptivecpp-toolchain', 'adaptivecpp-runtime', 'adaptivecpp-base',
            'adaptivecpp-hpc', 'adaptivecpp-hpc-cuda', 'adaptivecpp-hpc-rocm',
            'adaptivecpp-hpc-multigpu', 'intel-sycl-base', 'intel-sycl-hpc')
BUILD = re.compile(r'build-([1-9][0-9]*)-([1-9][0-9]*)\Z')


def api(path, method='GET'):
    command = ['gh', 'api', '--method', method, path]
    result = subprocess.run(command, check=True, capture_output=True, text=True)
    return json.loads(result.stdout) if result.stdout.strip() else None


def pages(path, key=None):
    result = []
    for page in range(1, 10001):
        data = api(f'{path}?per_page=100&page={page}')
        batch = data[key] if key else data
        if not isinstance(batch, list):
            raise ValueError('Unexpected paginated API response')
        result.extend(batch)
        if len(batch) < 100:
            return result
    raise RuntimeError('Pagination limit exceeded; refusing partial inventory')


def timestamp(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00'))


def tags(version):
    return version['metadata']['container']['tags']


def attempt(repository, tag):
    run, number = BUILD.fullmatch(tag).groups()
    path = f'repos/{repository}/actions/runs/{run}/attempts/{number}'
    data = api(path)
    if data['path'] != '.github/workflows/docker-publish.yml':
        raise ValueError(f'{tag} does not belong to the publishing workflow')
    jobs = pages(path + '/jobs', 'jobs')
    expected = {f'promote ({package})' for package in PACKAGES}
    promoted = {job['name'] for job in jobs
                if job['conclusion'] == 'success' and job['name'] in expected}
    return {'success': promoted == expected,
            'completed': data['status'] == 'completed',
            'time': timestamp(data['updated_at'])}


def plan(inventory, attempts, now):
    """Return whole package versions safe under the retention policy."""
    cutoff = now - timedelta(days=7)
    successful = sorted((tag for tag, info in attempts.items() if info['success']),
                        key=lambda tag: (attempts[tag]['time'], tag), reverse=True)
    keep = set(successful[:3])
    expendable = set()
    for tag, info in attempts.items():
        if tag in keep or not info['completed']:
            continue
        if info['success'] or info['time'] < cutoff:
            expendable.add(tag)
    result = []
    for package, versions in inventory.items():
        for version in versions:
            refs = tags(version)
            # Any other tag protects the entire digest, including frozen/release tags.
            if not refs or not all(BUILD.fullmatch(tag) for tag in refs):
                continue
            if not set(refs) <= expendable:
                continue
            # A recent retag or incomplete build gets a full seven-day grace period.
            if any(not attempts[tag]['success'] for tag in refs):
                if timestamp(version['updated_at']) >= cutoff:
                    continue
            result.append((package, version))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository', required=True)
    parser.add_argument('--apply', action='store_true', help='Delete planned versions (Actions only)')
    args = parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', args.repository):
        parser.error('Expected owner/repository')
    if args.apply and not (os.environ.get('GITHUB_ACTIONS') == 'true'
                           and os.environ.get('GITHUB_REPOSITORY') == args.repository
                           and os.environ.get('GITHUB_REF') == 'refs/heads/main'):
        parser.error('--apply is restricted to this repository’s main-branch Actions workflow')
    owner = args.repository.split('/')[0]
    owner_type = api(f'users/{owner}')['type']
    prefix = 'orgs' if owner_type == 'Organization' else 'users'
    root = f'{prefix}/{owner}/packages/container'
    inventory = {package: pages(f'{root}/{package}/versions') for package in PACKAGES}
    build_tags = {tag for versions in inventory.values() for version in versions
                  for tag in tags(version) if BUILD.fullmatch(tag)}
    # Collect all evidence before any deletion; missing history/API errors abort safely.
    attempts = {tag: attempt(args.repository, tag) for tag in sorted(build_tags)}
    candidates = plan(inventory, attempts, datetime.now(timezone.utc))
    print(json.dumps([{'package': package, 'id': version['id'], 'tags': tags(version)}
                      for package, version in candidates], indent=2))
    if not args.apply:
        print('Dry run only; no versions deleted.')
        return
    for package, old in candidates:
        path = f"{root}/{package}/versions/{old['id']}"
        current = api(path)
        # Protect versions changed since the inventory was read.
        if current['name'] != old['name'] or current['updated_at'] != old['updated_at'] or tags(current) != tags(old):
            raise RuntimeError(f'{package}/{old["id"]} changed; stopping cleanup')
        api(path, 'DELETE')
        print(f'Deleted {package}/{old["id"]}')


if __name__ == '__main__':
    main()
