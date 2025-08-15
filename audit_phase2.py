# audit_phase2.py
import re, json
from pathlib import Path

SRC = Path("src/openchronicle")
FAIL, WARN, OK = [], [], []

def read(p): 
    return p.read_text(encoding="utf-8", errors="ignore")

# 1) No infra imports in domain/application
offenders = []
for base in ["domain", "application"]:
    for p in (SRC/base).rglob("*.py"):
        t = read(p)
        if re.search(r"^(from|import)\s+openchronicle\.infrastructure", t, re.M):
            offenders.append(str(p))
if offenders: FAIL.append({"infra_in_core": offenders})
else: OK.append("no infra imports in domain/application")

# 2) MemoryValidator uses a Port
mv = SRC / "domain/services/narrative/engines/consistency/memory_validator.py"
if mv.exists():
    t = read(mv)
    if not re.search(r"(MemoryValidationPort|IMemoryPort)", t):
        FAIL.append("memory_validator does not use a Port")
    else:
        OK.append("memory_validator depends on a Port")
else:
    WARN.append("memory_validator.py not found (path changed?)")

# 3) Adapter implements the Port
impls = []
for p in (SRC/"infrastructure").rglob("*.py"):
    t = read(p)
    if re.search(r"class\s+\w+Adapter\([^)]*(Memory.*Port|MemoryValidationPort)[^)]*\):", t):
        impls.append(str(p))
if not impls: FAIL.append("no infra adapter implementing memory port found")
else: OK.append({"memory_port_adapters": impls})

# 4) Bootstrap wiring
boot = SRC / "infrastructure/bootstrap.py"
if boot.exists():
    t = read(boot)
    if re.search(r"Memory.*Port|memory_validation", t): 
        OK.append("bootstrap references memory port")
    else:
        WARN.append("bootstrap does not reference memory port (check DI path)")
else:
    WARN.append("bootstrap.py not found")

print(json.dumps({"ok": OK, "warn": WARN, "fail": FAIL}, indent=2))
exit(1 if FAIL else 0)
