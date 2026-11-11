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

fn run_with_path(arguments: &[&str], path: &Path) -> Output {
    Command::new(binary())
        .args(arguments)
        .env("PATH", path)
        .output()
        .expect("CLI process starts")
}

#[test]
fn top_level_help_points_to_builtins_and_adapters() {
    let output = run(&["--help"]);
    assert!(output.status.success());
    let stdout = String::from_utf8(output.stdout).expect("stdout is UTF-8");
    assert!(stdout.contains("anarres qualify <measurements.json>"));
    assert!(stdout.contains("anarres adapter list"));
    assert!(stdout.contains("anarres <adapter> --help"));
    assert!(stdout.contains("portable environment records"));
}

#[test]
fn shell_completions_are_generated_for_supported_shells() {
    for shell in ["bash", "elvish", "zsh", "fish", "powershell"] {
        let output = run(&["generate-shell-completion", shell]);
        assert!(
            output.status.success(),
            "{shell}: {}",
            String::from_utf8_lossy(&output.stderr)
        );
        let completion = String::from_utf8(output.stdout).expect("completion is UTF-8");
        assert!(
            completion.contains("anarres"),
            "{shell} completion has command name"
        );
        assert!(
            completion.contains("qualify"),
            "{shell} completion has built-ins"
        );
    }
}

#[cfg(unix)]
fn write_fake_adapter(directory: &Path, name: &str, version: &str) -> PathBuf {
    use std::os::unix::fs::PermissionsExt;

    let path = directory.join(format!("anarres-{name}"));
    let descriptor = format!(
        r#"{{"schema_version":"anarres.adapter-descriptor.v1","name":"{name}","version":"{version}","protocol_version":2,"domain":"test-{name}","executable":"anarres-{name}","profile_schema_versions":["anarres.environment-profile-input.v1"],"capabilities":["profile","verify"],"measurement_contracts":["test.{name}.v1"]}}"#
    );
    let script = format!(
        "#!/bin/sh\nif [ \"$1\" = \"--anarres-adapter-descriptor\" ]; then\n  printf '%s\\n' '{descriptor}'\n  exit 0\nfi\nif [ \"$1\" != \"--anarres-adapter-protocol\" ] || [ \"$2\" != \"2\" ] || [ \"$3\" != \"--anarres-adapter-name\" ] || [ \"$4\" != \"{name}\" ]; then\n  printf 'invalid runtime handshake\\n' >&2\n  exit 64\nfi\nshift 4\nprintf '%s\\n' \"$@\"\nif [ \"$1\" = \"fail\" ]; then exit 23; fi\n"
    );
    fs::write(&path, script).expect("fake adapter is written");
    let mut permissions = fs::metadata(&path).unwrap().permissions();
    permissions.set_mode(0o755);
    fs::set_permissions(&path, permissions).unwrap();
    path
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

#[cfg(unix)]
#[test]
fn adapter_list_and_doctor_use_the_versioned_descriptor() {
    let directory = temporary_directory();
    write_fake_adapter(&directory, "finance", "0.1.0");

    let listed = run_with_path(&["adapter", "list", "--json"], &directory);
    assert!(
        listed.status.success(),
        "{}",
        String::from_utf8_lossy(&listed.stderr)
    );
    let list: Value = serde_json::from_slice(&listed.stdout).expect("list is JSON");
    assert_eq!(list["schema_version"], "anarres.adapter-list.v1");
    assert_eq!(list["adapters"][0]["name"], "finance");

    let checked = run_with_path(&["adapter", "doctor", "finance", "--json"], &directory);
    assert!(
        checked.status.success(),
        "{}",
        String::from_utf8_lossy(&checked.stderr)
    );
    let doctor: Value = serde_json::from_slice(&checked.stdout).expect("doctor is JSON");
    assert_eq!(doctor["schema_version"], "anarres.adapter-doctor.v1");
    assert_eq!(doctor["valid"], true);
    assert_eq!(doctor["descriptor"]["domain"], "test-finance");

    fs::remove_dir_all(directory).unwrap();
}

#[cfg(unix)]
#[test]
fn direct_and_explicit_adapter_invocation_forward_arguments() {
    let directory = temporary_directory();
    write_fake_adapter(&directory, "finance", "0.1.0");

    let direct = run_with_path(&["finance", "status", "--json"], &directory);
    assert!(
        direct.status.success(),
        "{}",
        String::from_utf8_lossy(&direct.stderr)
    );
    assert_eq!(String::from_utf8_lossy(&direct.stdout), "status\n--json\n");

    let explicit = run_with_path(
        &["adapter", "run", "finance", "--", "profile", "--json"],
        &directory,
    );
    assert!(explicit.status.success());
    assert_eq!(
        String::from_utf8_lossy(&explicit.stdout),
        "profile\n--json\n"
    );

    let help = run_with_path(&["finance", "--help"], &directory);
    assert!(help.status.success());
    assert_eq!(String::from_utf8_lossy(&help.stdout), "--help\n");

    fs::remove_dir_all(directory).unwrap();
}

#[cfg(unix)]
#[test]
fn adapter_exit_codes_and_literal_arguments_are_preserved() {
    let directory = temporary_directory();
    write_fake_adapter(&directory, "finance", "0.1.0");
    let marker = directory.join("must-not-exist");
    let payload = format!("$(touch {})", marker.display());

    let literal = run_with_path(&["finance", &payload], &directory);
    assert!(literal.status.success());
    assert_eq!(
        String::from_utf8_lossy(&literal.stdout),
        format!("{payload}\n")
    );
    assert!(!marker.exists());

    let failed = run_with_path(&["finance", "fail"], &directory);
    assert_eq!(failed.status.code(), Some(23));

    fs::remove_dir_all(directory).unwrap();
}

#[cfg(unix)]
#[test]
fn invalid_missing_and_incompatible_adapters_fail_cleanly() {
    let directory = temporary_directory();
    let missing = run_with_path(&["adapter", "doctor", "missing", "--json"], &directory);
    assert_eq!(missing.status.code(), Some(1));
    let report: Value = serde_json::from_slice(&missing.stdout).expect("failure is JSON");
    assert_eq!(report["valid"], false);

    let invalid = run_with_path(&["../finance", "status"], &directory);
    assert_eq!(invalid.status.code(), Some(1));
    assert!(String::from_utf8_lossy(&invalid.stderr).contains("invalid adapter name"));

    let path = write_fake_adapter(&directory, "future", "0.1.0");
    let body = fs::read_to_string(&path)
        .unwrap()
        .replace("\"protocol_version\":2", "\"protocol_version\":99");
    fs::write(&path, body).unwrap();
    let incompatible = run_with_path(&["adapter", "doctor", "future", "--json"], &directory);
    assert_eq!(incompatible.status.code(), Some(1));
    let report: Value = serde_json::from_slice(&incompatible.stdout).expect("failure is JSON");
    assert!(
        report["errors"][0]
            .as_str()
            .unwrap()
            .contains("protocol 99")
    );

    fs::remove_dir_all(directory).unwrap();
}

#[cfg(unix)]
#[test]
fn incompatible_runtime_protocol_fails_before_the_adapter_workflow_runs() {
    use std::os::unix::fs::PermissionsExt;

    let directory = temporary_directory();
    let path = directory.join("anarres-broken");
    fs::write(
        &path,
        "#!/bin/sh\nif [ \"$1\" = \"--anarres-adapter-descriptor\" ]; then printf 'not-json\\n'; exit 0; fi\nif [ \"$1\" = \"--anarres-adapter-protocol\" ]; then printf 'unsupported runtime protocol\\n' >&2; exit 64; fi\ntouch workflow-ran\n",
    )
    .unwrap();
    let mut permissions = fs::metadata(&path).unwrap().permissions();
    permissions.set_mode(0o755);
    fs::set_permissions(&path, permissions).unwrap();

    let output = run_with_path(&["broken", "profile"], &directory);
    assert_eq!(output.status.code(), Some(64));
    assert!(String::from_utf8_lossy(&output.stderr).contains("unsupported runtime protocol"));
    assert!(!directory.join("workflow-ran").exists());

    let doctor = run_with_path(&["adapter", "doctor", "broken", "--json"], &directory);
    assert_eq!(doctor.status.code(), Some(1));
    let report: Value = serde_json::from_slice(&doctor.stdout).expect("failure is JSON");
    assert!(
        report["errors"][0]
            .as_str()
            .unwrap()
            .contains("invalid descriptor JSON")
    );

    fs::remove_dir_all(directory).unwrap();
}

#[cfg(unix)]
#[test]
fn built_in_commands_take_precedence_over_adapter_names() {
    let directory = temporary_directory();
    write_fake_adapter(&directory, "validate", "0.1.0");

    let output = run_with_path(
        &["validate", fixture().to_str().unwrap(), "--json"],
        &directory,
    );
    assert!(
        output.status.success(),
        "{}",
        String::from_utf8_lossy(&output.stderr)
    );
    let report: Value = serde_json::from_slice(&output.stdout).expect("built-in output is JSON");
    assert_eq!(report["valid"], true);

    fs::remove_dir_all(directory).unwrap();
}

#[cfg(unix)]
#[test]
fn adapter_list_reports_shadowed_executables_in_path_order() {
    let root = temporary_directory();
    let first = root.join("first");
    let second = root.join("second");
    fs::create_dir_all(&first).unwrap();
    fs::create_dir_all(&second).unwrap();
    let selected = write_fake_adapter(&first, "finance", "0.1.0");
    let shadowed = write_fake_adapter(&second, "finance", "0.2.0");
    let path = std::env::join_paths([&first, &second]).unwrap();

    let listed = run_with_path(&["adapter", "list", "--json"], Path::new(&path));
    assert!(listed.status.success());
    let report: Value = serde_json::from_slice(&listed.stdout).expect("list is JSON");
    assert_eq!(
        report["adapters"][0]["path"],
        fs::canonicalize(selected)
            .unwrap()
            .to_string_lossy()
            .as_ref()
    );
    assert_eq!(
        report["adapters"][0]["shadowed_paths"][0],
        fs::canonicalize(shadowed)
            .unwrap()
            .to_string_lossy()
            .as_ref()
    );

    fs::remove_dir_all(root).unwrap();
}
