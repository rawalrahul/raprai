"""WhatsApp in the compiled Windows app: neonize's short proto imports.

neonize puts its proto folder on sys.path and imports those packages by short
names ("waCommon", "waE2E.WAWebProtobufsE2E_pb2"). The Nuitka-built app has no
source files there, only modules compiled under their full names, so the
2.0.0 build failed its smoke test with "No module named 'waAICommon'". This
emulates that layout in a subprocess and checks the bridge's aliases fix it.
"""
import os
import shutil
import subprocess
import sys
import textwrap

import pytest

neonize = pytest.importorskip("neonize")

ROOT = os.path.join(os.path.dirname(__file__), "..")

EMULATE = textwrap.dedent('''
    import importlib.machinery, importlib.util, os, sys
    ROOT, MISSING, mode = sys.argv[1], "/nonexistent/dist", sys.argv[2]

    class CompiledFinder:
        """Like Nuitka's finder: neonize modules only by full name; package
        folders don't exist on disk."""
        def find_spec(self, name, path=None, target=None):
            if name != "neonize" and not name.startswith("neonize."):
                return None
            base = os.path.join(ROOT, *name.split("."))
            if os.path.isfile(os.path.join(base, "__init__.py")):
                loc = [base] if name == "neonize" else [MISSING]
                return importlib.util.spec_from_file_location(
                    name, os.path.join(base, "__init__.py"), submodule_search_locations=loc)
            if os.path.isdir(base):
                spec = importlib.machinery.ModuleSpec(name, None, is_package=True)
                spec.submodule_search_locations = [MISSING]
                return spec
            if os.path.isfile(base + ".py"):
                return importlib.util.spec_from_file_location(name, base + ".py")
            return None

    sys.meta_path.insert(0, CompiledFinder())
    sys.path.insert(0, sys.argv[3])
    from helm import whatsapp_bridge as wb
    wb._ensure_magic()
    if mode == "fix":
        wb._ensure_proto_aliases()
    try:
        from neonize.aioze.client import NewAClient  # noqa: F401
        import waE2E.WAWebProtobufsE2E_pb2 as short
        import neonize.proto.waE2E.WAWebProtobufsE2E_pb2 as full
        msg = full.Message.FromString(full.Message(conversation="hi").SerializeToString())
        print("OK", short is full, full.__spec__.name, msg.conversation)
    except Exception as e:
        print("FAIL", type(e).__name__, e)
''')


@pytest.fixture(scope="module")
def compiled_layout(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("compiled")
    src = os.path.dirname(neonize.__file__)
    shutil.copytree(src, tmp / "neonize", ignore=shutil.ignore_patterns("__pycache__"))
    init = tmp / "neonize" / "proto" / "__init__.py"
    # In the compiled app the folder neonize puts on sys.path has no sources.
    text = init.read_text()
    assert "sys.path.insert" in text
    init.write_text(text.replace("Path(__file__).parent.__str__()", '"/nonexistent/dist/neonize/proto"'))
    script = tmp / "emulate.py"
    script.write_text(EMULATE)
    return tmp, script


def _run(layout, mode):
    tmp, script = layout
    out = subprocess.run([sys.executable, str(script), str(tmp), mode, os.path.abspath(ROOT)],
                         capture_output=True, text=True, timeout=120, cwd=str(tmp))
    return (out.stdout.strip().splitlines() or [out.stderr[-500:]])[-1]


def test_without_aliases_reproduces_the_build_failure(compiled_layout):
    assert _run(compiled_layout, "nofix").startswith("FAIL ModuleNotFoundError")


def test_aliases_make_whatsapp_load_with_one_copy_of_each_module(compiled_layout):
    assert _run(compiled_layout, "fix") == "OK True neonize.proto.waE2E.WAWebProtobufsE2E_pb2 hi"
