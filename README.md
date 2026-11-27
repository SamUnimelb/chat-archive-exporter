# Chat Archive Exporter

[![lint](https://github.com/SamUnimelb/chat-archive-exporter/actions/workflows/lint.yml/badge.svg)](https://github.com/SamUnimelb/chat-archive-exporter/actions/workflows/lint.yml)

把「某国内绿色类 WhatsChat 聊天软件」（桌面版 4.x）中与指定联系人的聊天记录，导出为可长期保存的 **HTML / PDF / 纯文本 / 中英对照 **。

> 仅限导出**本人账号**、且**已取得对话对方同意**的聊天记录。使用前请阅读文末《免责声明与使用限制》。

## 功能

- **数据库解密**：在你自行提供密钥的前提下，解密 SQLCipher 4 数据库（本项目不含密钥提取代码）
- **消息解析**：文本、图片、语音（时长）、视频（时长与文件名）、文件（仅文件名）、表情、引用、链接、小程序、转账、红包、位置、名片、系统消息（可选）
- **图片还原**：V2 `.dat` 解密，优先原图，缺失时回退缩略图
- **多种导出**
  - 完整聊天：HTML + PDF（聊天气泡版式，保留时间与顺序）
  - 精简版 PDF：窄气泡，约 25–30 条/页
  - 纯文字 PDF / TXT：按日期排列，媒体只保留文件名、时长与大小
  - 第三方信息自动打码 + 中英机器对照
  - 关系时间线：关键词启发式提取关键节点 + 每月摘要
- **归档整理**：按月 / 按日拆分 PDF，图片按月归类并以 `IMG_yyyy_mm_dd_hh_mm_ss` 命名

## 环境要求

- Windows 10 / 11
- Python 3.11+
- Microsoft Edge 或 Google Chrome（用于无头打印 PDF）
- 可选：`argostranslate`（仅中英对照功能需要）

## 安装

```bat
python -m pip install -r requirements.txt
:: 可选：中英对照
python -m pip install argostranslate
```

## 配置

```bat
copy config.example.json config.json
```

然后填写 `config.json`：

- `account`：本人与对方的账号标识、显示名
- `paths`：本机数据目录（`db_storage`、`msg/attach`、`msg/video`）
- `crypto.image_code` / `image_xor`：图片 `.dat` 解密参数（可从本机配置或公开资料推导）
- `crypto.db_keys_file`：数据库密钥文件路径（默认 `output/keys.json`）

`config.json` 已被 `.gitignore` 忽略，不会被提交。

## 获取数据库密钥（需自行完成）

本项目**不提供**任何内存读取、进程注入或密钥提取代码。你需要在**自己完全拥有和控制的设备**上、针对**本人账号**，自行使用 Frida 等工具获取数据库密钥，并按 `src/crypto.py` 的读取逻辑准备 `output/keys.json`。建议把整个项目文件和这条需求整体丢给AI处理，或者你足够大神的话自己处理一下，但这部分请恕我真的因考虑到各种风险没法开源。

> 该步骤可能违反目标软件的服务条款，并受当地反规避、计算机犯罪与隐私法律约束。请自行评估风险，并确保已获得对话对方的同意。

## 使用

```bat
python src/main.py                 :: 完整聊天记录（HTML + PDF）
python src/export_data.py          :: 生成统一数据集（其余导出脚本的前置）
python src/export_compact.py       :: 精简版
python src/export_text.py          :: 纯文字版
python src/export_bilingual.py     :: 打码 + 中英对照
python src/export_timeline.py      :: 关系时间线
python src/split_daily.py          :: 拆分为每日 PDF
python src/export_translations.py  :: 中英对照按月/按日拆分
```

生成结果位于 `output/`，对外使用的成品集中放在 `output/最终结果/`（脚本默认布局，可按需修改）。

## 演示数据

仓库自带一份**完全合成**的演示数据，不包含任何真实聊天内容：

```bat
python src/export_demo.py
```

生成 `demo/demo.html` 与 `demo/demo.pdf`，可直接预览导出效果。

演示对话、昵称、图片均为程序生成的占位内容。

## 目录结构

```
config.example.json        配置模板
src/crypto.py              SQLCipher 4 解密、WAL 重放、V2 图片解密
src/messages.py            消息解析与字段归一化
src/export_data.py         统一数据集（图片尺寸、文件大小、表情文案等）
src/main.py                完整聊天导出
src/export_compact.py      精简版
src/export_text.py         纯文字版
src/redact.py              第三方信息打码
src/export_bilingual.py    中英对照
src/export_timeline.py     关系时间线
src/split_daily.py         每日拆分
src/export_translations.py 中英对照按月/按日拆分
src/export_demo.py         合成数据演示
assets/                    Jinja2 模板
demo/                      合成演示数据与图片
```

## 隐私与安全

- 导出的聊天记录、图片、密钥均为高度敏感的个人信息，请仅保存在本机，并自行加密备份
- 不要将 `output/`、`config.json`、密钥文件、数据库文件提交到本仓库或任何公开平台
- 仓库中的演示数据全部为合成内容

## 免责声明与使用限制 / Disclaimer

**用途限制**：本项目仅用于导出**你自己账号**中、且**已取得对话对方同意**的聊天记录，供个人备份、纪念或合法的签证/诉讼材料整理使用。严禁用于未经授权的监控、窃取、窥探他人隐私、跟踪、骚扰、敲诈或其他违法用途。

**合规责任**：未经法律或道德风险评估的情况下，使用或分发本工具可能涉及计算机犯罪、技术措施规避、隐私与数据保护、著作权以及平台服务条款等法律问题，各地规定差异很大（例如澳大利亚《版权法》第 116AN–116AP 条、美国 DMCA §1201、中国《刑法》第 285 条与《个人信息保护法》、欧盟 GDPR 等）。**是否合法取决于你所在的司法辖区、数据来源和使用方式；使用前请自行核实并咨询当地执业律师。** 因使用、分发或无法使用本工具产生的一切后果，由使用者自行承担。

**第三方与平台**：本项目与目标软件的权利人无任何关联，未获其授权或认可。读取本地数据、解密数据库等行为可能违反其服务条款，可能导致账号被限制或封禁。

**数据安全**：本仓库不包含任何真实聊天记录、图片、数据库、密钥或个人信息。请勿将他人的聊天内容、密钥、数据库文件提交到本仓库或任何公开平台。

**无担保**：本软件按“原样”（AS IS）提供，不附带任何明示或默示担保，包括但不限于适销性、特定用途适用性与不侵权担保。作者与贡献者不对数据丢失、账号封禁、法律纠纷或任何直接、间接、附带损失承担责任。

**非法律意见**：以上内容仅为一般性风险提示，不构成法律意见。

**English summary**: This project is intended only for exporting **your own** chat history with the **consent** of the other party, for personal backup, memento, or lawful evidence preparation. Do not use it for surveillance, stalking, or accessing anyone else's data without authorization. Decrypting local data may violate anti-circumvention and computer-misuse laws (e.g., Australia's Copyright Act ss 116AN–116AP, US DMCA §1201, PRC Criminal Law Art. 285), privacy laws, and the target application's Terms of Service; legality depends on your jurisdiction — consult a qualified lawyer. This project is not affiliated with or endorsed by the application vendor. The software is provided "AS IS", without warranty of any kind; the authors accept no liability for any use or misuse. Nothing here is legal advice.

## 第三方组件

第三方组件与参考资料 / Third-Party Notices
本项目采用 MIT 许可证（见 LICENSE）。运行时依赖以下第三方组件，其版权归各自作者所有，使用时请遵守各自许可证：

组件	用途	许可证
PyCryptodome	AES / HMAC / PBKDF2	BSD 2-Clause
cryptography	补充密码学原语	Apache-2.0 / BSD
lxml	XML 解析	BSD
Jinja2	模板渲染	BSD 3-Clause
Pillow	图片处理	HPND / BSD-style
zstandard	zstd 解压	BSD 3-Clause
pypdf	PDF 合并与校验	BSD 3-Clause
Argos Translate（可选）	离线机器翻译	MIT
CTranslate2（可选）	Argos 推理后端	MIT

## 参考资料
实现过程中参考了以下公开项目与资料的设计思路（未包含其源代码）：

tzwkb/wechat-decrypt — 本地数据库解密思路
LC044/WeChatMsg — 聊天记录解析与导出的工程实践
sjzar/chatlog — 聊天记录索引与导出
SQLCipher 公开文档 — 页格式与 KDF 参数
如你在此基础上继续分发，请自行核实并保留相应项目的版权与许可声明。

## 许可证

[MIT](LICENSE)
