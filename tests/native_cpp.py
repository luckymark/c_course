"""Compile C++17 notebook examples, completed exercises and full programs.

Run `python tests/native_cpp.py`; set CXX to a C++17 compiler if needed.
Notebook cpp_role distinguishes declarations from scoped interactive statements.
The same student fixtures and folded answers are used by native and browser checks.
"""

import json
import os
import re
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TypedDict, cast

from exercise_solutions import Exercise, parse_exercises
from native_examples import NativeCase


class CourseMetadata(TypedDict, total=False):
    cpp_role: str
    expected_stdout: str
    native_cases: list[NativeCase]


class CellMetadata(TypedDict, total=False):
    course: CourseMetadata


class Cell(TypedDict):
    cell_type: str
    source: list[str]
    metadata: CellMetadata


class Notebook(TypedDict):
    cells: list[Cell]


def verify_cpp(source: str, cases: list[NativeCase], label: str) -> None:
    """Compile with strict diagnostics and require exact output and exit status."""
    with TemporaryDirectory(prefix="course-cpp-") as directory:
        path: Path = Path(directory)
        source_path: Path = path / "lesson.cpp"
        source_path.write_text(source, encoding="utf-8")
        executable: Path = path / "lesson"
        command: list[str] = [os.environ.get("CXX", "c++"), "-std=c++17", "-Wall", "-Wextra",
                              "-Wpedantic", "-Werror", str(source_path), "-o", str(executable)]
        compiled: subprocess.CompletedProcess[str] = subprocess.run(
            command, capture_output=True, text=True, timeout=60, check=False,
        )
        if compiled.returncode != 0:
            raise RuntimeError(f"{label}: command={command!r}; exit={compiled.returncode}; stderr={compiled.stderr}")
        for case in cases:
            result: subprocess.CompletedProcess[str] = subprocess.run(
                [str(executable)], input=case["stdin"], capture_output=True, text=True, timeout=5, check=False,
            )
            if (result.stdout, result.stderr, result.returncode) != (case["stdout"], "", case["returncode"]):
                raise AssertionError(f"{label}: input={case['stdin']!r}; expected={case!r}; result={result!r}")


def wrap_statements(source: str) -> str:
    """Hoist includes out of interactive scoped statements into a complete program."""
    includes: list[str] = re.findall(r"^#include[^\n]*", source, re.MULTILINE)
    body: str = re.sub(r"^#include[^\n]*\n?", "", source, flags=re.MULTILINE)
    return "\n".join(includes) + "\nint main() {\n" + body + "\n}\n"


def notebook_program(notebook: Notebook, label: str) -> tuple[str, str]:
    """Preserve declaration order and call scoped examples in notebook order."""
    definitions: list[str] = []
    calls: list[str] = []
    outputs: list[str] = []
    for index, cell in enumerate(notebook["cells"]):
        if cell["cell_type"] != "code":
            continue
        source: str = "".join(cell["source"])
        course: CourseMetadata = cell["metadata"].get("course", {})
        if "expected_stdout" not in course:
            raise ValueError(f"{label}: code cell {index} needs expected_stdout")
        outputs.append(course["expected_stdout"])
        role: str | None = course.get("cpp_role")
        if role == "declarations":
            definitions.append(source)
        elif role == "statements":
            program: str = wrap_statements(source).replace("int main()", f"void lesson_cell_{index}()", 1)
            definitions.append(program)
            calls.append(f"lesson_cell_{index}();")
        else:
            raise ValueError(f"{label}: code cell {index} has invalid cpp_role={role!r}")
    return "\n".join(definitions) + "\nint main() {\n" + "\n".join(calls) + "\n}\n", "".join(outputs)


def check_cpp(root: Path) -> None:
    paths: list[Path] = sorted((root / "content").glob("C++第*章*.ipynb"))
    if not paths:
        raise AssertionError("No C++ lessons found")
    total_cases: int = 0
    for path in paths:
        text: str = path.read_text(encoding="utf-8")
        notebook: Notebook = cast(Notebook, json.loads(text))
        source, output = notebook_program(notebook, path.name)
        verify_cpp(source, [{"stdin": "", "stdout": output, "returncode": 0}], path.name)
        answers: list[Exercise] = parse_exercises(text, path.name)
        if not answers:
            raise AssertionError(f"{path.name}: no checked exercise answers")
        for answer in answers:
            verify_cpp(wrap_statements(answer.code), [{"stdin": "", "stdout": answer.expected_stdout, "returncode": 0}], answer.label)
        programs: int = 0
        for cell in notebook["cells"]:
            cases: list[NativeCase] | None = cell["metadata"].get("course", {}).get("native_cases")
            if cases is None:
                continue
            sources: list[str] = re.findall(r"```cpp\n(.*?)\n```", "".join(cell["source"]), re.DOTALL)
            if cell["cell_type"] != "markdown" or len(sources) != 1 or not cases:
                raise ValueError(f"{path.name}: native_cases needs one complete cpp program")
            verify_cpp(sources[0], cases, path.name)
            total_cases += len(cases)
            programs += 1
        if programs == 0:
            raise AssertionError(f"{path.name}: no complete native program")
        print(f"PASS: {path.name}: all cells, {len(answers)} exercise answers, {programs} complete programs", flush=True)
    print(f"PASS: {len(paths)} C++ chapters; {total_cases} native I/O cases", flush=True)


if __name__ == "__main__":
    check_cpp(Path(__file__).resolve().parents[1])
