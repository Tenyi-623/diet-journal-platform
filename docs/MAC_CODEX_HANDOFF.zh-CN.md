# 给 Mac Codex 的 iOS 开发交接说明

更新时间：2026-10-19

项目仓库：<https://github.com/Tenyi-623/diet-journal-platform>

请在 Mac 上打开本仓库，并依照本文准备、运行和验证「食日记」iOS 客户端。本文是开发任务说明，不包含账号密码、令牌或其他凭据。

## 已确认的目标

- 用于毕业设计和内部真机演示，不做公开商店发布。
- 客户端使用 Expo / React Native，同时支持 Android 和 iOS；Mac 用于本地 Xcode/iOS 开发，代码通过 GitHub 同步。
- 复用现有 FastAPI 服务和预创建演示账户；不增加注册入口，不让手机直接访问 PostgreSQL 或 Ollama。
- 演示阶段暂时使用可信局域网内的 HTTP。此通道只适合合成演示账号和数据；真实用户数据或公开访问前必须改为 HTTPS。
- 首版页面范围和业务行为以 [`docs/superpowers/specs/2026-10-13-mobile-app-design.md`](superpowers/specs/2026-10-13-mobile-app-design.md) 为准；如与较早的路线图文字冲突，以用户后来确认的要求和当前代码为准。

## 仓库和客户端现状

- GitHub 正式仓库：`https://github.com/Tenyi-623/diet-journal-platform.git`。
- 本交接文件编写时，工作区干净，`main` 与 `origin/main` 一致，基线提交为 `d97674a`；同步本文后仓库 HEAD 会包含本文件提交。
- 移动端位于 `mobile/`，使用 Expo SDK `~57.0.28`、React Native `0.86.3`，依赖锁文件为 `mobile/package-lock.json`。
- 页面和业务代码位于 `mobile/src/`；`mobile/app.json` 中的 iOS Bundle ID 为 `jp.aitd.dietjournal`。
- 项目采用 Expo Continuous Native Generation（CNG）。`mobile/ios/` 和 `mobile/android/` 被忽略，由 Expo 本机生成。初期请继续维护 `app.json`、配置插件和 JS/TS 源码，不要把生成目录提交，也不要直接在生成目录里做长期修改。若确实需要原生 Swift 工程长期维护，先向用户说明 CNG 与提交原生目录的维护取舍，再调整架构。
- `mobile/eas.json` 目前只有 Android 内部 `preview` APK 配置，没有 iOS EAS 构建配置；本任务优先验证 Mac 本地 Xcode 模拟器/设备流程，不要假设已有 TestFlight 构建能力。
- 当前 API 客户端默认要求 HTTPS。临时局域网 HTTP 开关只覆盖 Android 预览；`mobile/app.json` 的 iOS ATS 当前禁止任意明文请求。因此 iOS 目前不能直接使用 Android 的 HTTP 演示配置。
- `mobile/eas.json` 中现存的演示 API 地址只是旧配置值。开发前必须验证 Mac 当前网络下配置地址是否仍是正确且可达的服务地址，不能把它当作已保证在线的地址。
- 移动端 README 记录后端 API 当前停止。服务状态会变化；请在 Mac 上实际检查，不要据此假定服务仍停止或已经运行。

## 执行步骤

### 1. 在 Mac 同步并检查项目

```bash
git clone https://github.com/Tenyi-623/diet-journal-platform.git
cd diet-journal-platform
git status --short --branch
git log -1 --oneline
```

若仓库已克隆，先 `git fetch origin` 并检查工作区，再基于 `origin/main` 开始。保留用户本地改动；不要用 `reset --hard`、`clean -fd` 等命令清理。开始前阅读 `mobile/AGENTS.md`、`mobile/README.zh-CN.md`、本文和移动端设计说明。

开发改动请放在独立分支，例如 `codex/ios-local-build`，不要直接把实现提交到 `main`。不要更改 GitHub 仓库名或 `origin`。

### 2. 检查 Mac 构建环境并建立基线

先确认 Xcode、iOS Simulator、Xcode Command Line Tools、Node.js/npm 可用；按仓库锁文件使用 npm：

```bash
cd mobile
npm ci
npx expo-doctor
npm test -- --runInBand
npm run lint
npm run typecheck
```

遵守 `mobile/AGENTS.md`：当前 Expo 主版本为 57。任何 Expo、EAS、React Native 或 iOS 原生配置改动前，先查阅 Expo SDK 57 对应官方文档和 Apple ATS 文档，不要依赖过时记忆。记录原有失败，区分环境问题和代码回归。

### 3. 安全地支持 iOS 局域网演示 API

先查清 FastAPI 实际监听地址、Mac 与服务端的网络连通性和真实健康检查路径；使用合成演示账号。不要假设服务自动运行，也不要为了客户端构建擅自启动整套后端、worker、数据库或 Ollama。

若确认 iOS 必须在局域网 HTTP 下演示，再实现范围有限的开发/内部预览配置：

- 默认和正式配置仍强制 HTTPS；不开启全局 `NSAllowsArbitraryLoads`。
- HTTP 只允许明确启用的开发或内部演示构建连接 RFC1918 私有 IPv4 地址；拒绝公网 IP、localhost、格式错误地址和未启用开关的请求。
- 通过 Expo 配置或配置插件生成所需 ATS 设置，避免把手工修改写进生成的 `ios/` 目录；只对必要的局域网目标放行。
- 保持 Android 现有策略不回退；新增单元测试覆盖 iOS 开发配置允许私有局域网 HTTP、正式配置拒绝 HTTP、HTTPS 正常、非私有地址拒绝等分支。
- 将本机 API 地址放在未跟踪的本地环境文件或安全的构建环境变量中；不要提交私人网络地址、密码或令牌。不要把演示凭据写进测试快照、日志或 Git。

如果 ATS 无法按目标范围可靠限制，优先停在 HTTPS 配置或向用户报告阻塞点，不要用全局明文例外绕过平台安全策略。

### 4. 构建并运行 iOS 模拟器

确认环境变量已指向 Mac 可访问的 API 后，在 `mobile/` 运行：

```bash
npx expo run:ios
```

允许 Expo 在本机生成被 Git 忽略的 `ios/` 工程。先验证模拟器能编译、启动和显示登录页；API 未就绪时如实记录集成阻塞，不用假数据伪装服务端结果。

### 5. 完成首版关键流程回归

在模拟器以及可用时的 iPhone 上，用合成演示账户验证：登录/退出、今日菜谱及图片、用户档案（包括日元个人税前年收入档次和预算）、饮食聊天、非饮食问题的固定拒答、推荐历史和菜谱详情。特别检查：

- 图片地址可由 iOS 设备访问，加载失败时有明确占位展示。
- API 网络断开、服务不可达、401、空档案或未确认过敏信息时，不展示伪造的个性化推荐。
- 应用切到后台再回来、键盘弹出、窄屏布局时页面仍可操作。
- HTTP 仅在显式开启的内部演示配置中工作；发布配置仍拒绝 HTTP。

如需后端协助，先查阅仓库运行手册并向用户报告需要启动的服务和原因；不得绕过项目服务管理方式。

### 6. 验证、交付和同步

完成后重新运行受影响测试，以及：

```bash
npx expo-doctor
npm test -- --runInBand
npm run lint
npm run typecheck
git diff --check
git status --short --branch
```

提交前检查没有加入 `.env*`（示例文件除外）、凭据、令牌、真实健康资料、`ios/` / `android/` 生成目录、构建产物或 APK。通过 GitHub 分支提交实现，并向用户报告：iOS 模拟器/真机验证结果、测试结果、需要用户提供的外部条件、提交链接和已知限制。

## 发行边界

- 当前目标是本机开发和内部真机演示，不是 App Store 上架。
- 先完成模拟器开发；如果要给 iPhone 安装，检查 Xcode 当前签名方式和 Apple 账号条件，并准确说明免费 Personal Team 与付费 Apple Developer Program 在有效期、设备分发、TestFlight 上的区别。不要承诺免费签名可替代 TestFlight 或长期发行。
- 不创建或发布 EAS iOS 构建，除非确认账户、签名和分发方式都已具备，并且用户明确要做该发行步骤。
- 真实用户数据或跨公网访问前，必须先提供并验证 HTTPS；局域网 HTTP 仅限合成数据的短期演示。
