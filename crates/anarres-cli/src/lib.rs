use std::collections::{BTreeMap, BTreeSet};
use std::ffi::OsString;
use std::fs;
use std::fs::OpenOptions;
use std::io::{self, Write};
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicU64, Ordering};

use clap::{Args, CommandFactory, Parser, Subcommand};
use clap_complete::{Shell, generate};
use serde::{Deserialize, Serialize};
use serde_json::{Value, json};
use sha2::{Digest, Sha256};

mod adapter;
mod profile;

use profile::{
    PROFILE_INPUT_SCHEMA, PROFILE_SCHEMA, build_profile, parse_profile, parse_profile_input,
    profile_design_report, profile_human_summary, profile_qualification_json, record_schema,
};

const MANIFEST_SCHEMA: &str = "anarres.environment-manifest.v1";
const STATUSES: [&str; 4] = ["admitted", "reserve", "repair", "quarantine"];
static NEXT_TEMPORARY_FILE: AtomicU64 = AtomicU64::new(0);

#[derive(Debug, Parser)]
#[command(
    name = "anarres",
    version,
    about = "Measure, compare, and validate learning environments",
    long_about = "Measure, compare, and validate learning environments.\n\n\
        Built-in commands operate on versioned local records and write no network state.\n\
        Installed adapters run under their own documented contracts.",
    arg_required_else_help = true
)]
struct Cli {
    #[command(subcommand)]
    command: Command,
}

#[derive(Debug, Subcommand)]
enum Command {
    /// Check whether measured evidence is ready for comparison.
    Qualify(InputArgs),
    /// Normalize measurements into a content-addressed environment record.
    Measure(MeasureArgs),
    /// Compare measured candidates and audit panel compatibility.
    Design(DesignArgs),
    /// Check supported records and content integrity.
    Validate(ValidateArgs),
    /// Discover, inspect, and run installed domain adapters.
    Adapter(AdapterArgs),
    /// Generate a completion script for a supported shell.
    GenerateShellCompletion(CompletionArgs),
    /// Run an installed domain adapter by name.
    #[command(external_subcommand)]
    External(Vec<OsString>),
}

#[derive(Debug, Args)]
struct AdapterArgs {
    #[command(subcommand)]
    command: AdapterCommand,
}

#[derive(Debug, Args)]
struct CompletionArgs {
    /// Shell to generate completions for.
    shell: Shell,
}

#[derive(Debug, Subcommand)]
enum AdapterCommand {
    /// List installed adapters found on PATH.
    List(AdapterListArgs),
    /// Validate an installed adapter and its protocol descriptor.
    Doctor(AdapterDoctorArgs),
    /// Run an installed adapter with explicit arguments.
    Run(AdapterRunArgs),
}

#[derive(Debug, Args)]
struct AdapterListArgs {
    /// Print a machine-readable report.
    #[arg(long)]
    json: bool,
}

#[derive(Debug, Args)]
struct AdapterDoctorArgs {
    /// Installed adapter name.
    name: String,
    /// Print a machine-readable report.
    #[arg(long)]
    json: bool,
}

#[derive(Debug, Args)]
#[command(trailing_var_arg = true, disable_help_flag = true)]
struct AdapterRunArgs {
    /// Installed adapter name.
    name: String,
    /// Arguments passed to the adapter.
    #[arg(num_args = 0.., allow_hyphen_values = true)]
    arguments: Vec<OsString>,
}

#[derive(Debug, Args)]
struct InputArgs {
    /// Policy-probe or environment-profile input to qualify.
    input: PathBuf,
    /// Print a machine-readable report.
    #[arg(long)]
    json: bool,
}

#[derive(Debug, Args)]
struct MeasureArgs {
    /// Policy-probe or environment-profile input to measure.
    input: PathBuf,
    /// Destination for the content-addressed environment record.
    #[arg(short, long)]
    output: PathBuf,
    /// Replace an existing output file.
    #[arg(long)]
    force: bool,
    /// Print the manifest to standard output after writing it.
    #[arg(long)]
    json: bool,
}

#[derive(Debug, Args)]
struct DesignArgs {
    /// Environment manifests or profiles in one candidate panel.
    #[arg(required = true, num_args = 2..)]
    manifests: Vec<PathBuf>,
    /// Print a machine-readable comparison report.
    #[arg(long)]
    json: bool,
}

#[derive(Debug, Args)]
struct ValidateArgs {
    /// Supported inputs, manifests, or profiles to validate.
    #[arg(required = true)]
    records: Vec<PathBuf>,
    /// Print a machine-readable validation report.
    #[arg(long)]
    json: bool,
}

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq)]
#[serde(deny_unknown_fields)]
struct ProbeContract {
    group_size: u64,
    views: u64,
    temperature: f64,
    max_new_tokens: u64,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
struct ProbeGroup {
    task_id: String,
    oracle_passed: bool,
    noop_passed: bool,
    infrastructure_valid: bool,
    rewards: Vec<f64>,
    admitted_advantage_mass: f64,
    generated_action_tokens: u64,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
struct ProbeInput {
    environment_id: String,
    policy_id: String,
    policy_revision: String,
    source_license: String,
    source_revision: String,
    source_uri: String,
    probe_contract: ProbeContract,
    groups: Vec<ProbeGroup>,
}

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq)]
#[serde(deny_unknown_fields)]
struct Coordinates {
    rho_per_million_tokens: f64,
    effective_coverage: f64,
    total_admitted_advantage_mass: f64,
    generated_action_tokens: u64,
    prompt_count: u64,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
struct ProcessedGroup {
    task_id: String,
    status: String,
    reason: String,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
struct EnvironmentManifest {
    schema_version: String,
    environment_id: String,
    policy_id: String,
    policy_revision: String,
    source_license: String,
    source_revision: String,
    source_uri: String,
    probe_contract: ProbeContract,
    status_counts: BTreeMap<String, u64>,
    coordinates: Coordinates,
    groups: Vec<ProcessedGroup>,
    input_digest: String,
    manifest_digest: String,
}

#[derive(Debug)]
struct QualificationReport {
    environment_id: String,
    policy_id: String,
    status_counts: BTreeMap<String, u64>,
    groups: Vec<ProcessedGroup>,
    input_digest: String,
}

#[derive(Debug, Serialize)]
struct CandidateSummary {
    environment_id: String,
    path: String,
    rho_per_million_tokens: f64,
    effective_coverage: f64,
    generated_action_tokens: u64,
    admitted: u64,
    reserve: u64,
    repair: u64,
    quarantine: u64,
}

#[derive(Debug, Serialize)]
pub(crate) struct RangeSummary {
    pub(crate) minimum: f64,
    pub(crate) maximum: f64,
}

#[derive(Debug, Serialize)]
struct DesignReport {
    compatible: bool,
    policy_id: String,
    policy_revision: String,
    candidate_count: usize,
    issues: Vec<String>,
    rho_per_million_tokens: RangeSummary,
    effective_coverage: RangeSummary,
    candidates: Vec<CandidateSummary>,
}

#[derive(Debug, Serialize)]
struct ValidationResult {
    path: String,
    record_type: String,
    valid: bool,
    error: Option<String>,
}

pub fn run() -> i32 {
    let cli = Cli::parse();
    match execute(cli.command) {
        Ok(code) => code,
        Err(error) => {
            let _ = writeln!(io::stderr(), "error: {error}");
            1
        }
    }
}

fn execute(command: Command) -> Result<i32, String> {
    match command {
        Command::Qualify(args) => command_qualify(args),
        Command::Measure(args) => command_measure(args),
        Command::Design(args) => command_design(args),
        Command::Validate(args) => command_validate(args),
        Command::Adapter(args) => match args.command {
            AdapterCommand::List(args) => adapter::list(args.json),
            AdapterCommand::Doctor(args) => adapter::doctor(&args.name, args.json),
            AdapterCommand::Run(args) => adapter::run(&args.name, &args.arguments),
        },
        Command::GenerateShellCompletion(args) => {
            let mut command = Cli::command();
            generate(args.shell, &mut command, "anarres", &mut io::stdout());
            Ok(0)
        }
        Command::External(mut arguments) => {
            if arguments.is_empty() {
                return Err("missing adapter name".to_owned());
            }
            let name = arguments.remove(0).into_string().map_err(|_| {
                "adapter names must contain valid UTF-8 lowercase letters, digits, and hyphens"
                    .to_owned()
            })?;
            adapter::run(&name, &arguments)
        }
    }
}

fn command_qualify(args: InputArgs) -> Result<i32, String> {
    let raw = read_json(&args.input)?;
    match record_schema(&raw) {
        Some(PROFILE_INPUT_SCHEMA) => {
            let input = parse_profile_input(&raw)?;
            let report = profile_qualification_json(&input);
            if args.json {
                print_json(&report)?;
            } else {
                println!("Environment  {}", input.environment_id);
                println!("Domain       {}", input.domain);
                println!("Subject      {}", input.subject.id);
                println!(
                    "Ready        {}",
                    yes_no(report["ready"].as_bool().unwrap_or(false))
                );
                for check in &input.qualification_checks {
                    println!(
                        "{:<7} {:<8} {}",
                        check.status, check.severity, check.summary
                    );
                }
            }
        }
        Some(schema) => return Err(format!("qualify does not accept schema_version {schema}")),
        None => {
            let probe = parse_probe(&raw)?;
            let report = qualify_probe(&probe, &raw)?;
            if args.json {
                print_json(&json!({
                    "environment_id": report.environment_id,
                    "policy_id": report.policy_id,
                    "status_counts": report.status_counts,
                    "groups": report.groups,
                    "input_digest": report.input_digest,
                }))?;
            } else {
                println!("Environment  {}", report.environment_id);
                println!("Policy       {}", report.policy_id);
                println!("Groups       {}", report.groups.len());
                print_status_counts(&report.status_counts);
                print_group_exceptions(&report.groups);
            }
        }
    }
    Ok(0)
}

fn command_measure(args: MeasureArgs) -> Result<i32, String> {
    let raw = read_json(&args.input)?;
    match record_schema(&raw) {
        Some(PROFILE_INPUT_SCHEMA) => {
            let input = parse_profile_input(&raw)?;
            let profile = build_profile(&input, &raw)?;
            let output = serde_json::to_vec_pretty(&profile).map_err(|error| error.to_string())?;
            write_atomic(&args.output, &output, args.force)?;
            if args.json {
                print_json(&profile)?;
            } else {
                profile_human_summary(&profile, &args.output);
            }
        }
        Some(schema) => return Err(format!("measure does not accept schema_version {schema}")),
        None => {
            let probe = parse_probe(&raw)?;
            let manifest = build_manifest(&probe, &raw)?;
            let output = serde_json::to_vec_pretty(&manifest).map_err(|error| error.to_string())?;
            write_atomic(&args.output, &output, args.force)?;
            if args.json {
                print_json(&manifest)?;
            } else {
                println!("Environment  {}", manifest.environment_id);
                println!("Policy       {}", manifest.policy_id);
                println!(
                    "Signal       {:.4} admitted advantage mass / M tokens",
                    manifest.coordinates.rho_per_million_tokens
                );
                println!(
                    "Coverage     {:.4}",
                    manifest.coordinates.effective_coverage
                );
                println!(
                    "Measured     {} groups · {} generated tokens",
                    manifest.coordinates.prompt_count, manifest.coordinates.generated_action_tokens
                );
                println!("Manifest     {}", args.output.display());
                println!("Digest       {}", manifest.manifest_digest);
            }
        }
    }
    Ok(0)
}

fn command_design(args: DesignArgs) -> Result<i32, String> {
    let first = read_json(&args.manifests[0])?;
    if record_schema(&first) == Some(PROFILE_SCHEMA) {
        let report = profile_design_report(&args.manifests)?;
        if args.json {
            print_json(&report)?;
        } else {
            println!("Candidate panel");
            println!("Domain       {}", report.domain);
            println!("Subject      {}", report.subject.id);
            println!(
                "Adapter      {} @ {}",
                report.producer.id, report.producer.revision
            );
            println!("Contract     {}", report.measurement_contract.id);
            println!("Candidates   {}", report.candidate_count);
            println!("Compatible   {}", yes_no(report.compatible));
            println!();
            for (name, span) in &report.coordinate_ranges {
                println!(
                    "{:<24} {:.4} to {:.4}",
                    truncate(name, 24),
                    span.minimum,
                    span.maximum
                );
            }
            for issue in &report.issues {
                println!("Issue        {issue}");
            }
        }
        return Ok(if report.compatible { 0 } else { 1 });
    }
    if let Some(schema) = record_schema(&first) {
        if schema != MANIFEST_SCHEMA {
            return Err(format!("design does not accept schema_version {schema}"));
        }
    }
    let report = design_report(&args.manifests)?;
    if args.json {
        print_json(&report)?;
    } else {
        println!("Candidate panel");
        println!("Policy       {}", report.policy_id);
        println!("Revision     {}", report.policy_revision);
        println!("Candidates   {}", report.candidate_count);
        println!("Compatible   {}", yes_no(report.compatible));
        println!();
        println!(
            "{:<24} {:>12} {:>10} {:>9} {:>8}",
            "ENVIRONMENT", "RHO / M TOK", "COVERAGE", "ADMITTED", "REPAIR"
        );
        for candidate in &report.candidates {
            println!(
                "{:<24} {:>12.4} {:>10.4} {:>9} {:>8}",
                truncate(&candidate.environment_id, 24),
                candidate.rho_per_million_tokens,
                candidate.effective_coverage,
                candidate.admitted,
                candidate.repair,
            );
        }
        println!();
        println!(
            "Signal span  {:.4} to {:.4}",
            report.rho_per_million_tokens.minimum, report.rho_per_million_tokens.maximum
        );
        println!(
            "Coverage     {:.4} to {:.4}",
            report.effective_coverage.minimum, report.effective_coverage.maximum
        );
        for issue in &report.issues {
            println!("Issue        {issue}");
        }
    }
    Ok(if report.compatible { 0 } else { 1 })
}

fn command_validate(args: ValidateArgs) -> Result<i32, String> {
    let mut results = Vec::with_capacity(args.records.len());
    for path in &args.records {
        results.push(validate_record(path));
    }
    let valid = results.iter().all(|result| result.valid);

    if args.json {
        print_json(&json!({"valid": valid, "records": results}))?;
    } else {
        for result in &results {
            if result.valid {
                println!("ok    {:<22} {}", result.record_type, result.path);
            } else {
                println!("error {:<22} {}", result.record_type, result.path);
                if let Some(error) = &result.error {
                    println!("      {error}");
                }
            }
        }
    }
    Ok(if valid { 0 } else { 1 })
}

pub(crate) fn read_json(path: &Path) -> Result<Value, String> {
    let bytes =
        fs::read(path).map_err(|error| format!("could not read {}: {error}", path.display()))?;
    serde_json::from_slice(&bytes)
        .map_err(|error| format!("{} is not valid JSON: {error}", path.display()))
}

fn parse_probe(raw: &Value) -> Result<ProbeInput, String> {
    let probe: ProbeInput = serde_json::from_value(raw.clone())
        .map_err(|error| format!("invalid probe input: {error}"))?;
    validate_probe(&probe)?;
    Ok(probe)
}

fn validate_probe(probe: &ProbeInput) -> Result<(), String> {
    require_text("environment_id", &probe.environment_id)?;
    require_text("policy_id", &probe.policy_id)?;
    require_text("policy_revision", &probe.policy_revision)?;
    require_text("source_license", &probe.source_license)?;
    require_text("source_revision", &probe.source_revision)?;
    require_text("source_uri", &probe.source_uri)?;
    if probe.probe_contract.group_size < 2 {
        return Err("probe_contract.group_size must be at least 2".into());
    }
    if probe.probe_contract.views == 0 || probe.probe_contract.max_new_tokens == 0 {
        return Err("probe views and max_new_tokens must be positive".into());
    }
    if !probe.probe_contract.temperature.is_finite() || probe.probe_contract.temperature < 0.0 {
        return Err("probe temperature must be finite and non-negative".into());
    }
    if probe.groups.is_empty() {
        return Err("probe input must contain a non-empty groups list".into());
    }
    let mut task_ids = BTreeSet::new();
    for group in &probe.groups {
        require_text("groups[].task_id", &group.task_id)?;
        if !task_ids.insert(&group.task_id) {
            return Err(format!("duplicate task_id: {}", group.task_id));
        }
        if group.generated_action_tokens == 0 {
            return Err(format!(
                "group {} must have positive generated_action_tokens",
                group.task_id
            ));
        }
        if !group.admitted_advantage_mass.is_finite() || group.admitted_advantage_mass < 0.0 {
            return Err(format!(
                "group {} has invalid admitted_advantage_mass",
                group.task_id
            ));
        }
        if group.rewards.iter().any(|reward| !reward.is_finite()) {
            return Err(format!("group {} has a non-finite reward", group.task_id));
        }
    }
    Ok(())
}

pub(crate) fn require_text(field: &str, value: &str) -> Result<(), String> {
    if value.trim().is_empty() {
        Err(format!("{field} must not be empty"))
    } else {
        Ok(())
    }
}

fn qualify_probe(probe: &ProbeInput, raw: &Value) -> Result<QualificationReport, String> {
    let mut status_counts = BTreeMap::new();
    let mut groups = Vec::with_capacity(probe.groups.len());
    for group in &probe.groups {
        let (status, reason) = qualify_group(group);
        *status_counts.entry(status.to_owned()).or_insert(0) += 1;
        groups.push(ProcessedGroup {
            task_id: group.task_id.clone(),
            status: status.to_owned(),
            reason: reason.to_owned(),
        });
    }
    Ok(QualificationReport {
        environment_id: probe.environment_id.clone(),
        policy_id: probe.policy_id.clone(),
        status_counts,
        groups,
        input_digest: sha256_digest(raw)?,
    })
}

fn qualify_group(group: &ProbeGroup) -> (&'static str, &'static str) {
    if !group.infrastructure_valid {
        return ("repair", "infrastructure_invalid");
    }
    if !group.oracle_passed {
        return ("quarantine", "oracle_failed");
    }
    if group.noop_passed {
        return ("quarantine", "noop_accepted");
    }
    if group.rewards.is_empty() {
        return ("repair", "missing_rewards");
    }
    let first = group.rewards[0];
    if group.rewards.iter().all(|reward| *reward == first) {
        return ("reserve", "zero_reward_variance");
    }
    ("admitted", "mixed_valid_group")
}

fn compute_coordinates(
    probe: &ProbeInput,
    groups: &[ProcessedGroup],
) -> Result<Coordinates, String> {
    let measured: Vec<&ProbeGroup> = probe
        .groups
        .iter()
        .zip(groups)
        .filter_map(|(group, processed)| {
            matches!(processed.status.as_str(), "admitted" | "reserve").then_some(group)
        })
        .collect();
    if measured.is_empty() {
        return Err("probe produced no scientifically valid groups".into());
    }

    let total_mass: f64 = measured
        .iter()
        .map(|group| group.admitted_advantage_mass)
        .sum();
    let total_tokens: u64 = measured
        .iter()
        .map(|group| group.generated_action_tokens)
        .sum();
    let squared_mass: f64 = measured
        .iter()
        .map(|group| group.admitted_advantage_mass.powi(2))
        .sum();
    let rho = 1_000_000.0 * total_mass / total_tokens as f64;
    let coverage = if squared_mass == 0.0 {
        0.0
    } else {
        total_mass.powi(2) / squared_mass / measured.len() as f64
    };
    if !rho.is_finite() || !coverage.is_finite() {
        return Err("environment coordinates must be finite".into());
    }
    Ok(Coordinates {
        rho_per_million_tokens: rho,
        effective_coverage: coverage,
        total_admitted_advantage_mass: total_mass,
        generated_action_tokens: total_tokens,
        prompt_count: measured.len() as u64,
    })
}

fn build_manifest(probe: &ProbeInput, raw: &Value) -> Result<EnvironmentManifest, String> {
    let report = qualify_probe(probe, raw)?;
    let coordinates = compute_coordinates(probe, &report.groups)?;
    let mut manifest = EnvironmentManifest {
        schema_version: MANIFEST_SCHEMA.to_owned(),
        environment_id: probe.environment_id.clone(),
        policy_id: probe.policy_id.clone(),
        policy_revision: probe.policy_revision.clone(),
        source_license: probe.source_license.clone(),
        source_revision: probe.source_revision.clone(),
        source_uri: probe.source_uri.clone(),
        probe_contract: probe.probe_contract.clone(),
        status_counts: report.status_counts,
        coordinates,
        groups: report.groups,
        input_digest: report.input_digest,
        manifest_digest: String::new(),
    };
    let mut value = serde_json::to_value(&manifest).map_err(|error| error.to_string())?;
    value
        .as_object_mut()
        .ok_or_else(|| "manifest must serialize as an object".to_owned())?
        .remove("manifest_digest");
    manifest.manifest_digest = sha256_digest(&value)?;
    Ok(manifest)
}

fn parse_manifest(raw: &Value) -> Result<EnvironmentManifest, String> {
    let manifest: EnvironmentManifest = serde_json::from_value(raw.clone())
        .map_err(|error| format!("invalid environment manifest: {error}"))?;
    validate_manifest(&manifest, raw)?;
    Ok(manifest)
}

fn validate_manifest(manifest: &EnvironmentManifest, raw: &Value) -> Result<(), String> {
    if manifest.schema_version != MANIFEST_SCHEMA {
        return Err(format!(
            "unsupported schema_version: {}",
            manifest.schema_version
        ));
    }
    require_text("environment_id", &manifest.environment_id)?;
    require_text("policy_id", &manifest.policy_id)?;
    require_text("policy_revision", &manifest.policy_revision)?;
    if !is_digest(&manifest.input_digest) || !is_digest(&manifest.manifest_digest) {
        return Err("input_digest and manifest_digest must be prefixed SHA-256 digests".into());
    }
    if manifest.coordinates.generated_action_tokens == 0 || manifest.coordinates.prompt_count == 0 {
        return Err("manifest coordinates must describe at least one measured group".into());
    }
    if !manifest.coordinates.rho_per_million_tokens.is_finite()
        || manifest.coordinates.rho_per_million_tokens < 0.0
        || !manifest.coordinates.effective_coverage.is_finite()
        || !(0.0..=1.0).contains(&manifest.coordinates.effective_coverage)
    {
        return Err("manifest coordinates are outside their valid ranges".into());
    }

    let mut counts = BTreeMap::new();
    let mut measured = 0_u64;
    let mut task_ids = BTreeSet::new();
    for group in &manifest.groups {
        require_text("groups[].task_id", &group.task_id)?;
        require_text("groups[].reason", &group.reason)?;
        if !STATUSES.contains(&group.status.as_str()) {
            return Err(format!("unsupported group status: {}", group.status));
        }
        if !task_ids.insert(&group.task_id) {
            return Err(format!("duplicate task_id: {}", group.task_id));
        }
        *counts.entry(group.status.clone()).or_insert(0) += 1;
        if matches!(group.status.as_str(), "admitted" | "reserve") {
            measured += 1;
        }
    }
    if counts != manifest.status_counts {
        return Err("status_counts do not match the manifest groups".into());
    }
    if measured != manifest.coordinates.prompt_count {
        return Err("coordinates.prompt_count does not match admitted and reserve groups".into());
    }

    let mut unhashed = raw.clone();
    unhashed
        .as_object_mut()
        .ok_or_else(|| "environment manifest must be a JSON object".to_owned())?
        .remove("manifest_digest");
    let actual = sha256_digest(&unhashed)?;
    if actual != manifest.manifest_digest {
        return Err(format!(
            "manifest digest mismatch: recorded {}, computed {actual}",
            manifest.manifest_digest
        ));
    }
    Ok(())
}

fn design_report(paths: &[PathBuf]) -> Result<DesignReport, String> {
    let mut loaded = Vec::with_capacity(paths.len());
    for path in paths {
        let raw = read_json(path)?;
        loaded.push((path, parse_manifest(&raw)?));
    }
    let first = &loaded[0].1;
    let mut issues = Vec::new();
    let mut environment_ids = BTreeSet::new();
    let mut candidates = Vec::with_capacity(loaded.len());

    for (path, manifest) in &loaded {
        if manifest.policy_id != first.policy_id
            || manifest.policy_revision != first.policy_revision
        {
            issues.push(format!(
                "{} uses a different starting policy",
                manifest.environment_id
            ));
        }
        if manifest.probe_contract != first.probe_contract {
            issues.push(format!(
                "{} uses a different probe contract",
                manifest.environment_id
            ));
        }
        if !environment_ids.insert(&manifest.environment_id) {
            issues.push(format!(
                "duplicate environment_id: {}",
                manifest.environment_id
            ));
        }
        candidates.push(CandidateSummary {
            environment_id: manifest.environment_id.clone(),
            path: path.display().to_string(),
            rho_per_million_tokens: manifest.coordinates.rho_per_million_tokens,
            effective_coverage: manifest.coordinates.effective_coverage,
            generated_action_tokens: manifest.coordinates.generated_action_tokens,
            admitted: count(&manifest.status_counts, "admitted"),
            reserve: count(&manifest.status_counts, "reserve"),
            repair: count(&manifest.status_counts, "repair"),
            quarantine: count(&manifest.status_counts, "quarantine"),
        });
    }
    candidates.sort_by(|left, right| left.environment_id.cmp(&right.environment_id));

    Ok(DesignReport {
        compatible: issues.is_empty(),
        policy_id: first.policy_id.clone(),
        policy_revision: first.policy_revision.clone(),
        candidate_count: candidates.len(),
        rho_per_million_tokens: range(
            candidates
                .iter()
                .map(|candidate| candidate.rho_per_million_tokens),
        ),
        effective_coverage: range(
            candidates
                .iter()
                .map(|candidate| candidate.effective_coverage),
        ),
        issues,
        candidates,
    })
}

fn validate_record(path: &Path) -> ValidationResult {
    let path_text = path.display().to_string();
    let raw = match read_json(path) {
        Ok(raw) => raw,
        Err(error) => {
            return ValidationResult {
                path: path_text,
                record_type: "unknown".into(),
                valid: false,
                error: Some(error),
            };
        }
    };
    let (record_type, result) = match record_schema(&raw) {
        Some(MANIFEST_SCHEMA) => ("environment manifest", parse_manifest(&raw).map(|_| ())),
        Some(PROFILE_INPUT_SCHEMA) => (
            "environment profile input",
            parse_profile_input(&raw).map(|_| ()),
        ),
        Some(PROFILE_SCHEMA) => ("environment profile", parse_profile(&raw).map(|_| ())),
        Some(schema) => (
            "unsupported record",
            Err(format!("unsupported schema_version: {schema}")),
        ),
        None => ("policy probe", parse_probe(&raw).map(|_| ())),
    };
    match result {
        Ok(()) => ValidationResult {
            path: path_text,
            record_type: record_type.into(),
            valid: true,
            error: None,
        },
        Err(error) => ValidationResult {
            path: path_text,
            record_type: record_type.into(),
            valid: false,
            error: Some(error),
        },
    }
}

pub(crate) fn range(values: impl Iterator<Item = f64>) -> RangeSummary {
    values.fold(
        RangeSummary {
            minimum: f64::INFINITY,
            maximum: f64::NEG_INFINITY,
        },
        |current, value| RangeSummary {
            minimum: current.minimum.min(value),
            maximum: current.maximum.max(value),
        },
    )
}

fn count(counts: &BTreeMap<String, u64>, status: &str) -> u64 {
    counts.get(status).copied().unwrap_or(0)
}

pub(crate) fn is_digest(value: &str) -> bool {
    value.len() == 71
        && value.starts_with("sha256:")
        && value[7..]
            .bytes()
            .all(|byte| byte.is_ascii_digit() || (b'a'..=b'f').contains(&byte))
}

pub(crate) fn sha256_digest(value: &Value) -> Result<String, String> {
    let bytes = serde_json::to_vec(value).map_err(|error| error.to_string())?;
    let digest = Sha256::digest(bytes);
    Ok(format!("sha256:{digest:x}"))
}

fn write_atomic(path: &Path, content: &[u8], force: bool) -> Result<(), String> {
    if path.exists() && !force {
        return Err(format!(
            "{} already exists; pass --force to replace it",
            path.display()
        ));
    }
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent)
            .map_err(|error| format!("could not create {}: {error}", parent.display()))?;
    }
    let file_name = path
        .file_name()
        .and_then(|name| name.to_str())
        .ok_or_else(|| format!("invalid output path: {}", path.display()))?;
    let sequence = NEXT_TEMPORARY_FILE.fetch_add(1, Ordering::Relaxed);
    let temporary = path.with_file_name(format!(
        ".{file_name}.tmp-{}-{sequence}",
        std::process::id()
    ));
    let mut bytes = content.to_vec();
    bytes.push(b'\n');
    let mut file = OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(&temporary)
        .map_err(|error| format!("could not create {}: {error}", temporary.display()))?;
    if let Err(error) = file.write_all(&bytes).and_then(|()| file.sync_all()) {
        let _ = fs::remove_file(&temporary);
        return Err(format!("could not write {}: {error}", temporary.display()));
    }
    drop(file);

    if force && path.exists() {
        fs::remove_file(path)
            .map_err(|error| format!("could not replace {}: {error}", path.display()))?;
    }
    if let Err(error) = fs::hard_link(&temporary, path) {
        let _ = fs::remove_file(&temporary);
        return Err(format!("could not publish {}: {error}", path.display()));
    }
    fs::remove_file(&temporary)
        .map_err(|error| format!("could not remove {}: {error}", temporary.display()))
}

fn print_json(value: &impl Serialize) -> Result<(), String> {
    let stdout = io::stdout();
    let mut output = stdout.lock();
    serde_json::to_writer_pretty(&mut output, value).map_err(|error| error.to_string())?;
    writeln!(output).map_err(|error| error.to_string())
}

fn print_status_counts(counts: &BTreeMap<String, u64>) {
    for status in STATUSES {
        println!("{:<12} {}", capitalize(status), count(counts, status));
    }
}

fn print_group_exceptions(groups: &[ProcessedGroup]) {
    let exceptions: Vec<_> = groups
        .iter()
        .filter(|group| matches!(group.status.as_str(), "repair" | "quarantine"))
        .collect();
    if exceptions.is_empty() {
        return;
    }
    println!();
    println!("Groups requiring action");
    for group in exceptions {
        println!(
            "  {:<24} {:<10} {}",
            group.task_id, group.status, group.reason
        );
    }
}

fn capitalize(value: &str) -> String {
    let mut characters = value.chars();
    match characters.next() {
        Some(first) => first.to_uppercase().collect::<String>() + characters.as_str(),
        None => String::new(),
    }
}

pub(crate) fn yes_no(value: bool) -> &'static str {
    if value { "yes" } else { "no" }
}

fn truncate(value: &str, width: usize) -> String {
    if value.chars().count() <= width {
        return value.to_owned();
    }
    let prefix: String = value.chars().take(width.saturating_sub(1)).collect();
    format!("{prefix}…")
}

#[cfg(test)]
mod tests {
    use super::*;

    fn fixture() -> Value {
        serde_json::from_str(include_str!(
            "../../../examples/environment-processing/probe.json"
        ))
        .expect("fixture is valid JSON")
    }

    #[test]
    fn fixture_matches_reference_coordinates() {
        let raw = fixture();
        let probe = parse_probe(&raw).expect("fixture is a valid probe");
        let manifest = build_manifest(&probe, &raw).expect("manifest builds");
        assert_eq!(manifest.status_counts.get("admitted"), Some(&2));
        assert_eq!(manifest.status_counts.get("reserve"), Some(&1));
        assert_eq!(manifest.status_counts.get("repair"), Some(&1));
        assert_eq!(manifest.status_counts.get("quarantine"), Some(&1));
        assert_eq!(manifest.coordinates.generated_action_tokens, 4_200);
        assert!((manifest.coordinates.rho_per_million_tokens - 833.333_333).abs() < 1e-6);
        assert!((manifest.coordinates.effective_coverage - 0.653_333_333).abs() < 1e-6);
        assert_eq!(
            manifest.input_digest,
            "sha256:6d19bd63a87522223495bfe944d2c2520393ad50a2a45d5539189877631d3856"
        );
        assert_eq!(
            manifest.manifest_digest,
            "sha256:5471a6e0fb121640260770060a3b858f2e31100a66b73eb2210bd59603dd76d9"
        );
    }

    #[test]
    fn infrastructure_failure_is_not_reward_zero() {
        let raw = fixture();
        let probe = parse_probe(&raw).expect("fixture is a valid probe");
        let report = qualify_probe(&probe, &raw).expect("qualification succeeds");
        let failed = report
            .groups
            .iter()
            .find(|group| group.task_id == "math-demo-005")
            .expect("infrastructure fixture is present");
        assert_eq!(failed.status, "repair");
        assert_eq!(failed.reason, "infrastructure_invalid");
    }

    #[test]
    fn manifest_digest_detects_changes() {
        let raw = fixture();
        let probe = parse_probe(&raw).expect("fixture is a valid probe");
        let manifest = build_manifest(&probe, &raw).expect("manifest builds");
        let mut value = serde_json::to_value(manifest).expect("manifest serializes");
        value["coordinates"]["effective_coverage"] = json!(0.1);
        let error = parse_manifest(&value).expect_err("tampering must fail");
        assert!(error.contains("digest mismatch"));
    }

    #[test]
    fn duplicate_tasks_are_rejected() {
        let mut raw = fixture();
        let duplicate = raw["groups"][0].clone();
        raw["groups"].as_array_mut().unwrap().push(duplicate);
        let error = parse_probe(&raw).expect_err("duplicates must fail");
        assert!(error.contains("duplicate task_id"));
    }
}
