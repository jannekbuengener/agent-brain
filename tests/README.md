# Tests

Diese Testfläche schützt die eigenständigen Agent-Brain-Verträge.

## Konvention

- `tests/test_*.py`: kleine Repository-/Smoke-Tests, solange noch keine fachlichen Module existieren.
- spätere Unit-Tests werden nach Modulverantwortung gruppiert, ohne Claire-spezifische Policy in den generischen Contract zu ziehen.
- `tests/fixtures/`: statische, produktneutrale Fixtures; Herkunft und Zweck müssen im jeweiligen Fixture dokumentiert sein.
- `tests/conftest.py`: nur kleine, wiederverwendbare prozedurale Fixtures.
- Claire-Parity-Fixtures werden erst in den dafür vorgesehenen Slices übernommen oder neutral rekonstruiert; keine blinde Testdatei-Kopie.

Der Scaffold-Smoke beweist nur Installierbarkeit und importierbare Modulgrenzen. Er behauptet noch keine fachliche API.
