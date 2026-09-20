"""Run against a built site: python tests/browser_smoke.py http://127.0.0.1:8765.

Install dependencies with `python -m pip install --group test`, then
`python -m playwright install chromium`. BROWSER_CHANNEL=chrome selects an
installed Chrome instead. This uses a fresh browser profile and the site's
real WebAssembly kernels, without COOP/COEP headers (as on GitHub Pages).
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import TypedDict, cast
from urllib.parse import quote
from urllib.request import urlopen

from playwright.async_api import Page, Route, async_playwright

from exercise_solutions import Exercise, ProgramCheck, parse_exercises, parse_program_checks


class Cell(TypedDict):
    label: str
    code: str


class Result(TypedDict):
    label: str
    status: str
    output: str
    errors: list[str]
    input_requests: int


class CourseMetadata(TypedDict, total=False):
    expected_stdout: str


class CellMetadata(TypedDict, total=False):
    course: CourseMetadata


class NotebookCell(TypedDict):
    cell_type: str
    source: list[str]
    metadata: CellMetadata


class KernelSpec(TypedDict):
    name: str


class Metadata(TypedDict):
    kernelspec: KernelSpec


class Notebook(TypedDict):
    cells: list[NotebookCell]
    metadata: Metadata


# Execute on an actual kernel; a timeout or execution error fails the test.
# The application is exposed only in intercepted test responses, never in production.
RUN_CELLS = """async (cells) => {
    const kernel = await window.jupyterapp.serviceManager.kernels.startNew({name: 'xc17'});
    const results = [];
    try {
        const info = await kernel.info;
        if (info.implementation_version !== '0.10.0' || info.language_info.version !== 'c17') {
            throw new Error('Unexpected kernel: ' + JSON.stringify(info));
        }
        for (const cell of cells) {
            const result = {label: cell.label, status: '', output: '', errors: [], input_requests: 0};
            const future = kernel.requestExecute({code: cell.code, allow_stdin: true, stop_on_error: true});
            future.onIOPub = message => {
                if (message.header.msg_type === 'stream') result.output += message.content.text;
                if (message.header.msg_type === 'error') result.errors.push(message.content.evalue);
            };
            future.onStdin = message => {
                result.input_requests += 1;
                kernel.sendInputReply({value: '42', status: 'ok'}, message.header);
            };
            let timer;
            try {
                const reply = await Promise.race([
                    future.done,
                    new Promise((_, reject) => {
                        timer = setTimeout(() => reject(new Error('Execution timed out: ' + cell.label)), 30000);
                    })
                ]);
                result.status = reply.content.status;
            } finally {
                clearTimeout(timer);
                future.dispose();
            }
            results.push(result);
        }
        return results;
    } finally {
        await kernel.shutdown();
        kernel.dispose();
    }
}"""


class PageConfig(TypedDict, total=False):
    exposeAppInBrowser: bool


SiteConfig = TypedDict("SiteConfig", {"jupyter-config-data": PageConfig})


async def expose_application(route: Route) -> None:
    """Enable the upstream test hook only in this browser's config response."""
    response = await route.fetch()
    config = cast(SiteConfig, await response.json())
    updated: SiteConfig = {
        **config,
        "jupyter-config-data": {**config["jupyter-config-data"], "exposeAppInBrowser": True},
    }
    await route.fulfill(response=response, json=updated)


async def execute(page: Page, cells: list[Cell]) -> list[Result]:
    results = cast(list[Result], await page.evaluate(RUN_CELLS, cells))
    for result in results:
        if result["status"] != "ok" or result["errors"]:
            raise RuntimeError(json.dumps(result, ensure_ascii=False))
    return results


def require_output(result: Result, expected: str) -> None:
    if result["output"] != expected or result["input_requests"] != 0:
        raise AssertionError(f"Expected output {expected!r} without stdin prompts: {result}")


async def check_browser(base_url: str) -> None:
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(channel=os.environ.get("BROWSER_CHANNEL"))
        try:
            page: Page = await browser.new_page()
            await page.route("**/jupyter-lite.json", expose_application)
            await page.goto(base_url + "/lab/")
            await page.wait_for_function(
                "window.jupyterapp?.serviceManager.kernelspecs.specs?.kernelspecs?.xc17",
                timeout=60000,
            )
            await page.evaluate("async () => {await jupyterapp.started; await jupyterapp.serviceManager.ready;}")
            # Known outputs check arithmetic, functions, repeated scoped statements, and sscanf.
            results: list[Result] = await execute(page, [
                {"label": "function", "code": '#include <stdio.h>\nint twice(int n) { return n * 2; }\nprintf("%d\\n", twice(21));'},
                {"label": "scope", "code": '{ int n = 7; printf("%d\\n", n); }'},
                {"label": "repeat scope", "code": '{ int n = 7; printf("%d\\n", n); }'},
                {"label": "sscanf", "code": '{ int n; int count = sscanf("42", "%d", &n); printf("%d %d\\n", count, n); }'},
            ])
            for result, expected in zip(results, ["42\n", "7\n", "7\n", "1 42\n"], strict=True):
                require_output(result, expected)
            # Pin the observed stdin limitation; an upstream behavior change requires review.
            probes: list[tuple[str, str, str]] = [
                ("scanf", '{ int n = -1; int count = scanf("%d", &n); printf("%d %d\\n", count, n); }', "-1 -1\n"),
                ("getchar", '{ printf("%d\\n", getchar()); }', "-1\n"),
                ("fgets", '{ char text[32]; printf("%d\\n", fgets(text, sizeof text, stdin) == NULL); }', "1\n"),
            ]
            for label, code, expected in probes:
                result = (await execute(page, [{"label": label, "code": "#include <stdio.h>\n" + code}]))[0]
                require_output(result, expected)
                print(json.dumps(result, ensure_ascii=False), flush=True)
            await page.evaluate("""async () => {
                const kernel = await jupyterapp.serviceManager.kernels.startNew({name: 'xc17'});
                try {
                    await kernel.info;
                    const first = kernel.requestExecute({code: 'int restart_value = 9;'});
                    if ((await first.done).content.status !== 'ok') throw new Error('Initial definition failed');
                    first.dispose();
                    await kernel.restart();
                    await kernel.info;
                    const second = kernel.requestExecute({code: 'int restart_value = 9;'});
                    if ((await second.done).content.status !== 'ok') throw new Error('Kernel restart retained definitions');
                    second.dispose();
                } finally {
                    await kernel.shutdown();
                    kernel.dispose();
                }
            }""")
            print("PASS: functions, repeated cells, sscanf, stdin limitations, kernel restart", flush=True)
            root: Path = Path(__file__).resolve().parents[1]
            downloads: list[Path] = sorted(
                path for path in (root / "content" / "practice").rglob("*") if path.is_file()
            )
            if not downloads:
                raise AssertionError("No downloadable practice files found")
            for path in downloads:
                relative: str = path.relative_to(root / "content").as_posix()
                with urlopen(base_url + "/files/" + quote(relative), timeout=30) as response:
                    if response.read() != path.read_bytes():
                        raise AssertionError(f"Published practice file differs from source: {relative}")
            print(f"PASS: {len(downloads)} downloadable practice files", flush=True)
            total: int = 0
            for path in sorted((root / "content").glob("*.ipynb")):
                with urlopen(base_url + "/files/" + quote(path.name), timeout=30) as response:
                    notebook = cast(Notebook, json.load(response))
                if notebook["metadata"]["kernelspec"]["name"] != "xc17":
                    raise AssertionError(f"Expected C17 metadata: {path.name}")
                code_cells: list[NotebookCell] = [
                    cell for cell in notebook["cells"]
                    if cell["cell_type"] == "code" and "".join(cell["source"]).strip()
                ]
                cells: list[Cell] = [
                    {"label": f"{path.name}:cell {index + 1}", "code": "".join(cell["source"])}
                    for index, cell in enumerate(notebook["cells"])
                    if cell["cell_type"] == "code" and "".join(cell["source"]).strip()
                ]
                results = await execute(page, cells)
                for cell, result in zip(code_cells, results, strict=True):
                    expected: str | None = cell["metadata"].get("course", {}).get("expected_stdout")
                    if expected is not None:
                        require_output(result, expected)
                total += len(results)
                print(f"PASS: {path.name}: {len(results)} cells", flush=True)
                answers: list[Exercise] = parse_exercises(json.dumps(notebook), path.name)
                if answers:
                    completed: list[Cell] = [
                        {"label": answer.label,
                         "code": "#include <stdio.h>\n#include <string.h>\n" + answer.code}
                        for answer in answers
                    ]
                    checked: list[Result] = await execute(page, completed)
                    for answer, result in zip(answers, checked, strict=True):
                        require_output(result, answer.expected_stdout)
                    print(f"PASS: {path.name}: {len(answers)} exercise answers", flush=True)
                program_checks: list[ProgramCheck] = parse_program_checks(json.dumps(notebook), path.name)
                for check in program_checks:
                    verified: list[Result] = await execute(page, [
                        {"label": check.label + ":reference", "code": check.declarations},
                        {"label": check.label + ":checker", "code": check.checker},
                    ])
                    require_output(verified[0], "")
                    require_output(verified[1], check.expected_stdout)
                    print(f"PASS: {path.name}: reference program + student checker", flush=True)
            print(f"PASS: {total} non-empty course cells", flush=True)
        finally:
            await browser.close()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python tests/browser_smoke.py http://127.0.0.1:8765")
    asyncio.run(asyncio.wait_for(check_browser(sys.argv[1].rstrip("/")), timeout=600))
