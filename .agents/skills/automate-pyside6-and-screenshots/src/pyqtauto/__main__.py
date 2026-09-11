"""PyQtAuto CLI - Command-line interface for controlling PySide6 applications.

Usage:
    pyqtauto --help
    pyqtauto tree
    pyqtauto click @name:my_button
    pyqtauto type @name:my_input "Hello World"
    pyqtauto screenshot output.png
"""

from __future__ import annotations

import json
import sys

import click

from .client import PyQtAutoClient, PyQtAutoError
from .protocol import DEFAULT_HOST, DEFAULT_PORT


@click.group()
@click.option(
    "--host",
    "-h",
    default=DEFAULT_HOST,
    help=f"Server host (default: {DEFAULT_HOST})",
)
@click.option(
    "--port",
    "-p",
    default=DEFAULT_PORT,
    type=int,
    help=f"Server port (default: {DEFAULT_PORT})",
)
@click.option(
    "--timeout",
    "-t",
    default=30.0,
    type=float,
    help="Connection timeout in seconds (default: 30)",
)
@click.pass_context
def cli(ctx, host: str, port: int, timeout: float):
    """PyQtAuto - Automation tool for PySide6 applications.

    Control and test PySide6 applications remotely via a simple
    JSON-over-TCP protocol.
    """
    ctx.ensure_object(dict)
    ctx.obj["host"] = host
    ctx.obj["port"] = port
    ctx.obj["timeout"] = timeout


def get_client(ctx) -> PyQtAutoClient:
    """Get a client instance from context."""
    return PyQtAutoClient(
        host=ctx.obj["host"],
        port=ctx.obj["port"],
        timeout=ctx.obj["timeout"],
    )


def handle_error(e: Exception):
    """Handle and display errors."""
    if isinstance(e, PyQtAutoError):
        click.echo(f"Error [{e.code}]: {e.message}", err=True)
        if e.details:
            click.echo(f"Details: {json.dumps(e.details, indent=2)}", err=True)
    else:
        click.echo(f"Error: {e}", err=True)
    sys.exit(1)


# Introspection commands


@cli.command()
@click.option(
    "--depth", "-d", default=-1, type=int, help="Maximum depth (-1 for unlimited)"
)
@click.option("--invisible", "-i", is_flag=True, help="Include invisible widgets")
@click.option("--no-properties", is_flag=True, help="Exclude widget properties")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_context
def tree(ctx, depth: int, invisible: bool, no_properties: bool, as_json: bool):
    """Get the widget tree."""
    try:
        with get_client(ctx) as client:
            result = client.get_tree(
                depth=depth,
                include_invisible=invisible,
                include_properties=not no_properties,
            )
            if as_json:
                click.echo(json.dumps(result, indent=2))
            else:
                _print_tree(result, 0)
    except Exception as e:
        handle_error(e)


def _print_tree(node: dict, indent: int):
    """Pretty print a widget tree node."""
    prefix = "  " * indent
    name = node.get("objectName") or node.get("class")
    class_name = node.get("class", "")
    visible = "visible" if node.get("visible") else "hidden"
    enabled = "enabled" if node.get("enabled") else "disabled"

    text = node.get("text", "")
    text_info = (
        f' "{text[:30]}..."'
        if text and len(text) > 30
        else f' "{text}"'
        if text
        else ""
    )

    click.echo(f"{prefix}- {name} ({class_name}) [{visible}, {enabled}]{text_info}")

    for child in node.get("children", []):
        _print_tree(child, indent + 1)


@cli.command()
@click.argument("selector")
@click.option("--max-results", "-n", default=10, type=int, help="Maximum results")
@click.option("--invisible", "-i", is_flag=True, help="Include invisible widgets")
@click.pass_context
def find(ctx, selector: str, max_results: int, invisible: bool):
    """Find widgets matching a selector."""
    try:
        with get_client(ctx) as client:
            results = client.find(
                selector, max_results=max_results, visible_only=not invisible
            )
            if not results:
                click.echo("No widgets found.")
            else:
                click.echo(f"Found {len(results)} widget(s):")
                for widget in results:
                    name = widget.get("objectName") or "(no name)"
                    click.echo(f"  - {name} ({widget.get('class')})")
    except Exception as e:
        handle_error(e)


@cli.command("get")
@click.argument("selector")
@click.argument("property")
@click.pass_context
def get_property(ctx, selector: str, property: str):
    """Get a property value from a widget."""
    try:
        with get_client(ctx) as client:
            value = client.get_property(selector, property)
            click.echo(value)
    except Exception as e:
        handle_error(e)


@cli.command("props")
@click.argument("selector")
@click.pass_context
def list_properties(ctx, selector: str):
    """List all properties of a widget."""
    try:
        with get_client(ctx) as client:
            props = client.list_properties(selector)
            for name, value in props.items():
                click.echo(f"  {name}: {value}")
    except Exception as e:
        handle_error(e)


# Action commands


@cli.command()
@click.argument("selector")
@click.option(
    "--button", "-b", default="left", help="Mouse button (left, right, middle)"
)
@click.option("--x", type=int, help="X position relative to widget")
@click.option("--y", type=int, help="Y position relative to widget")
@click.pass_context
def click_cmd(ctx, selector: str, button: str, x: int | None, y: int | None):
    """Click a widget."""
    try:
        with get_client(ctx) as client:
            pos = {"x": x, "y": y} if x is not None and y is not None else None
            client.click(selector, button=button, pos=pos)
            click.echo("Clicked.")
    except Exception as e:
        handle_error(e)


# Alias for click command (since 'click' conflicts with the click library)
cli.add_command(click_cmd, name="click")


@cli.command()
@click.argument("selector")
@click.pass_context
def dblclick(ctx, selector: str):
    """Double-click a widget."""
    try:
        with get_client(ctx) as client:
            client.double_click(selector)
            click.echo("Double-clicked.")
    except Exception as e:
        handle_error(e)


@cli.command()
@click.argument("selector")
@click.pass_context
def rclick(ctx, selector: str):
    """Right-click a widget."""
    try:
        with get_client(ctx) as client:
            client.right_click(selector)
            click.echo("Right-clicked.")
    except Exception as e:
        handle_error(e)


@cli.command("type")
@click.argument("selector")
@click.argument("text")
@click.option("--no-clear", is_flag=True, help="Don't clear existing text first")
@click.pass_context
def type_text(ctx, selector: str, text: str, no_clear: bool):
    """Type text into a widget."""
    try:
        with get_client(ctx) as client:
            client.type(selector, text, clear_first=not no_clear)
            click.echo(f"Typed: {text}")
    except Exception as e:
        handle_error(e)


@cli.command()
@click.argument("selector")
@click.argument("key")
@click.option("--ctrl", is_flag=True, help="Hold Ctrl")
@click.option("--shift", is_flag=True, help="Hold Shift")
@click.option("--alt", is_flag=True, help="Hold Alt")
@click.option("--meta", is_flag=True, help="Hold Meta/Cmd")
@click.pass_context
def key(ctx, selector: str, key: str, ctrl: bool, shift: bool, alt: bool, meta: bool):
    """Press a key on a widget."""
    try:
        modifiers = []
        if ctrl:
            modifiers.append("ctrl")
        if shift:
            modifiers.append("shift")
        if alt:
            modifiers.append("alt")
        if meta:
            modifiers.append("meta")

        with get_client(ctx) as client:
            client.key(selector, key, modifiers=modifiers)
            click.echo(f"Pressed: {key}")
    except Exception as e:
        handle_error(e)


@cli.command()
@click.argument("selector")
@click.argument("sequence")
@click.pass_context
def shortcut(ctx, selector: str, sequence: str):
    """Press a key sequence (e.g., Ctrl+S)."""
    try:
        with get_client(ctx) as client:
            client.key_sequence(selector, sequence)
            click.echo(f"Pressed: {sequence}")
    except Exception as e:
        handle_error(e)


@cli.command()
@click.argument("selector")
@click.pass_context
def focus(ctx, selector: str):
    """Set focus to a widget."""
    try:
        with get_client(ctx) as client:
            client.focus(selector)
            click.echo("Focused.")
    except Exception as e:
        handle_error(e)


@cli.command()
@click.argument("selector")
@click.pass_context
def clear(ctx, selector: str):
    """Clear a widget's content."""
    try:
        with get_client(ctx) as client:
            client.clear(selector)
            click.echo("Cleared.")
    except Exception as e:
        handle_error(e)


@cli.command("set")
@click.argument("selector")
@click.argument("value")
@click.pass_context
def set_value(ctx, selector: str, value: str):
    """Set a widget's value (smart setter)."""
    try:
        # Try to parse as JSON for non-string values
        try:
            parsed_value = json.loads(value)
        except json.JSONDecodeError:
            parsed_value = value

        with get_client(ctx) as client:
            client.set_value(selector, parsed_value)
            click.echo(f"Set: {value}")
    except Exception as e:
        handle_error(e)


# Verification commands


@cli.command()
@click.argument("filename", required=False)
@click.option("--target", "-t", help="Widget selector (default: root window)")
@click.option("--format", "-f", "fmt", default="png", help="Image format (png, jpg)")
@click.pass_context
def screenshot(ctx, filename: str | None, target: str | None, fmt: str):
    """Take a screenshot."""
    try:
        with get_client(ctx) as client:
            if filename:
                saved = client.screenshot_to_file(filename, target=target, format=fmt)
                click.echo(f"Saved: {saved}")
            else:
                result = client.screenshot(target=target, format=fmt)
                # Output base64 to stdout
                click.echo(result["image"])
    except Exception as e:
        handle_error(e)


@cli.command()
@click.argument("selector")
@click.pass_context
def exists(ctx, selector: str):
    """Check if a widget exists."""
    try:
        with get_client(ctx) as client:
            if client.exists(selector):
                click.echo("true")
                sys.exit(0)
            else:
                click.echo("false")
                sys.exit(1)
    except Exception as e:
        handle_error(e)


@cli.command()
@click.argument("selector")
@click.pass_context
def visible(ctx, selector: str):
    """Check if a widget is visible."""
    try:
        with get_client(ctx) as client:
            if client.is_visible(selector):
                click.echo("true")
                sys.exit(0)
            else:
                click.echo("false")
                sys.exit(1)
    except Exception as e:
        handle_error(e)


@cli.command()
@click.argument("selector")
@click.pass_context
def enabled(ctx, selector: str):
    """Check if a widget is enabled."""
    try:
        with get_client(ctx) as client:
            if client.is_enabled(selector):
                click.echo("true")
                sys.exit(0)
            else:
                click.echo("false")
                sys.exit(1)
    except Exception as e:
        handle_error(e)


# Synchronization commands


@cli.command()
@click.argument("selector")
@click.option("--condition", "-c", default="visible", help="Condition to wait for")
@click.option(
    "--timeout", "-t", "timeout_ms", default=5000, type=int, help="Timeout in ms"
)
@click.pass_context
def wait(ctx, selector: str, condition: str, timeout_ms: int):
    """Wait for a condition to be met."""
    try:
        with get_client(ctx) as client:
            if client.wait(selector, condition=condition, timeout_ms=timeout_ms):
                click.echo("Condition met.")
            else:
                click.echo("Timeout.")
                sys.exit(1)
    except Exception as e:
        handle_error(e)


@cli.command()
@click.option(
    "--timeout", "-t", "timeout_ms", default=5000, type=int, help="Timeout in ms"
)
@click.pass_context
def idle(ctx, timeout_ms: int):
    """Wait for the application to be idle."""
    try:
        with get_client(ctx) as client:
            client.wait_idle(timeout_ms=timeout_ms)
            click.echo("Idle.")
    except Exception as e:
        handle_error(e)


@cli.command()
@click.argument("ms", type=int)
@click.pass_context
def sleep(ctx, ms: int):
    """Sleep for a specified time in milliseconds."""
    try:
        with get_client(ctx) as client:
            client.sleep(ms)
            click.echo(f"Slept {ms}ms.")
    except Exception as e:
        handle_error(e)


# App control commands


@cli.command("close")
@click.argument("selector", required=False)
@click.pass_context
def close_window(ctx, selector: str | None):
    """Close a window."""
    try:
        with get_client(ctx) as client:
            client.close(selector)
            click.echo("Closed.")
    except Exception as e:
        handle_error(e)


@cli.command()
@click.pass_context
def quit_app(ctx):
    """Quit the application."""
    try:
        with get_client(ctx) as client:
            client.quit()
            click.echo("Quit signal sent.")
    except Exception as e:
        handle_error(e)


# Interactive mode


@cli.command()
@click.pass_context
def shell(ctx):
    """Start an interactive shell."""
    try:
        client = get_client(ctx)
        click.echo(f"Connected to {client.host}:{client.port}")
        click.echo("Type 'help' for available commands, 'exit' to quit.")
        click.echo()

        while True:
            try:
                line = input("pyqtauto> ").strip()
            except (EOFError, KeyboardInterrupt):
                click.echo()
                break

            if not line:
                continue
            if line in ("exit", "quit"):
                break
            if line == "help":
                click.echo("Available commands:")
                click.echo("  tree              - Show widget tree")
                click.echo("  find <selector>   - Find widgets")
                click.echo("  click <selector>  - Click widget")
                click.echo("  type <selector> <text> - Type text")
                click.echo("  screenshot [file] - Take screenshot")
                click.echo("  exit              - Exit shell")
                continue

            parts = line.split(maxsplit=2)
            cmd = parts[0]

            try:
                if cmd == "tree":
                    result = client.get_tree()
                    _print_tree(result, 0)
                elif cmd == "find" and len(parts) > 1:
                    results = client.find(parts[1])
                    for w in results:
                        click.echo(f"  {w.get('objectName')} ({w.get('class')})")
                elif cmd == "click" and len(parts) > 1:
                    client.click(parts[1])
                    click.echo("Clicked.")
                elif cmd == "type" and len(parts) > 2:
                    client.type(parts[1], parts[2])
                    click.echo("Typed.")
                elif cmd == "screenshot":
                    if len(parts) > 1:
                        client.screenshot_to_file(parts[1])
                        click.echo(f"Saved: {parts[1]}")
                    else:
                        result = client.screenshot()
                        click.echo(f"Screenshot: {result['width']}x{result['height']}")
                else:
                    click.echo(f"Unknown command: {cmd}")
            except PyQtAutoError as e:
                click.echo(f"Error: {e.message}")

    except Exception as e:
        handle_error(e)


def main():
    cli()


if __name__ == "__main__":
    main()
