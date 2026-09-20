"""Run the downloadable local projects against real files and separate C objects.

Run `python tests/native_projects.py`. Every case has a fresh working directory;
fixtures, reports and compiled objects never modify the course source tree.
"""

import subprocess
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory

from native_examples import compile_sources


@dataclass(frozen=True)
class FileCase:
    name: str
    contents: str | None
    output_name: str
    existing_report: str | None
    returncode: int
    stdout: str
    stderr: str
    report: str | None


def verify_file_case(executable: Path, case: FileCase) -> None:
    """Check exit status, both streams, report bytes and preservation of input."""
    with TemporaryDirectory(prefix="c-course-file-case-") as directory:
        work: Path = Path(directory)
        source: Path = work / "scores.txt"
        report: Path = work / case.output_name
        if case.contents is not None:
            source.write_text(case.contents, encoding="utf-8")
        if case.existing_report is not None:
            report.write_text(case.existing_report, encoding="utf-8")
        command: list[str] = [str(executable), "scores.txt", case.output_name]
        result: subprocess.CompletedProcess[str] = subprocess.run(
            command, cwd=work, capture_output=True, text=True, timeout=5, check=False,
        )
        expected: tuple[int, str, str] = (case.returncode, case.stdout, case.stderr)
        if (result.returncode, result.stdout, result.stderr) != expected:
            raise AssertionError(f"{case.name}: command={command!r}; result={result!r}; expected={expected!r}")
        actual_report: str | None = report.read_text(encoding="utf-8") if report.exists() else None
        if actual_report != case.report:
            raise AssertionError(f"{case.name}: report={actual_report!r}; expected={case.report!r}")
        actual_input: str | None = source.read_text(encoding="utf-8") if source.exists() else None
        if actual_input != case.contents:
            raise AssertionError(f"{case.name}: input changed: {actual_input!r}")


def check_file_project(project: Path, executable: Path) -> int:
    """Exercise normal reads, input validation, EOF and file-open failures."""
    compile_sources([project / "main.c"], executable)
    cases: list[FileCase] = [
        FileCase("sample", (project / "scores.txt").read_text(encoding="utf-8"), "report.txt", None,
                 0, "已生成报告\n", "", "人数=3\n平均分=77.67\n最高分=90\n及格=2\n"),
        FileCase("final line without newline", "60", "report.txt", None,
                 0, "已生成报告\n", "", "人数=1\n平均分=60.00\n最高分=60\n及格=1\n"),
        FileCase("boundaries and whitespace", " 0 \n+100\n", "report.txt", None,
                 0, "已生成报告\n", "", "人数=2\n平均分=50.00\n最高分=100\n及格=1\n"),
        FileCase("missing", None, "report.txt", None, 1, "", "无法打开输入文件: scores.txt\n", None),
        FileCase("empty", "", "report.txt", None, 1, "", "输入文件没有成绩: scores.txt\n", None),
        FileCase("blank line", "85\n\n", "report.txt", None, 1, "", "第2行不是0..100的整数\n", None),
        FileCase("negative", "-1\n", "report.txt", None, 1, "", "第1行不是0..100的整数\n", None),
        FileCase("above limit", "101\n", "report.txt", None, 1, "", "第1行不是0..100的整数\n", None),
        FileCase("suffix", "85abc\n", "report.txt", None, 1, "", "第1行不是0..100的整数\n", None),
        FileCase("two scores on a line", "85 90\n", "report.txt", None, 1, "", "第1行不是0..100的整数\n", None),
        FileCase("huge integer", "9" * 30 + "\n", "report.txt", None, 1, "", "第1行不是0..100的整数\n", None),
        FileCase("long line", " " * 33 + "85\n", "report.txt", None, 1, "", "第1行超过32字节\n", None),
        FileCase("too many", "60\n" * 101, "report.txt", None, 1, "", "人数超过100\n", None),
        FileCase("missing output directory", "60\n", "missing/report.txt", None,
                 1, "", "无法打开输出文件: missing/report.txt\n", None),
        FileCase("existing output", "60\n", "report.txt", "保留原报告\n",
                 1, "", "无法打开输出文件: report.txt\n", "保留原报告\n"),
        FileCase("input is output", "60\n", "scores.txt", None,
                 1, "", "无法打开输出文件: scores.txt\n", "60\n"),
    ]
    for case in cases:
        verify_file_case(executable, case)
    return len(cases)


def check_modules_project(project: Path, work: Path) -> None:
    """Link two separate clients to the same implementation and run both."""
    program: Path = work / "grade_report"
    checker: Path = work / "grade_checks"
    compile_sources([project / "main.c", project / "grades.c"], program)
    compile_sources([project / "grade_checks.c", project / "grades.c"], checker)
    expectations: list[tuple[Path, str]] = [
        (program, "平均分=77.67 最高分=90 及格=2\n"),
        (checker, "".join(f"PASS {name}\n" for name in
                          ["normal", "single", "boundaries", "empty", "negative", "too_high", "null", "too_many"])
         + "8/8 PASS\n"),
    ]
    for executable, expected in expectations:
        result: subprocess.CompletedProcess[str] = subprocess.run(
            [str(executable)], cwd=work, capture_output=True, text=True, timeout=5, check=False,
        )
        if (result.returncode, result.stdout, result.stderr) != (0, expected, ""):
            raise AssertionError(f"{executable.name}: result={result!r}; expected stdout={expected!r}")


def check_projects(root: Path) -> None:
    """Validate the single-file file report and the multi-file statistics module."""
    projects: Path = root / "content" / "practice"
    with TemporaryDirectory(prefix="c-course-projects-") as directory:
        work: Path = Path(directory)
        count: int = check_file_project(projects / "file_io", work / "file_report")
        print(f"PASS: file I/O: {count} real-file cases", flush=True)
        check_modules_project(projects / "modules", work)
        print("PASS: separate compilation, report client and 8/8 module checks", flush=True)


if __name__ == "__main__":
    check_projects(Path(__file__).resolve().parents[1])
