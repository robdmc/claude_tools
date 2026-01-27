#!/usr/bin/env python3
"""
Claude Tools Uninstall Script

Safely removes installed Claude tools (skills, agents, commands) from
global (~/.claude/) or project (.claude/) locations.

Usage:
    python uninstall.py --target global|project --list           # Show installed tools
    python uninstall.py --target global|project --tools t1,t2    # Uninstall specific tools
"""

import argparse
import shutil
import sys
from pathlib import Path


def find_repo_root() -> Path:
    """Find the repository root by looking for CLAUDE.md or .git."""
    current = Path(__file__).resolve().parent

    # Walk up looking for markers
    while current != current.parent:
        if (current / "CLAUDE.md").exists() or (current / ".git").exists():
            return current
        current = current.parent

    # Fall back to parent of .claude directory
    script_path = Path(__file__).resolve()
    # .claude/skills/uninstall/uninstall.py -> go up 4 levels
    return script_path.parents[3]


def get_known_tools(repo_root: Path) -> set[str]:
    """
    Get the set of known tool names from the repository.

    This provides a safety check - we only uninstall tools that exist in the repo.
    """
    skip_dirs = {".claude", ".git", ".github", "__pycache__", "node_modules", ".venv", "venv"}
    tools = set()

    for item in repo_root.iterdir():
        if not item.is_dir():
            continue
        if item.name.startswith(".") or item.name in skip_dirs:
            continue

        # Check if it has any tool components
        has_skills = (item / "skills" / "SKILL.md").exists()
        has_agents = (item / "agents").is_dir() and list((item / "agents").glob("*.md"))
        has_commands = (item / "commands").is_dir() and list((item / "commands").glob("*.md"))

        if has_skills or has_agents or has_commands:
            tools.add(item.name)

    return tools


def resolve_target(target: str) -> Path:
    """Resolve target name to actual path."""
    if target == "global":
        return Path.home() / ".claude"
    elif target == "project":
        return Path.cwd() / ".claude"
    else:
        raise ValueError(f"Invalid target: {target}. Must be 'global' or 'project'")


def validate_target_path(target_path: Path, target: str) -> bool:
    """
    Safety check: ensure target path is exactly what we expect.

    This prevents accidental deletion in wrong directories.
    """
    expected_global = Path.home() / ".claude"
    expected_project = Path.cwd() / ".claude"

    resolved = target_path.resolve()

    if target == "global":
        return resolved == expected_global.resolve()
    elif target == "project":
        return resolved == expected_project.resolve()
    return False


def get_installed_tools(target_dir: Path, known_tools: set[str]) -> dict[str, dict]:
    """
    Discover what tools are installed in the target directory.

    Returns a dict mapping tool name to installation details.
    """
    installed = {}

    # Check skills directory
    skills_dir = target_dir / "skills"
    if skills_dir.exists():
        for item in skills_dir.iterdir():
            if not item.is_dir() and not item.is_symlink():
                continue

            tool_name = item.name
            if tool_name not in known_tools:
                continue

            if tool_name not in installed:
                installed[tool_name] = {"skill": None, "agents": [], "commands": []}

            installed[tool_name]["skill"] = {
                "path": item,
                "is_symlink": item.is_symlink(),
                "target": str(item.resolve()) if item.is_symlink() else None,
            }

    # Check agents directory
    agents_dir = target_dir / "agents"
    if agents_dir.exists():
        for agent_file in agents_dir.glob("*.md"):
            # Try to match agent to a known tool by checking symlink targets
            # or by looking up which tool has this agent
            matched_tool = match_agent_to_tool(agent_file, known_tools, find_repo_root())
            if matched_tool:
                if matched_tool not in installed:
                    installed[matched_tool] = {"skill": None, "agents": [], "commands": []}
                installed[matched_tool]["agents"].append({
                    "path": agent_file,
                    "name": agent_file.name,
                    "is_symlink": agent_file.is_symlink(),
                })

    # Check commands directory
    commands_dir = target_dir / "commands"
    if commands_dir.exists():
        for cmd_file in commands_dir.glob("*.md"):
            matched_tool = match_command_to_tool(cmd_file, known_tools, find_repo_root())
            if matched_tool:
                if matched_tool not in installed:
                    installed[matched_tool] = {"skill": None, "agents": [], "commands": []}
                installed[matched_tool]["commands"].append({
                    "path": cmd_file,
                    "name": cmd_file.name,
                    "is_symlink": cmd_file.is_symlink(),
                })

    return installed


def match_agent_to_tool(agent_file: Path, known_tools: set[str], repo_root: Path) -> str | None:
    """Match an installed agent file to its source tool."""
    # If it's a symlink, check where it points
    if agent_file.is_symlink():
        try:
            target = agent_file.resolve()
            # Check if target is in a known tool's agents directory
            for tool in known_tools:
                tool_agents = repo_root / tool / "agents"
                if tool_agents.exists() and target.parent == tool_agents.resolve():
                    return tool
        except (OSError, ValueError):
            pass

    # Otherwise check if the file exists in any tool's agents directory
    for tool in known_tools:
        tool_agent = repo_root / tool / "agents" / agent_file.name
        if tool_agent.exists():
            return tool

    return None


def match_command_to_tool(cmd_file: Path, known_tools: set[str], repo_root: Path) -> str | None:
    """Match an installed command file to its source tool."""
    # If it's a symlink, check where it points
    if cmd_file.is_symlink():
        try:
            target = cmd_file.resolve()
            for tool in known_tools:
                tool_commands = repo_root / tool / "commands"
                if tool_commands.exists() and target.parent == tool_commands.resolve():
                    return tool
        except (OSError, ValueError):
            pass

    # Otherwise check if the file exists in any tool's commands directory
    for tool in known_tools:
        tool_cmd = repo_root / tool / "commands" / cmd_file.name
        if tool_cmd.exists():
            return tool

    return None


def format_installed_list(installed: dict[str, dict], target_dir: Path) -> str:
    """Format installed tools for display."""
    if not installed:
        return f"No tools installed in {target_dir}"

    lines = [f"Installed tools in {target_dir}:\n"]

    for tool_name in sorted(installed.keys()):
        info = installed[tool_name]
        lines.append(f"  {tool_name}/")

        # Show skill info
        if info["skill"]:
            skill = info["skill"]
            mode = "symlink" if skill["is_symlink"] else "copy"
            lines.append(f"    skills/{tool_name}/ ({mode})")

        # Show agents
        for agent in info["agents"]:
            mode = "symlink" if agent["is_symlink"] else "copy"
            lines.append(f"    agents/{agent['name']} ({mode})")

        # Show commands
        for cmd in info["commands"]:
            mode = "symlink" if cmd["is_symlink"] else "copy"
            lines.append(f"    commands/{cmd['name']} ({mode})")

        lines.append("")

    return "\n".join(lines)


def remove_item(path: Path) -> str:
    """
    Safely remove a symlink, file, or directory.

    Returns a description of what was done.
    """
    if path.is_symlink():
        path.unlink()
        return "Unlinked"
    elif path.is_file():
        path.unlink()
        return "Deleted"
    elif path.is_dir():
        shutil.rmtree(path)
        return "Deleted"
    else:
        return "Not found"


def uninstall_tool(tool_name: str, tool_info: dict) -> list[str]:
    """
    Uninstall a tool and all its components.

    Returns a list of messages describing what was removed.
    """
    messages = []

    # Remove skill directory
    if tool_info["skill"]:
        skill_path = tool_info["skill"]["path"]
        if skill_path.exists() or skill_path.is_symlink():
            action = remove_item(skill_path)
            messages.append(f"  {action} skills/{tool_name}/")

    # Remove agents
    for agent in tool_info["agents"]:
        agent_path = agent["path"]
        if agent_path.exists() or agent_path.is_symlink():
            action = remove_item(agent_path)
            messages.append(f"  {action} agents/{agent['name']}")

    # Remove commands
    for cmd in tool_info["commands"]:
        cmd_path = cmd["path"]
        if cmd_path.exists() or cmd_path.is_symlink():
            action = remove_item(cmd_path)
            messages.append(f"  {action} commands/{cmd['name']}")

    return messages


def main():
    parser = argparse.ArgumentParser(
        description="Uninstall Claude tools",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--target",
        choices=["global", "project"],
        required=True,
        help="Target location: global (~/.claude/) or project (.claude/)",
    )

    parser.add_argument(
        "--list",
        action="store_true",
        help="List installed tools",
    )

    parser.add_argument(
        "--tools",
        type=str,
        help="Comma-separated list of tool names to uninstall",
    )

    args = parser.parse_args()

    # Resolve and validate target directory
    target_dir = resolve_target(args.target)

    if not validate_target_path(target_dir, args.target):
        print(f"Error: Target path validation failed for {target_dir}", file=sys.stderr)
        return 1

    if not target_dir.exists():
        print(f"Target directory does not exist: {target_dir}")
        return 0

    # Get known tools from repository
    repo_root = find_repo_root()
    known_tools = get_known_tools(repo_root)

    # Discover installed tools
    installed = get_installed_tools(target_dir, known_tools)

    if args.list:
        print(format_installed_list(installed, target_dir))
        return 0

    if args.tools:
        # Parse tool names to uninstall
        tool_names = [t.strip() for t in args.tools.split(",")]

        # Filter to only tools that are actually installed (no-op for others)
        not_installed = [t for t in tool_names if t not in installed]
        tools_to_remove = [t for t in tool_names if t in installed]

        if not_installed:
            for tool in not_installed:
                print(f"Skipping {tool} (not installed)")

        if not tools_to_remove:
            print("No tools to uninstall.")
            return 0

        print(f"Uninstalling from: {target_dir}")

        # Uninstall each tool
        all_messages = []
        for tool_name in tools_to_remove:
            print(f"\nRemoving {tool_name}...")
            messages = uninstall_tool(tool_name, installed[tool_name])
            all_messages.extend(messages)

        # Print results
        for msg in all_messages:
            print(msg)

        print("\nUninstall complete!")
        return 0

    # No action specified
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
