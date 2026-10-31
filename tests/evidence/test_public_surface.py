from agent_brain import evidence


def test_public_surface_exports_importable():
    for name in evidence.__all__:
        assert hasattr(evidence, name)
