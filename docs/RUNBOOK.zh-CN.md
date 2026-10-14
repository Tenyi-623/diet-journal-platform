# 本机运行与维护

日常重启、Spark 搬到新网络、SSH 访问、数据库及模型服务启动，以项目根目录的
[中文 README](../README.md) 为准；本文件补充应用机制和维护细节。

当前工作目录：`/home/aitd/hypertension-diet`。已经完成初始化，无需重复导入食品和知识库。Web 默认监听 `0.0.0.0:8000`，支持局域网访问；`backend/.venv/bin/python -m scripts.lan` 显示当前网卡 IP 和访问网址。换网络无需修改监听配置。

## 进入系统

1. 打开 `http://127.0.0.1:8000`，未登录时进入登录页。
2. 从本机 `data/private/local-accounts.csv` 取得分配给演示者的ID与初始密码。共有 diet001–diet050；不要把整个账号文件放到网页或论文附件。
3. 登录后进入食谱图片主页。首次显示未个性化示例，进入用户信息填写合成年龄、健康/过敏状态、收入档次、预算并确认演示参数。
4. 收入口径：个人税前年收入JPY。六档为[0,200万)、[200万,400万)、[400万,600万)、[600万,800万)、[800万,1000万)、[1000万,+∞)。演示默认每日预算分别为900/1100/1300/1500/1700/1900日元。
5. 本次明确预算优先于档案预算，档案预算优先于收入策略；低预算不会降低过敏约束。价格是每100g可食状态的模拟食用成本，不是购物小票或采购预算。
6. 在聊天中输入“预算900日元安排一天三餐”；输入“推荐几部电影”应得到当前饮食助手覆盖范围的说明，并提示可继续询问的饮食问题。无法返回结果时应同时显示具体原因与下一步。历史页面可换一道菜并重算全天。
7. diet050 已写入40岁、无已知过敏的合成演示档案和测试方案。diet044–diet048有无关聊天压力检查记录，其他账户可从空档案开始。

## 启停

```bash
cd /home/aitd/hypertension-diet
backend/.venv/bin/python -m scripts.service start
backend/.venv/bin/python -m scripts.service status
backend/.venv/bin/python -m scripts.service restart
backend/.venv/bin/python -m scripts.service stop
```

API与worker是脱离终端的进程，PID与日志位于 `data/runtime/`。关闭终端不会主动结束它们；当前未安装开机自启或崩溃自动拉起服务。重启机器后需运行start。脚本只管理自身PID，不会杀死占用8000的其他程序；端口冲突查看api.log。

worker通过PostgreSQL会话锁限制为一个实例，所有模型任务排队。运行任务租约10分钟；进程异常后过期任务最多再认领一次，超过上限明确失败。取消后不再发布该任务结果；已经开始的Ollama推理可能仍占资源直到请求结束。

### CUDA 故障恢复（2026-10-11）

本机 GB10 / Ollama 0.40.0 / `qwen3.6:35b-a3b` 在带会话历史的请求中复现
`CUDA error: an illegal memory access was encountered`（模型接口 HTTP 500）。
模型列表接口正常或短提示成功不足以证明聊天恢复；需要测试真实会话历史。

生成请求现在默认使用 `num_batch=64`，可通过 `backend/.env` 的
`LLM_NUM_BATCH` 设置正整数，修改后重启 API/worker。这是经过本机验证的应用侧规避，
尚未定位到上游具体 CUDA 内核或驱动缺陷，不代表已经修复驱动。
遇到 CUDA 5xx 时先通过 Ollama API 卸载当前生成模型（`keep_alive=0`），
再重试一次；持续失败明确终止，不绕过意图分类或营养校验。
其他临时 HTTP 错误最多重试一次，404 等配置错误不重试。
日志记录模型、次数、状态码与错误类别，不记录提示词或上游响应正文。
卸载接口依据 Ollama 官方 FAQ：https://docs.ollama.com/faq#how-do-i-keep-a-model-loaded-in-memory-or-make-it-unload-immediately

同时修正了分类提示：历史助手的“请完善资料”不等于当前资料仍未完成，
资料是否完整由后端检查当前档案。健康和过敏限制继续生效。
修复验收见 `docs/evaluation/cuda-recovery.json`：原会话经真实 HTTP 提交、
worker 执行、历史回读返回 ready 和三餐；隔离库自动化测试 34 项通过，
知识问答也验证了 embedding→生成模型的切换。

### 菜单解释与来源

异步生成三餐、聊天生成三餐及换餐会先完成独立数值校验，再用最多60秒获取知识库说明。
检索在排名之前限定 `guideline_commentary` 和 `dietary_reference_intakes` 类型，
不把糖尿病章节或隔离的肾病文档用于普通成人菜单解释。
后端从原文提取定性句子并排除显式特殊人群句子，模型只能选择候选句子ID和生成翻译；
输出再次核对引用ID、原句匹配、餐次及数字限制。此检查不等于医学支持性或翻译质量审核。

`knowledge_explanation.status` 为 `ready`、`no_evidence` 或 `unavailable`，
`claims` 保存翻译、原句、引用片段ID和对应餐次，顶层 `evidence` 保存引用原文快照与文献页码。
这些字段和菜单一起保存到任务、推荐历史和聊天记录。模型不得覆盖配方、营养计算或预算。
无依据或超时仍保留已通过校验的菜单，前端明确显示知识库说明缺失。
旧历史记录不会被回填成仿佛当时已有引用；其数值筛选理由可显示，知识库部分提示重新提交。

页面“为什么这样推荐”依据历史中的目标、预算、档案和计算快照显示；
“知识库依据”可点击引用编号直接展开文献原文；
“营养与菜谱出处”可展开每种配料的Excel工作表、行号和营养素单元格。
临床原则来源、成分表数值、自建菜谱模板和模拟价格分别标注。
不要把查到一段原文说成指南直接制定了这份菜单，也不要把表值估算说成实测。

`/api/health`仅表示API存活；登录后的 `/api/readiness`检查数据库与模型列表，不代表模型推理速度。`/docs`为登录保护的接口测试页；`/api/openapi.json`为完整契约。旧通用 `/api/chat` 与 `/api/embed` 已关闭（鉴权后410）。

数据库5433与Ollama11434当前均只绑定127.0.0.1。其他设备通过 Spark 当前 IP 的8000端口访问 Web，无需开放数据库或模型端口。局域网 HTTP 不加密传输，HTTPS反向代理和Secure Cookie尚未配置。IP查询、访问方法和防火墙排查详见根目录 README 第3节；跨设备访问还需所在网络允许互访。

## 重建应用层

需要已有食品/知识库数据和Ollama模型。空数据库应先按已有 backend/README.md 的导入流程恢复数据，不能仅运行seed得到知识库。

```bash
python3 -m venv backend/.venv
backend/.venv/bin/python -m pip install -r backend/requirements.lock.txt
# 按 backend/.env.example 配置迁移账号、Ollama和模型，不使用示例密码。
backend/.venv/bin/python -m backend.app.setup
backend/.venv/bin/python -m backend.app.seed
bash scripts/build_frontend.sh
backend/.venv/bin/python -m scripts.service start
```

本机Node22.23.3位于 `.tools/node/current/bin`；build脚本优先使用它，其他机器需准备与当前前端依赖兼容的Node。前端使用package-lock锁定依赖；后端requirements.lock锁定当前环境。迁移按文件名和SHA256执行，已执行迁移不可改写，应新增SQL文件。重复setup不会覆盖已存在账户密码；运行账号diet_web与原导入/迁移账号分离，食品基础表保持只读，菜谱和知识库管理在后端权限检查后使用对应写入权限。

## 账号维护

```bash
backend/.venv/bin/python -m scripts.manage_accounts disable diet001
backend/.venv/bin/python -m scripts.manage_accounts enable diet001
backend/.venv/bin/python -m scripts.manage_accounts reset-password diet001
```

命令行重置密码写入 `data/private/password-resets.csv`（0600），不在终端打印；初始密码表不会反映后来改密。维护命令撤销已有会话。没有公开自助注册；管理员可以通过用户管理页面创建账号及重置密码。网页生成的密码按页面提示保存，不写入上述命令行重置记录。

## 备份与恢复

```bash
backend/.venv/bin/python -m scripts.backup_database
backend/.venv/bin/python -m scripts.verify_restore
```

前者生成完整custom格式dump和SHA256清单。后者把最新完整dump恢复到新建 `diet_verify_<时间戳>` 数据库，并比较食品/成分/片段/账号/菜谱计数；不会覆盖演示库。完整恢复已实际通过，见evaluation/restore.json。验证库含密码哈希及演示数据，仍属于私有备份资料。备份不包括PostgreSQL集群角色：迁移到新主机时需重新建立角色/授权；原始文件、backend/.env、backend/app.env和账号文件也须单独安全备份。

恢复演示库之前必须停止API与worker，保留当前完整备份，并明确目标数据库。不要将测试库恢复命令直接改写为生产库名字后盲目执行。

## 验证

```bash
backend/.venv/bin/python -m scripts.test_application
backend/.venv/bin/python -m scripts.evaluate_demo
# 以下在frontend目录运行，使用合成演示账号；会产生测试聊天与方案记录。
PATH="$PWD/../.tools/node/current/bin:$PATH" node browser-check.mjs
PATH="$PWD/../.tools/node/current/bin:$PATH" node browser-flow.mjs
```

集成测试强制使用 `diet_restore_check`，会清空该测试库的应用账号及关联数据，绝不使用演示库。该库已从原始完整备份恢复；在新机器需先建立同名隔离测试库并恢复基础食品/知识数据。普通 `python -m unittest discover -s backend/tests` 未配置测试库时会跳过应用集成测试，不能把跳过当通过。

浏览器测试需要frontend开发依赖及Chromium：`npx playwright install chromium`。本机已安装。模型冻结评测脚本仅读取演示库，不修改长期档案。性能检查脚本会向指定合成账号写入无关聊天。
