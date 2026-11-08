# s8u6l2 学它的原因很直接：一旦隐私设计出错，代价通常不是“功能 / 合规（Compliance）不是“写完代码再补的文档”，

> 来源 `content/lessons/s8u6l2.json`

## arch.sec.data_privacy

## 一句话直觉

**数据隐私（Data Privacy）** 要解决的核心问题是：**系统在处理个人数据时，如何保证数据只被该看的人、在该用的场景、以可解释的方式使用。** 对 AI 系统而言，这不仅是合规要求，更直接影响模型训练、推理、日志、缓存、第三方调用等每个环节。

学它的原因很直接：一旦隐私设计出错，代价通常不是“功能 bug”，而是**法律罚款、用户信任崩塌、模型下架、数据泄露事故**。

---

## 1. 隐私的第一性原理：数据最小化与目的限制

隐私工程（Privacy Engineering）里最基础的两个原则是：

- **数据最小化（Data Minimization）**：只收集、存储、处理完成当前目的所必需的数据。
- **目的限制（Purpose Limitation）**：数据只能用于收集时明确告知的目的，不能“顺手”拿去训练、分析、出售。

在工程上，这意味着：

- 能用聚合数据，就不要用原始明细；
- 能本地计算，就不要上传原始数据；
- 能短期保留，就不要永久存储；
- 能匿名化，就不要保留可识别字段。

**关键结论**：隐私不是“加个勾选框”，而是数据流每一跳都要问：**这个字段真的需要吗？**

```python
# 示例：最小化用户画像字段
# 不推荐：收集完整生日、精确地址、手机号
raw_user = {
    "name": "张三",
    "birthday": "1990-05-12",
    "address": "北京市朝阳区某小区3号楼",
    "phone": "13800000000",
    "age": 34,
}

# 推荐：只保留当前推荐场景需要的粗粒度特征
minimized_user = {
    "age_bucket": "30-39",
    "city_tier": "一线城市",
}

print(minimized_user)
```

---

## 2. 匿名化、假名化与去标识化：别把“改名”当“匿名”

这三个词经常被混淆：

- **匿名化（Anonymization）**：处理后无法再识别到个人，通常不可逆。
- **假名化（Pseudonymization）**：用代号替换直接标识符，但通过额外信息仍可还原。
- **去标识化（De-identification）**：移除或模糊标识符，但可能通过组合字段重新识别。

**关键结论**：假名化不等于匿名化。只要还存在可关联的辅助数据，就可能被**重识别（Re-identification）**。

例如：邮编 + 生日 + 性别，在很多地区足以唯一锁定一个人。

```python
# 示例：假名化并不等于匿名化
import hashlib

user_id = "user_12345"

# 假名化：稳定映射，便于关联，但仍可被字典攻击或交叉比对
pseudonym = hashlib.sha256(user_id.encode()).hexdigest()[:12]
print("pseudonym:", pseudonym)

# 如果攻击者知道 user_12345 的哈希规则，仍可反推
known = "user_12345"
print("match:", hashlib.sha256(known.encode()).hexdigest()[:12] == pseudonym)
```

---

## 3. 差分隐私：让“统计结果”不泄露个体

**差分隐私（Differential Privacy, DP）** 是目前最严格的隐私数学框架之一。它的直觉是：

> 无论某个人的数据在不在数据集里，查询结果的分布几乎一样。

这样攻击者无法通过对比查询结果，判断某个人是否在数据中。

常见做法是给统计结果加噪声，例如拉普拉斯机制（Laplace Mechanism）。

**关键结论**：差分隐私保护的是“个体是否参与”的信息，而不是简单删掉姓名。

```python
# 示例：拉普拉斯机制做差分隐私计数
import numpy as np

def laplace_mechanism(true_value: float, sensitivity: float, epsilon: float) -> float:
    """
    true_value: 真实统计值
    sensitivity: 单个个体对结果的最大影响
    epsilon: 隐私预算，越小越隐私，噪声越大
    """
    scale = sensitivity / epsilon
    noise = np.random.laplace(0, scale)
    return true_value + noise

# 真实有 1000 个用户患病
print(laplace_mechanism(1000, 1, 0.1))
print(laplace_mechanism(1000, 1, 1.0))
```

---

## 4. AI 系统里的隐私风险点

AI 系统常见的隐私风险不只是“数据库被拖库”，还包括：

- **训练数据记忆（Memorization）**：模型可能记住训练集中的敏感样本。
- **成员推断攻击（Membership Inference）**：判断某条数据是否参与训练。
- **模型反演（Model Inversion）**：从模型输出反推输入特征。
- **提示词泄露（Prompt Leakage）**：LLM 可能泄露系统提示或上下文中的隐私。
- **第三方 API 调用**：把原始用户数据发给外部模型服务。

**关键结论**：AI 隐私必须覆盖**训练、推理、日志、缓存、评估、第三方调用**全链路。

```python
# 示例：推理前做敏感信息过滤，避免把隐私直接送给第三方
import re

def redact_pii(text: str) -> str:
    # 简单示例：遮盖手机号和邮箱
    text = re.sub(r"1[3-9]\d{9}", "[PHONE]", text)
    text = re.sub(r"[\w.-]+@[\w.-]+\.\w+", "[EMAIL]", text)
    return text

prompt = "请联系张三，手机13800000000，邮箱zhangsan@example.com"
print(redact_pii(prompt))
```

---

## 5. 工程落地：把隐私做成默认能力

隐私不能靠“记得处理”，要变成系统能力：

- **数据分类分级**：哪些是 PII（Personally Identifiable Information，个人可识别信息）、哪些是敏感数据。
- **访问控制**：最小权限、按需授权、审计日志。
- **加密**：传输加密、存储加密、密钥管理。
- **脱敏与合成数据**：测试环境不用真实数据。
- **保留与删除策略**：到期删除、被遗忘权。
- **隐私影响评估（PIA / DPIA）**：上线前评估风险。

**关键结论**：隐私工程的目标不是“零数据”，而是**在可用性和隐私之间做可验证的权衡**。

```python
# 示例：一个简单的隐私检查清单函数
def privacy_checklist(features: dict) -> list:
    issues = []
    pii_fields = {"name", "phone", "email", "address", "id_card"}
    for field in features:
        if field in pii_fields:
            issues.append(f"发现直接标识符: {field}")
    if "birthday" in features and "zipcode" in features:
        issues.append("生日+邮编可能重识别")
    return issues

sample = {"name": "张三", "birthday": "1990-05-12", "zipcode": "100020"}
print(privacy_checklist(sample))
```

---

## 动手练习

**任务：实现一个“隐私友好的用户行为日志管道”**

要求：

1. 输入一条原始日志，包含 `user_id`、`phone`、`email`、`event`、`timestamp`、`ip`。
2. 输出一条可写入分析系统的日志：
   - 移除或哈希 `user_id`；
   - 遮盖 `phone`、`email`；
   - `ip` 只保留前两段；
   - 保留 `event` 和按小时取整的 `timestamp`。
3. 写一个函数 `sanitize_log(log: dict) -> dict`。
4. 额外写一个 `check_reidentification_risk(log: dict) -> list`，提示是否存在重识别风险字段组合。
5. 用 3 条不同日志测试，并打印结果。

**提交形式**：一个 `.py` 文件，包含函数定义、测试数据和输出。

**进阶挑战**：给 `event` 统计加差分隐私噪声，比较 `epsilon=0.1` 和 `epsilon=1.0` 的输出差异。

```python
import hashlib
import re
from datetime import datetime

def sanitize_log(log: dict) -> dict:
    """隐私友好的日志清洗：去标识、遮盖、粗化。"""
    out = {}

    # 1. user_id 假名化，保留可关联性但去掉直接身份
    uid = str(log.get("user_id", ""))
    out["user_pseudo"] = hashlib.sha256(uid.encode()).hexdigest()[:12]

    # 2. 遮盖手机号和邮箱
    phone = str(log.get("phone", ""))
    out["phone_masked"] = re.sub(r"(\d{3})\d{4}(\d{4})", r"\1****\2", phone) if phone else ""

    email = str(log.get("email", ""))
    out["email_masked"] = re.sub(r"(.{2}).*(@.*)", r"\1***\2", email) if email else ""

    # 3. IP 只保留前两段
    ip = str(log.get("ip", ""))
    parts = ip.split(".")
    out["ip_prefix"] = ".".join(parts[:2]) + ".0.0" if len(parts) == 4 else ""

    # 4. 时间按小时粗化
    ts = log.get("timestamp")
    if isinstance(ts, datetime):
        out["hour_bucket"] = ts.strftime("%Y-%m-%d %H:00")
    else:
        out["hour_bucket"] = ""

    # 5. 事件本身通常可保留
    out["event"] = log.get("event", "")

    return out


def check_reidentification_risk(log: dict) -> list:
    """检查是否存在常见重识别风险字段组合。"""
    issues = []
    risky = ["birthday", "zipcode", "gender", "job", "company"]
    present = [f for f in risky if f in log]
    if len(present) >= 3:
        issues.append(f"多个准标识符同时存在，可能重识别: {present}")
    if "phone" in log and "email" in log:
        issues.append("手机号与邮箱同时出现，关联风险高")
    return issues


if __name__ == "__main__":
    logs = [
        {
            "user_id": "user_001",
            "phone": "13800000000",
            "email": "zhangsan@example.com",
            "event": "click_banner",
            "timestamp": datetime(2024, 6, 1, 14, 37, 22),
            "ip": "192.168.1.100",
        },
        {
            "user_id": "user_002",
            "phone": "13911112222",
            "email": "lisi@test.org",
            "event": "purchase",
            "timestamp": datetime(2024, 6, 1, 9, 5, 0),
            "ip": "10.0.0.8",
        },
    ]

    for log in logs:
        print("原始:", log)
        print("清洗后:", sanitize_log(log))
        print("风险:", check_reidentification_risk(log))
        print("-" * 40)
```

## arch.sec.compliance

## 一句话直觉

合规（Compliance）不是“写完代码再补的文档”，而是把法律、行业和公司规则变成**可执行、可检查、可审计**的工程约束，让系统在运行时就能证明自己“守规矩”。

---

## 1. 什么是合规：从“人治”到“机制”

合规指系统及其开发流程满足法律、监管、合同或内部政策要求。对架构师来说，关键不是背条款，而是把条款翻译成：

- **策略（Policy）**：允许/禁止什么行为。
- **控制（Control）**：用什么技术或流程落实策略。
- **证据（Evidence）**：如何证明控制确实生效。
- **审计（Audit）**：谁在何时做了什么、结果如何。

> 直觉：合规 = 规则 + 自动化检查 + 可追溯证据。

```python
# 一个最小的“合规规则”表示：把规则写成数据，而不是散落在注释里
compliance_rules = [
    {
        "id": "DATA-001",
        "desc": "个人身份信息（PII, Personally Identifiable Information）必须加密存储",
        "check": lambda record: record.get("pii_encrypted") is True,
    },
    {
        "id": "LOG-002",
        "desc": "敏感操作必须记录审计日志（Audit Log）",
        "check": lambda record: record.get("audit_logged") is True,
    },
]

# 模拟一条待检查的数据记录
record = {"pii_encrypted": True, "audit_logged": False}

# 执行检查：返回违规规则列表
violations = [r["id"] for r in compliance_rules if not r["check"](record)]
print(violations)  # ['LOG-002']
```

---

## 2. 合规在架构中的位置：分层与边界

合规不是单点功能，而是横切关注点（Cross-Cutting Concern）。常见分层：

- **数据层**：加密、脱敏、保留期限（Retention）、数据驻留（Data Residency）。
- **应用层**：访问控制（Access Control）、输入校验、审计日志。
- **接口层**：鉴权、速率限制、传输加密（TLS）。
- **运维层**：不可变日志、备份、漏洞管理、变更审批。

> 直觉：越靠近数据，合规成本越高；越早设计，返工越少。

```python
# 用装饰器把“审计日志”作为横切关注点织入业务函数
import functools, datetime, json

audit_trail = []

def audit(action: str):
    """合规控制：敏感操作自动记录审计日志"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            audit_trail.append({
                "action": action,
                "time": datetime.datetime.utcnow().isoformat(),
                "args": str(args),
                "result": str(result),
            })
            return result
        return wrapper
    return decorator

@audit("export_user_data")
def export_user_data(user_id: int):
    return {"user_id": user_id, "data": "..."}

export_user_data(42)
print(json.dumps(audit_trail, ensure_ascii=False, indent=2))
```

---

## 3. 把合规变成“可验证”的工程能力

合规要可验证，通常需要：

- **策略即代码（Policy as Code）**：规则可版本化、可测试。
- **持续检查（Continuous Compliance）**：在 CI/CD 和运行时都检查。
- **证据链（Evidence Chain）**：日志、报告、签名、时间戳。
- **最小权限（Least Privilege）**：默认拒绝，按需授权。

> 直觉：不能自动检查的合规，最后都会变成“口头合规”。

```python
# 策略即代码示例：用简单断言模拟 CI 中的合规门禁
from dataclasses import dataclass

@dataclass
class ServiceConfig:
    name: str
    encryption_at_rest: bool
    audit_log_enabled: bool
    data_region: str

def check_compliance(cfg: ServiceConfig) -> list:
    """返回不合规项；空列表表示通过"""
    issues = []
    if not cfg.encryption_at_rest:
        issues.append("缺少静态加密（Encryption at Rest）")
    if not cfg.audit_log_enabled:
        issues.append("缺少审计日志")
    if cfg.data_region not in {"cn-north", "cn-south"}:
        issues.append("数据驻留区域不合规")
    return issues

svc = ServiceConfig("payment", encryption_at_rest=True, audit_log_enabled=False, data_region="us-east")
print(check_compliance(svc))
# ['缺少审计日志', '数据驻留区域不合规']
```

---

## 4. 常见合规框架与工程映射

你不需要成为法律专家，但要知道条款通常落在哪些技术控制上：

- **GDPR（General Data Protection Regulation）**：数据主体权利、删除权、数据最小化。
- **HIPAA（Health Insurance Portability and Accountability Act）**：医疗数据保护、访问审计。
- **PCI DSS（Payment Card Industry Data Security Standard）**：支付卡数据加密、网络隔离。
- **SOC 2（System and Organization Controls 2）**：安全、可用性、保密性等控制证据。
- **等保 2.0**：中国网络安全等级保护，强调分域、审计、备份。

> 直觉：框架不同，但技术落点高度重叠：加密、访问控制、日志、备份、隔离。

```python
# 把多个框架的共性控制抽象成“合规基线”
baseline_controls = {
    "encryption": ["GDPR", "HIPAA", "PCI DSS", "等保2.0"],
    "access_control": ["GDPR", "HIPAA", "PCI DSS", "SOC 2", "等保2.0"],
    "audit_log": ["HIPAA", "PCI DSS", "SOC 2", "等保2.0"],
    "backup": ["SOC 2", "等保2.0"],
}

# 找出被最多框架要求的控制
ranked = sorted(baseline_controls.items(), key=lambda kv: len(kv[1]), reverse=True)
print(ranked[0])
# ('access_control', ['GDPR', 'HIPAA', 'PCI DSS', 'SOC 2', '等保2.0'])
```

---

## 5. 架构师视角：合规设计检查清单

- 数据分类（Data Classification）：先知道什么数据敏感。
- 数据流图（Data Flow Diagram）：数据从哪里来、到哪里去。
- 默认安全（Secure by Default）：默认加密、默认拒绝、默认记录。
- 可审计（Auditability）：关键操作不可抵赖。
- 可删除（Right to Erasure）：能按主体删除或匿名化。
- 可迁移（Portability）：数据可导出。
- 持续验证：CI/CD 门禁 + 运行时监控 + 定期审计。

> 直觉：合规架构的目标是“让正确的事成为默认，让错误的事难以发生”。

```python
# 一个极简的“合规检查清单”执行器
checklist = {
    "data_classified": True,
    "encryption_enabled": True,
    "audit_log_enabled": True,
    "can_delete_by_subject": False,
}

failed = [k for k, v in checklist.items() if not v]
print("未通过:", failed)
# 未通过: ['can_delete_by_subject']
```

---

## 动手练习

任务：为你熟悉的一个小系统（比如“用户注册服务”）写一个 **合规检查脚本**。

要求：
1. 定义至少 4 条合规规则，覆盖：加密、访问控制、审计日志、数据删除。
2. 用 Python 字典或列表表示规则，并为每条规则写一个 `check` 函数。
3. 输入一个配置对象（可用字典模拟），输出所有不合规项。
4. 把脚本放到本地 `compliance_check.py`，运行并截图或保存输出。
5. 加分项：把检查接入一个简单的 `if __name__ == "__main__":`，返回非零退出码表示不合规。

示例骨架：

```python
def check_compliance(config: dict) -> list:
    rules = [
        ("ENC-001", lambda c: c.get("encryption"), "必须启用加密"),
        # 继续补充...
    ]
    return [rid for rid, fn, _ in rules if not fn(config)]
```

```python
import functools
import datetime
import json

# 合规规则：策略即代码
compliance_rules = [
    {
        "id": "DATA-001",
        "desc": "个人身份信息（PII）必须加密存储",
        "check": lambda record: record.get("pii_encrypted") is True,
    },
    {
        "id": "LOG-002",
        "desc": "敏感操作必须记录审计日志",
        "check": lambda record: record.get("audit_logged") is True,
    },
]

# 横切关注点：审计日志装饰器
audit_trail = []

def audit(action: str):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            audit_trail.append({
                "action": action,
                "time": datetime.datetime.utcnow().isoformat(),
                "args": str(args),
                "result": str(result),
            })
            return result
        return wrapper
    return decorator

@audit("export_user_data")
def export_user_data(user_id: int):
    return {"user_id": user_id, "data": "..."}

# 运行检查
record = {"pii_encrypted": True, "audit_logged": False}
violations = [r["id"] for r in compliance_rules if not r["check"](record)]
print("违规规则:", violations)

export_user_data(42)
print("审计日志:", json.dumps(audit_trail, ensure_ascii=False, indent=2))
```


---

## 本课题目

### single_choice · None



- [A] 为了将来可能有用，尽量多收集用户信息并长期保存
- [B] 只收集实现当前业务功能所必需的最少数据，并设定保留期限
- [C] 把所有用户数据集中到一个大表中方便统一管理
- [D] 将数据最小化理解为压缩存储体积以节省磁盘

**参考答案**：1

**解析**：数据最小化原则要求仅收集和处理实现特定目的所必需的最少数据，并限制保留时间。选项 A 与最小化相反；C 是集中化问题，与最小化无关；D 把数据最小化误解为物理存储压缩，属于概念混淆。

### single_choice · None



- [A] 将日志文件权限改为只有管理员可读即可
- [B] 对敏感字段进行脱敏或掩码处理后再写入日志
- [C] 把日志保存期限从一年缩短为一个月
- [D] 把日志从明文改为二进制格式存储

**参考答案**：1

**解析**：日志是隐私泄露的高风险渠道，直接记录完整敏感信息即使权限受限也存在泄露风险。脱敏/掩码是业界常规做法。缩短保留期和改二进制都不改变明文可读性，权限控制只是辅助手段而非根本解决。

### multi_choice · None



- [A] 主动预防而非事后补救
- [B] 默认设置即为最保护隐私的状态
- [C] 隐私应嵌入设计，而非事后附加
- [D] 为了功能优先，隐私可以最后再考虑
- [E] 全生命周期保护数据

**参考答案**：[0, 1, 2, 4]

**解析**：隐私设计强调主动预防、默认保护、嵌入设计、全生命周期、端到端安全、可见性与用户中心。选项 D 把隐私当作事后补充，与该原则相悖。

### multi_choice · None



- [A] 去除或泛化准标识符（如精确出生日期改为年龄段）
- [B] 对数据进行聚合或加入噪声
- [C] 保留完整邮编与精确生日但不做处理
- [D] 限制数据的访问和使用范围

**参考答案**：[0, 1, 3]

**解析**：降低再识别风险靠去标识化、泛化、聚合/扰动以及访问限制。保留完整邮编和精确生日恰恰是再识别的常见突破口。

### multi_choice · None



- [A] 应遵循最小权限原则，仅授予完成工作所需的权限
- [B] 应记录敏感数据访问审计日志
- [C] 所有员工默认拥有生产库读写权限比较方便
- [D] 对敏感字段可结合角色进行字段级访问控制

**参考答案**：[0, 1, 3]

**解析**：最小权限、审计日志、字段级/角色级访问控制都是隐私保护的常规手段。全员默认读写生产库违反最小权限，是常见的危险做法。

### multi_choice · None



- [A] 明确告知采集目的并获取同意
- [B] 默认开启后台持续精确定位且不提示
- [C] 提供关闭采集的选项
- [D] 仅在前台需要时采集并按需降低精度

**参考答案**：[0, 2, 3]

**解析**：位置属于敏感数据，需要告知与同意、可撤回、按需最小化精度和采集时机。默认后台持续精确定位且不提示违反透明度和最小化原则。

### fill_blank · None



**参考答案**：["最小", "最小化", "最小化原则", "minimal", "minimization"]

**解析**：数据最小化原则要求收集和处理的数据限于实现目的所必需，且与目的相关。

### fill_blank · None



**参考答案**：["假名", "假名化", "pseudonymization", "pseudonymisation"]

**解析**：假名化是替换标识符但保留可重新关联可能；与不可逆的匿名化不同。

### code_reading · None



**参考答案**：把用户的邮箱和身份证号等敏感个人信息以明文写入日志，属于过度记录和敏感数据暴露风险；应改为脱敏或只记录不可关联的标识，并控制日志访问与保留期限。

**解析**：日志中记录完整敏感字段会扩大数据暴露面，一旦日志被读取即造成隐私泄露，违反最小化和目的限制原则。

### code_reading · None



**参考答案**：缺少租户隔离校验，任何用户只要猜到或遍历 user_id 就可能读取其他租户的订单数据，造成跨租户越权访问和数据泄露；应在数据访问层强制注入租户条件或使用行级安全策略。

**解析**：多租户系统必须在数据层强制租户上下文，仅靠应用层判断容易遗漏，导致越权读取他人数据。

### scenario · None



**解析**：健康数据属于敏感个人信息，应默认最小化采集、显式同意且可撤回、设定保留期限、传输与存储加密，并做去标识化/脱敏以降低可识别性，不能默认永久保存。

### scenario · None



**解析**：接入第三方 SDK 前应评估其采集范围，确保用户被告知并同意、只开启必要能力、签订数据处理协议、限制用途，并建立审计与退出机制。

### single_choice · None



- [A] 两者等价，只是叫法不同
- [B] 假名化后数据仍可能通过关联其他信息重新识别到个人，匿名化则要求不可逆地无法识别
- [C] 匿名化只是把姓名替换成编号，假名化是删除所有字段
- [D] 假名化只适用于日志，匿名化只适用于数据库

**参考答案**：1

**解析**：假名化是用假名替代直接标识符，但仍保留可通过额外信息重新关联到个人的可能；匿名化要求经过处理后无法再识别到特定个人且不可逆。两者法律与合规含义不同，选项 A/C/D 均为常见误解。

### single_choice · None



- [A] 在应用层每次查询都拼接 tenant_id 条件，并在数据库层启用行级安全策略
- [B] 把所有租户数据放在同一张表但加密存储
- [C] 依靠前端隐藏其他租户的数据入口
- [D] 为每个租户分配不同的表名后缀但共用一个数据库账号

**参考答案**：0

**解析**：多租户隔离需要在数据访问层强制租户上下文（如行级安全或强制 tenant 过滤），应用层过滤容易被遗漏。仅加密存储、前端隐藏或共用高权限账号都无法防止越权读取，尤其共用账号会让数据库无法区分租户。

### single_choice · None



- [A] 直接发送原始明文数据，因为对方签了保密协议
- [B] 先对直接标识符进行假名化或去标识化，并签订数据处理协议、限定用途
- [C] 只发送邮箱的哈希值就一定安全，不需要其他约束
- [D] 把数据压缩加密后发送即可，无需约定用途

**参考答案**：1

**解析**：向第三方共享数据时，应同时采取技术去标识化和合同/用途限制等多层措施。仅签保密协议不够；单纯哈希邮箱仍可能因低熵被暴力枚举；仅加密不限制用途仍可能被滥用。

### single_choice · None



- [A] 只要用户注册时勾选了一次同意，之后任何用途都可使用其数据
- [B] 同意应是具体、知情、自愿的，且用户应能撤回，用途变更通常需重新获取同意
- [C] 用户一旦同意就不可撤回
- [D] 同意只对营销邮件有效，对数据分析无效

**参考答案**：1

**解析**：有效同意需要具体、知情、自愿且可撤回，用途变更往往需要重新获得同意。选项 A、C 把同意当成一次性永久授权；D 错误限定了同意的适用范围。

### single_choice · None



- [A] 传输用 HTTP，存储时再整体加密
- [B] 传输使用 TLS，存储对敏感字段加密，并妥善管理密钥
- [C] 只要在内网传输就无需加密
- [D] 把所有数据都用同一个硬编码密钥加密

**参考答案**：1

**解析**：隐私保护要求传输中加密（如 TLS）和静态加密（敏感字段加密），并做好密钥管理。内网传输不加密、硬编码统一密钥都是常见但危险的做法。

### single_choice · None



- [A] 直接显示用户真实姓名和头像
- [B] 显示用户 ID 后四位加昵称首字母
- [C] 显示为随机分配的展示名，且不与其他系统标识关联
- [D] 显示邮箱前缀作为展示名

**参考答案**：2

**解析**：用与真实身份无关的随机展示名可降低可识别性。真实姓名、邮箱前缀、ID 片段都可能被关联识别或推断，属于常见误解。

### single_choice · None



- [A] 数据永久保留，删除麻烦且可能影响审计
- [B] 根据业务和合规要求设定保留期限，到期后安全删除或匿名化
- [C] 只要用户不投诉就一直保留
- [D] 保留期限越长越好，便于将来分析

**参考答案**：1

**解析**：数据保留应遵循目的限制和存储限制原则，到期后应删除或匿名化。永久保留、无限期保留都违反隐私原则。

### single_choice · None



- [A] 只删除用户表里的主记录即可
- [B] 需要在所有存储位置（主库、备份、缓存、日志、第三方）处理该用户数据，并考虑法律要求的保留例外
- [C] 只要前端不再显示该用户即算删除
- [D] 删除操作越快越好，不需要记录

**参考答案**：1

**解析**：用户删除权要求覆盖所有数据副本和下游系统，还要处理备份、缓存、日志与第三方。仅删主记录或前端隐藏都不彻底，也可能遗漏合规要求。

### single_choice · None



- [A] 直接在 import 语句出错时用 pip install 安装最新版本，保证功能可用
- [B] 使用带版本约束的依赖清单，并配合哈希校验（如 --require-hashes 方式安装）
- [C] 只要包在官方索引上能搜到，就默认它是安全可信的
- [D] 把依赖全部改为从随机论坛下载的 wheel 文件以获取更快的下载速度

**参考答案**：1

**解析**：合规的依赖管理强调可复现与完整性：固定版本并校验哈希能防止包在传输或索引侧被替换成篡改版本。仅凭'能搜到'不等于可信，随意下载来源不明的 wheel 更是高风险行为。

### single_choice · None



- [A] 让代码运行速度更快
- [B] 减少代码总行数
- [C] 能够追溯每次变更的作者、时间与审批记录，为审计和责任界定提供依据
- [D] 让开发人员无需写单元测试

**参考答案**：2

**解析**：合规中的可追溯性指记录谁在何时因何做了何种变更并获得何种批准，是审计与事后追责的基础，与性能、代码量无关。

### single_choice · None



- [A] 记录请求的完整原始报文，包含所有个人标识
- [B] 对个人标识进行哈希或掩码处理后再记录，并限制日志访问权限
- [C] 把日志上传到公开的公共存储桶以免丢失
- [D] 干脆不记日志，靠用户口述复现问题

**参考答案**：1

**解析**：脱敏/掩码可在保留排查价值的同时降低隐私风险，配合访问控制进一步减少暴露。公开存储桶与记录原始个人数据都违反合规要求。

### multi_choice · None



- [A] 对依赖清单固定版本并校验哈希
- [B] 从来源不明的镜像站随意下载依赖
- [C] 持续监控依赖的已知漏洞并制定修复流程
- [D] 对引入的开源组件核对许可证义务
- [E] 把构建用的私钥提交到公开仓库

**参考答案**：[0, 2, 3]

**解析**：固定版本加校验、持续漏洞监控、核对许可证均属于供应链合规实践。来源不明的依赖和泄露构建私钥都会显著提升风险。

### multi_choice · None



- [A] 应记录谁在何时执行了何种敏感操作
- [B] 日志应防止被未授权用户随意篡改或删除
- [C] 日志中应明文保存用户密码以便核对身份
- [D] 应控制日志的访问权限，仅授权人员可读
- [E] 日志可随意丢弃，无需保留期

**参考答案**：[0, 1, 3]

**解析**：审计日志需可追溯、防篡改、受访问控制。明文保存密码严重违反安全与隐私要求，无保留期则无法满足审计。

### multi_choice · None



- [A] 收集前明确目的并仅收集必要数据
- [B] 为方便分析，把全部原始个人数据导出到个人电脑长期保存
- [C] 按法规设定留存期限，到期删除或匿名化
- [D] 对敏感数据进行加密存储并限制访问
- [E] 将个人数据出售给第三方以获取额外收益

**参考答案**：[0, 2, 3]

**解析**：目的限制、最小必要、留存期限、加密与访问控制都是合规处理个人数据的要点。私自导出长期保存和擅自出售数据通常违规。

### fill_blank · None



**参考答案**：["哈希", "hash", "哈希值", "hash 值"]

**解析**：哈希校验（如通过 --require-hashes）可确保下载的包与预期内容一致，防止被篡改或替换，是供应链合规的常见手段。

### fill_blank · None



**参考答案**：["审计", "audit", "审计日志", "audit log"]

**解析**：审计日志用于记录谁在何时做了何种敏感操作，是合规审计与事后追责的关键依据。

### code_reading · None



**参考答案**：代码把 API 密钥和数据库口令以明文硬编码在源码中。一旦源码进入版本控制或被共享，凭证就会泄露，且难以轮换；合规上违反密钥管理要求。应改为从环境变量或密钥管理服务读取，并确保不进入版本库。

**解析**：硬编码凭证是最常见的合规与安全问题之一。凭证应外置并通过环境变量或密钥管理服务注入，同时保证不进入版本控制历史。

### code_reading · None



**参考答案**：日志中记录了明文密码和身份证号等敏感个人信息，违反最小必要与隐私合规要求，且日志一旦泄露会造成严重后果。改进方式：只记录审计所需的事件（如用户名、时间、结果），对敏感字段脱敏或掩码，并限制日志访问权限。

**解析**：日志常被长期留存且访问面较广，写入明文密码和个人敏感信息会显著放大风险。应遵循最小必要原则并脱敏。

### scenario · None



**解析**：合规的供应链管理要求构建可复现、内容可校验、风险可跟踪。固定版本并用哈希校验保证一致性；持续扫描已知漏洞并及时修复；核对引入组件的许可证义务；确保构建可复现以便审计。

### scenario · None



**解析**：把真实用户数据完整复制到开发环境违反最小必要与环境隔离要求，扩大隐私泄露面。替代方案是对数据进行脱敏或使用合成数据，并遵循留存期限与访问控制，确保符合合规。

### single_choice · None



- [A] 满足合规要求就一定安全，因为没有漏洞才会被审计通过
- [B] 合规是一套外部要求的最低标准，安全是持续降低风险的过程，二者相关但不完全重合
- [C] 安全就是合规，两者可以互相替代
- [D] 只要通过一次合规审计，之后无需再关注安全

**参考答案**：1

**解析**：合规通常对应法规或标准设定的基线要求，而安全是持续的风险管理过程。满足合规不等于消除了所有安全风险，反之亦然。

### single_choice · None



- [A] 把密钥硬编码在源码里，方便团队共享
- [B] 把密钥提交到公开仓库，依靠'没人会看'来保密
- [C] 通过环境变量或专用密钥管理服务注入，并确保密钥不进入版本控制
- [D] 把密钥写在注释里，正式代码里再读取

**参考答案**：2

**解析**：密钥应外置到环境变量或密钥管理系统中，避免进入版本库历史。硬编码或写入注释都会随仓库泄露，且难以轮换。

### single_choice · None



- [A] 完整记录用户的身份证号、银行卡号和明文密码
- [B] 只记录与审计相关的事件类型、时间、操作者标识，并对敏感字段做脱敏
- [C] 把所有请求体和响应体原样落盘，方便日后排查
- [D] 不记录任何日志，避免隐私问题

**参考答案**：1

**解析**：最小必要原则要求只采集达成目的所需的数据。记录审计所需事件并脱敏，既满足可追溯又避免过度收集敏感信息。原样落盘会放大泄露面。

### single_choice · None



- [A] 任何开源代码都可以随意商用，无需关注许可证
- [B] 不同许可证对再分发、修改、商用的条件不同，使用前需确认其义务是否与项目相符
- [C] 只要不修改源码就不涉及许可证问题
- [D] 许可证只与作者有关，使用者无需关心

**参考答案**：1

**解析**：许可证规定了使用、修改、分发代码时的权利与义务（如是否需开源衍生作品）。即使不修改，分发或商用也可能触发义务，因此使用前需核对。

### single_choice · None



- [A] 只在项目上线当天扫描一次，之后不再关注
- [B] 把扫描结果一律忽略，因为误报太多
- [C] 将漏洞扫描纳入流水线，对高危漏洞设置阻断阈值并跟踪修复
- [D] 仅扫描自研代码，完全不看第三方依赖

**参考答案**：2

**解析**：依赖漏洞会随时间变化（新披露），因此需持续扫描。设置阻断阈值并跟踪修复，才能在合规与交付之间取得平衡。

### single_choice · None



- [A] 数据留得越久越好，方便随时回溯
- [B] 应依据法规与业务需要设定留存期限，到期后安全删除或匿名化
- [C] 只要加密存储，留存多久都无所谓
- [D] 留存策略只与存储成本有关，与合规无关

**参考答案**：1

**解析**：合规要求数据留存不超过必要期限，超期应删除或匿名化。加密能降低泄露影响，但不能替代留存期限的约束。

### single_choice · None



- [A] 生产数据库与测试数据库共用同一实例，只是表名不同
- [B] 测试环境直接使用生产环境的真实用户数据，方便复现问题
- [C] 生产与测试环境使用独立资源与独立凭证，测试数据需脱敏或合成
- [D] 所有环境共用同一套管理员账号，减少管理成本

**参考答案**：2

**解析**：环境隔离与凭证分离是合规的常见要求。测试使用真实生产数据且不脱敏会造成隐私与泄露风险，共用管理员账号则削弱审计与最小权限原则。

### single_choice · None



- [A] 给每个用户授予管理员权限，方便随时处理问题
- [B] 仅授予完成任务所必需的权限，且权限应可回收与审计
- [C] 权限一经授予就长期保留，避免频繁调整
- [D] 最小权限只适用于人类用户，不适用于服务账号

**参考答案**：1

**解析**：最小权限强调只授予必需权限并定期审查回收，适用于用户与服务账号。长期的超范围权限会扩大攻击面并妨碍审计。
