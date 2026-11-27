# 第三方组件与参考资料 / Third-Party Notices

本项目采用 MIT 许可证（见 `LICENSE`）。运行时依赖以下第三方组件，其版权归各自作者所有，使用时请遵守各自许可证：

| 组件 | 用途 | 许可证 |
| --- | --- | --- |
| PyCryptodome | AES / HMAC / PBKDF2 | BSD 2-Clause |
| cryptography | 补充密码学原语 | Apache-2.0 / BSD |
| lxml | XML 解析 | BSD |
| Jinja2 | 模板渲染 | BSD 3-Clause |
| Pillow | 图片处理 | HPND / BSD-style |
| zstandard | zstd 解压 | BSD 3-Clause |
| pypdf | PDF 合并与校验 | BSD 3-Clause |
| Argos Translate（可选） | 离线机器翻译 | MIT |
| CTranslate2（可选） | Argos 推理后端 | MIT |

## 参考资料

实现过程中参考了以下公开项目与资料的设计思路（未包含其源代码）：

- `tzwkb/wechat-decrypt` — 本地数据库解密思路
- `LC044/WeChatMsg` — 聊天记录解析与导出的工程实践
- `sjzar/chatlog` — 聊天记录索引与导出
- SQLCipher 公开文档 — 页格式与 KDF 参数

如你在此基础上继续分发，请自行核实并保留相应项目的版权与许可声明。
