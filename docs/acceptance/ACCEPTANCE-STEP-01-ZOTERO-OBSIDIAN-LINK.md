# 验收步骤 01：Zotero 文献记录生成 Obsidian 论文笔记

> 你不需要理解 Python 代码，只需要观察文件和链接。

## 一、示例数据体验

```bash
cd services/me-reader-core
python -m pip install -e '.[dev]'
cd ../..
mkdir -p /tmp/me-reader-acceptance-vault
me-reader create-paper-note \
  --item-json examples/me-reader/sample-zotero-item.json \
  --vault /tmp/me-reader-acceptance-vault
```

打开 `/tmp/me-reader-acceptance-vault/papers/`，应当只有：

```text
wang2026bim--ABCD1234.md
```

笔记中应包含：标题、作者、年份、DOI、“在 Zotero 中打开”、“打开 PDF”、“人工笔记”、“Agent 精读”、“Claim 与证据”和“待复核”。

第二次执行相同命令，状态应从 `created` 变为 `existing`，并且仍然只有一篇笔记。

在 `USER-CONTENT` 标记之间加入人工笔记后再次执行，人工内容必须保留。

## 二、真实 Zotero 条目验收

在 Zotero 的“设置 → 高级”中开启：

```text
允许本机上的其他应用与 Zotero 通信
```

取得一篇真实文献的 Zotero Item Key 后执行：

```bash
me-reader create-paper-note-from-zotero \
  --item-key 你的ITEM_KEY \
  --zotero-base-url http://127.0.0.1:23119/api \
  --vault 你的OBSIDIAN_VAULT路径
```

第二个 Zotero 实例将地址切换到实际端口，例如：

```text
http://127.0.0.1:23120/api
```

体验通过标准：

- [ ] 不需要手工制作 JSON；
- [ ] 标题、作者、年份和期刊与 Zotero 一致；
- [ ] 若条目有 PDF，笔记中出现真实附件回跳链接；
- [ ] 若 Extra 中有 Better BibTeX Citation Key，文件名优先使用 Citation Key；
- [ ] 对同一 Item Key 重复执行，不产生重复笔记；
- [ ] 人工笔记不会被覆盖。

## 三、诊断报告

```bash
me-reader diagnose \
  --item-json examples/me-reader/sample-zotero-item.json \
  --vault /tmp/me-reader-acceptance-vault
```

报告位于 `/tmp/me-reader-acceptance-vault/diagnostics/me-reader-diagnostic.md`。

## 四、当前暂未包含

- 从 Zotero 界面按钮一键触发；
- 自动判断 Zotero 当前选中的条目；
- 调用 Hermes 精读论文；
- 从 PDF 页面生成 Claim 与 Evidence；
- 通过 Obsidian 按钮触发任务。
