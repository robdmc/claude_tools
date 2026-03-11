"""ddag_marimo.py — Export a .ddag node to a Marimo notebook and import changes back."""

import argparse
import ast
import sys
import textwrap
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ddag_core


def generate_notebook(function_body, sources_dict, outputs_dict, params_dict):
    """Generate a Marimo notebook string from node metadata.

    Returns the full notebook content as a string.
    """
    # Build the dict literals for the run cell
    sources_literal = repr(sources_dict)
    params_literal = repr(params_dict)
    outputs_literal = repr(outputs_dict)

    # Ensure function_body is just the inner code (no def line)
    stripped = function_body.strip("\n")
    if stripped.startswith("def transform("):
        # Strip the signature line and dedent the body
        lines = stripped.split("\n")
        inner = textwrap.dedent("\n".join(lines[1:]))
        stripped = inner.strip("\n")

    # Indent the body to sit inside def transform(...)
    body_lines = stripped.split("\n")
    indented_body = "\n".join("    " + line for line in body_lines)

    notebook = f'''\
import marimo

app = marimo.App()


@app.cell
def _():
    import marimo as mo
    return


@app.function
def transform(sources, params, outputs):
{indented_body}


@app.cell
def _():
    sources = {sources_literal}
    params = {params_literal}
    outputs = {outputs_literal}
    transform(sources, params, outputs)
    return


if __name__ == "__main__":
    app.run()
'''
    return notebook


def extract_transform_from_notebook(notebook_path):
    """Parse a Marimo notebook and extract the transform function body.

    Handles two formats:
    - @app.function style: top-level `def transform(sources, params, outputs)`
    - Legacy @app.cell style: `def transform_cell()` with nested `def transform`

    Returns the inner body of the transform function (without the def line),
    or None if not found.
    """
    source = Path(notebook_path).read_text()
    tree = ast.parse(source)
    lines = source.split("\n")

    def _extract_body(func_node):
        """Extract the function body (everything after the def line), dedented."""
        func_lines = lines[func_node.lineno - 1 : func_node.end_lineno]
        func_text = textwrap.dedent("\n".join(func_lines))
        # Strip the def line, dedent the body
        body_lines = func_text.split("\n")[1:]
        body = textwrap.dedent("\n".join(body_lines))
        return body.strip("\n") + "\n"

    # Look for top-level def transform (marimo @app.function style)
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "transform":
            return _extract_body(node)

    # Fallback: legacy nested style inside transform_cell
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "transform_cell":
            for child in ast.walk(node):
                if isinstance(child, ast.FunctionDef) and child.name == "transform":
                    return _extract_body(child)

    return None


def ensure_marimo_docs(root):
    """Fetch marimo CLAUDE.md to .claude/prompts/marimo.md if not present."""
    prompts_dir = Path(root) / ".claude" / "prompts"
    marimo_md = prompts_dir / "marimo.md"
    if marimo_md.exists():
        return str(marimo_md)

    import urllib.request
    import urllib.error

    url = "https://docs.marimo.io/CLAUDE.md"
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            content = resp.read().decode("utf-8")
    except (urllib.error.URLError, OSError) as e:
        print(f"Warning: Could not fetch marimo docs from {url}: {e}", file=sys.stderr)
        return None

    prompts_dir.mkdir(parents=True, exist_ok=True)
    marimo_md.write_text(content)
    print(f"Saved marimo docs to {marimo_md}", file=sys.stderr)
    return str(marimo_md)


def export_notebook(ddag_path, root="."):
    """Export a .ddag node to a Marimo notebook file.

    Returns the output notebook path.
    """
    meta = ddag_core.read_node(ddag_path)
    if meta["is_source_node"]:
        raise ValueError(f"{ddag_path} is a source node (no transform to export)")
    if not meta["transform_function"]:
        raise ValueError(f"{ddag_path} has no transform function")

    function_body = meta["transform_function"]
    sources_dict = ddag_core.get_sources_dict(ddag_path)
    outputs_dict = ddag_core.get_outputs_dict(ddag_path)
    params_dict = ddag_core.get_params_dict(ddag_path)

    notebook_content = generate_notebook(function_body, sources_dict, outputs_dict, params_dict)

    stem = Path(ddag_path).stem
    notebook_path = f"{stem}.ddag.nb.py"

    if Path(notebook_path).exists():
        print(f"Warning: Overwriting existing {notebook_path}", file=sys.stderr)

    Path(notebook_path).write_text(notebook_content)

    # Run marimo check --fix to add __generated_with and fix formatting
    import shutil
    marimo_bin = shutil.which("marimo")
    if marimo_bin:
        import subprocess
        result = subprocess.run(
            [marimo_bin, "check", "--fix", notebook_path],
            capture_output=True, text=True,
        )
        if result.returncode != 0 and result.stderr:
            print(f"marimo check --fix warning: {result.stderr.strip()}", file=sys.stderr)
    else:
        print(
            "Warning: 'marimo' not found on PATH. "
            "Activate an environment with marimo installed to auto-fix notebook formatting.",
            file=sys.stderr,
        )

    # Ensure marimo docs are available in the project
    ensure_marimo_docs(root)

    return notebook_path


def import_notebook(ddag_path, notebook_path=None):
    """Import a transform function from a Marimo notebook back into a .ddag node.

    Returns (notebook_path, changed) where changed is True if the function was updated.
    """
    meta = ddag_core.read_node(ddag_path)
    if meta["is_source_node"]:
        raise ValueError(f"{ddag_path} is a source node (no transform to import)")

    if notebook_path is None:
        stem = Path(ddag_path).stem
        notebook_path = f"{stem}.ddag.nb.py"

    if not Path(notebook_path).exists():
        raise FileNotFoundError(f"Notebook not found: {notebook_path}")

    new_body = extract_transform_from_notebook(notebook_path)
    if new_body is None:
        raise ValueError(f"Could not find def transform(sources, params, outputs) in {notebook_path}")

    old_body = meta["transform_function"]
    if new_body.rstrip("\n") == (old_body or "").rstrip("\n"):
        print("No changes detected in transform function.", file=sys.stderr)
        return notebook_path, False

    # Preserve existing transform_plan
    plan = meta["transform_plan"]
    if not plan:
        plan = "(imported from marimo notebook)"
    ddag_core.set_function(ddag_path, new_body, plan)
    print(f"Updated transform function in {ddag_path} from {notebook_path}", file=sys.stderr)
    return notebook_path, True


def main():
    parser = argparse.ArgumentParser(description="Export/import ddag nodes to/from Marimo notebooks")
    parser.add_argument("ddag_path", help="Path to the .ddag file")
    parser.add_argument("--import", dest="do_import", action="store_true",
                        help="Import transform from notebook back into node")
    parser.add_argument("--notebook", help="Path to notebook file (default: <stem>.ddag.nb.py)")
    parser.add_argument("--root", default=".", help="Project root directory")

    args = parser.parse_args()

    if args.do_import:
        nb_path, changed = import_notebook(args.ddag_path, args.notebook)
        if changed:
            print(f"Imported from {nb_path}")
        else:
            print(f"No changes to import from {nb_path}")
    else:
        nb_path = export_notebook(args.ddag_path, args.root)
        print(f"Exported to {nb_path}")


if __name__ == "__main__":
    main()
