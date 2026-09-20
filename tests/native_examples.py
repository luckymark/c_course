"""Compile the complete C programs embedded in the lessons and check their I/O.

Run `python tests/native_examples.py` from the repository. Set CC to a C17
compiler executable if needed. The notebook's course.native_cases metadata
holds the inputs, expected stdout and exit status next to its program.
Programs are compiled and run in a temporary directory; no examples are copied
into a second source tree.
"""

import json
import os
import re
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TypedDict, cast


class NativeCase(TypedDict):
    stdin: str
    stdout: str
    returncode: int


class CourseMetadata(TypedDict, total=False):
    native_cases: list[NativeCase]


class CellMetadata(TypedDict, total=False):
    course: CourseMetadata


class NotebookCell(TypedDict):
    cell_type: str
    source: list[str]
    metadata: CellMetadata


class Notebook(TypedDict):
    cells: list[NotebookCell]


def verify_program(source: str, cases: list[NativeCase], label: str) -> None:
    """Treat compiler warnings, incorrect outputs and unexpected exits as errors."""
    with TemporaryDirectory(prefix="c-course-native-") as directory:
        source_path: Path = Path(directory) / "lesson.c"
        executable: Path = Path(directory) / "lesson"
        source_path.write_text(source, encoding="utf-8")
        command: list[str] = [
            os.environ.get("CC", "cc"), "-std=c17", "-Wall", "-Wextra",
            "-Wpedantic", "-Werror", str(source_path), "-o", str(executable),
        ]
        compiled: subprocess.CompletedProcess[str] = subprocess.run(
            command, capture_output=True, text=True, timeout=30, check=False,
        )
        if compiled.returncode != 0:
            raise RuntimeError(f"{label}: compiler failed: {command!r}\n{compiled.stderr}")
        for case in cases:
            result: subprocess.CompletedProcess[str] = subprocess.run(
                [str(executable)], input=case["stdin"], capture_output=True,
                text=True, timeout=5, check=False,
            )
            if (result.returncode, result.stdout, result.stderr) != (
                case["returncode"], case["stdout"], "",
            ):
                raise AssertionError(
                    f"{label}: case={case!r}; exit={result.returncode}; "
                    f"stdout={result.stdout!r}; stderr={result.stderr!r}"
                )


def check_lessons(root: Path) -> None:
    programs: int = 0
    cases_count: int = 0
    for path in sorted((root / "content").glob("*.ipynb")):
        notebook = cast(Notebook, json.loads(path.read_text(encoding="utf-8")))
        chapter_programs: int = 0
        for index, cell in enumerate(notebook["cells"]):
            cases: list[NativeCase] | None = cell["metadata"].get("course", {}).get("native_cases")
            if cases is None:
                continue
            sources: list[str] = re.findall(r"```c\n(.*?)\n```", "".join(cell["source"]), re.DOTALL)
            if cell["cell_type"] != "markdown" or len(sources) != 1 or not cases:
                raise ValueError(f"{path.name}: cell {index + 1} needs one complete C program and test cases")
            verify_program(sources[0], cases, f"{path.name}:cell {index + 1}")
            programs += 1
            chapter_programs += 1
            cases_count += len(cases)
        if chapter_programs != 1:
            raise AssertionError(f"{path.name}: expected one complete local program, got {chapter_programs}")
        print(f"PASS: {path.name}: native C17", flush=True)
    if programs == 0:
        raise AssertionError("No lesson programs found")
    print(f"PASS: {programs} native programs, {cases_count} input/output cases", flush=True)


if __name__ == "__main__":
    check_lessons(Path(__file__).resolve().parents[1])
