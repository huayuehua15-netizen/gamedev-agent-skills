"""剪影门禁的纯数学单元测试（不需要 Blender）。

运行：python tests/test_silhouette_gate.py
覆盖：归一化、IoU、宽高比校验、空剪影、blockout 与 final 的阈值差异。
"""

import importlib.util
import io
import os
import sys
import types

# --- UTF-8 输出守卫：Windows 控制台默认 cp1252/cp936，print 中文会抛 UnicodeEncodeError ---
import sys as _sys
for _s in (_sys.stdout, _sys.stderr):
    if _s is not None and hasattr(_s, "reconfigure"):
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
import numpy as np

# Windows 的默认控制台编码不是 UTF-8（常见 cp1252 / cp936 / cp437）。
# qa_render 返回的 error 字段是中文，直接 print 会抛 UnicodeEncodeError，
# 在 CI 上表现为"单元测试失败"而本地却正常。这里把标准输出包成 UTF-8。
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(
        sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True)
if hasattr(sys.stderr, "buffer"):
    sys.stderr = io.TextIOWrapper(
        sys.stderr.buffer, encoding="utf-8", errors="replace", line_buffering=True)

# 用桩替换 Blender 模块，只加载 qa_render 里的纯数学部分
sys.modules.setdefault("bpy", types.ModuleType("bpy"))
mu = types.ModuleType("mathutils")


class Vector:
    pass


mu.Vector = Vector
sys.modules.setdefault("mathutils", mu)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(
    ROOT, "plugins", "blender-modeling-craft", "skills",
    "blender-modeling-craft", "scripts", "qa_render.py")


def load_module():
    spec = importlib.util.spec_from_file_location("qa_render", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def rect(w, h, canvas=400, x=100, y=100):
    mask = np.zeros((canvas, canvas), dtype=bool)
    mask[y:y + h, x:x + w] = True
    return mask


def main():
    mod = load_module()
    ref = rect(100, 200)

    holed = rect(100, 200)
    holed[120:250, 130:160] = False  # 包围盒不变，剪影少一块

    identical = mod.compare_view("front", rect(100, 200), ref, 0.85, 0.05)
    translated = mod.compare_view("front", rect(100, 200, x=180, y=160), ref, 0.85, 0.05)
    narrow = mod.compare_view("front", rect(80, 200), ref, 0.85, 0.05)
    hollow_final = mod.compare_view("front", holed, ref, 0.85, 0.05)
    hollow_blockout = mod.compare_view("front", holed, ref, 0.70, 0.10)
    empty = mod.compare_view("front", np.zeros((400, 400), dtype=bool), ref, 0.85, 0.05)
    blockout_ok = mod.compare_view("front", rect(90, 190, y=105), ref, 0.70, 0.10)

    assert identical["pass"] and abs(identical["iou"] - 1.0) < 1e-6
    assert translated["pass"] and abs(translated["iou"] - 1.0) < 1e-6
    assert not narrow["pass"] and narrow["aspect_error"] > 0.15
    assert hollow_blockout["pass"] and not hollow_final["pass"]
    assert not empty["pass"] and "error" in empty
    assert blockout_ok["pass"]

    print("identical :", identical)
    print("translated:", translated)
    print("narrow    :", narrow)
    print("hollow    :", hollow_blockout, "|", hollow_final)
    print("empty     :", empty)
    print("blockout  :", blockout_ok)
    print("ALL PASS")


if __name__ == "__main__":
    main()
