from pathlib import Path

from asset_factory.cli import _half_per_subject
from asset_factory.models import ExportProfile, ScienceSubject
from asset_factory.specs import load_asset_spec, seed_spec_paths

REPO_ROOT = Path(__file__).resolve().parents[1]
SEED_DIR = REPO_ROOT / "assets" / "seeds"
EXPECTED_EXPORTS = {
    ExportProfile.WEB,
    ExportProfile.UNITY,
    ExportProfile.UNREAL,
}


def test_all_seed_specs_validate():
    seed_paths = sorted(SEED_DIR.glob("*.yaml"))

    assert len(seed_paths) == 25
    for path in seed_paths:
        spec = load_asset_spec(path)
        assert spec.id
        assert spec.learning_goal
        assert set(spec.exports) == EXPECTED_EXPORTS


def test_saturn_replaces_comet_as_warm_astronomy_example():
    specs = [load_asset_spec(path) for path in seed_spec_paths(SEED_DIR)]
    astronomy = [spec.id for spec in specs if spec.subject is ScienceSubject.ASTRONOMY]
    warm = {
        spec.id for spec in _half_per_subject(specs) if spec.subject is ScienceSubject.ASTRONOMY
    }

    assert astronomy.index("saturn_001") < astronomy.index("comet_001")
    assert "saturn_001" in warm
    assert "comet_001" not in warm
