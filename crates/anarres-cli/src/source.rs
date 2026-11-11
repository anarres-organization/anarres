use std::ffi::OsString;
use std::fs;
use std::path::{Path, PathBuf};

use serde::{Deserialize, Serialize};

use crate::adapter;
use crate::require_text;

pub(crate) const SOURCE_SCHEMA: &str = "anarres.environment-source.v1";
pub(crate) const SOURCE_FILENAME: &str = "anarres.toml";

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq)]
#[serde(deny_unknown_fields)]
pub(crate) struct NativeSource {
    pub(crate) uri: String,
    pub(crate) revision: String,
    pub(crate) license: String,
}

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq)]
#[serde(deny_unknown_fields)]
pub(crate) struct EnvironmentSource {
    pub(crate) schema_version: String,
    pub(crate) environment_id: String,
    pub(crate) domain: String,
    pub(crate) adapter: String,
    pub(crate) adapter_version: String,
    pub(crate) native_format: String,
    pub(crate) source: NativeSource,
}

#[derive(Debug, Serialize)]
pub(crate) struct SourceInspection {
    pub(crate) schema_version: &'static str,
    pub(crate) manifest: String,
    pub(crate) environment_id: String,
    pub(crate) domain: String,
    pub(crate) adapter: String,
    pub(crate) adapter_installed: bool,
    pub(crate) required_adapter_version: String,
    pub(crate) installed_adapter_version: Option<String>,
    pub(crate) native_format: String,
    pub(crate) native_format_supported: bool,
    pub(crate) source_uri: String,
    pub(crate) resolved_local_source: Option<String>,
    pub(crate) source_exists: Option<bool>,
    pub(crate) source_revision: String,
    pub(crate) source_license: String,
    pub(crate) can_qualify: bool,
    pub(crate) can_probe: bool,
    pub(crate) issues: Vec<String>,
}

pub(crate) fn locate(path: &Path) -> Option<PathBuf> {
    if path.is_dir() {
        let candidate = path.join(SOURCE_FILENAME);
        candidate.is_file().then_some(candidate)
    } else if path.file_name().and_then(|name| name.to_str()) == Some(SOURCE_FILENAME) {
        path.is_file().then_some(path.to_owned())
    } else {
        None
    }
}

pub(crate) fn load(path: &Path) -> Result<(PathBuf, EnvironmentSource), String> {
    let manifest_path = locate(path).ok_or_else(|| {
        format!(
            "{} is not an environment source; expected an {} file",
            path.display(),
            SOURCE_FILENAME
        )
    })?;
    let bytes = fs::read(&manifest_path)
        .map_err(|error| format!("could not read {}: {error}", manifest_path.display()))?;
    let text = std::str::from_utf8(&bytes)
        .map_err(|error| format!("{} is not UTF-8: {error}", manifest_path.display()))?;
    let source: EnvironmentSource = toml::from_str(text)
        .map_err(|error| format!("invalid environment source manifest: {error}"))?;
    validate(&source)?;
    Ok((manifest_path, source))
}

pub(crate) fn validate(source: &EnvironmentSource) -> Result<(), String> {
    if source.schema_version != SOURCE_SCHEMA {
        return Err(format!(
            "unsupported environment source schema_version: {}",
            source.schema_version
        ));
    }
    require_text("environment_id", &source.environment_id)?;
    require_text("domain", &source.domain)?;
    require_text("adapter", &source.adapter)?;
    adapter::validate_adapter_name(&source.adapter)?;
    require_text("adapter_version", &source.adapter_version)?;
    require_slug("native_format", &source.native_format)?;
    require_text("source.uri", &source.source.uri)?;
    require_text("source.revision", &source.source.revision)?;
    require_text("source.license", &source.source.license)?;
    Ok(())
}

pub(crate) fn inspect(path: &Path) -> Result<SourceInspection, String> {
    let (manifest_path, source) = load(path)?;
    let local_source = resolve_local_source(&manifest_path, &source.source.uri);
    let source_exists = local_source.as_ref().map(|candidate| candidate.exists());
    let mut issues = Vec::new();
    if source_exists == Some(false) {
        issues.push("the local native source does not exist".to_owned());
    }

    let mut adapter_installed = false;
    let mut installed_adapter_version = None;
    let mut native_format_supported = false;
    let mut can_qualify = false;
    let mut can_probe = false;
    match adapter::descriptor(&source.adapter) {
        Ok(descriptor) => {
            adapter_installed = true;
            installed_adapter_version = Some(descriptor.version.clone());
            if descriptor.version != source.adapter_version {
                issues.push(format!(
                    "adapter version '{}' does not match manifest version '{}'",
                    descriptor.version, source.adapter_version
                ));
            }
            if descriptor.domain != source.domain {
                issues.push(format!(
                    "adapter domain '{}' does not match manifest domain '{}'",
                    descriptor.domain, source.domain
                ));
            }
            native_format_supported = descriptor
                .source_formats
                .iter()
                .any(|format| format == &source.native_format);
            if !native_format_supported {
                issues.push(format!(
                    "adapter '{}' does not declare native format '{}'",
                    source.adapter, source.native_format
                ));
            }
            can_qualify = descriptor
                .capabilities
                .iter()
                .any(|capability| capability == "source-qualification");
            can_probe = descriptor
                .capabilities
                .iter()
                .any(|capability| capability == "policy-probe");
            if !can_qualify {
                issues.push(format!(
                    "adapter '{}' does not declare source qualification",
                    source.adapter
                ));
            }
            if !can_probe {
                issues.push(format!(
                    "adapter '{}' does not declare policy probing",
                    source.adapter
                ));
            }
        }
        Err(error) => issues.push(error),
    }

    Ok(SourceInspection {
        schema_version: SOURCE_SCHEMA,
        manifest: manifest_path.display().to_string(),
        environment_id: source.environment_id,
        domain: source.domain,
        adapter: source.adapter,
        adapter_installed,
        required_adapter_version: source.adapter_version,
        installed_adapter_version,
        native_format: source.native_format,
        native_format_supported,
        source_uri: source.source.uri,
        resolved_local_source: local_source.map(|candidate| candidate.display().to_string()),
        source_exists,
        source_revision: source.source.revision,
        source_license: source.source.license,
        can_qualify,
        can_probe,
        issues,
    })
}

pub(crate) fn dispatch_qualify(path: &Path, as_json: bool) -> Result<i32, String> {
    let inspection = inspect(path)?;
    require_operation_ready(&inspection, "source qualification")?;
    let mut arguments = vec![
        OsString::from("qualify-source"),
        OsString::from("--manifest"),
        OsString::from(&inspection.manifest),
    ];
    if as_json {
        arguments.push(OsString::from("--json"));
    }
    adapter::run(&inspection.adapter, &arguments)
}

pub(crate) fn dispatch_probe(
    path: &Path,
    policy: &str,
    policy_revision: &str,
    output: &Path,
    force: bool,
    adapter_arguments: &[OsString],
) -> Result<i32, String> {
    require_text("policy", policy)?;
    require_text("policy_revision", policy_revision)?;
    let inspection = inspect(path)?;
    require_operation_ready(&inspection, "policy probe")?;
    if output.exists() && !force {
        return Err(format!(
            "{} already exists\nhint: pass --force to let the adapter replace it",
            output.display()
        ));
    }
    let mut arguments = vec![
        OsString::from("probe-source"),
        OsString::from("--manifest"),
        OsString::from(&inspection.manifest),
        OsString::from("--policy"),
        OsString::from(policy),
        OsString::from("--policy-revision"),
        OsString::from(policy_revision),
        OsString::from("--output"),
        output.as_os_str().to_owned(),
    ];
    if force {
        arguments.push(OsString::from("--force"));
    }
    arguments.extend_from_slice(adapter_arguments);
    adapter::run(&inspection.adapter, &arguments)
}

fn require_operation_ready(inspection: &SourceInspection, operation: &str) -> Result<(), String> {
    let capability_ready = match operation {
        "source qualification" => inspection.can_qualify,
        "policy probe" => inspection.can_probe,
        _ => false,
    };
    let domain_mismatch = inspection
        .issues
        .iter()
        .any(|issue| issue.contains("does not match manifest domain"));
    let version_mismatch = inspection
        .issues
        .iter()
        .any(|issue| issue.contains("does not match manifest version"));
    if inspection.adapter_installed
        && inspection.native_format_supported
        && capability_ready
        && inspection.source_exists != Some(false)
        && !domain_mismatch
        && !version_mismatch
    {
        return Ok(());
    }
    Err(format!(
        "environment '{}' is not ready for {operation}: {}",
        inspection.environment_id,
        inspection.issues.join("; ")
    ))
}

fn resolve_local_source(manifest_path: &Path, uri: &str) -> Option<PathBuf> {
    if uri.contains("://") {
        return None;
    }
    let source = Path::new(uri);
    Some(if source.is_absolute() {
        source.to_owned()
    } else {
        manifest_path
            .parent()
            .unwrap_or_else(|| Path::new("."))
            .join(source)
    })
}

fn require_slug(field: &str, value: &str) -> Result<(), String> {
    require_text(field, value)?;
    let valid = value.bytes().enumerate().all(|(index, byte)| match byte {
        b'a'..=b'z' | b'0'..=b'9' => true,
        b'-' | b'.' => index > 0 && index + 1 < value.len(),
        _ => false,
    });
    if valid
        && !value.contains("..")
        && !value.contains("--")
        && !value.contains(".-")
        && !value.contains("-.")
    {
        Ok(())
    } else {
        Err(format!(
            "{field} must contain lowercase letters, digits, and interior '-' or '.' separators"
        ))
    }
}
