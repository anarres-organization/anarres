use std::collections::{BTreeMap, BTreeSet};
use std::path::{Path, PathBuf};

use serde::{Deserialize, Serialize};
use serde_json::{Value, json};

use crate::{RangeSummary, is_digest, read_json, require_text, sha256_digest};

pub(crate) const PROFILE_INPUT_SCHEMA: &str = "anarres.environment-profile-input.v1";
pub(crate) const PROFILE_SCHEMA: &str = "anarres.environment-profile.v1";

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub(crate) struct VersionedIdentity {
    pub(crate) kind: String,
    pub(crate) id: String,
    pub(crate) revision: String,
}

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub(crate) struct SourceIdentity {
    pub(crate) uri: String,
    pub(crate) revision: String,
    pub(crate) license: String,
}

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub(crate) struct MeasurementContract {
    pub(crate) kind: String,
    pub(crate) id: String,
    pub(crate) revision: String,
    pub(crate) repetitions: u64,
    pub(crate) cost_unit: String,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct QualificationCheck {
    pub(crate) check_id: String,
    pub(crate) category: String,
    pub(crate) status: String,
    pub(crate) severity: String,
    pub(crate) summary: String,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct Uncertainty {
    pub(crate) kind: String,
    pub(crate) lower: f64,
    pub(crate) upper: f64,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub(crate) level: Option<f64>,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct DefinitionReference {
    pub(crate) uri: String,
    pub(crate) revision: String,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct ProfileCoordinate {
    pub(crate) name: String,
    pub(crate) definition: DefinitionReference,
    pub(crate) role: String,
    pub(crate) value: f64,
    pub(crate) unit: String,
    pub(crate) direction: String,
    pub(crate) estimator: String,
    pub(crate) sample_count: u64,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub(crate) uncertainty: Option<Uncertainty>,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct ArtifactReference {
    pub(crate) uri: String,
    pub(crate) sha256: String,
    pub(crate) media_type: String,
    pub(crate) size_bytes: u64,
    pub(crate) license: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub(crate) producing_run: Option<String>,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct ProfileArtifact {
    pub(crate) role: String,
    pub(crate) reference: ArtifactReference,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct EnvironmentProfileInput {
    pub(crate) schema_version: String,
    pub(crate) environment_id: String,
    pub(crate) domain: String,
    pub(crate) subject: VersionedIdentity,
    pub(crate) producer: VersionedIdentity,
    pub(crate) source: SourceIdentity,
    pub(crate) measurement_contract: MeasurementContract,
    pub(crate) qualification_checks: Vec<QualificationCheck>,
    pub(crate) coordinates: Vec<ProfileCoordinate>,
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub(crate) artifacts: Vec<ProfileArtifact>,
    #[serde(default, skip_serializing_if = "BTreeMap::is_empty")]
    pub(crate) attributes: BTreeMap<String, Value>,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct QualificationSummary {
    pub(crate) passed: u64,
    pub(crate) failed: u64,
    pub(crate) unknown: u64,
    pub(crate) warnings: u64,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct EnvironmentProfile {
    pub(crate) schema_version: String,
    pub(crate) environment_id: String,
    pub(crate) domain: String,
    pub(crate) subject: VersionedIdentity,
    pub(crate) producer: VersionedIdentity,
    pub(crate) source: SourceIdentity,
    pub(crate) measurement_contract: MeasurementContract,
    pub(crate) qualification_checks: Vec<QualificationCheck>,
    pub(crate) qualification_summary: QualificationSummary,
    pub(crate) ready: bool,
    pub(crate) coordinates: Vec<ProfileCoordinate>,
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub(crate) artifacts: Vec<ProfileArtifact>,
    #[serde(default, skip_serializing_if = "BTreeMap::is_empty")]
    pub(crate) attributes: BTreeMap<String, Value>,
    pub(crate) input_digest: String,
    pub(crate) profile_digest: String,
}

#[derive(Debug, Serialize)]
pub(crate) struct ProfileCandidateSummary {
    environment_id: String,
    path: String,
    ready: bool,
    coordinates: BTreeMap<String, f64>,
}

#[derive(Debug, Serialize)]
pub(crate) struct ProfileDesignReport {
    pub(crate) compatible: bool,
    pub(crate) domain: String,
    pub(crate) subject: VersionedIdentity,
    pub(crate) producer: VersionedIdentity,
    pub(crate) measurement_contract: MeasurementContract,
    pub(crate) candidate_count: usize,
    pub(crate) issues: Vec<String>,
    pub(crate) coordinate_ranges: BTreeMap<String, RangeSummary>,
    pub(crate) candidates: Vec<ProfileCandidateSummary>,
}

pub(crate) fn parse_profile_input(raw: &Value) -> Result<EnvironmentProfileInput, String> {
    let input: EnvironmentProfileInput = serde_json::from_value(raw.clone())
        .map_err(|error| format!("invalid environment profile input: {error}"))?;
    validate_profile_input(&input)?;
    Ok(input)
}

fn validate_profile_input(input: &EnvironmentProfileInput) -> Result<(), String> {
    if input.schema_version != PROFILE_INPUT_SCHEMA {
        return Err(format!(
            "unsupported schema_version: {}",
            input.schema_version
        ));
    }
    require_text("environment_id", &input.environment_id)?;
    require_text("domain", &input.domain)?;
    validate_versioned_identity("subject", &input.subject)?;
    validate_versioned_identity("producer", &input.producer)?;
    require_text("source.uri", &input.source.uri)?;
    require_text("source.revision", &input.source.revision)?;
    require_text("source.license", &input.source.license)?;
    validate_measurement_contract(&input.measurement_contract)?;

    if input.qualification_checks.is_empty() {
        return Err("qualification_checks must not be empty".into());
    }
    let mut check_ids = BTreeSet::new();
    for check in &input.qualification_checks {
        require_text("qualification_checks[].check_id", &check.check_id)?;
        require_text("qualification_checks[].summary", &check.summary)?;
        if !check_ids.insert(&check.check_id) {
            return Err(format!("duplicate qualification check: {}", check.check_id));
        }
        if !matches!(
            check.category.as_str(),
            "source" | "infrastructure" | "verifier" | "measurement" | "safety" | "other"
        ) && !is_namespaced_identifier(&check.category)
        {
            return Err(format!(
                "unsupported qualification category: {}",
                check.category
            ));
        }
        if !matches!(check.status.as_str(), "pass" | "fail" | "unknown") {
            return Err(format!(
                "unsupported qualification status: {}",
                check.status
            ));
        }
        if !matches!(check.severity.as_str(), "error" | "warning") {
            return Err(format!(
                "unsupported qualification severity: {}",
                check.severity
            ));
        }
    }

    if input.coordinates.is_empty() {
        return Err("coordinates must not be empty".into());
    }
    let mut coordinate_names = BTreeSet::new();
    for coordinate in &input.coordinates {
        validate_coordinate(coordinate)?;
        if !coordinate_names.insert(&coordinate.name) {
            return Err(format!("duplicate coordinate: {}", coordinate.name));
        }
    }

    for artifact in &input.artifacts {
        require_text("artifacts[].role", &artifact.role)?;
        require_text("artifacts[].reference.uri", &artifact.reference.uri)?;
        require_text(
            "artifacts[].reference.media_type",
            &artifact.reference.media_type,
        )?;
        require_text("artifacts[].reference.license", &artifact.reference.license)?;
        if !is_digest(&artifact.reference.sha256) {
            return Err(format!(
                "artifact {} has an invalid SHA-256 digest",
                artifact.reference.uri
            ));
        }
        if let Some(run) = &artifact.reference.producing_run {
            require_text("artifacts[].reference.producing_run", run)?;
        }
    }
    for (name, value) in &input.attributes {
        require_text("attributes key", name)?;
        if !matches!(value, Value::String(_) | Value::Number(_) | Value::Bool(_)) {
            return Err(format!(
                "attribute {name} must be a string, number, or boolean"
            ));
        }
    }
    Ok(())
}

fn validate_versioned_identity(field: &str, identity: &VersionedIdentity) -> Result<(), String> {
    require_text(&format!("{field}.kind"), &identity.kind)?;
    require_text(&format!("{field}.id"), &identity.id)?;
    require_text(&format!("{field}.revision"), &identity.revision)
}

fn validate_measurement_contract(contract: &MeasurementContract) -> Result<(), String> {
    require_text("measurement_contract.kind", &contract.kind)?;
    require_text("measurement_contract.id", &contract.id)?;
    require_text("measurement_contract.revision", &contract.revision)?;
    require_text("measurement_contract.cost_unit", &contract.cost_unit)?;
    if contract.repetitions == 0 {
        return Err("measurement_contract.repetitions must be positive".into());
    }
    Ok(())
}

fn validate_coordinate(coordinate: &ProfileCoordinate) -> Result<(), String> {
    require_text("coordinates[].name", &coordinate.name)?;
    require_text("coordinates[].definition.uri", &coordinate.definition.uri)?;
    require_text(
        "coordinates[].definition.revision",
        &coordinate.definition.revision,
    )?;
    require_text("coordinates[].unit", &coordinate.unit)?;
    require_text("coordinates[].estimator", &coordinate.estimator)?;
    if !matches!(
        coordinate.role.as_str(),
        "signal" | "coverage" | "cost" | "reliability" | "target_affinity" | "other"
    ) && !is_namespaced_identifier(&coordinate.role)
    {
        return Err(format!("unsupported coordinate role: {}", coordinate.role));
    }
    if !matches!(
        coordinate.direction.as_str(),
        "higher" | "lower" | "contextual"
    ) {
        return Err(format!(
            "unsupported coordinate direction: {}",
            coordinate.direction
        ));
    }
    if !coordinate.value.is_finite() {
        return Err(format!("coordinate {} must be finite", coordinate.name));
    }
    if coordinate.sample_count == 0 {
        return Err(format!(
            "coordinate {} must have a positive sample_count",
            coordinate.name
        ));
    }
    if let Some(uncertainty) = &coordinate.uncertainty {
        require_text("coordinates[].uncertainty.kind", &uncertainty.kind)?;
        if !uncertainty.lower.is_finite()
            || !uncertainty.upper.is_finite()
            || uncertainty.lower > coordinate.value
            || coordinate.value > uncertainty.upper
        {
            return Err(format!(
                "coordinate {} has an invalid uncertainty interval",
                coordinate.name
            ));
        }
        if let Some(level) = uncertainty.level {
            if !level.is_finite() || !(0.0..1.0).contains(&level) {
                return Err(format!(
                    "coordinate {} has an invalid uncertainty level",
                    coordinate.name
                ));
            }
        }
    }
    Ok(())
}

fn is_namespaced_identifier(value: &str) -> bool {
    let mut parts = value.split('.');
    let valid_part = |part: &str| {
        !part.is_empty()
            && part.bytes().enumerate().all(|(index, byte)| match byte {
                b'a'..=b'z' => true,
                b'0'..=b'9' | b'_' if index > 0 => true,
                _ => false,
            })
    };
    let Some(first) = parts.next() else {
        return false;
    };
    valid_part(first) && parts.clone().next().is_some() && parts.all(valid_part)
}

fn qualification_summary(checks: &[QualificationCheck]) -> QualificationSummary {
    let mut summary = QualificationSummary {
        passed: 0,
        failed: 0,
        unknown: 0,
        warnings: 0,
    };
    for check in checks {
        match check.status.as_str() {
            "pass" => summary.passed += 1,
            "fail" => summary.failed += 1,
            "unknown" => summary.unknown += 1,
            _ => unreachable!("qualification status was validated"),
        }
        if check.severity == "warning" && check.status != "pass" {
            summary.warnings += 1;
        }
    }
    summary
}

fn is_ready(checks: &[QualificationCheck]) -> bool {
    checks
        .iter()
        .all(|check| check.severity != "error" || check.status == "pass")
}

pub(crate) fn build_profile(
    input: &EnvironmentProfileInput,
    raw: &Value,
) -> Result<EnvironmentProfile, String> {
    let mut checks = input.qualification_checks.clone();
    checks.sort_by(|left, right| left.check_id.cmp(&right.check_id));
    let mut coordinates = input.coordinates.clone();
    coordinates.sort_by(|left, right| left.name.cmp(&right.name));
    let mut artifacts = input.artifacts.clone();
    artifacts.sort_by(|left, right| {
        (&left.role, &left.reference.uri).cmp(&(&right.role, &right.reference.uri))
    });

    let mut profile = EnvironmentProfile {
        schema_version: PROFILE_SCHEMA.to_owned(),
        environment_id: input.environment_id.clone(),
        domain: input.domain.clone(),
        subject: input.subject.clone(),
        producer: input.producer.clone(),
        source: input.source.clone(),
        measurement_contract: input.measurement_contract.clone(),
        qualification_summary: qualification_summary(&checks),
        ready: is_ready(&checks),
        qualification_checks: checks,
        coordinates,
        artifacts,
        attributes: input.attributes.clone(),
        input_digest: sha256_digest(raw)?,
        profile_digest: String::new(),
    };
    let mut value = serde_json::to_value(&profile).map_err(|error| error.to_string())?;
    value
        .as_object_mut()
        .ok_or_else(|| "environment profile must serialize as an object".to_owned())?
        .remove("profile_digest");
    profile.profile_digest = sha256_digest(&value)?;
    Ok(profile)
}

pub(crate) fn parse_profile(raw: &Value) -> Result<EnvironmentProfile, String> {
    let profile: EnvironmentProfile = serde_json::from_value(raw.clone())
        .map_err(|error| format!("invalid environment profile: {error}"))?;
    validate_profile(&profile, raw)?;
    Ok(profile)
}

fn validate_profile(profile: &EnvironmentProfile, raw: &Value) -> Result<(), String> {
    if profile.schema_version != PROFILE_SCHEMA {
        return Err(format!(
            "unsupported schema_version: {}",
            profile.schema_version
        ));
    }
    let input = EnvironmentProfileInput {
        schema_version: PROFILE_INPUT_SCHEMA.to_owned(),
        environment_id: profile.environment_id.clone(),
        domain: profile.domain.clone(),
        subject: profile.subject.clone(),
        producer: profile.producer.clone(),
        source: profile.source.clone(),
        measurement_contract: profile.measurement_contract.clone(),
        qualification_checks: profile.qualification_checks.clone(),
        coordinates: profile.coordinates.clone(),
        artifacts: profile.artifacts.clone(),
        attributes: profile.attributes.clone(),
    };
    validate_profile_input(&input)?;
    if !is_digest(&profile.input_digest) || !is_digest(&profile.profile_digest) {
        return Err("input_digest and profile_digest must be prefixed SHA-256 digests".into());
    }
    let expected_summary = qualification_summary(&profile.qualification_checks);
    if serde_json::to_value(&profile.qualification_summary).map_err(|error| error.to_string())?
        != serde_json::to_value(expected_summary).map_err(|error| error.to_string())?
    {
        return Err("qualification_summary does not match qualification_checks".into());
    }
    if profile.ready != is_ready(&profile.qualification_checks) {
        return Err("ready does not match error-level qualification checks".into());
    }
    if !profile
        .qualification_checks
        .windows(2)
        .all(|pair| pair[0].check_id < pair[1].check_id)
        || !profile
            .coordinates
            .windows(2)
            .all(|pair| pair[0].name < pair[1].name)
    {
        return Err("profile checks and coordinates must use normalized ordering".into());
    }
    let mut unhashed = raw.clone();
    unhashed
        .as_object_mut()
        .ok_or_else(|| "environment profile must be a JSON object".to_owned())?
        .remove("profile_digest");
    let actual = sha256_digest(&unhashed)?;
    if actual != profile.profile_digest {
        return Err(format!(
            "profile digest mismatch: recorded {}, computed {actual}",
            profile.profile_digest
        ));
    }
    Ok(())
}

pub(crate) fn profile_qualification_json(input: &EnvironmentProfileInput) -> Value {
    let summary = qualification_summary(&input.qualification_checks);
    json!({
        "environment_id": input.environment_id,
        "domain": input.domain,
        "subject": input.subject,
        "producer": input.producer,
        "ready": is_ready(&input.qualification_checks),
        "qualification_summary": summary,
        "qualification_checks": input.qualification_checks,
    })
}

pub(crate) fn profile_design_report(paths: &[PathBuf]) -> Result<ProfileDesignReport, String> {
    let mut loaded = Vec::with_capacity(paths.len());
    for path in paths {
        let raw = read_json(path)?;
        loaded.push((path, parse_profile(&raw)?));
    }
    let first = &loaded[0].1;
    let first_definitions = coordinate_definitions(first);
    let mut issues = Vec::new();
    let mut environment_ids = BTreeSet::new();
    let mut candidates = Vec::with_capacity(loaded.len());

    for (path, profile) in &loaded {
        if profile.domain != first.domain {
            issues.push(format!(
                "{} uses a different domain",
                profile.environment_id
            ));
        }
        if profile.subject != first.subject {
            issues.push(format!(
                "{} uses a different starting subject",
                profile.environment_id
            ));
        }
        if profile.producer != first.producer {
            issues.push(format!(
                "{} uses a different adapter revision",
                profile.environment_id
            ));
        }
        if profile.measurement_contract != first.measurement_contract {
            issues.push(format!(
                "{} uses a different measurement contract",
                profile.environment_id
            ));
        }
        if coordinate_definitions(profile) != first_definitions {
            issues.push(format!(
                "{} uses different coordinate definitions",
                profile.environment_id
            ));
        }
        if !profile.ready {
            issues.push(format!(
                "{} has unresolved error-level qualification checks",
                profile.environment_id
            ));
        }
        if !environment_ids.insert(&profile.environment_id) {
            issues.push(format!(
                "duplicate environment_id: {}",
                profile.environment_id
            ));
        }
        candidates.push(ProfileCandidateSummary {
            environment_id: profile.environment_id.clone(),
            path: path.display().to_string(),
            ready: profile.ready,
            coordinates: profile
                .coordinates
                .iter()
                .map(|coordinate| (coordinate.name.clone(), coordinate.value))
                .collect(),
        });
    }
    candidates.sort_by(|left, right| left.environment_id.cmp(&right.environment_id));

    let mut coordinate_ranges = BTreeMap::new();
    for definition in first_definitions.keys() {
        let values = loaded.iter().filter_map(|(_, profile)| {
            profile
                .coordinates
                .iter()
                .find(|coordinate| &coordinate.name == definition)
                .map(|coordinate| coordinate.value)
        });
        coordinate_ranges.insert(definition.clone(), crate::range(values));
    }

    Ok(ProfileDesignReport {
        compatible: issues.is_empty(),
        domain: first.domain.clone(),
        subject: first.subject.clone(),
        producer: first.producer.clone(),
        measurement_contract: first.measurement_contract.clone(),
        candidate_count: candidates.len(),
        issues,
        coordinate_ranges,
        candidates,
    })
}

fn coordinate_definitions(
    profile: &EnvironmentProfile,
) -> BTreeMap<String, (String, String, String, String, String, String)> {
    profile
        .coordinates
        .iter()
        .map(|coordinate| {
            (
                coordinate.name.clone(),
                (
                    coordinate.definition.uri.clone(),
                    coordinate.definition.revision.clone(),
                    coordinate.role.clone(),
                    coordinate.unit.clone(),
                    coordinate.direction.clone(),
                    coordinate.estimator.clone(),
                ),
            )
        })
        .collect()
}

pub(crate) fn record_schema(raw: &Value) -> Option<&str> {
    raw.get("schema_version").and_then(Value::as_str)
}

pub(crate) fn profile_human_summary(profile: &EnvironmentProfile, path: &Path) {
    crate::ui::success("Measured", &profile.environment_id);
    crate::ui::field("Domain", &profile.domain);
    crate::ui::field("Subject", &profile.subject.id);
    crate::ui::field(
        "Adapter",
        format_args!("{} @ {}", profile.producer.id, profile.producer.revision),
    );
    crate::ui::field("Ready", crate::yes_no(profile.ready));
    crate::ui::field("Coordinates", profile.coordinates.len());
    crate::ui::field("Record", path.display());
    crate::ui::muted(format_args!("Digest  {}", profile.profile_digest));
}

#[cfg(test)]
mod tests {
    use super::*;

    fn profile_input() -> Value {
        serde_json::from_str(include_str!(
            "../../../examples/environment-profiles/robotics-a.profile-input.json"
        ))
        .expect("fixture is valid JSON")
    }

    #[test]
    fn error_level_unknown_blocks_readiness() {
        let mut raw = profile_input();
        raw["qualification_checks"][0]["status"] = json!("unknown");
        let input = parse_profile_input(&raw).expect("input remains structurally valid");
        let profile = build_profile(&input, &raw).expect("profile builds");
        assert!(!profile.ready);
    }

    #[test]
    fn profile_digest_detects_changes() {
        let raw = profile_input();
        let input = parse_profile_input(&raw).expect("input is valid");
        let profile = build_profile(&input, &raw).expect("profile builds");
        let mut value = serde_json::to_value(profile).expect("profile serializes");
        value["coordinates"][1]["value"] = json!(0.99);
        let error = parse_profile(&value).expect_err("tampering must fail");
        assert!(error.contains("digest mismatch"));
    }

    #[test]
    fn uncertainty_must_contain_the_estimate() {
        let mut raw = profile_input();
        let coordinate = raw["coordinates"]
            .as_array_mut()
            .expect("coordinates are an array")
            .iter_mut()
            .find(|coordinate| coordinate["name"] == "episode_success_variation")
            .expect("fixture retains an uncertain coordinate");
        coordinate["uncertainty"]["upper"] = json!(-1.0);
        let error = parse_profile_input(&raw).expect_err("invalid interval must fail");
        assert!(error.contains("invalid uncertainty interval"));
    }

    #[test]
    fn namespaced_domain_semantics_do_not_require_core_changes() {
        let mut raw = profile_input();
        raw["qualification_checks"][0]["category"] = json!("robotics.episode_integrity");
        raw["coordinates"][0]["role"] = json!("robotics.policy_frontier");
        parse_profile_input(&raw).expect("namespaced semantics are supported");
    }

    #[test]
    fn profile_preserves_coordinate_definitions_and_native_evidence() {
        let raw = profile_input();
        let input = parse_profile_input(&raw).expect("input is valid");
        let profile = build_profile(&input, &raw).expect("profile builds");
        let coordinate = profile
            .coordinates
            .iter()
            .find(|coordinate| coordinate.name == "episode_success_variation")
            .expect("coordinate is retained");
        assert!(
            coordinate
                .definition
                .uri
                .ends_with("#episode_success_variation")
        );
        assert_eq!(coordinate.definition.revision, "v1-development");
        assert_eq!(profile.artifacts[0].role, "native-measurements");
        assert_eq!(
            profile.artifacts[0].reference.sha256,
            "sha256:0000000000000000000000000000000000000000000000000000000000000000"
        );
    }
}
