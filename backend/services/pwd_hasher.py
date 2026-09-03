# services/pwd_hasher.py —— 密码哈希（sha256 前置 + bcrypt）
# 说明：bcrypt 原生密码上限 72 字节，且新版 bcrypt 与 passlib 存在兼容问题。
#       我们先用 sha256 把密码哈希成 32 字节，再 hex 编码为 64 字节字符串，
#       然后交给 bcrypt 处理，既规避 72 字节上限，也避开 passlib 的坑。

from __future__ import annotations

import base64
import hashlib

import bcrypt


def _pre_hash(pw: str) -> bytes:
    # sha256 -> 64 字符 hex 字符串，编码为 bytes，保证 bcrypt 输入稳定为 64 字节
    return hashlib.sha256(pw.encode("utf-8")).hexdigest().encode("ascii")


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_pre_hash(password), bcrypt.gensalt(rounds=12)).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(_pre_hash(password), password_hash.encode("utf-8"))
    except ValueError:
        return False
    except Exception:
        return False
