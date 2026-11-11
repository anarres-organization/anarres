use std::collections::{BTreeMap, BTreeSet};
use std::env;
use std::ffi::OsString;
use std::fs;
use std::io::{self, Read};
use std::path::{Path, PathBuf};
use std::process::{Command, ExitStatus, Stdio};
use std::thread;
use std::time::{Duration, Instant};

use serde::{Deserialize, Serialize};

pub(crate) const ADAPTER_DESCRIPTOR_SCHEMA: &str = "anarres.adapter-descriptor.v1";
const ADAPTER_LIST_SCHEMA: &str = "anarres.adapter-list.v1";
const ADAPTER_DOCTOR_SCHEMA: &str = "anarres.adapter-doctor.v1";
const ADAPTER_PROTOCOL_VERSION: u64 = 2;
const ADAPTER_PREFIX: &str = "anarres-";
const ADAPTER_PROTOCOL_FLAG: &str = "--anarres-adapter-protocol";
const ADAPTER_NAME_FLAG: &str = "--anarres-adapter-name";
const DESCRIPTOR_TIMEOUT: Duration = Duration::from_secs(5);
const DESCRIPTOR_OUTPUT_LIMIT: usize = 256 * 1024;

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq)]
#[serde(deny_unknown_fields)]
pub(crate) struct AdapterDescriptor {
    pub(crate) schema_version: String,
    pub(crate) name: String,
    pub(crate) version: String,
    pub(crate) protocol_version: u64,
    pub(crate) domain: String,
    pub(crate) executable: String,
    pub(crate) profile_schema_versions: Vec<String>,
    pub(crate) capabilities: Vec<String>,
    #[serde(default)]
    pub(crate) measurement_contracts: Vec<String>,
    #[serde(default)]
    pub(crate) source_formats: Vec<String>,
}

#[derive(Clone, Debug, Serialize)]
struct AdapterInstallation {
    name: String,
    path: String,
    shadowed_paths: Vec<String>,
}

#[derive(Clone, Debug)]
struct ResolvedAdapter {
    name: String,
    path: PathBuf,
    shadowed_paths: Vec<PathBuf>,
}

#[derive(Debug, Serialize)]
struct AdapterListReport {
    schema_version: &'static str,
    adapters: Vec<AdapterInstallation>,
}

#[derive(Debug, Serialize)]
struct AdapterDoctorReport {
    schema_version: &'static str,
    name: String,
    path: Option<String>,
    shadowed_paths: Vec<String>,
    valid: bool,
    descriptor: Option<AdapterDescriptor>,
    errors: Vec<String>,
}

pub(crate) fn list(as_json: bool) -> Result<i32, String> {
    let adapters = discover_adapters()?;
    let installations = adapters
        .values()
        .map(AdapterInstallation::from)
        .collect::<Vec<_>>();
    if as_json {
        print_json(&AdapterListReport {
            schema_version: ADAPTER_LIST_SCHEMA,
            adapters: installations,
        })?;
        return Ok(0);
    }

    if installations.is_empty() {
        crate::ui::title("Installed adapters");
        crate::ui::muted("None found on PATH.");
        crate::ui::next("see docs/adapters.md to add a domain workflow");
        return Ok(0);
    }
    crate::ui::title("Installed adapters");
    crate::ui::blank();
    for adapter in installations {
        crate::ui::success(&adapter.name, &adapter.path);
        for shadowed in adapter.shadowed_paths {
            crate::ui::warning_stderr(format_args!(
                "adapter '{}' at {} is shadowed by an earlier PATH entry",
                adapter.name, shadowed
            ));
        }
    }
    Ok(0)
}

pub(crate) fn doctor(name: &str, as_json: bool) -> Result<i32, String> {
    validate_adapter_name(name)?;
    let mut report = AdapterDoctorReport {
        schema_version: ADAPTER_DOCTOR_SCHEMA,
        name: name.to_owned(),
        path: None,
        shadowed_paths: Vec::new(),
        valid: false,
        descriptor: None,
        errors: Vec::new(),
    };

    match resolve_adapter(name) {
        Ok(adapter) => {
            report.path = Some(display_path(&adapter.path));
            report.shadowed_paths = adapter
                .shadowed_paths
                .iter()
                .map(|path| display_path(path))
                .collect();
            match read_descriptor(&adapter) {
                Ok(descriptor) => {
                    report.valid = true;
                    report.descriptor = Some(descriptor);
                }
                Err(error) => report.errors.push(error),
            }
        }
        Err(error) => report.errors.push(error),
    }

    if as_json {
        print_json(&report)?;
    } else if report.valid {
        let descriptor = report.descriptor.as_ref().expect("valid descriptor exists");
        crate::ui::success("Ready", &descriptor.name);
        crate::ui::field("Domain", &descriptor.domain);
        crate::ui::field("Version", &descriptor.version);
        crate::ui::field("Protocol", descriptor.protocol_version);
        crate::ui::field("Executable", report.path.as_deref().unwrap_or("unknown"));
        if !descriptor.source_formats.is_empty() {
            crate::ui::field("Source formats", descriptor.source_formats.join(", "));
        }
        for path in &report.shadowed_paths {
            crate::ui::warning_stderr(format_args!(
                "adapter '{}' at {} is shadowed by an earlier PATH entry",
                name, path
            ));
        }
    } else {
        for error in &report.errors {
            crate::ui::error(error);
        }
    }
    Ok(i32::from(!report.valid))
}

pub(crate) fn run(name: &str, arguments: &[OsString]) -> Result<i32, String> {
    validate_adapter_name(name)?;
    let adapter = resolve_adapter(name)?;
    let status = Command::new(&adapter.path)
        .arg(ADAPTER_PROTOCOL_FLAG)
        .arg(ADAPTER_PROTOCOL_VERSION.to_string())
        .arg(ADAPTER_NAME_FLAG)
        .arg(name)
        .args(arguments)
        .status()
        .map_err(|error| format!("failed to start adapter '{name}': {error}"))?;
    Ok(exit_code(status))
}

pub(crate) fn descriptor(name: &str) -> Result<AdapterDescriptor, String> {
    validate_adapter_name(name)?;
    let adapter = resolve_adapter(name)?;
    read_descriptor(&adapter)
}

fn discover_adapters() -> Result<BTreeMap<String, ResolvedAdapter>, String> {
    let path = env::var_os("PATH").unwrap_or_default();
    let mut found: BTreeMap<String, Vec<PathBuf>> = BTreeMap::new();
    let mut seen_paths = BTreeSet::new();
    for directory in env::split_paths(&path) {
        if directory.as_os_str().is_empty() {
            continue;
        }
        let Ok(entries) = fs::read_dir(&directory) else {
            continue;
        };
        for entry in entries.flatten() {
            let candidate = entry.path();
            if !is_executable(&candidate) {
                continue;
            }
            let Some(name) = adapter_name_from_path(&candidate) else {
                continue;
            };
            if validate_adapter_name(&name).is_err() {
                continue;
            }
            let canonical = fs::canonicalize(&candidate).unwrap_or(candidate);
            if !seen_paths.insert(canonical.clone()) {
                continue;
            }
            found.entry(name).or_default().push(canonical);
        }
    }

    Ok(found
        .into_iter()
        .filter_map(|(name, mut paths)| {
            if paths.is_empty() {
                return None;
            }
            let path = paths.remove(0);
            Some((
                name.clone(),
                ResolvedAdapter {
                    name,
                    path,
                    shadowed_paths: paths,
                },
            ))
        })
        .collect())
}

fn resolve_adapter(name: &str) -> Result<ResolvedAdapter, String> {
    let path = env::var_os("PATH").unwrap_or_default();
    let mut paths = Vec::new();
    let mut seen = BTreeSet::new();
    for directory in env::split_paths(&path) {
        if directory.as_os_str().is_empty() {
            continue;
        }
        for filename in executable_filenames(name) {
            let candidate = directory.join(filename);
            if !is_executable(&candidate) {
                continue;
            }
            let canonical = fs::canonicalize(&candidate).unwrap_or(candidate);
            if seen.insert(canonical.clone()) {
                paths.push(canonical);
            }
        }
    }
    if paths.is_empty() {
        return Err(format!(
            "adapter '{name}' was not found on PATH\nhint: run `anarres adapter list` or install the {name} domain workflow"
        ));
    }
    let path = paths.remove(0);
    Ok(ResolvedAdapter {
        name: name.to_owned(),
        path,
        shadowed_paths: paths,
    })
}

fn executable_filenames(name: &str) -> Vec<OsString> {
    let base = format!("{ADAPTER_PREFIX}{name}");
    #[cfg(windows)]
    {
        [".exe", ".cmd", ".bat", ""]
            .into_iter()
            .map(|suffix| format!("{base}{suffix}").into())
            .collect()
    }
    #[cfg(not(windows))]
    {
        vec![base.into()]
    }
}

fn read_descriptor(adapter: &ResolvedAdapter) -> Result<AdapterDescriptor, String> {
    let output = descriptor_output(adapter, DESCRIPTOR_TIMEOUT)?;
    if !output.status.success() {
        let detail = String::from_utf8_lossy(&output.stderr).trim().to_owned();
        return Err(if detail.is_empty() {
            format!(
                "adapter '{}' descriptor command exited with status {}",
                adapter.name, output.status
            )
        } else {
            format!("adapter '{}' descriptor failed: {detail}", adapter.name)
        });
    }
    let descriptor: AdapterDescriptor =
        serde_json::from_slice(&output.stdout).map_err(|error| {
            format!(
                "adapter '{}' returned invalid descriptor JSON: {error}",
                adapter.name
            )
        })?;
    validate_descriptor(adapter, &descriptor)?;
    Ok(descriptor)
}

fn descriptor_output(
    adapter: &ResolvedAdapter,
    timeout: Duration,
) -> Result<std::process::Output, String> {
    let mut child = Command::new(&adapter.path)
        .arg("--anarres-adapter-descriptor")
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|error| {
            format!(
                "failed to query adapter '{}' at {}: {error}",
                adapter.name,
                display_path(&adapter.path)
            )
        })?;
    let stdout = child
        .stdout
        .take()
        .ok_or_else(|| format!("failed to capture adapter '{}' stdout", adapter.name))?;
    let stderr = child
        .stderr
        .take()
        .ok_or_else(|| format!("failed to capture adapter '{}' stderr", adapter.name))?;
    let stdout_reader = thread::spawn(move || read_capped(stdout, DESCRIPTOR_OUTPUT_LIMIT));
    let stderr_reader = thread::spawn(move || read_capped(stderr, DESCRIPTOR_OUTPUT_LIMIT));
    let deadline = Instant::now() + timeout;

    let status = loop {
        match child.try_wait() {
            Ok(Some(status)) => break status,
            Ok(None) if Instant::now() < deadline => thread::sleep(Duration::from_millis(5)),
            Ok(None) => {
                let _ = child.kill();
                let _ = child.wait();
                return Err(format!(
                    "adapter '{}' descriptor timed out after {:.1} seconds",
                    adapter.name,
                    timeout.as_secs_f64()
                ));
            }
            Err(error) => {
                let _ = child.kill();
                let _ = child.wait();
                return Err(format!(
                    "failed while waiting for adapter '{}' descriptor: {error}",
                    adapter.name
                ));
            }
        }
    };
    let (stdout, stdout_exceeded) = join_reader(stdout_reader, deadline, &adapter.name, "stdout")?;
    let (stderr, stderr_exceeded) = join_reader(stderr_reader, deadline, &adapter.name, "stderr")?;
    if stdout_exceeded || stderr_exceeded {
        return Err(format!(
            "adapter '{}' descriptor output exceeded {} bytes",
            adapter.name, DESCRIPTOR_OUTPUT_LIMIT
        ));
    }
    Ok(std::process::Output {
        status,
        stdout,
        stderr,
    })
}

fn read_capped<R: Read>(mut reader: R, limit: usize) -> io::Result<(Vec<u8>, bool)> {
    let mut output = Vec::new();
    let mut exceeded = false;
    let mut buffer = [0_u8; 8192];
    loop {
        let count = reader.read(&mut buffer)?;
        if count == 0 {
            break;
        }
        let available = limit.saturating_sub(output.len());
        output.extend_from_slice(&buffer[..count.min(available)]);
        exceeded |= count > available;
    }
    Ok((output, exceeded))
}

fn join_reader(
    reader: thread::JoinHandle<io::Result<(Vec<u8>, bool)>>,
    deadline: Instant,
    adapter: &str,
    stream: &str,
) -> Result<(Vec<u8>, bool), String> {
    while !reader.is_finished() && Instant::now() < deadline {
        thread::sleep(Duration::from_millis(5));
    }
    if !reader.is_finished() {
        return Err(format!(
            "adapter '{adapter}' descriptor {stream} remained open after the process exited"
        ));
    }
    reader
        .join()
        .map_err(|_| format!("adapter '{adapter}' descriptor {stream} reader panicked"))?
        .map_err(|error| format!("failed to read adapter '{adapter}' descriptor {stream}: {error}"))
}

fn validate_descriptor(
    adapter: &ResolvedAdapter,
    descriptor: &AdapterDescriptor,
) -> Result<(), String> {
    if descriptor.schema_version != ADAPTER_DESCRIPTOR_SCHEMA {
        return Err(format!(
            "adapter '{}' uses unsupported descriptor schema '{}'",
            adapter.name, descriptor.schema_version
        ));
    }
    if descriptor.protocol_version != ADAPTER_PROTOCOL_VERSION {
        return Err(format!(
            "adapter '{}' uses protocol {}, but this CLI supports protocol {}",
            adapter.name, descriptor.protocol_version, ADAPTER_PROTOCOL_VERSION
        ));
    }
    if descriptor.name != adapter.name {
        return Err(format!(
            "adapter name '{}' does not match executable name '{}'",
            descriptor.name, adapter.name
        ));
    }
    let expected_executable = format!("{ADAPTER_PREFIX}{}", adapter.name);
    if descriptor.executable != expected_executable {
        return Err(format!(
            "adapter '{}' declares executable '{}', expected '{}'",
            adapter.name, descriptor.executable, expected_executable
        ));
    }
    for (field, value) in [
        ("version", descriptor.version.as_str()),
        ("domain", descriptor.domain.as_str()),
    ] {
        if value.trim().is_empty() {
            return Err(format!("adapter '{}' has an empty {field}", adapter.name));
        }
    }
    validate_sorted_unique(
        &adapter.name,
        "profile_schema_versions",
        &descriptor.profile_schema_versions,
        true,
    )?;
    validate_sorted_unique(
        &adapter.name,
        "capabilities",
        &descriptor.capabilities,
        true,
    )?;
    validate_sorted_unique(
        &adapter.name,
        "measurement_contracts",
        &descriptor.measurement_contracts,
        false,
    )?;
    validate_sorted_unique(
        &adapter.name,
        "source_formats",
        &descriptor.source_formats,
        false,
    )?;
    Ok(())
}

fn validate_sorted_unique(
    adapter: &str,
    field: &str,
    values: &[String],
    required: bool,
) -> Result<(), String> {
    if required && values.is_empty() {
        return Err(format!("adapter '{adapter}' has no {field}"));
    }
    if values.iter().any(|value| value.trim().is_empty()) {
        return Err(format!("adapter '{adapter}' has an empty value in {field}"));
    }
    if values.windows(2).any(|pair| pair[0] >= pair[1]) {
        return Err(format!(
            "adapter '{adapter}' must declare {field} in sorted, unique order"
        ));
    }
    Ok(())
}

pub(crate) fn validate_adapter_name(name: &str) -> Result<(), String> {
    let valid = !name.is_empty()
        && name.len() <= 64
        && name.bytes().enumerate().all(|(index, byte)| match byte {
            b'a'..=b'z' | b'0'..=b'9' => true,
            b'-' => index > 0 && index + 1 < name.len(),
            _ => false,
        })
        && !name.contains("--");
    if valid {
        Ok(())
    } else {
        Err(format!(
            "invalid adapter name '{name}'; use lowercase letters, digits, and single interior hyphens"
        ))
    }
}

fn adapter_name_from_path(path: &Path) -> Option<String> {
    let filename = path.file_name()?.to_str()?;
    #[cfg(windows)]
    let filename = [".exe", ".cmd", ".bat"]
        .iter()
        .find_map(|suffix| filename.strip_suffix(suffix))
        .unwrap_or(filename);
    filename.strip_prefix(ADAPTER_PREFIX).map(str::to_owned)
}

fn is_executable(path: &Path) -> bool {
    let Ok(metadata) = fs::metadata(path) else {
        return false;
    };
    if !metadata.is_file() {
        return false;
    }
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        metadata.permissions().mode() & 0o111 != 0
    }
    #[cfg(not(unix))]
    {
        true
    }
}

fn exit_code(status: ExitStatus) -> i32 {
    if let Some(code) = status.code() {
        return code;
    }
    #[cfg(unix)]
    {
        use std::os::unix::process::ExitStatusExt;
        status.signal().map_or(1, |signal| 128 + signal)
    }
    #[cfg(not(unix))]
    {
        1
    }
}

fn display_path(path: &Path) -> String {
    path.to_string_lossy().into_owned()
}

fn print_json<T: Serialize>(value: &T) -> Result<(), String> {
    let rendered = serde_json::to_string_pretty(value).map_err(|error| error.to_string())?;
    println!("{rendered}");
    Ok(())
}

impl From<&ResolvedAdapter> for AdapterInstallation {
    fn from(adapter: &ResolvedAdapter) -> Self {
        Self {
            name: adapter.name.clone(),
            path: display_path(&adapter.path),
            shadowed_paths: adapter
                .shadowed_paths
                .iter()
                .map(|path| display_path(path))
                .collect(),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    static NEXT_TEST_FILE: std::sync::atomic::AtomicU64 = std::sync::atomic::AtomicU64::new(0);

    #[test]
    fn descriptor_output_is_capped() {
        let (output, exceeded) = read_capped(&b"abcdef"[..], 4).expect("read succeeds");
        assert_eq!(output, b"abcd");
        assert!(exceeded);
    }

    #[cfg(unix)]
    #[test]
    fn descriptor_query_times_out() {
        use std::os::unix::fs::PermissionsExt;

        let path = env::temp_dir().join(format!(
            "anarres-adapter-timeout-{}-{}",
            std::process::id(),
            NEXT_TEST_FILE.fetch_add(1, std::sync::atomic::Ordering::Relaxed)
        ));
        fs::write(&path, "#!/bin/sh\nwhile :; do :; done\n").expect("write test adapter");
        let mut permissions = fs::metadata(&path).expect("adapter metadata").permissions();
        permissions.set_mode(0o700);
        fs::set_permissions(&path, permissions).expect("mark adapter executable");
        let adapter = ResolvedAdapter {
            name: "timeout".into(),
            path: path.clone(),
            shadowed_paths: Vec::new(),
        };
        let error = descriptor_output(&adapter, Duration::from_millis(25))
            .expect_err("descriptor should time out");
        fs::remove_file(path).expect("remove test adapter");
        assert!(error.contains("timed out"));
    }

    #[test]
    fn adapter_names_are_strict_slugs() {
        for valid in ["finance", "formal-verification", "robotics2"] {
            assert!(validate_adapter_name(valid).is_ok());
        }
        for invalid in [
            "",
            "Finance",
            "finance_adapter",
            "../finance",
            "finance--audit",
            "-finance",
        ] {
            assert!(
                validate_adapter_name(invalid).is_err(),
                "accepted {invalid}"
            );
        }
    }

    #[test]
    fn descriptors_require_sorted_unique_fields() {
        let adapter = ResolvedAdapter {
            name: "finance".into(),
            path: PathBuf::from("anarres-finance"),
            shadowed_paths: Vec::new(),
        };
        let valid = AdapterDescriptor {
            schema_version: ADAPTER_DESCRIPTOR_SCHEMA.into(),
            name: "finance".into(),
            version: "0.1.0".into(),
            protocol_version: 2,
            domain: "agentic-finance".into(),
            executable: "anarres-finance".into(),
            profile_schema_versions: vec!["anarres.environment-profile-input.v1".into()],
            capabilities: vec!["profile".into(), "verify".into()],
            measurement_contracts: vec![
                "finance.business-bench-starting-policy-qualification.v1".into(),
            ],
            source_formats: Vec::new(),
        };
        assert!(validate_descriptor(&adapter, &valid).is_ok());

        let mut duplicate = valid;
        duplicate.capabilities = vec!["profile".into(), "profile".into()];
        assert!(validate_descriptor(&adapter, &duplicate).is_err());
    }
}
