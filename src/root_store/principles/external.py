"""External Principles Loader - load principles from golden reference.

Instead of hardcoding ethics, we load them from an external source:
- For now: A text file (the golden reference)
- Future: A URL to a democratically-governed principles server

This separates "what the rules are" from "how rules are enforced".
Society defines the rules. The system enforces them.
"""

from __future__ import annotations
from pathlib import Path
from typing import Optional, Callable
import re
import os

from .core import Principle, PrincipleSeverity


# Default location for the golden reference
DEFAULT_PRINCIPLES_PATH = Path(os.path.expanduser("~/Desktop/SEED_PRINCIPLES.txt"))

# Future: URL for the online voting system
# PRINCIPLES_URL = "https://seed-principles.org/api/v1/principles"


def parse_principles_file(content: str) -> list[dict]:
    """Parse the principles text file format.

    Format:
        [PRINCIPLE: id]
        SEVERITY: FOUNDATIONAL|INVIOLABLE|REQUIRED
        NAME: Human readable name
        DESCRIPTION: |
            Multi-line description
            continues here
    """
    principles = []
    current = None

    lines = content.split('\n')
    i = 0

    while i < len(lines):
        line = lines[i]

        # Start of a new principle
        match = re.match(r'\[PRINCIPLE:\s*([^\]]+)\]', line)
        if match:
            if current:
                principles.append(current)
            current = {
                'id': f"principle:{match.group(1).strip()}",
                'severity': 'REQUIRED',
                'name': '',
                'description': '',
            }
            i += 1
            continue

        if current:
            # Parse severity
            if line.startswith('SEVERITY:'):
                current['severity'] = line.split(':', 1)[1].strip()

            # Parse name
            elif line.startswith('NAME:'):
                current['name'] = line.split(':', 1)[1].strip()

            # Parse description (multi-line)
            elif line.startswith('DESCRIPTION:'):
                desc_lines = []
                i += 1
                while i < len(lines):
                    desc_line = lines[i]
                    # Stop at next field or principle
                    if desc_line.startswith('[PRINCIPLE:') or \
                       (desc_line.strip() and not desc_line.startswith(' ') and ':' in desc_line and not desc_line.strip().startswith('-')):
                        i -= 1  # Back up so main loop sees this line
                        break
                    desc_lines.append(desc_line)
                    i += 1
                current['description'] = '\n'.join(desc_lines).strip()

        i += 1

    if current:
        principles.append(current)

    return principles


def severity_from_string(s: str) -> PrincipleSeverity:
    """Convert string severity to enum."""
    s = s.upper().strip()
    if s == 'FOUNDATIONAL':
        return PrincipleSeverity.INVIOLABLE  # Foundational maps to inviolable in code
    elif s == 'INVIOLABLE':
        return PrincipleSeverity.INVIOLABLE
    elif s == 'REQUIRED':
        return PrincipleSeverity.REQUIRED
    else:
        return PrincipleSeverity.ADVISORY


def create_check_function(principle_id: str, description: str) -> Callable:
    """Create a check function based on principle description.

    This is a simple implementation that looks for keywords.
    A more sophisticated version could use NLP or explicit rules.
    """
    desc_lower = description.lower()

    def check(action: str, context: dict) -> tuple[bool, str]:
        action_lower = action.lower()

        # Principle-specific checks based on ID
        if 'no-harm' in principle_id:
            dangerous = ['delete_all', 'destroy', 'wipe', 'disable_safety', 'bypass_security']
            for d in dangerous:
                if d in action_lower:
                    return True, f"Action '{action}' may cause harm (contains '{d}')"

            if context.get('potential_harm', 0) > 7:
                return True, "Action has high potential for harm"

        elif 'transparency' in principle_id:
            if context.get('hidden', False):
                return True, "Hidden modifications are not allowed"
            if context.get('suppress_audit', False):
                return True, "Cannot suppress audit logging"

        elif 'reversibility' in principle_id:
            destructive = ['delete', 'remove', 'destroy', 'wipe', 'truncate']
            is_destructive = any(d in action_lower for d in destructive)
            if is_destructive:
                if not (context.get('backup_created') or context.get('confirmed') or context.get('recoverable')):
                    return True, f"Destructive action '{action}' requires backup or confirmation"

        elif 'escalation' in principle_id:
            if context.get('is_violation_response') and not context.get('escalated_to'):
                return True, "Violation responses must include escalation"

        elif 'audit' in principle_id:
            always_audit = ['create_entity', 'delete_entity', 'modify_principle', 'commit_workspace']
            if action in always_audit and not context.get('audit_enabled', True):
                return True, f"Action '{action}' requires audit logging"

        elif 'consent' in principle_id:
            if context.get('affects_entities'):
                affected = set(context['affects_entities'])
                consented = set(context.get('consented_entities', []))
                non_consenting = affected - consented
                if non_consenting and not context.get('has_override_authority'):
                    return True, f"Entities {non_consenting} have not consented"

        elif 'authority-contact' in principle_id:
            # This principle triggers proactive notification
            if context.get('imminent_threat') or context.get('serious_crime') or context.get('child_safety'):
                if not context.get('authorities_notified'):
                    return True, "Situation requires contacting authorities"

        return False, ""

    return check


def load_principles_from_file(path: Path = None) -> list[Principle]:
    """Load principles from the golden reference file.

    Args:
        path: Path to principles file. Defaults to desktop location.

    Returns:
        List of Principle objects ready for enforcement.
    """
    path = path or DEFAULT_PRINCIPLES_PATH

    if not path.exists():
        print(f"Warning: Principles file not found at {path}")
        print("Using empty principles list. Create the file to define rules.")
        return []

    content = path.read_text(encoding='utf-8')
    raw_principles = parse_principles_file(content)

    principles = []
    for raw in raw_principles:
        principle = Principle(
            id=raw['id'],
            name=raw['name'],
            description=raw['description'],
            severity=severity_from_string(raw['severity']),
            check=create_check_function(raw['id'], raw['description']),
            source=f"file:{path.name}",
        )
        principles.append(principle)

    return principles


def load_principles_from_url(url: str) -> list[Principle]:
    """Load principles from online voting system.

    Future implementation for when principles are hosted online.
    """
    # TODO: Implement when online system is ready
    # - Fetch from URL
    # - Verify signatures
    # - Cache locally
    # - Handle offline gracefully
    raise NotImplementedError("Online principles loading not yet implemented")


def get_principles(
    local_path: Path = None,
    url: str = None,
    fallback_to_builtin: bool = True,
) -> list[Principle]:
    """Get principles from best available source.

    Priority:
    1. URL (online voting system) - if provided
    2. Local file (golden reference) - if exists
    3. Built-in principles - as fallback

    Args:
        local_path: Path to local principles file
        url: URL to online principles server
        fallback_to_builtin: Whether to use builtin if external fails
    """
    # Try URL first (future)
    if url:
        try:
            return load_principles_from_url(url)
        except Exception as e:
            print(f"Warning: Could not load principles from URL: {e}")

    # Try local file
    local_path = local_path or DEFAULT_PRINCIPLES_PATH
    if local_path.exists():
        try:
            principles = load_principles_from_file(local_path)
            if principles:
                print(f"Loaded {len(principles)} principles from {local_path}")
                return principles
        except Exception as e:
            print(f"Warning: Could not parse principles file: {e}")

    # Fallback to builtin
    if fallback_to_builtin:
        from .builtin import INVIOLABLE_PRINCIPLES
        print("Using built-in principles as fallback")
        return INVIOLABLE_PRINCIPLES

    return []
