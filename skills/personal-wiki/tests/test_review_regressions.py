"""Independent-review regressions; all data is synthetic."""
import hashlib
import unittest
import test_wiki

class ReviewRegressions(unittest.TestCase):
    def fixture(self):
        t = test_wiki.WikiTests()
        t.setUp()
        self.addCleanup(t.tearDown)
        return t, t.intake()['source_id']

    def test_ancestor_target_conflict_is_rejected_before_any_write(self):
        t, sid = self.fixture()
        ids = t.submit([t.proposal(sid, target='02-生活/a.md'), t.proposal(sid, claim_key='nested', target='02-生活/a.md/b.md')])['candidate_ids']
        t.decision([{'id': cid, 'action': 'approve', 'approve_structure': True} for cid in ids], ok=False)
        self.assertFalse((t.root / '02-生活/a.md').exists())
        s = t.run_cli('status')
        self.assertFalse(s['recovery_required'])
        self.assertIsNone(s['lock_token'])

    def test_context_hash_uses_original_crlf_bytes(self):
        t, sid = self.fixture()
        body = b'old\r\npage\r\n'
        path = t.root / '02-生活/阅读.md'
        path.write_bytes(body)
        page = t.run_cli('context')['pages'][0]
        self.assertEqual(page['sha256'], hashlib.sha256(body).hexdigest())
        t.submit([t.proposal(sid, operation='replace', expected_hash=page['sha256'])])

    def test_already_queued_duplicate_cannot_bypass_later_rejection(self):
        t, sid = self.fixture()
        ids = t.submit([t.proposal(sid), t.proposal(sid, claim_key='queued', target='02-生活/其他.md')])['candidate_ids']
        t.decision([{'id': ids[0], 'action': 'reject'}])
        t.decision([{'id': ids[1], 'action': 'approve', 'approve_structure': True}], ok=False)
        self.assertFalse((t.root / '02-生活/其他.md').exists())
        self.assertFalse(t.run_cli('status')['recovery_required'])
