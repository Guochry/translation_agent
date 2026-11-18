#!/usr/bin/env python3
"""Upload unchanged videos to a public Hugging Face dataset in resumable batches.

Uses the configured Hugging Face login, verifies remote LFS hashes, and skips
identical files. Batching reduces API requests for thousands of short clips.
"""
import argparse
import hashlib
from pathlib import Path
import re
import time
from huggingface_hub import HfApi, CommitOperationAdd, get_token
from huggingface_hub.errors import HfHubHTTPError


def retry(action):
    for attempt in range(8):
        try:
            return action()
        except Exception as error:
            # Parallel LFS uploads wrap HTTP failures in RuntimeError.
            cause = error
            response = None
            while cause is not None:
                if getattr(cause, 'response', None) is not None:
                    response = cause.response
                    break
                cause = cause.__cause__
            status = response.status_code if response is not None else None
            if status not in (429, 500, 502, 503, 504) or attempt == 7:
                raise
            delay = min(300, 30 * (attempt + 1))
            if response is not None and status == 429:
                reset = re.search(r'\bt=(\d+)', response.headers.get('RateLimit', ''))
                if reset:
                    delay = max(delay, int(reset[1]) + 2)
            print(f'Host returned {status}; retrying in {delay}s.', flush=True)
            deadline = time.monotonic() + delay
            while time.monotonic() < deadline:
                time.sleep(min(30, max(0, deadline - time.monotonic())))


def file_hash(path, root, use_cache=True):
    # Reuse the standard HF large-folder uploader's already computed hashes.
    metadata = root / '.cache/huggingface/upload' / (path.relative_to(root).as_posix() + '.metadata')
    if use_cache and metadata.is_file():
        try:
            lines = metadata.read_text().splitlines()
            stat = path.stat()
            if len(lines) >= 4 and re.fullmatch(r'[0-9a-f]{64}', lines[3]) and float(lines[0]) >= stat.st_mtime and int(lines[1]) == stat.st_size:
                return lines[3]
        except (OSError, ValueError):
            pass  # An incomplete cache entry can be recomputed safely.
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo-id', required=True)
    parser.add_argument('--media-dir', type=Path, default=Path(__file__).resolve().parents[1] / 'evaluation_assets/subtitle_evaluation')
    parser.add_argument('--workers', type=int, default=4)
    parser.add_argument('--batch-size', type=int, default=250)
    parser.add_argument('--verify-only', action='store_true', help='Check every prepared video against the public dataset without uploading')
    args = parser.parse_args()
    if not get_token() and not args.verify_only:
        raise SystemExit('Log in first with: hf auth login')
    paths = sorted(args.media_dir.rglob('*.mp4'))
    if not paths:
        raise SystemExit('Run prepare_subtitle_evaluation.py first.')
    if args.batch_size < 1 or args.workers < 1:
        raise SystemExit('Batch size and workers must be positive.')
    api = HfApi()
    # Public reads avoid consuming the authenticated account's upload quota.
    reader = HfApi(token=False)
    try:
        remote = {f.path: f.lfs.sha256 for f in reader.list_repo_tree(args.repo_id, repo_type='dataset', recursive=True)
                  if getattr(f, 'lfs', None)}
    except HfHubHTTPError as error:
        if error.response is None or error.response.status_code != 404:
            raise
        if args.verify_only:
            raise SystemExit('The public media dataset does not exist.')
        retry(lambda: api.create_repo(repo_id=args.repo_id, repo_type='dataset', private=False, exist_ok=True))
        remote = {}
    pending = []
    for path in paths:
        relative = path.relative_to(args.media_dir).as_posix()
        if relative not in remote or remote[relative] != file_hash(path, args.media_dir, use_cache=not args.verify_only):
            pending.append(path)
    print(f'{len(paths) - len(pending)}/{len(paths)} videos already verified; {len(pending)} to upload.', flush=True)
    if args.verify_only:
        if pending:
            raise SystemExit(f'{len(pending)} videos are missing or differ from local media.')
        print('All public video hashes match the prepared media.', flush=True)
        return
    for offset in range(0, len(pending), args.batch_size):
        batch = pending[offset:offset + args.batch_size]
        def commit():
            # Fresh operations allow retrying an interrupted preupload/commit.
            operations = [CommitOperationAdd(path_in_repo=p.relative_to(args.media_dir).as_posix(), path_or_fileobj=p) for p in batch]
            return api.create_commit(repo_id=args.repo_id, repo_type='dataset', operations=operations,
                                     commit_message=f'Upload subtitle videos {offset + 1}–{offset + len(batch)}', num_threads=args.workers)
        retry(commit)
        print(f'Committed {offset + len(batch)}/{len(pending)} remaining videos.', flush=True)
    print(f'Media base: https://huggingface.co/datasets/{args.repo_id}/resolve/main/', flush=True)


if __name__ == '__main__':
    main()
