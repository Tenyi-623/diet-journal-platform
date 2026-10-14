# 食日记 Android / iOS 客户端

这是现有 FastAPI 饮食推荐系统的 Expo / React Native 普通用户客户端。首个交付目标是内部 Android APK；管理功能仍由网页后台提供。

## 本地运行

1. 复制 `.env.example` 为 `.env.local`。
2. 将 `EXPO_PUBLIC_API_URL` 设置为手机可以访问的 HTTPS 服务地址。可以填写域名根地址或以 `/api` 结尾的地址，客户端会自动补齐 API 路径。
3. 执行 `npm install`，再执行 `npm start`。

内部 Android 演示 APK 的 `preview` 配置临时使用 `http://192.168.1.86:8000`。Android 只对该 API 的私有 IPv4 主机放行 HTTP，其他主机仍默认拒绝明文流量；客户端也会拒绝非 RFC1918 IPv4 的 HTTP 地址。若开发机的局域网地址变化，请更新 `eas.json` 的 `EXPO_PUBLIC_API_URL` 并重新构建。此 HTTP 通道会明文传输账号、健康档案和会话令牌，只使用合成演示账号和可信局域网；有真实数据或公开发布前必须切换为 HTTPS。

## 检查

```sh
npm test
npm run typecheck
npm run lint
npx expo-doctor
```

## 构建内部 Android APK

此开发机没有 Android SDK，使用 Expo EAS 云构建。后端 API 需运行在开发机 `:8000`，手机和开发机需处于允许互访的同一局域网：

```sh
npx eas-cli@latest login
npx eas-cli@latest build:configure
npm run build:apk
```

构建配置使用 `preview` 环境变量和内部 APK。首次构建时 EAS 会请求创建/选择 Expo 项目和 Android 签名密钥。内部构建下载链接只分享给演示者。

## 认证与后端

- 不提供注册入口；用户通过现有演示账号登录。
- `POST /api/auth/mobile/login` 返回 12 小时 Bearer 会话，移动端只把令牌保存在系统安全存储中。
- 其他接口使用 `Authorization: Bearer ...`。网页继续使用原有 HttpOnly Cookie 和 CSRF 校验。
- 后端仍负责账户授权、个人数据隔离、任务队列和推荐验证。聊天非饮食问题的答复由后端固定为 `无法回答与饮食无关的内容`。
- 修改密码会撤销所有会话；退出登录会撤销服务端会话并清除本地令牌。

## 服务端就绪条件

当前演示 API 为局域网 HTTP `:8000`；手机需连接同一允许互访的 Wi-Fi，数据库和 Ollama 不应直接暴露给手机。服务端目前处于停止状态，安装 APK 演示前需按项目根目录运行手册启动后端 API 和推荐 worker。正式发布前需提供手机可访问的 HTTPS 入口，并移除 preview HTTP 配置。
