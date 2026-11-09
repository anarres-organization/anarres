import json
from pathlib import Path


PATH = Path(__file__).parent / "data" / "niblett_2025_architecture_compatibility.json"


def load():
    return json.loads(PATH.read_text())


def test_released_archive_identity_and_environment_counts():
    data = load()
    assert data["source_archive"]["bytes"] == 1_971_779_899
    assert data["source_archive"]["md5"] == "1cbf2ec5286bbd3cd30b15a8e01178f7"
    assert {
        name: env["configurations"]
        for name, env in data["training_environments"].items()
    } == {"OPLS": 203, "OPLS+SM": 803, "OPLS+VS": 223, "Full": 935}


def test_same_environment_order_is_architecture_dependent():
    data = load()
    force = {
        panel["architecture"]: panel["outcomes"]
        for panel in data["panels"]
        if panel["panel"] == "force_rmse_ec_dec"
    }
    assert min(force["DeePMD"], key=force["DeePMD"].get) == "OPLS"
    assert min(force["MACE"], key=force["MACE"].get) == "Full"
    assert max(force["DeePMD"], key=force["DeePMD"].get) == "OPLS+VS"
    assert max(force["MACE"], key=force["MACE"].get) == "OPLS"


def test_active_learning_changes_deepmd_environment_order():
    data = load()
    panels = {
        (panel["panel"], panel["active_learning"]): panel["outcomes"]
        for panel in data["panels"]
        if panel["architecture"] == "DeePMD" and panel["panel"].startswith("stability_")
    }
    assert max(panels[("stability_ec_dec", False)], key=panels[("stability_ec_dec", False)].get) == "Full"
    assert max(panels[("stability_ec_dec", True)], key=panels[("stability_ec_dec", True)].get) == "OPLS"
    assert max(panels[("stability_pc", False)], key=panels[("stability_pc", False)].get) == "Full"
    assert max(panels[("stability_pc", True)], key=panels[("stability_pc", True)].get) == "OPLS+SM"


def test_unmatched_cost_boundary_is_explicit():
    data = load()
    boundary = " ".join(data["interpretation_boundary"])
    assert "do not enter the matched-cost predictive bridge" in boundary
