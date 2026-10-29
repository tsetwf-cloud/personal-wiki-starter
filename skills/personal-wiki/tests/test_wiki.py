import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

CLI = Path(__file__).resolve().parents[1] / 'scripts/wiki.py'

class WikiTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR'))
        self.base = Path(self.tmp.name)
        self.root = self.base / 'wiki'

    def tearDown(self):
        self.tmp.cleanup()

    def run_cli(self, *args, ok=True, env=None):
        p = subprocess.run([sys.executable, '-B', str(CLI), '--root', str(self.root), *args], text=True, capture_output=True, env={**os.environ, **(env or {})})
        if ok:
            self.assertEqual(p.returncode, 0, p.stderr + p.stdout)
            return json.loads(p.stdout)
        self.assertNotEqual(p.returncode, 0, p.stdout)
        return p

    def init(self):
        return self.run_cli('init')

    def test_init_creates_only_first_level_categories(self):
        self.init()
        self.assertEqual(sorted(p.name for p in self.root.iterdir() if p.name != '.wiki'), ['00-基础信息', '01-认知', '02-生活', '03-工作', '04-创业', '99-收件箱'])
        self.assertEqual(list((self.root / '03-工作').iterdir()), [])

    def test_init_never_overwrites_nonempty_directory(self):
        self.root.mkdir()
        (self.root / 'keep.txt').write_text('keep')
        self.run_cli('init', ok=False)
        self.assertEqual((self.root / 'keep.txt').read_text(), 'keep')
        self.assertFalse((self.root / '.wiki').exists())

    def source(self, text='Fictional user plans a quiet reading hour.'):
        path = self.base / 'note.txt'
        path.write_text(text, encoding='utf-8')
        return path

    def intake(self, text='Fictional user plans a quiet reading hour.'):
        self.init()
        self.run_cli('configure', '--channels', 'current,file', '--model-permission', 'none', '--scope', 'only selected files')
        return self.run_cli('ingest', '--file', str(self.source(text)), '--channel', 'file', '--scope', 'selected note', '--date', '2026-01-02')

    def test_ingest_archives_exact_bytes_and_deduplicates(self):
        result = self.intake()
        archived = self.root / result['source']['archive']
        self.assertEqual(archived.read_bytes(), (self.base / 'note.txt').read_bytes())
        self.assertEqual(hashlib.sha256(archived.read_bytes()).hexdigest(), result['source_id'])
        repeated = self.run_cli('ingest', '--file', str(self.base / 'note.txt'), '--channel', 'file', '--scope', 'selected note', '--date', '2026-01-02')
        self.assertEqual(repeated['status'], 'duplicate')
        self.assertEqual(repeated['source_id'], result['source_id'])

    def test_ingest_requires_permission_and_explicit_scope(self):
        self.init()
        path = self.source()
        self.run_cli('ingest', '--file', str(path), '--channel', 'file', '--scope', 'selected', '--date', '2026-01-02', ok=False)
        self.assertEqual(list((self.root / '99-收件箱').iterdir()), [])

    def test_ingest_interruption_requires_exact_recovery_token(self):
        self.init()
        self.run_cli('configure', '--channels', 'file', '--model-permission', 'none', '--scope', 'selected')
        self.run_cli('ingest', '--file', str(self.source()), '--channel', 'file', '--scope', 'selected', '--date', '2026-01-02', env={'WIKI_FAIL_AFTER': '1'}, ok=False)
        status = self.run_cli('status')
        self.assertTrue(status['recovery_required'])
        self.run_cli('recover', '--token', 'wrong', ok=False)
        recovered = self.run_cli('recover', '--token', status['lock_token'])
        self.assertEqual(recovered['status'], 'recovered')
        self.assertEqual(len(self.run_cli('status')['sources']), 1)

    def test_mutation_lock_is_exclusive(self):
        self.init()
        (self.root / '.wiki/lock.json').write_text('{"token":"owned"}')
        self.run_cli('configure', '--channels', 'file', '--model-permission', 'none', '--scope', 'selected', ok=False)
        self.assertEqual(json.loads((self.root / '.wiki/lock.json').read_text())['token'], 'owned')

    def proposal(self, sid, **changes):
        item = {'source_id': sid, 'claim_key': 'reading-preference', 'kind': 'plan', 'quote': 'quiet reading hour', 'text': 'Plan a quiet reading hour.', 'target': '02-生活/阅读.md', 'sensitive': False, 'operation': 'create', 'expected_hash': None}
        item.update(changes)
        return item

    def submit(self, items):
        path = self.base / 'proposal.json'
        path.write_text(json.dumps({'candidates': items}, ensure_ascii=False), encoding='utf-8')
        return self.run_cli('submit', '--file', str(path))

    def test_submit_creates_traceable_review_without_formal_write(self):
        sid = self.intake()['source_id']
        submitted = self.submit([self.proposal(sid)])
        cid = submitted['candidate_ids'][0]
        state = self.run_cli('status')
        candidate = state['candidates'][cid]
        self.assertEqual(candidate['status'], 'pending')
        self.assertEqual(candidate['source_id'], sid)
        self.assertIn('02-生活/阅读.md', (self.root / candidate['review']).read_text())
        self.assertFalse((self.root / '02-生活/阅读.md').exists())
        self.assertEqual(self.submit([self.proposal(sid)])['candidate_ids'], [cid])

    def test_submit_validates_quote_classification_and_paths(self):
        sid = self.intake()['source_id']
        for changes in ({'quote': 'not in source'}, {'kind': 'certain'}, {'sensitive': 'false'}, {'target': '../escape.md'}, {'target': '99-收件箱/raw.md'}, {'target': '.wiki/state.json'}, {'claim_key': ''}):
            with self.subTest(changes=changes):
                path = self.base / 'bad.json'
                path.write_text(json.dumps({'candidates': [self.proposal(sid, **changes)]}))
                self.run_cli('submit', '--file', str(path), ok=False)
        self.assertEqual(self.run_cli('status')['candidates'], {})

    def decision(self, decisions, ok=True, env=None):
        path = self.base / 'decisions.json'
        path.write_text(json.dumps({'decisions': decisions}), encoding='utf-8')
        return self.run_cli('decide', '--file', str(path), ok=ok, env=env)

    def test_partial_decisions_resume_exact_ids_and_preserve_rejection(self):
        sid = self.intake()['source_id']
        ids = self.submit([self.proposal(sid), self.proposal(sid, claim_key='rejected', quote='Fictional user', target='01-认知/观点.md'), self.proposal(sid, claim_key='later', quote='plans a', target='03-工作/安排.md')])['candidate_ids']
        result = self.decision([{'id': ids[0], 'action': 'approve', 'approve_structure': True}, {'id': ids[1], 'action': 'reject', 'reason': 'not durable'}, {'id': ids[2], 'action': 'later'}])
        self.assertEqual(result['pending_ids'], [ids[2]])
        self.assertEqual(self.run_cli('status')['candidates'][ids[1]]['status'], 'rejected')
        repeated = self.submit([self.proposal(sid, claim_key='rejected', quote='Fictional user', target='01-认知/观点.md', text='Paraphrased retry')])
        self.assertEqual(repeated['statuses'][ids[1]], 'rejected')
        self.decision([{'id': ids[1], 'action': 'approve', 'approve_structure': True}], ok=False)
        self.decision([{'id': ids[2][:10], 'action': 'approve'}], ok=False)
        self.decision([{'id': ids[2], 'action': 'approve', 'approve_structure': True, 'text': 'A revised user-approved plan.'}])
        page = (self.root / '03-工作/安排.md').read_text()
        self.assertIn('A revised user-approved plan.', page)
        self.assertIn(sid, page)
        self.assertIn('updated:', page)
        self.assertEqual(self.run_cli('status')['candidates'][ids[0]]['status'], 'approved')

    def test_sensitive_and_new_structure_require_separate_item_gates(self):
        sid = self.intake()['source_id']
        cid = self.submit([self.proposal(sid, sensitive=True)])['candidate_ids'][0]
        self.decision([{'id': cid, 'action': 'approve'}], ok=False)
        self.decision([{'id': cid, 'action': 'approve', 'approve_structure': True}], ok=False)
        self.assertFalse((self.root / '02-生活/阅读.md').exists())
        self.decision([{'id': cid, 'action': 'approve', 'approve_structure': True, 'approve_sensitive': True}])
        self.assertIn('Plan a quiet reading hour.', (self.root / '02-生活/阅读.md').read_text())

    def test_update_replaces_explicit_whole_page_and_checks_old_hash(self):
        sid = self.intake()['source_id']
        target = self.root / '02-生活/阅读.md'
        target.write_text('Existing unrelated knowledge.\n', encoding='utf-8')
        old_hash = hashlib.sha256(target.read_bytes()).hexdigest()
        cid = self.submit([self.proposal(sid, operation='replace', expected_hash=old_hash, text='Existing unrelated knowledge.\nUpdated plan.')])['candidate_ids'][0]
        self.decision([{'id': cid, 'action': 'approve'}], ok=False)
        target.write_text('Concurrent edit.\n')
        self.decision([{'id': cid, 'action': 'approve', 'approve_replace': True}], ok=False)
        self.assertEqual(target.read_text(), 'Concurrent edit.\n')
        target.write_text('Existing unrelated knowledge.\n', encoding='utf-8')
        self.decision([{'id': cid, 'action': 'approve', 'approve_replace': True}])
        self.assertIn('Existing unrelated knowledge.', target.read_text())
        backups = list((self.root / '.wiki/backups').rglob('阅读.md'))
        self.assertTrue(any(p.read_text() == 'Existing unrelated knowledge.\n' for p in backups))
        self.assertIn('"action": "decide"', (self.root / '.wiki/events.jsonl').read_text())

    def test_context_only_reads_formal_pages_and_links_verified_evidence(self):
        sid = self.intake()['source_id']
        cid = self.submit([self.proposal(sid)])['candidate_ids'][0]
        self.assertEqual(self.run_cli('context', '--query', 'reading')['pages'], [])
        self.decision([{'id': cid, 'action': 'approve', 'approve_structure': True}])
        context = self.run_cli('context', '--query', 'reading')
        self.assertEqual([p['path'] for p in context['pages']], ['02-生活/阅读.md'])
        self.assertEqual(context['pages'][0]['evidence'][0]['sha256'], sid)
        self.assertNotIn('Fictional user', json.dumps(context))
        self.assertEqual(self.run_cli('check')['status'], 'ok')
        (self.root / '99-收件箱/原始资料/bad.md').write_text('[broken](missing.md)')
        (self.root / '.wiki/backups/unrelated.md').write_text('[broken](missing.md)')
        self.assertEqual(self.run_cli('check')['status'], 'ok')
        (self.root / '02-生活/阅读.md').write_text('[bad](missing.md)')
        self.assertEqual(self.run_cli('check')['status'], 'issues')

    def test_context_blocks_while_transaction_needs_recovery(self):
        sid = self.intake()['source_id']
        cid = self.submit([self.proposal(sid)])['candidate_ids'][0]
        self.decision([{'id': cid, 'action': 'approve', 'approve_structure': True}], env={'WIKI_FAIL_AFTER': '1'}, ok=False)
        self.run_cli('context', '--query', 'reading', ok=False)
        state = self.run_cli('status')
        self.run_cli('recover', '--token', state['lock_token'])
        self.assertEqual(len(self.run_cli('context', '--query', 'reading')['pages']), 1)

    def test_target_symlink_and_reserved_paths_are_rejected(self):
        sid = self.intake()['source_id']
        outside = self.base / 'outside'
        outside.mkdir()
        (self.root / '02-生活/link').symlink_to(outside, target_is_directory=True)
        for target in ['02-生活/link/page.md', '02-生活/CON.md', '/absolute.md', '02-生活/.hidden.md', '02-生活/a/../../out.md']:
            path = self.base / 'bad.json'
            path.write_text(json.dumps({'candidates': [self.proposal(sid, target=target)]}))
            self.run_cli('submit', '--file', str(path), ok=False)
        self.assertEqual(list(outside.iterdir()), [])

    def test_approved_source_replay_is_noop_and_changed_claim_keys_do_not_revive_rejections(self):
        sid = self.intake()['source_id']
        cid = self.submit([self.proposal(sid)])['candidate_ids'][0]
        self.decision([{'id': cid, 'action': 'reject'}])
        repeated = self.submit([self.proposal(sid, claim_key='new-key', text='Reworded rejected proposal')])
        self.assertEqual(repeated['candidate_ids'], [cid])
        self.assertEqual(repeated['statuses'][cid], 'rejected')
        other = self.proposal(sid, claim_key='distinct', target='03-工作/安排.md', quote='Fictional user')
        aid = self.submit([other])['candidate_ids'][0]
        self.decision([{'id': aid, 'action': 'approve', 'approve_structure': True}])
        self.assertEqual(self.submit([other])['statuses'][aid], 'approved')

    def test_multifile_recovery_at_every_decision_write_boundary(self):
        for boundary in range(1, 5):
            with self.subTest(boundary=boundary):
                self.root = self.base / ('wiki-' + str(boundary))
                sid = self.intake()['source_id']
                cid = self.submit([self.proposal(sid)])['candidate_ids'][0]
                self.decision([{'id': cid, 'action': 'approve', 'approve_structure': True}], env={'WIKI_FAIL_AFTER': str(boundary)}, ok=False)
                before = self.run_cli('status')
                self.run_cli('recover', '--token', before['lock_token'])
                after = self.run_cli('status')
                self.assertEqual(after['candidates'][cid]['status'], 'approved')
                self.assertFalse(after['recovery_required'])
                self.assertIsNone(after['lock_token'])
                self.assertEqual(self.run_cli('check')['status'], 'ok')
                events = [json.loads(line) for line in (self.root / '.wiki/events.jsonl').read_text().splitlines()]
                self.assertEqual(sum(e['action'] == 'decide' for e in events), 1)

    def test_recovery_preflights_conflicts_before_more_writes(self):
        sid = self.intake()['source_id']
        cid = self.submit([self.proposal(sid)])['candidate_ids'][0]
        self.decision([{'id': cid, 'action': 'approve', 'approve_structure': True}], env={'WIKI_FAIL_AFTER': '1'}, ok=False)
        review = self.root / self.run_cli('status')['candidates'][cid]['review']
        original = review.read_bytes()
        (self.root / '.wiki/state.json').write_bytes((self.root / '.wiki/state.json').read_bytes() + b' ')
        self.run_cli('recover', '--token', self.run_cli('status')['lock_token'], ok=False)
        self.assertEqual(review.read_bytes(), original)

    def test_existing_library_inspect_then_adopt_never_overwrites(self):
        self.root.mkdir()
        for category in ['00-基础信息', '01-认知', '02-生活', '03-工作', '04-创业', '99-收件箱']:
            (self.root / category).mkdir()
        page = self.root / '03-工作/现有.md'
        page.write_text('User-owned existing knowledge.')
        inspected = self.run_cli('inspect')
        self.assertTrue(inspected['can_adopt'])
        self.assertFalse((self.root / '.wiki').exists())
        self.run_cli('adopt', '--confirm-root', str(self.base / 'wrong'), ok=False)
        self.run_cli('adopt', '--confirm-root', str(self.root.absolute()))
        self.assertEqual(page.read_text(), 'User-owned existing knowledge.')
        self.run_cli('adopt', '--confirm-root', str(self.root.absolute()), ok=False)

    def test_decision_batch_failure_has_no_partial_side_effects(self):
        sid = self.intake()['source_id']
        ids = self.submit([self.proposal(sid), self.proposal(sid, claim_key='other', target='03-工作/other.md')])['candidate_ids']
        self.decision([{'id': ids[0], 'action': 'approve', 'approve_structure': True}, {'id': ids[1], 'action': 'approve'}], ok=False)
        self.assertFalse((self.root / '02-生活/阅读.md').exists())
        self.assertTrue(all(c['status'] == 'pending' for c in self.run_cli('status')['candidates'].values()))

    def test_fingerprint_rejection_follows_same_evidence_to_another_target(self):
        sid = self.intake()['source_id']
        cid = self.submit([self.proposal(sid)])['candidate_ids'][0]
        self.decision([{'id': cid, 'action': 'reject'}])
        repeated = self.submit([self.proposal(sid, claim_key='reworded', target='01-认知/重复.md')])
        self.assertEqual(repeated['candidate_ids'], [cid])

    def test_pending_candidate_id_collision_does_not_silently_discard_changed_proposal(self):
        sid = self.intake()['source_id']
        self.submit([self.proposal(sid)])
        path = self.base / 'changed.json'
        path.write_text(json.dumps({'candidates': [self.proposal(sid, text='Changed without review')]}))
        self.run_cli('submit', '--file', str(path), ok=False)

    def test_relative_root_supports_context_and_check(self):
        sid = self.intake()['source_id']
        cid = self.submit([self.proposal(sid)])['candidate_ids'][0]
        self.decision([{'id': cid, 'action': 'approve', 'approve_structure': True}])
        for command in ['context', 'check']:
            p = subprocess.run([sys.executable, '-B', str(CLI), '--root', 'wiki', command], cwd=self.base, capture_output=True, text=True)
            self.assertEqual(p.returncode, 0, p.stderr)

    def test_doctor_reports_observed_and_unverified_capabilities(self):
        report = self.run_cli('doctor')
        self.assertEqual(report['core']['status'], 'verified')
        self.assertEqual(report['channels']['wechat']['status'], 'unsupported')
        self.assertEqual(report['agent_host']['status'], 'unverified')
        self.assertFalse(self.root.exists())

    def test_configure_is_progressive_explicit_and_does_not_enable_scheduling(self):
        self.init()
        result = self.run_cli('configure', '--channels', 'current,file', '--model-permission', 'local', '--scope', 'Only supplied notes')
        self.assertEqual(result['config']['channels'], ['current', 'file'])
        self.assertEqual(result['config']['schedule'], 'manual')
        self.run_cli('configure', '--channels', 'wechat', '--scope', 'all', '--model-permission', 'remote', ok=False)

    def test_init_rejects_symlink_root(self):
        real = self.base / 'real'
        real.mkdir()
        self.root.symlink_to(real, target_is_directory=True)
        self.run_cli('init', ok=False)
        self.assertEqual(list(real.iterdir()), [])
