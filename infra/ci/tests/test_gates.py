"""Tests for the CI gate scripts in infra/ci (S01 R1.2, R4.4, R10.7, R13.6).

Each gate exposes find_violations(root) -> list[Violation] and main(argv) -> exit code.
"""

from pathlib import Path

import pytest

import check_dep_approvals
import check_no_console
import check_raw_sql


def write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def paths(violations: list[object]) -> set[str]:
    return {v.path for v in violations}  # type: ignore[attr-defined]


# --- no-console gate -------------------------------------------------------


def test_no_console_flags_print_and_console_calls(tmp_path: Path) -> None:
    write(tmp_path, "apps/api/src/imb_api/a.py", "def f() -> None:\n    print('x')\n")
    write(tmp_path, "apps/web/src/a.ts", "console.log('x')\n")
    write(tmp_path, "packages/contracts/src/b.tsx", "console.debug(1); console.info(2)\n")
    write(tmp_path, "apps/web/src/c.mjs", "console.log('x')\n")
    found = check_no_console.find_violations(tmp_path)
    assert paths(found) == {
        "apps/api/src/imb_api/a.py",
        "apps/web/src/a.ts",
        "packages/contracts/src/b.tsx",
        "apps/web/src/c.mjs",
    }
    assert all(v.line >= 1 for v in found)


def test_no_console_ignores_tests_scripts_and_allowed_calls(tmp_path: Path) -> None:
    write(tmp_path, "apps/api/tests/unit/test_a.py", "print('ok in tests')\n")
    write(tmp_path, "apps/web/e2e/a.spec.ts", "console.log('ok in e2e')\n")
    write(tmp_path, "apps/web/scripts/build.mjs", "console.log('ok in scripts')\n")
    write(tmp_path, "apps/web/src/ok.ts", "console.error('x'); console.warn('y')\n")
    write(
        tmp_path,
        "apps/api/src/imb_api/ok.py",
        "# print('a comment')\n"
        "label = 'print(this is text)'\n\n"
        "def blueprint() -> None:\n    pass\n",
    )
    write(tmp_path, "apps/web/node_modules/pkg/index.js", "console.log('vendor')\n")
    assert check_no_console.find_violations(tmp_path) == []


def test_no_console_main_exit_codes(tmp_path: Path) -> None:
    assert check_no_console.main([str(tmp_path)]) == 0
    write(tmp_path, "apps/web/src/a.ts", "console.log('x')\n")
    assert check_no_console.main([str(tmp_path)]) == 1


# --- raw SQL gate ----------------------------------------------------------

PREFIX = "from sqlalchemy import text\nx = '1'\nconn = None\nstmt = None\n"


@pytest.mark.parametrize(
    "snippet",
    [
        'conn.execute(text(f"SELECT * FROM t WHERE id = {x}"))',
        'conn.execute("SELECT * FROM t WHERE id = %s" % x)',
        'conn.execute(text("SELECT * FROM t WHERE id = {}".format(x)))',
        'conn.execute(text("SELECT * FROM t WHERE id = " + x))',
        'conn.exec_driver_sql(f"DELETE FROM t WHERE id = {x}")',
    ],
)
def test_raw_sql_flags_string_built_queries(tmp_path: Path, snippet: str) -> None:
    write(tmp_path, "apps/api/src/imb_api/q.py", PREFIX + snippet + "\n")
    found = check_raw_sql.find_violations(tmp_path)
    assert len(found) == 1
    assert found[0].path == "apps/api/src/imb_api/q.py"


@pytest.mark.parametrize(
    "snippet",
    [
        'conn.execute(text("SELECT * FROM t WHERE id = :id"), {"id": x})',
        "conn.execute(stmt)",
        'text("SELECT 1")',
    ],
)
def test_raw_sql_accepts_bound_parameters(tmp_path: Path, snippet: str) -> None:
    write(tmp_path, "packages/py-shared/src/imb_shared/q.py", PREFIX + snippet + "\n")
    assert check_raw_sql.find_violations(tmp_path) == []


def test_raw_sql_ignores_migrations(tmp_path: Path) -> None:
    write(
        tmp_path,
        "apps/api/migrations/versions/0001_baseline.py",
        PREFIX + 'conn.execute(text(f"GRANT SELECT ON {x} TO imb_api"))\n',
    )
    assert check_raw_sql.find_violations(tmp_path) == []


def test_raw_sql_main_exit_codes(tmp_path: Path) -> None:
    assert check_raw_sql.main([str(tmp_path)]) == 0
    write(tmp_path, "apps/api/src/imb_api/q.py", PREFIX + 'conn.execute(f"SELECT {x}")\n')
    assert check_raw_sql.main([str(tmp_path)]) == 1


# --- dependency approval gate ---------------------------------------------

DECISIONS = """# Decisions

### Dependency approvals

| Package | Registry URL | Version | Reason | Approved (date) |
|---|---|---|---|---|
| Flask | https://pypi.org/project/Flask/ | 3.1.3 | API | 2026-11-10 |
| psycopg | https://pypi.org/project/psycopg/ | 3.3.8 | driver | 2026-11-10 |
| pytest | https://pypi.org/project/pytest/ | 9.2.0 | tests | 2026-11-10 |
| next | https://www.npmjs.com/package/next | 16.4.6 | web | 2026-11-10 |
| @types/node | https://www.npmjs.com/package/@types/node | 26.6.6 | types | 2026-11-10 |

### ADR-001 Something else

| Not | A | Dependency | Table | Row |
|---|---|---|---|---|
| left-pad | x | 1.3.0 | y | z |
"""

GOOD_PYPROJECT = """[project]
name = "imb-api"
version = "0.0.0"
dependencies = ["flask==3.1.3", "psycopg[binary]==3.3.8"]

[dependency-groups]
dev = ["pytest==9.2.0"]
"""

GOOD_PACKAGE_JSON = """{
  "name": "@imbooored/web",
  "dependencies": {"next": "16.4.6", "@imbooored/contracts": "workspace:*"},
  "devDependencies": {"@types/node": "26.6.6"}
}
"""


def approved_repo(root: Path) -> None:
    write(root, "docs/DECISIONS.md", DECISIONS)
    write(root, "apps/api/pyproject.toml", GOOD_PYPROJECT)
    write(root, "apps/web/package.json", GOOD_PACKAGE_JSON)
    write(
        root, "package.json", '{"name": "root", "private": true, "packageManager": "pnpm@12.18.0"}'
    )


def test_dep_approvals_accepts_approved_exact_pins(tmp_path: Path) -> None:
    approved_repo(tmp_path)
    write(
        tmp_path, "apps/web/node_modules/x/package.json", '{"dependencies": {"left-pad": "^1.0.0"}}'
    )
    write(tmp_path, ".venv/lib/pyproject.toml", '[project]\ndependencies = ["requests>=1"]\n')
    assert check_dep_approvals.find_violations(tmp_path) == []


@pytest.mark.parametrize(
    ("rel", "text", "needle"),
    [
        (
            "apps/api/pyproject.toml",
            GOOD_PYPROJECT.replace('"flask==3.1.3"', '"requests==2.0.0"'),
            "requests",
        ),
        (
            "apps/api/pyproject.toml",
            GOOD_PYPROJECT.replace("flask==3.1.3", "flask==3.1.2"),
            "flask",
        ),
        (
            "apps/api/pyproject.toml",
            GOOD_PYPROJECT.replace("flask==3.1.3", "flask>=3.1.3"),
            "flask",
        ),
        ("apps/web/package.json", GOOD_PACKAGE_JSON.replace('"16.4.6"', '"^16.4.6"'), "next"),
        ("apps/web/package.json", GOOD_PACKAGE_JSON.replace('"16.4.6"', '"latest"'), "next"),
        (
            "apps/web/package.json",
            GOOD_PACKAGE_JSON.replace('"@types/node": "26.6.6"', '"left-pad": "1.3.0"'),
            "left-pad",
        ),
    ],
)
def test_dep_approvals_flags_unapproved_ranges_and_mismatches(
    tmp_path: Path, rel: str, text: str, needle: str
) -> None:
    approved_repo(tmp_path)
    write(tmp_path, rel, text)
    found = check_dep_approvals.find_violations(tmp_path)
    assert found, "expected a violation"
    assert any(needle in v.message.lower() for v in found)
    assert all(v.path == rel for v in found)


def test_dep_approvals_main_exit_codes(tmp_path: Path) -> None:
    approved_repo(tmp_path)
    assert check_dep_approvals.main([str(tmp_path)]) == 0
    write(tmp_path, "apps/web/package.json", GOOD_PACKAGE_JSON.replace('"16.4.6"', '"~16.4.6"'))
    assert check_dep_approvals.main([str(tmp_path)]) == 1
