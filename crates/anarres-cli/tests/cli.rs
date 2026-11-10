use std::fs;
use std::path::{Path, PathBuf};
use std::process::{Command, Output};
use std::sync::atomic::{AtomicU64, Ordering};

use serde_json::Value;

static NEXT_DIRECTORY: AtomicU64 = AtomicU64::new(0);

fn binary() -> &'static str {
    env!("CARGO_BIN_EXE_anarres")
}

fn fixture() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("../../examples/environment-processing/probe.json")
}

fn profile_fixture(name: &str) -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../../examples/environment-profiles")
        .join(name)
}

fn temporary_directory() -> PathBuf {
    let sequence = NEXT_DIRECTORY.fetch_add(1, Ordering::Relaxed);
    let directory = std::env::temp_dir().join(format!(
        "anarres-cli-test-{}-{sequence}",
        std::process::id()
    ));
    fs::create_dir_all(&directory).expect("temporary directory is created");
    directory
}

fn run(arguments: &[&str]) -> Output {
    Command::new(binary())
        .args(arguments)
        .output()
        .expect("CLI process starts")
}

fn write_probe_variant(path: &Path, environment_id: &str) {
    let mut probe: Value = serde_json::from_slice(&fs::read(fixture()).expect("fixture is read"))
        .expect("fixture is JSON");
    probe["environment_id"] = Value::String(environment_id.to_owned());
    fs::write(
        path,
        serde_json::to_vec_pretty(&probe).expect("probe serializes"),
    )
    .expect("probe variant is written");
}

#[test]
fn qualify_has_stable_json_output() {
    let output = run(&["qualify", fixture().to_str().unwrap(), "--json"]);
    assert!(
        output.status.success(),
        "{}",
        String::from_utf8_lossy(&output.stderr)
    );
    let report: Value = serde_json::from_slice(&output.stdout).expect("stdout is JSON");
    assert_eq!(report["environment_id"], "math-reference-demo-v1");
    assert_eq!(report["status_counts"]["admitted"], 2);
    assert_eq!(report["status_counts"]["repair"], 1);
}

#[test]
fn measure_validate_and_overwrite_safety_work_together() {
    let directory = temporary_directory();
    let manifest = directory.join("environment.json");
    let fixture = fixture();

    let measured = run(&[
        "measure",
        fixture.to_str().unwrap(),
        "--output",
        manifest.to_str().unwrap(),
    ]);
    assert!(
        measured.status.success(),
        "{}",
        String::from_utf8_lossy(&measured.stderr)
    );

    let validated = run(&["validate", manifest.to_str().unwrap(), "--json"]);
    assert!(
        validated.status.success(),
        "{}",
        String::from_utf8_lossy(&validated.stderr)
    );
    let report: Value = serde_json::from_slice(&validated.stdout).expect("stdout is JSON");
    assert_eq!(report["valid"], true);

    let overwrite = run(&[
        "measure",
        fixture.to_str().unwrap(),
        "--output",
        manifest.to_str().unwrap(),
    ]);
    assert_eq!(overwrite.status.code(), Some(1));
    assert!(String::from_utf8_lossy(&overwrite.stderr).contains("already exists"));

    let forced = run(&[
        "measure",
        fixture.to_str().unwrap(),
        "--output",
        manifest.to_str().unwrap(),
        "--force",
    ]);
    assert!(
        forced.status.success(),
        "{}",
        String::from_utf8_lossy(&forced.stderr)
    );
    let revalidated = run(&["validate", manifest.to_str().unwrap()]);
    assert!(revalidated.status.success());

    fs::remove_dir_all(directory).expect("temporary directory is removed");
}

#[test]
fn design_compares_compatible_candidate_manifests() {
    let directory = temporary_directory();
    let probe_a = directory.join("probe-a.json");
    let probe_b = directory.join("probe-b.json");
    let manifest_a = directory.join("manifest-a.json");
    let manifest_b = directory.join("manifest-b.json");
    write_probe_variant(&probe_a, "candidate-a");
    write_probe_variant(&probe_b, "candidate-b");

    for (probe, manifest) in [(&probe_a, &manifest_a), (&probe_b, &manifest_b)] {
        let measured = run(&[
            "measure",
            probe.to_str().unwrap(),
            "--output",
            manifest.to_str().unwrap(),
        ]);
        assert!(
            measured.status.success(),
            "{}",
            String::from_utf8_lossy(&measured.stderr)
        );
    }

    let designed = run(&[
        "design",
        manifest_a.to_str().unwrap(),
        manifest_b.to_str().unwrap(),
        "--json",
    ]);
    assert!(
        designed.status.success(),
        "{}",
        String::from_utf8_lossy(&designed.stderr)
    );
    let report: Value = serde_json::from_slice(&designed.stdout).expect("stdout is JSON");
    assert_eq!(report["compatible"], true);
    assert_eq!(report["candidate_count"], 2);

    fs::remove_dir_all(directory).expect("temporary directory is removed");
}

#[test]
fn profile_measure_validate_and_design_work_across_domain_coordinates() {
    let directory = temporary_directory();
    let input_a = profile_fixture("materials-a.profile-input.json");
    let input_b = profile_fixture("materials-b.profile-input.json");
    let profile_a = directory.join("materials-a.profile.json");
    let profile_b = directory.join("materials-b.profile.json");

    for (input, profile) in [(&input_a, &profile_a), (&input_b, &profile_b)] {
        let measured = run(&[
            "measure",
            input.to_str().unwrap(),
            "--output",
            profile.to_str().unwrap(),
        ]);
        assert!(
            measured.status.success(),
            "{}",
            String::from_utf8_lossy(&measured.stderr)
        );
    }

    let validated = run(&[
        "validate",
        input_a.to_str().unwrap(),
        profile_a.to_str().unwrap(),
        "--json",
    ]);
    assert!(
        validated.status.success(),
        "{}",
        String::from_utf8_lossy(&validated.stderr)
    );

    let designed = run(&[
        "design",
        profile_a.to_str().unwrap(),
        profile_b.to_str().unwrap(),
        "--json",
    ]);
    assert!(
        designed.status.success(),
        "{}",
        String::from_utf8_lossy(&designed.stderr)
    );
    let report: Value = serde_json::from_slice(&designed.stdout).expect("stdout is JSON");
    assert_eq!(report["compatible"], true);
    assert_eq!(report["domain"], "materials-interatomic-potentials");
    assert_eq!(
        report["coordinate_ranges"]["chemical_system_coverage"]["minimum"],
        0.68
    );

    fs::remove_dir_all(directory).expect("temporary directory is removed");
}

#[test]
fn legal_profiles_preserve_domain_coordinates_without_rho_or_h() {
    let directory = temporary_directory();
    let input_a = profile_fixture("legal-a.profile-input.json");
    let input_b = profile_fixture("legal-b.profile-input.json");
    let profile_a = directory.join("legal-a.profile.json");
    let profile_b = directory.join("legal-b.profile.json");

    for (input, profile) in [(&input_a, &profile_a), (&input_b, &profile_b)] {
        let measured = run(&[
            "measure",
            input.to_str().unwrap(),
            "--output",
            profile.to_str().unwrap(),
        ]);
        assert!(
            measured.status.success(),
            "{}",
            String::from_utf8_lossy(&measured.stderr)
        );
    }

    let designed = run(&[
        "design",
        profile_a.to_str().unwrap(),
        profile_b.to_str().unwrap(),
        "--json",
    ]);
    assert!(
        designed.status.success(),
        "{}",
        String::from_utf8_lossy(&designed.stderr)
    );
    let report: Value = serde_json::from_slice(&designed.stdout).expect("stdout is JSON");
    assert_eq!(report["compatible"], true);
    assert_eq!(report["domain"], "legal-procedural-reasoning");
    assert!(
        report["coordinate_ranges"]
            .get("usable_signal_density")
            .is_none()
    );
    assert!(
        report["coordinate_ranges"]
            .get("effective_coverage")
            .is_none()
    );
    assert_eq!(
        report["coordinate_ranges"]["reward_discrimination"]["maximum"],
        0.31
    );
    assert_eq!(
        report["coordinate_ranges"]["measurement_reliability"]["minimum"],
        0.76
    );

    fs::remove_dir_all(directory).expect("temporary directory is removed");
}

#[test]
fn robotics_profiles_preserve_program_measurements() {
    let directory = temporary_directory();
    let input_a = profile_fixture("robotics-a.profile-input.json");
    let input_b = profile_fixture("robotics-b.profile-input.json");
    let profile_a = directory.join("robotics-a.profile.json");
    let profile_b = directory.join("robotics-b.profile.json");

    for (input, profile) in [(&input_a, &profile_a), (&input_b, &profile_b)] {
        let measured = run(&[
            "measure",
            input.to_str().unwrap(),
            "--output",
            profile.to_str().unwrap(),
        ]);
        assert!(measured.status.success());
    }

    let designed = run(&[
        "design",
        profile_a.to_str().unwrap(),
        profile_b.to_str().unwrap(),
        "--json",
    ]);
    assert!(designed.status.success());
    let report: Value = serde_json::from_slice(&designed.stdout).expect("stdout is JSON");
    for coordinate in [
        "target_relevance",
        "policy_weakness",
        "selection_coverage",
        "quality_correction",
        "measurement_reliability",
        "missingness_rate",
        "mean_action_steps",
    ] {
        assert!(
            report["coordinate_ranges"].get(coordinate).is_some(),
            "missing robotics coordinate {coordinate}"
        );
    }

    fs::remove_dir_all(directory).expect("temporary directory is removed");
}

#[test]
fn profile_design_rejects_mismatched_coordinate_definitions() {
    let directory = temporary_directory();
    let input_a = profile_fixture("robotics-a.profile-input.json");
    let mut changed: Value = serde_json::from_slice(
        &fs::read(profile_fixture("robotics-b.profile-input.json")).expect("fixture is read"),
    )
    .expect("fixture is JSON");
    changed["coordinates"][2]["unit"] = Value::String("seconds_per_episode".into());
    changed["producer"]["revision"] = Value::String("fixture-v2".into());
    let input_b = directory.join("robotics-b-mismatched.json");
    fs::write(
        &input_b,
        serde_json::to_vec_pretty(&changed).expect("input serializes"),
    )
    .expect("input is written");
    let profile_a = directory.join("robotics-a.profile.json");
    let profile_b = directory.join("robotics-b.profile.json");
    for (input, profile) in [(&input_a, &profile_a), (&input_b, &profile_b)] {
        let measured = run(&[
            "measure",
            input.to_str().unwrap(),
            "--output",
            profile.to_str().unwrap(),
        ]);
        assert!(measured.status.success());
    }

    let designed = run(&[
        "design",
        profile_a.to_str().unwrap(),
        profile_b.to_str().unwrap(),
        "--json",
    ]);
    assert_eq!(designed.status.code(), Some(1));
    let report: Value = serde_json::from_slice(&designed.stdout).expect("stdout is JSON");
    assert_eq!(report["compatible"], false);
    let issues: Vec<&str> = report["issues"]
        .as_array()
        .unwrap()
        .iter()
        .map(|issue| issue.as_str().unwrap())
        .collect();
    assert!(
        issues
            .iter()
            .any(|issue| issue.contains("different adapter revision"))
    );
    assert!(
        issues
            .iter()
            .any(|issue| issue.contains("different coordinate definitions"))
    );

    fs::remove_dir_all(directory).expect("temporary directory is removed");
}

#[test]
fn unknown_schema_is_reported_as_unsupported() {
    let directory = temporary_directory();
    let record = directory.join("future.json");
    fs::write(&record, br#"{"schema_version":"anarres.future.v9"}"#).expect("record is written");
    let validated = run(&["validate", record.to_str().unwrap(), "--json"]);
    assert_eq!(validated.status.code(), Some(1));
    let report: Value = serde_json::from_slice(&validated.stdout).expect("stdout is JSON");
    assert_eq!(report["records"][0]["record_type"], "unsupported record");
    assert!(
        report["records"][0]["error"]
            .as_str()
            .unwrap()
            .contains("unsupported schema_version")
    );
    fs::remove_dir_all(directory).expect("temporary directory is removed");
}

#[test]
fn finance_status_runs_the_domain_adapter() {
    let output = run(&["finance", "status", "--json"]);
    assert!(
        output.status.success(),
        "{}",
        String::from_utf8_lossy(&output.stderr)
    );
    let report: Value = serde_json::from_slice(&output.stdout).expect("stdout is JSON");
    assert_eq!(report["domain"], "agentic-finance");
    assert_eq!(report["prospective_environment_outcome_opened"], false);
    assert!(
        report["capabilities"]
            .as_array()
            .unwrap()
            .iter()
            .any(|capability| capability == "retrospective_reproduction")
    );
}
