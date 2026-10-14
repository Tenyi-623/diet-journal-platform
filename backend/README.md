# 后端与数据导入说明

本文件保留食品数据、知识库和 OCR 的导入细节。**Spark 日常开机、换网络、模型启动、前端构建与排错，请先阅读 [项目中文 README](../README.md)**。现有机器已初始化，重启无需重复运行导入命令。

## 当前应用入口

在项目根目录启动 API 和后台 worker：

```bash
backend/.venv/bin/python -m scripts.service start
```

配置分别在 `backend/.env` 和 `backend/app.env`，模型服务通过 Ollama HTTP 调用。

- `GET /api/health`：只检查 API 存活，不检查 Ollama 推理。
- `GET /api/readiness`：登录后检查数据库和模型列表，不代表推理已通过。
- `POST /api/diet-chat/messages`：当前正式饮食聊天入口，使用登录会话与 CSRF。
- `/docs`：登录后的接口测试页。
- 旧 `/api/chat`、`/api/embed` 已停用，鉴权后返回 410。

实际模型调用检查使用根目录 README 第 7 节。`backend.smoke_test` 保留了早期旧接口调用，不适用于当前应用验收。

## PostgreSQL + pgvector 知识库

独立 Compose 数据库使用 PostgreSQL 16 + pgvector 0.8.2，只绑定本机 5433 端口；宿主机原有 5432 数据库不受影响。数据持久化在 `hypertension-diet_diet_pgdata` Docker 卷中。

项目根目录 `.env` 提供数据库密码；`backend/.env` 的 `DATABASE_URL` 使用同一密码。两者已生成并忽略提交；不要将实际密码复制到公开文档。请保留这两个文件，容器重启无需重新生成密码。

```bash
# 当前用户没有 Docker 权限时使用 sudo
sudo docker compose up -d db
# 检查 PDF、备份原件、生成逐页文本和质量报告，不调用模型
backend/.venv/bin/python -m backend.ingest --audit-only
# 初始化表结构并导入；可中断后用同一命令续传
backend/.venv/bin/python -m backend.ingest
```

原件快照在 `data/originals/`；逐页提取在 `data/extracted/`；检查报告在 `data/reports/pdf_audit.md`。这些路径均相对项目根目录。脚本只处理 `backend/sources.json` 显式列出的五份文件，默认从 `/home/aitd/下载` 读取，可通过 `--input-dir` 指定目录。

`kb_collections` 固定模型名称、实际 digest、维度和处理版本；`kb_documents` 保存文件 SHA-256、标题、机构、版本和资料类型；`kb_pages` 保存物理页码、已知印刷页码、文本和隔离原因；`kb_chunks` 保存单页片段及 `halfvec(2560)`。约1000字符切分、150字符重叠，优先换行或句末，不跨PDF页面。每8段提交，重复运行跳过已完成向量；未完整导入的文档不参与检索。模型或查询指令更改时需更新集合版本。同一PDF的提取修复会记录 `extraction_fingerprint`，按片段实际文本比对，仅复用完全相同的向量，并删除已失效片段。

模型更换后需重新导入。检索根据实际模型 digest 只选择兼容集合；不会把旧版本向量混进结果。查询加入检索任务指令，文档向量不加指令。

接口（重启后端后可在 `/docs` 测试）：

- `GET /api/knowledge/documents`：数据库扩展版本、文档状态、片段数、隔离页数、来源警示。
- `POST /api/knowledge/search`：例如 `{"query":"糖尿病の食事療法における管理栄養士の役割は？","top_k":5}`。可加 `document_id` 限定来源。返回原文、相似度、文档信息、PDF物理页码、已知印刷页码及引用标签。

初期查询使用过滤后的精确余弦排序，避免小语料库中HNSW过滤造成漏召回；HNSW索引已建立，后续规模扩大可切换并评估召回。相似度并非可靠性评分，当前未设经验证的无关查询拒答阈值。当前饮食聊天已接入带引用回答；异步三餐和换餐在数值校验后补充知识库原句及翻译。正式入口见上文，不再使用旧 `/api/chat`。

### 资料限制

高血压资料是5页指南解读，并非指南全文；糖尿病是食事疗法单章；食品成分表是2020版，疑似表格/索引页通过启发式规则隔离，剩余文字尚未逐页审核，不能用于精确营养计算。肾病文件是2007版且数值提取缺失；2025膳食摄入标准现已通过日语OCR及部分字体映射修复，经过质量筛选的正文可检索；肾病文件仍整份隔离。修复报告见 `data/reports/dri2025_repair.md`。OCR尚未逐页人工校对，仍需内容审核。精确营养计算使用后文单独导入的食品 Excel 结构化数据，不使用 PDF 检索段落代替营养值。

检查：

```bash
backend/.venv/bin/python -m unittest discover -s backend/tests -v
```

参考：[pgvector](https://github.com/pgvector/pgvector)、[Qwen3-Embedding-4B官方模型说明](https://huggingface.co/Qwen/Qwen3-Embedding-4B)。


## 2025 膳食摄入标准文字修复

原件和厚生劳动省官方全文的 SHA-256 完全一致，均缺少多种嵌入字体的 Unicode 映射。原件未改写。修复产物位于 `data/repair/dri2025/`：

- `dietary-reference-intakes-2025-ocr.pdf`：486页图像及机器OCR文字层，方便对照，尚有OCR误识别。
- `dietary-reference-intakes-2025-repaired.txt`：加入BIZ Gothic字体映射修复的全文，含不参与检索的待核对页面。
- `repaired-pages.json`：页码、OCR质量指标、修复文本、检索文本、排除行及原因。
- `recipe.json`：原件和OCR模型的哈希，防止缓存用于错误版本。

复现命令（项目根目录；当前机器已准备好工具）：

```bash
# 仅在重建本机工具时需要；适用于本项目 Ubuntu ARM64 环境
bash scripts/setup_ocr.sh
backend/.venv/bin/python -m backend.repair_dri
backend/.venv/bin/python -m backend.dri_text
backend/.venv/bin/python -m backend.ingest --only dietary_reference_intakes
```

OCR采用本机Tesseract 5.3.4、日语best模型、英语模型和400dpi渲染。BIZ Gothic可恢复的文字行用参考字体字形编号映射恢复。平均置信度低于85、低置信度字符比例超过10%的页面暂不检索；检测到较大复杂表格的页面亦隔离。行级OCR置信度不足80，或与原PDF可可靠提取的数字/单位不一致时，排除该行。阈值是工程筛选规则，不代表医学准确率，未校验到的OCR错误仍可能存在。

同一文件重建使用原文档ID，原PDF页码不变；部分页码由恢复的页脚直接获取。修复过程中的数据库快照：`data/backups/dri2025-intermediate-snapshot.dump`（含当时的部分导入进度，不是修复前完整状态）。当前源文件清单中的 `repaired_pages` 指向持久化修复产物；后续正常导入不会退回乱码文字层。

### 2020 八订食品结构化数据

官方入口：https://www.mext.go.jp/a_menu/syokuhinseibun/mext_01110.html

本次导入主表（更新日 2021-12-28），不混入增补 2023 数据。下载原件保存为
`data/food2020/012.xlsx`（官方路径末尾 `_012.xlsx`）和
`data/food2020/101.xlsx`（正误表，官方路径末尾 `_101.xlsx`）。
完整地址前缀：`https://www.mext.go.jp/content/20201225-mxt_kagsei-mext_01110`。

```bash
backend/.venv/bin/python -m backend.food_import
backend/.venv/bin/python -m unittest backend.tests.test_food_import
backend/.venv/bin/python -m backend.food_import --import-db
```

每次运行先验证，数据库导入使用单事务；相同文件 SHA256 重复导入会拒绝执行。
导入位于 `food_datasets`、`foods`、`food_nutrients`、`food_values`，与向量文本库独立。
营养素代码采用官方标识，`NA` 为钠、`K` 为钾、`NACL_EQ` 为食盐相当量；
单位及每100克可食部口径在 `food_nutrients.metadata` 中（廃棄率另为百分比）。
`raw` 保留原值，`estimated` 保留括号标识；Tr、横线和独立星号的 numeric value 为 NULL，不能当成 0。
原 PDF 缺第2章：PDF 页码仅标记关联说明、索引和旧能量对照，不代表主表营养值出处。
具体成分出处为 Excel 的工作表、行号、列号；来源版本、原件哈希、更正记录均保留。
结构化营养值已通过 `app_ingredients` 接入菜谱计算和推荐规划，食品来源随推荐快照保存。

查询示例：
```sql
SELECT f.code, f.name_ja, v.nutrient_code, v.value, v.raw, v.status,
       v.estimated, n.metadata->>'unit' AS unit,
       f.source->'pdf_references' AS pdf_references
FROM foods f JOIN food_values v ON (f.dataset_id,f.code)=(v.dataset_id,v.food_code)
JOIN food_nutrients n ON (n.dataset_id,n.code)=(v.dataset_id,v.nutrient_code)
WHERE f.code='01088' AND v.nutrient_code IN ('ENERC_KCAL','NA','K','PROT-');
```

验证报告：`data/reports/food2020_validation.json`；导入后逐条回读：
```bash
backend/.venv/bin/python -m backend.check_food_import
```
核桃面包 01210 的 Excel 能量 292 kcal 与 PDF 291 kcal 不一致，尚未找到明确的能量更正依据，
整条食品保留在本地暂存数据中，不导入生产食品表；其他差异只有在官方正误表的正确值与 Excel 相符时才放行。
