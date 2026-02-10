"""Tests for Faceted Prompting foundation (personas and policies)."""

from pathlib import Path

import pytest


# Personas directory paths
PERSONAS_DIR = Path("src/ensemble/templates/personas")
PERSONAS_LOCAL_DIR = Path(".claude/personas")

# Policies directory paths
POLICIES_DIR = Path("src/ensemble/templates/policies")
POLICIES_LOCAL_DIR = Path(".claude/policies")

# Expected files
EXPECTED_PERSONAS = [
    "conductor.md",
    "dispatch.md",
    "worker-coder.md",
    "reviewer-arch.md",
    "reviewer-security.md",
    "integrator.md",
    "learner.md",
]

EXPECTED_POLICIES = [
    "security.md",
    "coding.md",
    "review.md",
    "communication.md",
    "delegation.md",
]


def test_personas_directory_exists():
    """Test that personas/ directories exist."""
    assert PERSONAS_DIR.exists(), f"{PERSONAS_DIR} does not exist"
    assert PERSONAS_DIR.is_dir(), f"{PERSONAS_DIR} is not a directory"
    assert PERSONAS_LOCAL_DIR.exists(), f"{PERSONAS_LOCAL_DIR} does not exist"
    assert PERSONAS_LOCAL_DIR.is_dir(), f"{PERSONAS_LOCAL_DIR} is not a directory"


def test_policies_directory_exists():
    """Test that policies/ directories exist."""
    assert POLICIES_DIR.exists(), f"{POLICIES_DIR} does not exist"
    assert POLICIES_DIR.is_dir(), f"{POLICIES_DIR} is not a directory"
    assert POLICIES_LOCAL_DIR.exists(), f"{POLICIES_LOCAL_DIR} does not exist"
    assert POLICIES_LOCAL_DIR.is_dir(), f"{POLICIES_LOCAL_DIR} is not a directory"


def test_all_agents_have_persona():
    """Test that all 7 agents have persona files."""
    for persona_file in EXPECTED_PERSONAS:
        # Check in src/ensemble/templates/personas/
        template_path = PERSONAS_DIR / persona_file
        assert template_path.exists(), f"Missing persona: {template_path}"

        # Check in .claude/personas/
        local_path = PERSONAS_LOCAL_DIR / persona_file
        assert local_path.exists(), f"Missing local persona: {local_path}"


def test_persona_has_required_sections():
    """Test that each persona has required sections: 役割, モデル, 責務."""
    required_sections = ["## 役割", "## モデル", "## 責務"]

    for persona_file in EXPECTED_PERSONAS:
        persona_path = PERSONAS_DIR / persona_file
        content = persona_path.read_text()

        for section in required_sections:
            assert section in content, (
                f"{persona_file} is missing required section: {section}"
            )


def test_policy_has_required_sections():
    """Test that each policy has required sections: 適用対象, ルール."""
    required_sections = ["## 適用対象", "## ルール"]

    for policy_file in EXPECTED_POLICIES:
        policy_path = POLICIES_DIR / policy_file
        content = policy_path.read_text()

        for section in required_sections:
            assert section in content, (
                f"{policy_file} is missing required section: {section}"
            )


def test_no_duplicate_content():
    """Test that personas/ and policies/ do not have significant content duplication."""
    # Load all persona content
    persona_contents = []
    for persona_file in EXPECTED_PERSONAS:
        persona_path = PERSONAS_DIR / persona_file
        content = persona_path.read_text()
        persona_contents.append(content)

    # Load all policy content
    policy_contents = []
    for policy_file in EXPECTED_POLICIES:
        policy_path = POLICIES_DIR / policy_file
        content = policy_path.read_text()
        policy_contents.append(content)

    # Simple check: personas should not contain full policy sections
    # (We check for "## 禁止事項" which is a policy-specific section)
    for persona_content in persona_contents:
        # Personas can mention "禁止事項" in descriptions but shouldn't have
        # a full "## 禁止事項" section with multiple items
        # This is a heuristic check - we count occurrences
        if "## 禁止事項" in persona_content:
            # If it appears, it should be minimal (not a full section)
            lines_after_section = []
            in_section = False
            for line in persona_content.split("\n"):
                if "## 禁止事項" in line:
                    in_section = True
                    continue
                if in_section:
                    if line.startswith("##"):
                        break
                    if line.strip().startswith("-"):
                        lines_after_section.append(line)

            # Personas should not have extensive prohibition lists (that's for policies)
            assert len(lines_after_section) <= 3, (
                "Persona contains extensive prohibition list (should be in policies)"
            )


def test_local_personas_match_templates():
    """Test that .claude/personas/ files match src/ensemble/templates/personas/."""
    for persona_file in EXPECTED_PERSONAS:
        template_path = PERSONAS_DIR / persona_file
        local_path = PERSONAS_LOCAL_DIR / persona_file

        template_content = template_path.read_text()
        local_content = local_path.read_text()

        assert template_content == local_content, (
            f"{persona_file} content mismatch between template and local"
        )


def test_local_policies_match_templates():
    """Test that .claude/policies/ files match src/ensemble/templates/policies/."""
    for policy_file in EXPECTED_POLICIES:
        template_path = POLICIES_DIR / policy_file
        local_path = POLICIES_LOCAL_DIR / policy_file

        template_content = template_path.read_text()
        local_content = local_path.read_text()

        assert template_content == local_content, (
            f"{policy_file} content mismatch between template and local"
        )
