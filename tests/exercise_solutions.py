"""Validate folded answers using the exact exercise templates students execute.

Run `python tests/exercise_solutions.py`. Task and solution cells share a
course.exercise_id and declare exercise_role as task or solution. Only the
marked answer region is replaced; fixtures and feedback stay in the notebook.
"""

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import TypedDict, cast

from native_examples import verify_program


class CourseMetadata(TypedDict, total=False):
    exercise_id: str
    exercise_role: str
    expected_stdout: str
    reference_checker: str
    expected_reference_stdout: str


class CellMetadata(TypedDict, total=False):
    course: CourseMetadata


class Cell(TypedDict):
    id: str
    cell_type: str
    source: list[str]
    metadata: CellMetadata


class Notebook(TypedDict):
    cells: list[Cell]


@dataclass(frozen=True)
class Exercise:
    label: str
    code: str
    expected_stdout: str


@dataclass(frozen=True)
class ProgramCheck:
    label: str
    declarations: str
    checker: str
    expected_stdout: str


def parse_program_checks(notebook_text: str, label: str) -> list[ProgramCheck]:
    """Pair complete reference programs with their actual student checker cells."""
    notebook: Notebook = cast(Notebook, json.loads(notebook_text))
    cells: dict[str, Cell] = {cell["id"]: cell for cell in notebook["cells"]}
    if len(cells) != len(notebook["cells"]):
        raise ValueError(f"{label}: duplicate cell ids make reference checks ambiguous")
    checks: list[ProgramCheck] = []
    for cell in notebook["cells"]:
        course: CourseMetadata = cell["metadata"].get("course", {})
        checker_id: str | None = course.get("reference_checker")
        expected: str | None = course.get("expected_reference_stdout")
        if checker_id is None and expected is None:
            continue
        if checker_id is None or checker_id not in cells or expected is None:
            raise ValueError(f"{label}: reference_checker={checker_id!r} needs an existing cell and expected stdout")
        checker: Cell = cells[checker_id]
        programs: list[str] = re.findall(r"```c\n(.*?)\n```", "".join(cell["source"]), re.DOTALL)
        if cell["cell_type"] != "markdown" or len(programs) != 1 or checker["cell_type"] != "code":
            raise ValueError(f"{label}:{cell['id']}: expected one complete C program and a code checker")
        # Keep the complete source intact; its interactive main is never called.
        declarations: str = "#define main course_reference_main\n" + programs[0] + "\n#undef main\n"
        checks.append(ProgramCheck(
            f"{label}:{checker_id}", declarations, "".join(checker["source"]), expected,
        ))
    return checks


def parse_exercises(notebook_text: str, label: str) -> list[Exercise]:
    """Assemble answers without duplicating or changing student checkers."""
    notebook: Notebook = cast(Notebook, json.loads(notebook_text))
    tasks: dict[str, str] = {}
    solutions: dict[str, tuple[str, str]] = {}
    for cell in notebook["cells"]:
        course: CourseMetadata = cell["metadata"].get("course", {})
        exercise_id: str | None = course.get("exercise_id")
        role: str | None = course.get("exercise_role")
        if exercise_id is None and role is None:
            continue
        if not exercise_id:
            raise ValueError(f"{label}: exercise_role requires a nonempty exercise_id")
        source: str = "".join(cell["source"])
        if role == "task":
            if cell["cell_type"] != "code" or exercise_id in tasks:
                raise ValueError(f"{label}:{exercise_id}: expected one code task cell")
            tasks[exercise_id] = source
        elif role == "solution":
            blocks: list[str] = re.findall(r"```c\n(.*?)\n```", source, re.DOTALL)
            expected: str | None = course.get("expected_stdout")
            if (cell["cell_type"] != "markdown" or len(blocks) != 1
                    or expected is None or exercise_id in solutions):
                raise ValueError(f"{label}:{exercise_id}: expected one folded C answer and expected_stdout")
            solutions[exercise_id] = (blocks[0], expected)
        else:
            raise ValueError(f"{label}:{exercise_id}: invalid exercise_role={role!r}")
    if tasks.keys() != solutions.keys():
        raise ValueError(f"{label}: exercise tasks={list(tasks)} do not match solutions={list(solutions)}")
    exercises: list[Exercise] = []
    start: str = "/* BEGIN ANSWER */"
    end: str = "/* END ANSWER */"
    for exercise_id, template in tasks.items():
        if template.count(start) != 1 or template.count(end) != 1:
            raise ValueError(f"{label}:{exercise_id}: expected exactly one BEGIN/END ANSWER region")
        prefix, _, remaining = template.partition(start)
        _, separator, suffix = remaining.partition(end)
        if not separator:
            raise ValueError(f"{label}:{exercise_id}: END ANSWER must follow BEGIN ANSWER")
        solution, expected = solutions[exercise_id]
        exercises.append(Exercise(f"{label}:{exercise_id}", prefix + solution + suffix, expected))
    return exercises


def check_solutions(root: Path) -> None:
    """Compile completed exercise blocks as C17 and check every feedback line."""
    count: int = 0
    program_count: int = 0
    for path in sorted((root / "content").glob("*.ipynb")):
        notebook_text: str = path.read_text(encoding="utf-8")
        for exercise in parse_exercises(notebook_text, path.name):
            source: str = (
                "#include <stdio.h>\n#include <string.h>\nint main(void) {\n"
                + exercise.code + "\nreturn 0;\n}\n"
            )
            verify_program(source, [{"stdin": "", "stdout": exercise.expected_stdout, "returncode": 0}], exercise.label)
            count += 1
            print(f"PASS: {exercise.label}", flush=True)
        for check in parse_program_checks(notebook_text, path.name):
            source: str = check.declarations + "\nint main(void) {\n" + check.checker + "\nreturn 0;\n}\n"
            verify_program(source, [{"stdin": "", "stdout": check.expected_stdout, "returncode": 0}], check.label)
            program_count += 1
            print(f"PASS: reference program + student checker: {check.label}", flush=True)
    if count == 0:
        raise AssertionError("No exercise solutions found")
    if program_count == 0:
        raise AssertionError("No complete reference program checks found")
    print(f"PASS: {count} exercise answers with original student checkers", flush=True)
    print(f"PASS: {program_count} complete reference program checks", flush=True)


if __name__ == "__main__":
    check_solutions(Path(__file__).resolve().parents[1])
