"""Synthetic-only tests for a read-only Markdown ledger checker."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from ledger_check import cells, scan, check_path  # noqa: E402

HEADER = '| 作業 | 状態 | 実体・根拠 |\n| --- | --- | --- |\n'


def kinds(markdown, **options):
    return [x['type'] for x in scan(markdown, **options)['issues']]


class LedgerCheckTests(unittest.TestCase):
    def test_valid_table_and_list(self):
        md = HEADER + '| 調査 | 未投入 | |\n\n- [本人保留] 連絡待ち\n  メモです\n'
        self.assertEqual(scan(md)['status'], 'ok')
        self.assertEqual(scan(md)['entries'], 2)

    def test_optional_columns_can_be_omitted(self):
        md = '| 作業 | 状態 |\n| --- | --- |\n| 準備 | 実行中 |'
        self.assertEqual(kinds(md), [])

    def test_optional_cells_empty_allowed(self):
        self.assertEqual(kinds(HEADER + '| 準備 | 未投入 | |'), [])

    def test_duplicate_across_formats(self):
        self.assertIn('duplicate_title', kinds(HEADER + '| 準備 | 実行中 | |\n- [未投入] 準備'))

    def test_partial_state_rejected(self):
        self.assertIn('invalid_state', kinds(HEADER + '| 準備 | 実行 | |'))

    def test_unknown_state_rejected(self):
        self.assertIn('invalid_state', kinds('- [待機] 調査'))

    def test_bullet_without_state(self):
        self.assertIn('missing_state', kinds('- 準備'))

    def test_wait_marker_not_a_state(self):
        self.assertIn('missing_state', kinds('- [合図待ち] 準備'))
        self.assertEqual(kinds('- [合図待ち] [未投入] 準備'), [])
        self.assertEqual(kinds('- [未投入] [合図待ち] 準備'), [])

    def test_blank_required_fields(self):
        types = kinds(HEADER + '| | 未投入 | |\n| 準備 | | |')
        self.assertIn('missing_title', types)
        self.assertIn('missing_state', types)

    def test_wrong_columns(self):
        types = kinds(HEADER + '| A | 未投入 |\n| B | 実行中 | | EXTRA |')
        self.assertEqual(types.count('column_count'), 2)

    def test_escaped_pipe(self):
        self.assertEqual(cells(r'| A\|B | 未投入 | |'), [r'A\|B', '未投入', ''])
        self.assertEqual(kinds(HEADER + r'| A\|B | 未投入 | |'), [])

    def test_code_fence_ignored(self):
        self.assertEqual(kinds(chr(96)*3 + 'md\n' + HEADER + '| BAD | 不正 | |\n' + chr(96)*3 + '\n- [未投入] OK'), [])
        self.assertEqual(kinds('~~~\n- [完了] BAD\n~~~'), [])

    def test_other_table_excluded_then_ledger_continues(self):
        md = HEADER + '| 甲 | 未投入 | |\n\n| 見出し | 数字 |\n| --- | --- |\n| 乙 | 完了 |\n\n| 丙 | 実行中 | |'
        self.assertEqual(kinds(md), [])
        self.assertEqual(scan(md)['entries'], 2)

    def test_same_header_restores_table(self):
        md = HEADER + '| 甲 | 未投入 | |\n\n' + HEADER + '| 乙 | 実行中 | |'
        self.assertEqual(scan(md)['entries'], 2)

    def test_first_candidate_header_unknown_column(self):
        self.assertIn('invalid_header', kinds('| 作業 | 状態 | 余分 |\n| --- | --- | --- |'))

    def test_first_candidate_header_duplicate(self):
        self.assertIn('invalid_header', kinds('| 作業 | 状態 | 状態 |\n| --- | --- | --- |'))

    def test_other_table_before_canonical(self):
        md = '| 名称 | 値 |\n| --- | --- |\n| A | 1 |\n\n' + HEADER + '| B | 未投入 | |'
        self.assertEqual(kinds(md), [])
        self.assertEqual(scan(md)['entries'], 1)

    def test_completed_table_and_bullet(self):
        self.assertEqual(kinds(HEADER + '| A | 完了 | |\n- [完了] B').count('completed_retained'), 2)

    def test_completed_can_be_allowed(self):
        self.assertEqual(kinds('- [完了] 作業', allow_completed=True), [])

    def test_nonabsolute_reference_excluded(self):
        self.assertEqual(kinds('- [未投入] 見る: notes/abc.md, file.md, C:\\other\\x.md'), [])

    def test_missing_reference(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / 'does-not-exist.txt'
            self.assertIn('reference_missing', kinds(f'- [未投入] 参照 {chr(96)}{missing}{chr(96)}'))

    def test_unverifiable_reference(self):
        with patch('ledger_check.Path.stat', side_effect=PermissionError('denied')):
            self.assertEqual(check_path('/synthetic/path'), 'reference_unverifiable')

    def test_readonly_cli_and_exit_codes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ledger = root / 'test.md'
            ledger.write_text('- [未投入] 仕事', encoding='utf-8')
            before = ledger.read_bytes()
            cmd = [sys.executable, str(ROOT / 'scripts' / 'ledger_check.py'), str(ledger)]
            ok = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(ok.returncode, 0)
            self.assertEqual(json.loads(ok.stdout)['status'], 'ok')
            ledger.write_text('- [完了] 仕事', encoding='utf-8')
            bad = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(bad.returncode, 2)
            self.assertEqual(json.loads(bad.stdout)['status'], 'issues')
            self.assertEqual(ledger.read_bytes(), '- [完了] 仕事'.encode('utf-8'))
            missing = subprocess.run(cmd[:-1] + [str(root / 'absent.md')], capture_output=True, text=True)
            self.assertEqual(missing.returncode, 1)
            self.assertEqual(json.loads(missing.stdout)['status'], 'error')
            self.assertNotIn(str(root), missing.stdout)
            self.assertNotEqual(before, ledger.read_bytes())


if __name__ == '__main__':
    unittest.main()
