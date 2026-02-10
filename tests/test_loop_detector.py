"""Tests for loop detection system."""

import pytest

from ensemble.loop_detector import CycleDetector, LoopDetectedError, LoopDetector
from ensemble.workflow import check_loop, check_review_cycle


def test_loop_detector_no_loop():
    """Test that LoopDetector does not detect loop within threshold."""
    detector = LoopDetector(max_iterations=5)

    # Record 5 times (should not detect loop)
    for i in range(5):
        result = detector.record("task-001")
        assert not result, f"Incorrectly detected loop at iteration {i+1}"

    assert detector.get_count("task-001") == 5


def test_loop_detector_detects_loop():
    """Test that LoopDetector detects loop on 6th iteration."""
    detector = LoopDetector(max_iterations=5)

    # Record 5 times (no loop)
    for _ in range(5):
        assert not detector.record("task-001")

    # 6th time should detect loop
    assert detector.record("task-001") is True
    assert detector.get_count("task-001") == 6


def test_loop_detector_independent_tasks():
    """Test that different task IDs are counted independently."""
    detector = LoopDetector(max_iterations=5)

    # Record task-001 three times
    for _ in range(3):
        detector.record("task-001")

    # Record task-002 three times
    for _ in range(3):
        detector.record("task-002")

    # Both should be at 3, not 6
    assert detector.get_count("task-001") == 3
    assert detector.get_count("task-002") == 3


def test_loop_detector_get_count():
    """Test that get_count() returns accurate count."""
    detector = LoopDetector(max_iterations=5)

    # Unrecorded task should return 0
    assert detector.get_count("task-999") == 0

    detector.record("task-001")
    assert detector.get_count("task-001") == 1

    detector.record("task-001")
    detector.record("task-001")
    assert detector.get_count("task-001") == 3


def test_loop_detector_reset_single():
    """Test that reset() can reset a specific task."""
    detector = LoopDetector(max_iterations=5)

    detector.record("task-001")
    detector.record("task-001")
    detector.record("task-002")

    assert detector.get_count("task-001") == 2
    assert detector.get_count("task-002") == 1

    # Reset task-001
    detector.reset("task-001")

    assert detector.get_count("task-001") == 0
    assert detector.get_count("task-002") == 1  # task-002 should remain


def test_loop_detector_reset_all():
    """Test that reset() can reset all tasks when task_id is None."""
    detector = LoopDetector(max_iterations=5)

    detector.record("task-001")
    detector.record("task-002")
    detector.record("task-003")

    assert detector.get_count("task-001") == 1
    assert detector.get_count("task-002") == 1

    # Reset all
    detector.reset()

    assert detector.get_count("task-001") == 0
    assert detector.get_count("task-002") == 0
    assert detector.get_count("task-003") == 0


def test_cycle_detector_no_cycle():
    """Test that CycleDetector does not detect cycle within threshold."""
    detector = CycleDetector(max_cycles=3)

    # Record 3 times (should not detect cycle)
    for i in range(3):
        result = detector.record_cycle("task-001", "review", "fix")
        assert not result, f"Incorrectly detected cycle at iteration {i+1}"

    assert detector.get_cycle_count("task-001", "review", "fix") == 3


def test_cycle_detector_detects_cycle():
    """Test that CycleDetector detects cycle on 4th iteration."""
    detector = CycleDetector(max_cycles=3)

    # Record 3 times (no cycle)
    for _ in range(3):
        assert not detector.record_cycle("task-001", "review", "fix")

    # 4th time should detect cycle
    assert detector.record_cycle("task-001", "review", "fix") is True
    assert detector.get_cycle_count("task-001", "review", "fix") == 4


def test_cycle_detector_different_transitions():
    """Test that different transitions are counted independently."""
    detector = CycleDetector(max_cycles=3)

    # Record review->fix twice
    detector.record_cycle("task-001", "review", "fix")
    detector.record_cycle("task-001", "review", "fix")

    # Record fix->review twice
    detector.record_cycle("task-001", "fix", "review")
    detector.record_cycle("task-001", "fix", "review")

    # Both should be at 2, not 4
    assert detector.get_cycle_count("task-001", "review", "fix") == 2
    assert detector.get_cycle_count("task-001", "fix", "review") == 2


def test_cycle_detector_reset_single_task():
    """Test that reset() can reset cycles for a specific task."""
    detector = CycleDetector(max_cycles=3)

    detector.record_cycle("task-001", "review", "fix")
    detector.record_cycle("task-001", "fix", "review")
    detector.record_cycle("task-002", "review", "fix")

    assert detector.get_cycle_count("task-001", "review", "fix") == 1
    assert detector.get_cycle_count("task-002", "review", "fix") == 1

    # Reset task-001 (all transitions for this task)
    detector.reset("task-001")

    assert detector.get_cycle_count("task-001", "review", "fix") == 0
    assert detector.get_cycle_count("task-001", "fix", "review") == 0
    assert detector.get_cycle_count("task-002", "review", "fix") == 1  # Should remain


def test_cycle_detector_reset_all():
    """Test that reset() can reset all cycles when task_id is None."""
    detector = CycleDetector(max_cycles=3)

    detector.record_cycle("task-001", "review", "fix")
    detector.record_cycle("task-002", "review", "fix")

    # Reset all
    detector.reset()

    assert detector.get_cycle_count("task-001", "review", "fix") == 0
    assert detector.get_cycle_count("task-002", "review", "fix") == 0


def test_loop_detected_error():
    """Test LoopDetectedError exception attributes."""
    error = LoopDetectedError("task-123", 6, 5)

    assert error.task_id == "task-123"
    assert error.count == 6
    assert error.max_iterations == 5
    assert "task-123" in str(error)
    assert "6/5" in str(error)


def test_workflow_check_loop():
    """Test workflow.check_loop() convenience function."""
    detector = LoopDetector(max_iterations=3)

    # Should not raise for first 3 times
    check_loop("task-001", detector)
    check_loop("task-001", detector)
    check_loop("task-001", detector)

    # 4th time should raise
    with pytest.raises(LoopDetectedError) as exc_info:
        check_loop("task-001", detector)

    assert exc_info.value.task_id == "task-001"
    assert exc_info.value.count == 4


def test_workflow_check_review_cycle():
    """Test workflow.check_review_cycle() convenience function."""
    detector = CycleDetector(max_cycles=2)

    # Should not raise for first 2 times
    check_review_cycle("task-001", "review", "fix", detector)
    check_review_cycle("task-001", "review", "fix", detector)

    # 3rd time should raise
    with pytest.raises(LoopDetectedError) as exc_info:
        check_review_cycle("task-001", "review", "fix", detector)

    # The task_id in the error should include the transition
    assert "review->fix" in exc_info.value.task_id
    assert exc_info.value.count == 3
