# 获取并导入数据库密钥

本项目**不包含**任何内存读取、进程注入或密钥提取代码。数据库密钥需要你在**自己完全拥有和控制的设备**上、针对**本人账号**自行获取（例如使用 Frida 等通用调试工具，或使用你信任的社区方案）。

> 该步骤可能违反目标软件的服务条款，并受反规避、计算机犯罪与隐私法律的约束。请自行评估风险，并确保已取得对话对方的同意。本说明不构成对任何获取方式合法性或安全性的背书。

## 1. 密钥文件格式

将密钥保存为 JSON 文件（默认路径 `output/keys.json`）：

```json
{
  "message_0": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
  "message_1": "fedcba9876543210fedcba9876543210fedcba9876543210fedcba9876543210"
}
```

- 键名：数据库文件名去掉 `.db`（例如 `message_0.db` → `message_0`）
- 值：64 个十六进制字符（32 字节）的原始密钥
- 文件权限建议设为仅本人可读

## 2. 校验密钥

在导出前先校验，避免用错密钥产生空结果：

```bat
python src/import_key.py --keys output/keys.json
```

只做格式检查；如果要验证密钥是否正确：

```bat
python src/import_key.py --keys output/keys.json --db-dir "D:\path\to\db_storage"
```

输出示例：

```
format OK: 2 key(s)
OK   D:\path\to\db_storage\message\message_0.db
OK   D:\path\to\db_storage\message\message_1.db
verified: 2 ok, 0 failed, 0 skipped
```

`import_key.py` 只读取本地数据库文件，做一次 PBKDF2-HMAC-SHA512 + AES 校验，**不会访问任何运行中的进程**，也不需要管理员权限。

## 3. 常见问题

- `FAIL`：密钥不匹配，或该库使用了不同的 KDF 参数；请确认密钥来源与目标数据库版本。
- `SKIP`：该数据库没有对应的密钥条目，属于正常情况（不是所有库都需要导出）。
- 密钥属于高度敏感信息：不要提交到 Git、不要上传网盘、不要发给第三方。
