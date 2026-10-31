from __future__ import annotations

from agent_brain.distribution import (
    ChangeKind,
    CompatibilityVerdict,
    PublicSurfaceSnapshot,
    classify_surface_diff,
    compare_public_surfaces,
    evaluate_consumer_expectations,
    snapshot_public_surface,
)


def test_additive_public_export_is_compatible() -> None:
    baseline = PublicSurfaceSnapshot(
        exports={"agent_brain.distribution": frozenset({"PinSpec", "UpgradePlan"})}
    )
    candidate = PublicSurfaceSnapshot(
        exports={
            "agent_brain.distribution": frozenset({"PinSpec", "UpgradePlan", "RollbackPlan"})
        }
    )

    report = compare_public_surfaces(baseline, candidate)

    assert report.verdict is CompatibilityVerdict.COMPATIBLE
    assert report.kind is ChangeKind.ADDITIVE
    assert "agent_brain.distribution:RollbackPlan" in report.added


def test_removing_public_export_is_breaking() -> None:
    report = classify_surface_diff(
        removed={"agent_brain.distribution:PinSpec"},
        added=set(),
    )

    assert report.verdict is CompatibilityVerdict.INCOMPATIBLE
    assert report.kind is ChangeKind.BREAKING
    assert report.is_compatible is False


def test_consumer_expectations_detect_incompatible_contract() -> None:
    actual = snapshot_public_surface()
    expected = {
        "agent_brain": ("__version__",),
        "agent_brain.distribution": (
            "PinSpec",
            "UpgradePlan",
            "RollbackPlan",
            "snapshot_public_surface",
            "evaluate_consumer_expectations",
        ),
        "agent_brain.contracts": ("EvidenceRef", "ClaimRef"),
        "agent_brain.memory": ("MemoryStore", "MemoryScope"),
    }

    ok = evaluate_consumer_expectations(
        expected_exports=expected,
        actual_exports=actual.exports,
    )
    assert ok.is_compatible

    broken = evaluate_consumer_expectations(
        expected_exports={
            "agent_brain.distribution": ("PinSpec", "DoesNotExistExport"),
        },
        actual_exports=actual.exports,
    )
    assert broken.verdict is CompatibilityVerdict.INCOMPATIBLE
    assert "agent_brain.distribution:DoesNotExistExport" in broken.missing_expected


def test_live_public_surface_snapshot_includes_distribution() -> None:
    snapshot = snapshot_public_surface()

    assert "__version__" in snapshot.symbols_for("agent_brain")
    assert "PinSpec" in snapshot.symbols_for("agent_brain.distribution")
    assert "MemoryReadService" in snapshot.symbols_for("agent_brain.memory")
    assert "ProtocolGateway" in snapshot.symbols_for("agent_brain.protocol")
    assert "invoke" in snapshot.symbols_for("agent_brain.protocol")
