# 验收步骤 01：Zotero 文献记录生成 Obsidian 论文笔记

> 这一版本是第一条可运行链路，暂时通过示例 JSON 模拟 Zotero 插件传入的数据。你不需要理解 Python 代码，只需要观察文件和链接。

## 一、这一步能体验什么

完成后，你应当看到：

1. 指定的 Obsidian Vault 中自动出现 `papers` 文件夹；
2. 文件夹中出现一篇论文笔记；
3. 笔记包含标题、作者、年份、DOI 和 Zotero 回跳链接；
4. 同一个命令执行两次，不会出现第二篇重复笔记；
5. 你写入“人工笔记”的内容不会被第二次执行覆盖；
6. 系统可以自动生成一份诊断报告。

## 二、开发环境验收命令

```bash
cd services/me-reader-core
python -m pip install -e '.[dev]'
cd ../..
mkdir -p /tmp/me-reader-acceptance-vault
```

第一次生成笔记：

```bash
me-reader create-paper-note \
  --item-json examples/me-reader/sample-zotero-item.json \
  --vault /tmp/me-reader-acceptance-vault
```

## 三、你需要查看什么

打开 `/tmp/me-reader-acceptance-vault/papers/`，应当只有：

```text
wang2026bim--ABCD1234.md
```

用 Obsidian 打开 `/tmp/me-reader-acceptance-vault` 后，检查该笔记：

- 标题为“建筑信息模型在工程管理中的应用研究”；
- 有“在 Zotero 中打开”；
- 有“打开 PDF”；
- 有“人工笔记”；
- 有“Agent 精读”；
- 有“Claim 与证据”；
- 有“待复核”。

示例中的 Zotero Key 是虚拟值，因此链接格式应正确，但不会打开你本机的真实文献。接入真实 Zotero 后再验收实际跳转。

## 四、重复执行验收

再次执行完全相同的命令，输出状态应从 `created` 变成 `existing`，且 `papers` 文件夹仍然只有一个 Markdown 文件。

## 五、人工内容保护验收

在以下标记中间写入：

```markdown
<!-- USER-CONTENT:START -->
这是我的人工阅读笔记。
<!-- USER-CONTENT:END -->
```

第三次执行生成命令。重新打开文件，这句人工笔记必须仍然存在。

## 六、诊断报告验收

```bash
me-reader diagnose \
  --item-json examples/me-reader/sample-zotero-item.json \
  --vault /tmp/me-reader-acceptance-vault
```

打开 `/tmp/me-reader-acceptance-vault/diagnostics/me-reader-diagnostic.md`。报告应显示 Vault 存在、可写、文献元数据有效，并可生成 Zotero PDF 链接。

## 七、通过判定

- [ ] 第一次执行生成一篇笔记；
- [ ] 第二次执行不生成重复笔记；
- [ ] 中文内容没有乱码；
- [ ] Zotero 链接格式正确；
- [ ] 人工笔记没有被覆盖；
- [ ] 诊断报告成功生成。

## 八、当前暂未包含

- 直接从你的 Zotero 自动读取条目；
- 点击虚拟示例链接打开真实 PDF；
- 调用 Hermes 精读论文；
- 从 PDF 页面生成 Claim 与 Evidence；
- 通过 Obsidian 按钮触发任务。

当前目的只是先把“一个 Zotero 身份只对应一篇 Obsidian 笔记”的底层规则做稳。
