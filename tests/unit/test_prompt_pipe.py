"""Prompts work with the redirected stdin used by the operator UI."""
import subprocess
import sys


def test_redirected_line_and_any_key():
    code = ("from colosseum_shared.prompt._stdin import read_line, wait_any_key; "
            "print(repr(read_line(message='line', timeout_s=3))); "
            "print(wait_any_key(message='key', timeout_s=3))")
    result = subprocess.run([sys.executable, "-c", code], input="h?llo\n\n", text=True,
                            encoding="utf-8", capture_output=True, timeout=10, check=True)
    assert "'h?llo'" in result.stdout
    assert "True" in result.stdout


def test_redirected_timeout():
    code = "from colosseum_shared.prompt._stdin import read_line; print(read_line(message='line', timeout_s=0.05))"
    proc = subprocess.Popen([sys.executable, "-c", code], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, text=True)
    try:
        assert proc.wait(timeout=10) == 0
        assert "None" in proc.stdout.read()
    finally:
        proc.kill() if proc.poll() is None else None
        proc.communicate()
