"""Built-in inviolable principles.

These principles are hardcoded and cannot be modified or overridden.
They represent fundamental ethical constraints that exist above
all authority levels including humans.

Why these specific principles?
- NO HARM: The most fundamental - AI should not cause serious harm
- TRANSPARENCY: Hidden modifications enable manipulation
- REVERSIBILITY: Prevent permanent mistakes
- ESCALATION: Violations must be visible, not hidden
- AUDIT: Everything must be traceable
"""

from .core import Principle, PrincipleSeverity


def check_no_harm(action: str, context: dict) -> tuple[bool, str]:
    """Check if action could cause serious harm.

    This is necessarily imperfect - we can't predict all harms.
    But we can catch obvious cases.
    """
    # Dangerous actions that require extra scrutiny
    dangerous_keywords = [
        "delete_all", "destroy", "wipe", "format",
        "execute_arbitrary", "run_untrusted",
        "disable_safety", "bypass_security",
        "expose_secrets", "leak_credentials",
    ]

    action_lower = action.lower()
    for keyword in dangerous_keywords:
        if keyword in action_lower:
            return True, f"Action '{action}' contains dangerous keyword '{keyword}'"

    # Check context for harm indicators
    if context.get("affects_humans", False):
        if context.get("potential_harm", 0) > 7:  # Scale of 1-10
            return True, "Action has high potential for human harm"

    if context.get("irreversible", False) and context.get("scope", "") == "global":
        return True, "Irreversible global action requires extra verification"

    return False, ""


def check_transparency(action: str, context: dict) -> tuple[bool, str]:
    """Check if action maintains transparency."""

    # Hidden or stealth operations are forbidden
    if context.get("hidden", False):
        return True, "Hidden modifications are not allowed"

    if context.get("suppress_audit", False):
        return True, "Cannot suppress audit logging"

    if context.get("disguise_as"):
        return True, f"Cannot disguise action as '{context['disguise_as']}'"

    # All modifications must have a trail
    if action.startswith("modify") or action.startswith("delete"):
        if not context.get("modifier") and not context.get("actor"):
            return True, "Modifications must have an identified actor"

    return False, ""


def check_reversibility(action: str, context: dict) -> tuple[bool, str]:
    """Check if destructive actions are reversible or confirmed."""

    destructive_actions = [
        "delete", "remove", "destroy", "wipe", "truncate",
        "drop", "purge", "clear", "reset",
    ]

    is_destructive = any(d in action.lower() for d in destructive_actions)

    if is_destructive:
        # Must have backup or confirmation
        has_backup = context.get("backup_created", False)
        has_confirmation = context.get("confirmed", False)
        is_recoverable = context.get("recoverable", False)

        if not (has_backup or has_confirmation or is_recoverable):
            return True, f"Destructive action '{action}' requires backup, confirmation, or recovery path"

    return False, ""


def check_escalation(action: str, context: dict) -> tuple[bool, str]:
    """Check if violations are properly escalated."""

    # If this is a response to a violation, it must include escalation
    if context.get("is_violation_response", False):
        if not context.get("escalated_to"):
            return True, "Violation responses must include escalation"

    # Critical actions must notify guardians
    if context.get("criticality", 0) > 8:
        if not context.get("guardian_notified", False):
            return True, "Critical actions must notify guardians"

    return False, ""


def check_audit_trail(action: str, context: dict) -> tuple[bool, str]:
    """Ensure audit trail is maintained."""

    # Certain actions must always be audited
    always_audit = [
        "create_entity", "delete_entity",
        "modify_principle", "override_decision",
        "grant_authority", "revoke_authority",
        "commit_workspace", "merge_changes",
    ]

    if action in always_audit:
        if not context.get("audit_enabled", True):
            return True, f"Action '{action}' requires audit logging"

    return False, ""


def check_consent(action: str, context: dict) -> tuple[bool, str]:
    """Check if proper consent/authorization exists."""

    # Actions affecting other entities need consent
    if context.get("affects_entities"):
        affected = context["affects_entities"]
        consented = context.get("consented_entities", [])

        non_consenting = set(affected) - set(consented)
        if non_consenting:
            # Check if actor has override authority
            if not context.get("has_override_authority", False):
                return True, f"Entities {non_consenting} have not consented to this action"

    # Major system changes need broader authorization
    if context.get("system_wide", False):
        if not context.get("authorized_by"):
            return True, "System-wide changes require explicit authorization"

    return False, ""


# The inviolable principles - these cannot be modified or overridden
INVIOLABLE_PRINCIPLES = [
    Principle(
        id="principle:no-harm",
        name="No Serious Harm",
        description=(
            "Actions must not cause serious harm to humans. "
            "This includes direct harm, enabling harm, or removing protections against harm. "
            "When in doubt, err on the side of caution."
        ),
        severity=PrincipleSeverity.INVIOLABLE,
        check=check_no_harm,
        source="system:core",
    ),

    Principle(
        id="principle:transparency",
        name="Transparency",
        description=(
            "All modifications to the model must be visible and traceable. "
            "No hidden changes, no disguised actors, no suppressed audits. "
            "If it can't be done in the open, it shouldn't be done."
        ),
        severity=PrincipleSeverity.INVIOLABLE,
        check=check_transparency,
        source="system:core",
    ),

    Principle(
        id="principle:reversibility",
        name="Reversibility",
        description=(
            "Destructive actions must be reversible or explicitly confirmed. "
            "Create backups before deletion. Get confirmation for irreversible changes. "
            "Mistakes should be fixable."
        ),
        severity=PrincipleSeverity.INVIOLABLE,
        check=check_reversibility,
        source="system:core",
    ),

    Principle(
        id="principle:escalation",
        name="Mandatory Escalation",
        description=(
            "Principle violations must always be escalated to appropriate authorities. "
            "Critical actions must notify guardians. "
            "No violation should be silently ignored."
        ),
        severity=PrincipleSeverity.INVIOLABLE,
        check=check_escalation,
        source="system:core",
    ),

    Principle(
        id="principle:audit",
        name="Audit Trail",
        description=(
            "Important actions must maintain an audit trail. "
            "Who did what, when, and why must be recorded. "
            "History cannot be erased."
        ),
        severity=PrincipleSeverity.INVIOLABLE,
        check=check_audit_trail,
        source="system:core",
    ),

    Principle(
        id="principle:consent",
        name="Consent and Authorization",
        description=(
            "Actions affecting entities require their consent or proper override authority. "
            "System-wide changes require explicit authorization. "
            "No one should be affected without due process."
        ),
        severity=PrincipleSeverity.REQUIRED,  # Can be overridden with consensus
        check=check_consent,
        source="system:core",
    ),
]
