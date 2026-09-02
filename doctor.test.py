import sys
import unittest
from pathlib import Path
from typing import Any, ClassVar

import doctor

ROOT = Path(__file__).resolve().parent


class Stub:
    __slots__ = ("advice", "detail", "name", "ok")

    def __init__(self, name: str, ok: bool, detail: str, advice: str | None = None) -> None:
        self.name = name
        self.ok = ok
        self.detail = detail
        self.advice = advice


class FindingTest(unittest.TestCase):
    def test_a_passing_finding_reads_as_ok(self) -> None:
        one = doctor.Finding("thing", True, "fine")

        self.assertIn("ok", one.line)

    def test_a_failing_finding_is_marked(self) -> None:
        one = doctor.Finding("thing", False, "broken")

        self.assertIn("!", one.line)

    def test_a_failing_finding_carries_its_advice(self) -> None:
        one = doctor.Finding("thing", False, "broken", "do this")

        self.assertIn("do this", one.report)

    def test_a_passing_finding_does_not_repeat_advice_nobody_needs(self) -> None:
        one = doctor.Finding("thing", True, "fine", "do this")

        self.assertNotIn("do this", one.report)

    def test_a_failing_finding_with_no_advice_is_just_its_line(self) -> None:
        one = doctor.Finding("thing", False, "broken")

        self.assertEqual(one.report, one.line)

    def test_the_repr_says_whether_it_passed(self) -> None:
        self.assertIn("not ok", repr(doctor.Finding("thing", False, "broken")))

    def test_the_repr_of_a_passing_one_says_so(self) -> None:
        self.assertIn("ok", repr(doctor.Finding("thing", True, "fine")))


class PythonTest(unittest.TestCase):
    def test_the_running_interpreter_is_reported(self) -> None:
        self.assertIn("python", doctor._python().name)

    def test_this_interpreter_is_new_enough(self) -> None:
        self.assertTrue(doctor._python().ok)


class ProjectTest(unittest.TestCase):
    def test_the_project_reports_its_own_version(self) -> None:
        self.assertIn("version", doctor._project().detail)


class ModelTest(unittest.TestCase):
    def test_a_model_that_is_not_checked_out_says_so(self) -> None:
        found = doctor._model("mos65xx", ROOT / "nowhere", lambda name: None)

        self.assertFalse(found.ok)

    def test_a_model_that_is_not_checked_out_names_the_fix(self) -> None:
        found = doctor._model("mos65xx", ROOT / "nowhere", lambda name: None)

        self.assertIn("submodule", found.advice)

    def test_a_model_that_will_not_import_reports_what_it_threw(self) -> None:
        def refuse(name: str) -> Any:
            raise ImportError("no")

        found = doctor._model("mos65xx", ROOT, refuse)

        self.assertIn("ImportError", found.detail)

    def test_a_model_that_imports_reports_its_version(self) -> None:
        class Loaded:
            VERSION = "9.9.9"

        found = doctor._model("mos65xx", ROOT, lambda name: Loaded())

        self.assertIn("9.9.9", found.detail)

    def test_a_model_with_no_version_is_still_reported_as_present(self) -> None:
        found = doctor._model("mos65xx", ROOT, lambda name: object())

        self.assertTrue(found.ok)

    def test_an_empty_directory_reads_as_not_checked_out(self) -> None:
        empty = ROOT / "build" / "empty-for-the-doctor-test"
        empty.mkdir(parents=True, exist_ok=True)

        found = doctor._model("mos65xx", empty, lambda name: None)

        self.assertFalse(found.ok)


class MicrocodeTest(unittest.TestCase):
    def test_a_part_that_can_run_lists_what_it_has(self) -> None:
        found = doctor._microcode(lambda: None, lambda: ["dsp1"])

        self.assertIn("dsp1", found.detail)

    def test_a_part_that_cannot_run_says_why(self) -> None:
        found = doctor._microcode(lambda: "no image", lambda: [])

        self.assertIn("no image", found.detail)

    def test_a_part_that_cannot_run_says_where_to_put_one(self) -> None:
        found = doctor._microcode(lambda: "no image", lambda: [])

        self.assertIn("firmware", found.advice)

    def test_nothing_here_offers_to_fetch_an_image(self) -> None:
        found = doctor._microcode(lambda: "no image", lambda: [])

        self.assertIn("Nothing here downloads it", found.advice)

    def test_asking_the_part_and_failing_is_itself_the_finding(self) -> None:
        def refuse() -> Any:
            raise RuntimeError("broken")

        found = doctor._microcode(refuse, lambda: [])

        self.assertIn("RuntimeError", found.detail)

    def test_a_part_that_can_run_nothing_still_says_something(self) -> None:
        found = doctor._microcode(lambda: None, lambda: [])

        self.assertIn("nothing", found.detail)


class MasksTest(unittest.TestCase):
    def test_holding_both_masks_is_reported(self) -> None:
        found = doctor._masks(lambda: ["dsp1", "dsp1b"])

        self.assertTrue(found.ok)

    def test_holding_only_the_first_mask_is_not_a_failure(self) -> None:
        found = doctor._masks(lambda: ["dsp1"])

        self.assertTrue(found.ok)

    def test_holding_neither_mask_says_which_are_missing(self) -> None:
        found = doctor._masks(lambda: [])

        self.assertIn("dsp1", found.detail)

    def test_asking_which_masks_are_here_and_failing_is_reported(self) -> None:
        def refuse() -> Any:
            raise RuntimeError("broken")

        found = doctor._masks(refuse)

        self.assertIn("RuntimeError", found.detail)


class CartridgeTest(unittest.TestCase):
    def test_every_declared_region_produces_a_line(self) -> None:
        found = doctor._cartridges(root=ROOT / "nowhere")

        self.assertEqual(len(found), 3)

    def test_an_absent_dump_is_not_a_failure(self) -> None:
        found = doctor._cartridges(root=ROOT / "nowhere")

        self.assertTrue(all(one.ok for one in found))

    def test_a_manifest_that_cannot_be_read_is_the_finding(self) -> None:
        def refuse(root: Any) -> Any:
            raise ValueError("bad json")

        found = doctor._cartridges(root=ROOT, examine=refuse)

        self.assertIn("ValueError", found[0].detail)

    def test_nothing_here_says_where_to_obtain_a_dump(self) -> None:
        found = doctor._cartridges(root=ROOT / "nowhere")

        self.assertIn("nothing here says where to obtain", found[0].advice)


class BeneathTest(unittest.TestCase):
    def test_a_model_report_is_filed_under_its_repository(self) -> None:
        found = doctor._beneath(lambda: [("mos65xx-python", Stub("thing", True, "fine"))])

        self.assertIn("mos65xx-python", found[0].name)

    def test_a_part_this_cartridge_does_not_carry_stops_being_a_failure(self) -> None:
        found = doctor._beneath(
            lambda: [("snes-dsp-python", Stub("dsp4", False, "no image"))],
            unused=lambda: ["dsp4"],
        )

        self.assertTrue(found[0].ok)

    def test_that_line_is_kept_in_full_rather_than_hidden(self) -> None:
        found = doctor._beneath(
            lambda: [("snes-dsp-python", Stub("dsp4", False, "no image"))],
            unused=lambda: ["dsp4"],
        )

        self.assertIn("no image", found[0].detail)

    def test_that_line_says_why_it_does_not_matter_here(self) -> None:
        found = doctor._beneath(
            lambda: [("snes-dsp-python", Stub("dsp4", False, "no image"))],
            unused=lambda: ["dsp4"],
        )

        self.assertIn("does not carry it", found[0].detail)

    def test_a_part_this_cartridge_does_carry_stays_a_failure(self) -> None:
        found = doctor._beneath(
            lambda: [("snes-dsp-python", Stub("dsp1", False, "no image"))],
            unused=lambda: ["dsp4"],
        )

        self.assertFalse(found[0].ok)

    def test_a_model_that_cannot_be_examined_is_the_finding(self) -> None:
        def refuse() -> Any:
            raise RuntimeError("broken")

        found = doctor._beneath(refuse)

        self.assertIn("RuntimeError", found[0].detail)

    def test_advice_is_carried_through_from_the_model(self) -> None:
        found = doctor._beneath(
            lambda: [("mos65xx-python", Stub("thing", False, "bad", "fix it"))],
            unused=lambda: [],
        )

        self.assertEqual(found[0].advice, "fix it")


class AskEachTest(unittest.TestCase):
    def test_a_model_with_no_doctor_is_passed_over(self) -> None:
        def load(name: str) -> Any:
            raise ModuleNotFoundError(name)

        found = doctor._ask_each(["mos65xx"], lambda name: ROOT, load)

        self.assertEqual(found, [])

    def test_a_directory_that_is_not_there_is_passed_over(self) -> None:
        found = doctor._ask_each(["mos65xx"], lambda name: ROOT / "nowhere", lambda name: None)

        self.assertEqual(found, [])

    def test_a_model_with_a_doctor_has_its_findings_collected(self) -> None:
        class Underneath:
            @staticmethod
            def examine() -> list[Any]:
                return [Stub("thing", True, "fine")]

        found = doctor._ask_each(["mos65xx"], lambda name: ROOT, lambda name: Underneath())

        self.assertEqual(len(found), 1)


class UnusedTest(unittest.TestCase):
    def test_the_parts_this_cartridge_does_not_carry_are_listed(self) -> None:
        class Loaded:
            MODELS: ClassVar[dict[str, None]] = {"dsp1": None, "dsp2": None}

        self.assertEqual(doctor._default_unused(lambda name: Loaded()), ["dsp2"])

    def test_a_model_that_will_not_import_says_nothing_about_spare_parts(self) -> None:
        def refuse(name: str) -> Any:
            raise ImportError("no")

        self.assertEqual(doctor._default_unused(refuse), [])


class ReportTest(unittest.TestCase):
    def test_a_clean_run_says_how_many_checks_there_were(self) -> None:
        lines = doctor.report([doctor.Finding("thing", True, "fine")])

        self.assertIn("nothing to report", "\n".join(lines))

    def test_a_run_with_a_fault_counts_the_faults(self) -> None:
        lines = doctor.report([doctor.Finding("thing", False, "broken")])

        self.assertIn("1 of 1 checks did not pass", "\n".join(lines))

    def test_the_report_names_the_project_and_its_version(self) -> None:
        lines = doctor.report([])

        self.assertIn(doctor.PROJECT, lines[0])


class MainTest(unittest.TestCase):
    def test_a_clean_run_exits_zero(self) -> None:
        code = doctor.main(
            examine=lambda: [doctor.Finding("thing", True, "fine")], say=lambda x: None
        )

        self.assertEqual(code, 0)

    def test_a_run_with_a_fault_exits_non_zero(self) -> None:
        code = doctor.main(
            examine=lambda: [doctor.Finding("thing", False, "broken")], say=lambda x: None
        )

        self.assertEqual(code, 1)

    def test_a_run_prints_its_report(self) -> None:
        said: list[str] = []

        doctor.main(examine=lambda: [doctor.Finding("thing", True, "fine")], say=said.append)

        self.assertTrue(said)


class ExamineTest(unittest.TestCase):
    def test_examining_this_machine_produces_findings(self) -> None:
        found = doctor.examine(beneath=lambda: [])

        self.assertTrue(found)

    def test_nothing_it_prints_is_a_byte_of_a_cartridge(self) -> None:
        found = doctor.examine(beneath=lambda: [])
        said = "\n".join(one.report for one in found)

        self.assertNotIn("\x00", said)


class WiringTest(unittest.TestCase):
    def test_the_doctor_imports_nothing_from_the_project_before_the_path_is_set(self) -> None:
        source = (ROOT / "doctor.py").read_text()
        before = source.split("sys.path.insert", 1)[0]

        self.assertNotIn("import hardware", before)

    def test_the_doctor_is_reachable_as_a_script(self) -> None:
        self.assertIn('if __name__ == "__main__":', (ROOT / "doctor.py").read_text())

    def test_the_part_this_project_replaces_is_named(self) -> None:
        self.assertEqual(doctor.PART, "dsp1")

    def test_the_masks_it_looks_for_are_the_ones_the_manifest_declares(self) -> None:
        sys.path.insert(0, str(ROOT))
        import dumps

        declared = {one["model"] for one in dumps.through()[0]["images"]}

        self.assertEqual(set(doctor.MASKS), declared)


class DefaultBeneathTest(unittest.TestCase):
    def test_asking_every_model_underneath_returns_what_they_found(self) -> None:
        found = doctor._default_beneath()

        self.assertTrue(all(len(one) == 2 for one in found))

    def test_a_directory_not_yet_on_the_import_path_is_put_there(self) -> None:
        where = ROOT / "conformance"
        sys.path[:] = [one for one in sys.path if one != str(where)]

        def absent(name: str) -> Any:
            raise ModuleNotFoundError(name)

        doctor._ask_each(["conformance"], lambda name: where, absent)

        self.assertIn(str(where), sys.path)


if __name__ == "__main__":
    unittest.main()
