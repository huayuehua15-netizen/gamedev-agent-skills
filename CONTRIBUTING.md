# 贡献指南

感谢愿意改进这套技能。它面向的是**可被机器验证的交付质量**，所以贡献标准也围绕这一点。

## 最有价值的贡献类型

按优先级排序：

1. **修一个会误导人的事实错误**（数值、API 名、规范尺寸）。这类 bug 危害最大，
   因为 Agent 会原样照抄。请附上权威来源链接。
2. **让一个门禁真的能拦住问题**。附上"修复前放过 / 修复后拦住"的实测输出。
3. **补 2D 或非 Unity 引擎的缺口**。当前 2D 与 Godot/Unreal 仍是薄的一层。
4. 补充范文（本仓库只有场景单页有完整范例）。
5. 文档排版、错别字。

## 提交前请自检

```bash
# 1) Python 语法
python -m compileall -q plugins tools tests

# 2) 门禁数学单元测试（不需要 Blender）
python tests/test_silhouette_gate.py

# 3) 重新生成各宿主产物（改了 plugins/ 就必须跑）
python tools/build.py

# 4) 确认 dist/ 与 plugins/ 一致（dist/ 被 gitignore，但发布依赖它）
```

如果你改了 Blender 脚本，**请用真实 Blender 跑一遍**，并在 PR 里贴出退出码：

```bash
blender --background --python-exit-code 1 --python <脚本> -- <参数>
echo "exit=$?"
```

## 硬性规则

这些规则不是风格偏好，是本仓库存在的理由：

- **脚本必须有确定的退出码**：`0` 通过 / `1` 检查未通过 / `2` 参数或输入有问题。
  任何"出错了但返回 0"的写法都不接受。
- **禁止静默跳过**。不认识的参数要报错，不能 `else: i += 1`。
  空目标集要报错，不能打印"0 个问题"然后退出 0。
- **数值要么有权威来源，要么标 `【待确认】`**。不许写"行业参考值"来糊弄。
- **文档与代码必须一致**。改了模板 API，就要同步改 references 里的调用示例。
- **区分 3A / 中型 / 独立三档**。一个数字同时服务两种规模等于两种都不准确。
- **说明边界**。新技能要写清"不做什么"，和 README 里四个技能的分工表保持一致。

## 不要做的事

- 不要为了显得全面而堆砌空洞条目（"注意性能""保证质量"）。写不出可判定标准就别写。
- 不要在 references 里复制大段已有内容，用相对路径引用。
- 不要提交 `dist/`、`__pycache__`、`.pyc`（已在 `.gitignore`）。

## 新增一个技能的检查清单

- [ ] `SKILL.md` 的 frontmatter 有 `name` 与 `description`，description 同时包含中文和英文子句
- [ ] `SKILL.md` 开头说明"路径相对本文件所在目录"
- [ ] 有明确的「不做什么」边界
- [ ] `references/` 按需读取，不要求在 SKILL.md 里一次读完
- [ ] 脚本有退出码语义，并在文档里写明需要 `--python-exit-code 1`
- [ ] 至少一条可机器判定的验收项
- [ ] 在 `README.md` 的技能表里登记
- [ ] 跑过 `python tools/build.py`，`dist/` 产物正常

## 许可

贡献即视为同意以 MIT 许可发布，见 [LICENSE](LICENSE)。
