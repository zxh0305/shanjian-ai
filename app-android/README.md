# 闪剪 AI · Android 客户端（W8 起步）

技术栈定稿：Kotlin + Jetpack Compose + Navigation + Coil + Media3 ExoPlayer + OkHttp/Retrofit；
兜底导出用 Media3 Transformer（1080P、无转场/仅叠化）。

对应 5 页原型：首页·素材导入 / AI 分析与音乐匹配 / 成片预览 / 手动编辑器（轻编辑）/ 导出与分享。

服务端地址在设置页手填（如 `http://192.168.x.x:8600`），W11 后 mDNS 自动发现。
在服务端完成 W5–W7 之前，可先按 `docs/EDL-spec.md` 与服务端 Swagger（`/docs`）的契约开发 UI。
