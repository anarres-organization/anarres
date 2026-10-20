"""Tests for the identity-map axis extractors.

Run from this directory:  python3 -m unittest test_build_identity_map
Experiment-local scripts are not on the package `make test` discovery path, so
this suite is run manually and documented in the commit.
"""

from __future__ import annotations

import unittest

import build_identity_map as bim

ASAN_ERROR = """\
/out/magic_fuzzer: Running 1 inputs 1 time(s) each.
==14==ERROR: AddressSanitizer: heap-buffer-overflow on address 0xdead
    #7 0x498bf1 in LLVMFuzzerTestOneInput /src/magic_fuzzer.cc:52:3
DEDUP_TOKEN: match--file_softmagic--mget
"""

OSSFUZZ_ERROR = """\
+ FUZZER=mruby_fuzzer
+ run_fuzzer mruby_fuzzer /testcase /testcase
/out/mruby_fuzzer -rss_limit_mb=2560 -timeout=25 /testcase
==9==ERROR: MemorySanitizer: use-of-uninitialized-value
DEDUP_TOKEN: mrb_vm_exec--mrb_run
"""

PATCH_A = """\
diff --git a/src/funcs.c b/src/funcs.c
index d39056b7..33778ff1 100644
--- a/src/funcs.c
+++ b/src/funcs.c
@@ -508,7 +508,9 @@ protected int
        assert(rx->rc == 0);
+       memset(pmatch, 0, nmatch * sizeof(*pmatch));
        return regexec(&rx->rx, str, nmatch, pmatch, eflags);
"""

# Same change, different blob index and different hunk line numbers only.
PATCH_A_SHIFTED = """\
diff --git a/src/funcs.c b/src/funcs.c
index aaaaaaaa..bbbbbbbb 100644
--- a/src/funcs.c
+++ b/src/funcs.c
@@ -611,7 +611,9 @@ protected int
        assert(rx->rc == 0);
+       memset(pmatch, 0, nmatch * sizeof(*pmatch));
        return regexec(&rx->rx, str, nmatch, pmatch, eflags);
"""

PATCH_B = """\
diff --git a/src/other.c b/src/other.c
index 11111111..22222222 100644
--- a/src/other.c
+++ b/src/other.c
@@ -1,3 +1,3 @@
-    int x = 0;
+    int x = 1;
"""


class ExtractorTest(unittest.TestCase):
    def test_canon_repo_collapses_url_variants(self) -> None:
        a = bim.canon_repo("https://github.com/File/File.git")
        b = bim.canon_repo("git@github.com:file/file")
        self.assertEqual(a, "github.com/file/file")
        self.assertEqual(b, "github.com/file/file")

    def test_vulnerability_class_uses_sanitizer_and_dedup(self) -> None:
        self.assertEqual(
            bim.vulnerability_class(ASAN_ERROR),
            "addresssanitizer:heap-buffer-overflow:match--file_softmagic--mget",
        )

    def test_vulnerability_class_absent_when_unparseable(self) -> None:
        self.assertIsNone(bim.vulnerability_class("no crash here, clean run\n"))

    def test_fuzz_harness_from_ossfuzz_and_arvo(self) -> None:
        self.assertEqual(bim.fuzz_harness(OSSFUZZ_ERROR), "harness:mruby_fuzzer")
        self.assertEqual(bim.fuzz_harness(ASAN_ERROR), "harness:magic_fuzzer")

    def test_patch_class_stable_under_line_shift(self) -> None:
        # Same change at a different location in the file -> same class.
        self.assertEqual(
            bim.patch_equivalence_class(PATCH_A),
            bim.patch_equivalence_class(PATCH_A_SHIFTED),
        )

    def test_patch_class_differs_for_different_change(self) -> None:
        self.assertNotEqual(
            bim.patch_equivalence_class(PATCH_A),
            bim.patch_equivalence_class(PATCH_B),
        )

    def test_build_leaves_axes_absent_without_data_dir(self) -> None:
        tasks = [{"task_id": "arvo:1", "project_main_repo": "https://github.com/x/y.git"}]
        idmap = bim.build(tasks, data_dir=None)
        self.assertEqual(idmap["arvo:1"]["project"], "github.com/x/y")
        self.assertEqual(idmap["arvo:1"]["provenance"], "arvo")
        self.assertNotIn("vulnerability_class", idmap["arvo:1"])


if __name__ == "__main__":
    unittest.main()
