"""Inviolable Principles - ethics hardcoded above all authority.

The principle system enforces constraints that NO ONE can override:
- Not humans (they might be compromised, coerced, or malicious)
- Not AI (might be misaligned or manipulated)
- Not consensus (mob rule doesn't override ethics)

These aren't just guidelines - they're hardcoded checks that run
before any action that could violate them.

Core principles:
1. NO HARM: Actions must not cause serious harm to humans
2. TRANSPARENCY: No hidden modifications to the model
3. REVERSIBILITY: Destructive actions require confirmation
4. ESCALATION: Violations are always reported
5. CONSENT: Major changes require proper authorization

The enforcement runs at multiple levels:
- Pre-action: Check before allowing action
- Post-action: Audit after action completes
- Continuous: Background integrity monitoring
"""

from .core import Principle, PrincipleViolation, PrincipleCheck, PrincipleSeverity
from .enforcer import PrincipleEnforcer
from .builtin import INVIOLABLE_PRINCIPLES
from .external import load_principles_from_file, get_principles, DEFAULT_PRINCIPLES_PATH
