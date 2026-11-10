use std::collections::{BTreeMap, BTreeSet};
use std::env;
use std::ffi::OsString;
use std::fs;
use std::path::{Path, PathBuf};
use std::process::{Command, ExitStatus};

use serde::{Deserialize, Serialize};

pub(crate) const ADAPTER_DESCRIPTOR_SCHEMA: &str = "anarres.adapter-descriptor.v1";
const ADAPTER_LIST_SCHEMA: &str = "anarres.adapter-list.v1";
const ADAPTER_DOCTOR_SCHEMA: &str = "anarres.adapter-doctor.v1";
const ADAPTER_PROTOCOL_VERSION: u64 = 1;
const ADAPTER_PREFIX: &str = "anarres-";

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
        println!("No Anarres adapters found on PATH.");
        return Ok(0);
    }
    for adapter in installations {
        println!("{:<20} {}", adapter.name, adapter.path);
        for shadowed in adapter.shadowed_paths {
            eprintln!(
                "warning: adapter '{}' at {} is shadowed by an earlier PATH entry",
                adapter.name, shadowed
            );
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
        println!("Adapter      {}", descriptor.name);
        println!("Domain       {}", descriptor.domain);
        println!("Version      {}", descriptor.version);
        println!("Protocol     {}", descriptor.protocol_version);
        println!(
            "Executable   {}",
            report.path.as_deref().unwrap_or("unknown")
        );
        println!("Status       ready");
        for path in &report.shadowed_paths {
            eprintln!(
                "warning: adapter '{}' at {} is shadowed by an earlier PATH entry",
                name, path
            );
        }
    } else {
        for error in &report.errors {
            eprintln!("error: {error}");
        }
    }
    Ok(i32::from(!report.valid))
}

pub(crate) fn run(name: &str, arguments: &[OsString]) -> Result<i32, String> {
    validate_adapter_name(name)?;
    let adapter = resolve_adapter(name)?;
    read_descriptor(&adapter)?;
    let status = Command::new(&adapter.path)
        .args(arguments)
        .status()
        .map_err(|error| format!("failed to start adapter '{name}': {error}"))?;
    Ok(exit_code(status))
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
            "adapter '{name}' not found; install anarres-{name} on PATH"
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
        return [".exe", ".cmd", ".bat", ""]
            .into_iter()
            .map(|suffix| format!("{base}{suffix}").into())
            .collect();
    }
    #[cfg(not(windows))]
    {
        vec![base.into()]
    }
}

fn read_descriptor(adapter: &ResolvedAdapter) -> Result<AdapterDescriptor, String> {
    let output = Command::new(&adapter.path)
        .arg("--anarres-adapter-descriptor")
        .output()
        .map_err(|error| {
            format!(
                "failed to query adapter '{}' at {}: {error}",
                adapter.name,
                display_path(&adapter.path)
            )
        })?;
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

fn validate_adapter_name(name: &str) -> Result<(), String> {
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
            protocol_version: 1,
            domain: "agentic-finance".into(),
            executable: "anarres-finance".into(),
            profile_schema_versions: vec!["anarres.environment-profile-input.v1".into()],
            capabilities: vec!["profile".into(), "verify".into()],
            measurement_contracts: vec![
                "finance.business-bench-starting-policy-qualification.v1".into(),
            ],
        };
        assert!(validate_descriptor(&adapter, &valid).is_ok());

        let mut duplicate = valid;
        duplicate.capabilities = vec!["profile".into(), "profile".into()];
        assert!(validate_descriptor(&adapter, &duplicate).is_err());
    }
}
