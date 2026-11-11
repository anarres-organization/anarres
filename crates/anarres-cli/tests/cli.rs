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

fn probe_run_fixture() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("../../examples/environment-processing/probe-run")
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
    assert!(stdout.contains("anarres demo"));
    assert!(stdout.contains("anarres adapter list"));
    assert!(stdout.contains("anarres adapter doctor <name>"));
    assert!(stdout.contains("anarres inspect <directory>"));
    assert!(stdout.contains("anarres qualify <directory>"));
    assert!(stdout.contains("anarres measure <measurement>"));
    assert!(stdout.contains("anarres design <environment-a.json> <environment-b.json>"));
    assert!(stdout.contains("whether qualification and policy probing are available"));
}

#[test]
fn demo_writes_compares_and_validates_two_records() {
    let directory = temporary_directory();
    let record = directory.join("demo.json");
    let comparison = directory.join("demo-alternative.json");
    let output = run(&["demo", "--output", record.to_str().unwrap()]);
    assert!(
        output.status.success(),
        "{}",
        String::from_utf8_lossy(&output.stderr)
    );
    let stdout = String::from_utf8(output.stdout).expect("stdout is UTF-8");
    assert_eq!(
        stdout,
        format!(
            "Anarres demo\nRepeated attempts from one starting policy are qualified, measured, and compared.\n\nInput\n    Starting policy    synthetic-policy-v1\n    Candidates         2 synthetic alternatives\n    Task groups        5 per candidate\n    Group size         4 attempts\n    Measurements       outcomes, admitted advantage mass, and generated tokens\n    Validity           oracle, no-op, and infrastructure checks\n\n1. Qualify\n  ✓ Qualified    math-reference-demo-v1\n    Admitted           2\n    Reserve            1\n    Repair             1\n    Quarantine         1\n\n2. Measure\n  ✓ Measured     math-reference-demo-v1\n    Signal density     833.3333 advantage mass / million generated tokens\n    Effective coverage 0.6533 (0 to 1)\n    Evidence           3 eligible task groups, 4,200 generated tokens\n\n3. Compare\n  ✓ Compatible   candidate panel\n    Policy             synthetic-policy-v1\n    Revision           synthetic-reference-only\n    Candidates         2\n\nENVIRONMENT               SIGNAL / 1M   COVERAGE  ADMITTED   REPAIR\nmath-alternative-demo-v1     214.2857     0.4154         2        1\nmath-reference-demo-v1       833.3333     0.6533         2        1\n\n    Signal span        214.2857 to 833.3333\n    Coverage           0.4154 to 0.6533\n\nArtifacts\n  ✓ Wrote        {}\n  ✓ Wrote        {}\n  ✓ Validated    2 content digests\n\nNext  anarres design {} {}\n    Use your data: anarres qualify --help\n",
            record.display(),
            comparison.display(),
            record.display(),
            comparison.display()
        )
    );

    let raw: Value = serde_json::from_slice(&fs::read(&record).expect("record is written"))
        .expect("record is JSON");
    assert_eq!(raw["environment_id"], "math-reference-demo-v1");
    assert_eq!(raw["coordinates"]["prompt_count"], 3);
    let alternative: Value =
        serde_json::from_slice(&fs::read(&comparison).expect("comparison record is written"))
            .expect("comparison record is JSON");
    assert_eq!(alternative["environment_id"], "math-alternative-demo-v1");

    let designed = run(&[
        "design",
        record.to_str().unwrap(),
        comparison.to_str().unwrap(),
    ]);
    assert!(designed.status.success());
    assert!(String::from_utf8_lossy(&designed.stdout).contains("2"));

    let repeated = run(&["demo", "--output", record.to_str().unwrap()]);
    assert!(repeated.status.success());

    fs::write(&record, b"changed\n").expect("record is changed");
    let changed = run(&["demo", "--output", record.to_str().unwrap()]);
    assert_eq!(changed.status.code(), Some(1));
    assert!(String::from_utf8_lossy(&changed.stderr).contains("different content"));

    fs::remove_dir_all(directory).expect("temporary directory is removed");
}

#[test]
fn core_human_output_has_a_stable_layout() {
    let directory = temporary_directory();
    let record = directory.join("environment.json");
    let fixture = fixture();

    let qualified = run(&["qualify", fixture.to_str().unwrap()]);
    assert!(qualified.status.success());
    assert_eq!(
        String::from_utf8(qualified.stdout).expect("stdout is UTF-8"),
        "  ✓ Qualified    math-reference-demo-v1\n    Policy             synthetic-policy-v1\n    Admitted           2\n    Reserve            1\n    Repair             1\n    Quarantine         1\n\nAction required\n  ! quarantine   math-demo-004            noop accepted\n  ! repair       math-demo-005            infrastructure invalid\n"
    );

    let measured = run(&[
        "measure",
        fixture.to_str().unwrap(),
        "--output",
        record.to_str().unwrap(),
    ]);
    assert!(measured.status.success());
    assert_eq!(
        String::from_utf8(measured.stdout).expect("stdout is UTF-8"),
        format!(
            "  ✓ Measured     math-reference-demo-v1\n    Policy             synthetic-policy-v1\n    Signal density     833.3333 advantage mass / million generated tokens\n    Effective coverage 0.6533 (0 to 1)\n    Evidence           3 eligible task groups, 4,200 generated tokens\n    Record             {}\n    Digest  sha256:5471a6e0fb121640260770060a3b858f2e31100a66b73eb2210bd59603dd76d9\n",
            record.display()
        )
    );

    let validated = run(&["validate", record.to_str().unwrap()]);
    assert!(validated.status.success());
    assert_eq!(
        String::from_utf8(validated.stdout).expect("stdout is UTF-8"),
        format!(
            "  ✓ Valid        environment manifest\n    Path               {}\n",
            record.display()
        )
    );

    fs::remove_dir_all(directory).expect("temporary directory is removed");
}

#[test]
fn color_is_tty_aware_and_json_remains_unstyled() {
    let directory = temporary_directory();
    let plain_record = directory.join("plain.json");
    let color_record = directory.join("color.json");
    let no_color_record = directory.join("no-color.json");

    let automatic = run(&[
        "demo",
        "--output",
        plain_record.to_str().unwrap(),
        "--color",
        "auto",
    ]);
    assert!(automatic.status.success());
    assert!(!automatic.stdout.contains(&0x1b));

    let colored = run(&[
        "demo",
        "--output",
        color_record.to_str().unwrap(),
        "--color",
        "always",
    ]);
    assert!(colored.status.success());
    assert!(colored.stdout.contains(&0x1b));

    let no_color = Command::new(binary())
        .args([
            "demo",
            "--output",
            no_color_record.to_str().unwrap(),
            "--color",
            "auto",
        ])
        .env("NO_COLOR", "1")
        .output()
        .expect("CLI process starts");
    assert!(no_color.status.success());
    assert!(!no_color.stdout.contains(&0x1b));

    let json = run(&[
        "qualify",
        fixture().to_str().unwrap(),
        "--json",
        "--color",
        "always",
    ]);
    assert!(json.status.success());
    assert!(!json.stdout.contains(&0x1b));
    serde_json::from_slice::<Value>(&json.stdout).expect("colored mode preserves valid JSON");

    fs::remove_dir_all(directory).expect("temporary directory is removed");
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

#[cfg(unix)]
fn write_fake_source_adapter(directory: &Path, name: &str) -> PathBuf {
    use std::os::unix::fs::PermissionsExt;

    let path = directory.join(format!("anarres-{name}"));
    let descriptor = format!(
        r#"{{"schema_version":"anarres.adapter-descriptor.v1","name":"{name}","version":"0.1.0","protocol_version":2,"domain":"agentic-systems","executable":"anarres-{name}","profile_schema_versions":["anarres.environment-profile-input.v1"],"capabilities":["policy-probe","source-qualification"],"measurement_contracts":[],"source_formats":["openenv"]}}"#
    );
    let script = format!(
        "#!/bin/sh\nif [ \"$1\" = \"--anarres-adapter-descriptor\" ]; then\n  printf '%s\\n' '{descriptor}'\n  exit 0\nfi\nif [ \"$1\" != \"--anarres-adapter-protocol\" ] || [ \"$2\" != \"2\" ] || [ \"$3\" != \"--anarres-adapter-name\" ] || [ \"$4\" != \"{name}\" ]; then\n  exit 64\nfi\nshift 4\nprintf '%s\\n' \"$@\"\n"
    );
    fs::write(&path, script).expect("fake source adapter is written");
    let mut permissions = fs::metadata(&path).unwrap().permissions();
    permissions.set_mode(0o755);
    fs::set_permissions(&path, permissions).unwrap();
    path
}

fn write_environment_source(directory: &Path, adapter: &str) -> PathBuf {
    let environment = directory.join("candidate");
    fs::create_dir_all(environment.join("native-environment"))
        .expect("native environment is created");
    let manifest = environment.join("anarres.toml");
    fs::write(
        &manifest,
        format!(
            "schema_version = \"anarres.environment-source.v1\"\n\
             environment_id = \"candidate-a\"\n\
             domain = \"agentic-systems\"\n\
             adapter = \"{adapter}\"\n\
             adapter_version = \"0.1.0\"\n\
             native_format = \"openenv\"\n\n\
             [source]\n\
             uri = \"./native-environment\"\n\
             revision = \"git:0123456789abcdef0123456789abcdef01234567\"\n\
             license = \"Apache-2.0\"\n"
        ),
    )
    .expect("environment source is written");
    environment
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

#[cfg(unix)]
#[test]
fn environment_source_inspects_qualifies_and_probes_through_one_adapter() {
    let directory = temporary_directory();
    let bin = directory.join("bin");
    fs::create_dir_all(&bin).expect("bin directory is created");
    write_fake_source_adapter(&bin, "openenv");

    let initialized = directory.join("initialized-candidate");
    fs::create_dir_all(&initialized).expect("initialization source is created");
    let init = run_with_path(
        &[
            "init",
            initialized.to_str().unwrap(),
            "--adapter",
            "openenv",
            "--revision",
            "git:0123456789abcdef0123456789abcdef01234567",
            "--license",
            "Apache-2.0",
            "--json",
        ],
        &bin,
    );
    assert!(
        init.status.success(),
        "{}",
        String::from_utf8_lossy(&init.stderr)
    );
    let initialized_report: Value =
        serde_json::from_slice(&init.stdout).expect("initialization is JSON");
    assert_eq!(
        initialized_report["environment_id"],
        "initialized-candidate"
    );
    assert_eq!(initialized_report["domain"], "agentic-systems");
    assert_eq!(initialized_report["adapter_version"], "0.1.0");
    assert_eq!(initialized_report["native_format"], "openenv");
    let initialized_manifest =
        fs::read_to_string(initialized.join("anarres.toml")).expect("manifest is readable");
    assert!(initialized_manifest.contains("uri = \".\""));

    let human_init = run_with_path(
        &[
            "init",
            initialized.to_str().unwrap(),
            "--adapter",
            "openenv",
            "--revision",
            "git:0123456789abcdef0123456789abcdef01234567",
            "--license",
            "Apache-2.0",
            "--force",
        ],
        &bin,
    );
    assert!(human_init.status.success());
    let human_output = String::from_utf8(human_init.stdout).expect("human output is UTF-8");
    assert!(human_output.contains("Environment source"));
    assert!(human_output.contains("Initialized"));
    assert!(human_output.contains("Adapter version"));
    assert!(human_output.contains("Next"));
    assert!(human_output.contains("anarres inspect"));

    let repeated_init = run_with_path(
        &[
            "init",
            initialized.to_str().unwrap(),
            "--adapter",
            "openenv",
            "--revision",
            "git:0123456789abcdef0123456789abcdef01234567",
            "--license",
            "Apache-2.0",
        ],
        &bin,
    );
    assert_eq!(repeated_init.status.code(), Some(1));
    assert!(String::from_utf8_lossy(&repeated_init.stderr).contains("--force"));

    let environment = write_environment_source(&directory, "openenv");

    let inspected = run_with_path(&["inspect", environment.to_str().unwrap(), "--json"], &bin);
    assert!(
        inspected.status.success(),
        "{}",
        String::from_utf8_lossy(&inspected.stderr)
    );
    let report: Value = serde_json::from_slice(&inspected.stdout).expect("inspection is JSON");
    assert_eq!(report["environment_id"], "candidate-a");
    assert_eq!(report["native_format"], "openenv");
    assert_eq!(report["adapter_installed"], true);
    assert_eq!(report["required_adapter_version"], "0.1.0");
    assert_eq!(report["installed_adapter_version"], "0.1.0");
    assert_eq!(report["can_qualify"], true);
    assert_eq!(report["can_probe"], true);
    assert_eq!(report["issues"], serde_json::json!([]));

    let qualified = run_with_path(&["qualify", environment.to_str().unwrap(), "--json"], &bin);
    assert!(qualified.status.success());
    let qualified_args = String::from_utf8(qualified.stdout).expect("stdout is UTF-8");
    assert!(qualified_args.starts_with("qualify-source\n--manifest\n"));
    assert!(qualified_args.ends_with("--json\n"));

    let output = directory.join("probe-run");
    let probed = run_with_path(
        &[
            "probe",
            environment.to_str().unwrap(),
            "--policy",
            "qwen/example",
            "--policy-revision",
            "sha256:abc",
            "--output",
            output.to_str().unwrap(),
            "--",
            "--endpoint",
            "http://127.0.0.1:8000/v1",
        ],
        &bin,
    );
    assert!(
        probed.status.success(),
        "{}",
        String::from_utf8_lossy(&probed.stderr)
    );
    let probed_args = String::from_utf8(probed.stdout).expect("stdout is UTF-8");
    assert!(probed_args.starts_with("probe-source\n--manifest\n"));
    assert!(probed_args.contains("--policy\nqwen/example\n"));
    assert!(probed_args.contains("--policy-revision\nsha256:abc\n"));
    assert!(probed_args.ends_with("--endpoint\nhttp://127.0.0.1:8000/v1\n"));

    let validated = run(&[
        "validate",
        environment.join("anarres.toml").to_str().unwrap(),
        "--json",
    ]);
    assert!(validated.status.success());
    let validation: Value = serde_json::from_slice(&validated.stdout).expect("validation is JSON");
    assert_eq!(
        validation["records"][0]["record_type"],
        "environment source"
    );

    let measured = run(&[
        "measure",
        environment.to_str().unwrap(),
        "--output",
        directory.join("invalid.json").to_str().unwrap(),
    ]);
    assert_eq!(measured.status.code(), Some(1));
    assert!(String::from_utf8_lossy(&measured.stderr).contains("run `anarres probe` first"));

    let manifest = environment.join("anarres.toml");
    fs::write(
        &manifest,
        format!(
            "{}unexpected = true\n",
            fs::read_to_string(&manifest).unwrap()
        ),
    )
    .unwrap();
    let invalid = run(&["validate", manifest.to_str().unwrap(), "--json"]);
    assert_eq!(invalid.status.code(), Some(1));
    let invalid_report: Value =
        serde_json::from_slice(&invalid.stdout).expect("invalid report is JSON");
    assert!(
        invalid_report["records"][0]["error"]
            .as_str()
            .unwrap()
            .contains("unknown field")
    );

    fs::remove_dir_all(directory).expect("temporary directory is removed");
}

#[test]
fn raw_attempt_directory_qualifies_measures_and_validates() {
    let directory = temporary_directory();
    let manifest = directory.join("raw-environment.json");
    let probe_run = probe_run_fixture();

    let qualified = run(&["qualify", probe_run.to_str().unwrap(), "--json"]);
    assert!(
        qualified.status.success(),
        "{}",
        String::from_utf8_lossy(&qualified.stderr)
    );
    let report: Value = serde_json::from_slice(&qualified.stdout).expect("stdout is JSON");
    assert_eq!(report["attempt_count"], 20);
    assert_eq!(report["status_counts"]["admitted"], 2);
    assert_eq!(report["status_counts"]["repair"], 1);

    let measured = run(&[
        "measure",
        probe_run.to_str().unwrap(),
        "--output",
        manifest.to_str().unwrap(),
    ]);
    assert!(
        measured.status.success(),
        "{}",
        String::from_utf8_lossy(&measured.stderr)
    );
    let record: Value = serde_json::from_slice(&fs::read(&manifest).expect("manifest is written"))
        .expect("manifest is JSON");
    assert_eq!(record["coordinates"]["generated_action_tokens"], 4_200);
    let mass = record["coordinates"]["total_admitted_advantage_mass"]
        .as_f64()
        .expect("mass is numeric");
    assert!((mass - 14.0 / 3.0).abs() < 1e-12);

    let validated = run(&[
        "validate",
        probe_run.to_str().unwrap(),
        manifest.to_str().unwrap(),
        "--json",
    ]);
    assert!(validated.status.success());
    let validation: Value = serde_json::from_slice(&validated.stdout).expect("stdout is JSON");
    assert_eq!(validation["valid"], true);
    assert_eq!(validation["records"][0]["record_type"], "probe run");

    fs::remove_dir_all(directory).expect("temporary directory is removed");
}

#[test]
fn raw_attempt_digest_is_independent_of_completion_order() {
    let directory = temporary_directory();
    let ordered = directory.join("ordered");
    let reversed = directory.join("reversed");
    fs::create_dir_all(&ordered).expect("ordered directory is created");
    fs::create_dir_all(&reversed).expect("reversed directory is created");
    let fixture = probe_run_fixture();
    let metadata = fs::read(fixture.join("probe.json")).expect("metadata is read");
    fs::write(ordered.join("probe.json"), &metadata).expect("ordered metadata is written");
    fs::write(reversed.join("probe.json"), metadata).expect("reversed metadata is written");
    let attempts = fs::read_to_string(fixture.join("attempts.jsonl")).expect("attempts are read");
    fs::write(ordered.join("attempts.jsonl"), &attempts).expect("attempts are written");
    let reversed_attempts = attempts.lines().rev().collect::<Vec<_>>().join("\n") + "\n";
    fs::write(reversed.join("attempts.jsonl"), reversed_attempts)
        .expect("reversed attempts are written");

    let ordered_record = directory.join("ordered.json");
    let reversed_record = directory.join("reversed.json");
    for (probe_run, record) in [(&ordered, &ordered_record), (&reversed, &reversed_record)] {
        let measured = run(&[
            "measure",
            probe_run.to_str().unwrap(),
            "--output",
            record.to_str().unwrap(),
        ]);
        assert!(
            measured.status.success(),
            "{}",
            String::from_utf8_lossy(&measured.stderr)
        );
    }
    assert_eq!(
        fs::read(ordered_record).expect("ordered record is read"),
        fs::read(reversed_record).expect("reversed record is read")
    );

    fs::remove_dir_all(directory).expect("temporary directory is removed");
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

    let human = run(&[
        "design",
        profile_a.to_str().unwrap(),
        profile_b.to_str().unwrap(),
    ]);
    assert!(human.status.success());
    let human = String::from_utf8(human.stdout).expect("stdout is UTF-8");
    assert!(human.contains("eligible_response_fraction"));
    assert!(!human.contains('…'));

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
