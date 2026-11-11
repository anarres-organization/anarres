use std::collections::{BTreeMap, BTreeSet};
use std::fs::{self, File};
use std::io::{BufRead, BufReader};
use std::path::Path;

use serde::{Deserialize, Serialize};
use serde_json::{Value, json};
use sha2::{Digest, Sha256};

use crate::{ProbeContract, ProbeGroup, ProbeInput, require_text};

const METADATA_FILE: &str = "probe.json";
const ATTEMPTS_FILE: &str = "attempts.jsonl";
const RUN_SCHEMA: &str = "anarres.probe-run.v1";
const ATTEMPT_SCHEMA: &str = "anarres.probe-attempt.v1";
const ADVANTAGE_ESTIMATOR: &str = "leave-one-out-unnormalized";

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
struct RunContract {
    group_size: u64,
    temperature: f64,
    max_new_tokens: u64,
    advantage_estimator: String,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
struct RunMetadata {
    schema_version: String,
    environment_id: String,
    policy_id: String,
    policy_revision: String,
    source_license: String,
    source_revision: String,
    source_uri: String,
    probe_contract: RunContract,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
struct Attempt {
    schema_version: String,
    task_id: String,
    sample_index: u64,
    reward: Option<f64>,
    loss_admitted: bool,
    generated_action_tokens: u64,
    oracle_passed: bool,
    noop_passed: bool,
    infrastructure_valid: bool,
}

#[derive(Debug)]
struct GroupAccumulator {
    oracle_passed: bool,
    noop_passed: bool,
    infrastructure_valid: bool,
    attempts: BTreeMap<u64, Attempt>,
}

pub(super) struct LoadedBundle {
    pub(super) probe: ProbeInput,
    pub(super) digest_input: Value,
    pub(super) attempt_count: u64,
}

pub(super) fn load(path: &Path) -> Result<LoadedBundle, String> {
    if !path.is_dir() {
        return Err(format!("{} is not a probe-run directory", path.display()));
    }
    let metadata_path = path.join(METADATA_FILE);
    let attempts_path = path.join(ATTEMPTS_FILE);
    if !metadata_path.is_file() || !attempts_path.is_file() {
        return Err(format!(
            "{} is not a completed probe run; expected {} and {}\n\
             hint: run `anarres <adapter> qualify <environment>` and then the adapter's `probe` command",
            path.display(),
            METADATA_FILE,
            ATTEMPTS_FILE
        ));
    }
    let metadata_bytes = fs::read(&metadata_path)
        .map_err(|error| format!("could not read {}: {error}", metadata_path.display()))?;
    let metadata_value: Value = serde_json::from_slice(&metadata_bytes)
        .map_err(|error| format!("{} is not valid JSON: {error}", metadata_path.display()))?;
    let metadata: RunMetadata = serde_json::from_value(metadata_value.clone())
        .map_err(|error| format!("invalid probe-run metadata: {error}"))?;
    validate_metadata(&metadata)?;

    let file = File::open(&attempts_path)
        .map_err(|error| format!("could not read {}: {error}", attempts_path.display()))?;
    let mut reader = BufReader::new(file);
    let mut groups: BTreeMap<String, GroupAccumulator> = BTreeMap::new();
    let mut line = String::new();
    let mut line_number = 0_u64;
    let mut attempt_count = 0_u64;

    loop {
        line.clear();
        let bytes = reader
            .read_line(&mut line)
            .map_err(|error| format!("could not read {}: {error}", attempts_path.display()))?;
        if bytes == 0 {
            break;
        }
        line_number += 1;
        if line.trim().is_empty() {
            continue;
        }
        let attempt: Attempt = serde_json::from_str(&line).map_err(|error| {
            format!(
                "{} line {line_number} is not a valid probe attempt: {error}",
                attempts_path.display()
            )
        })?;
        validate_attempt(&attempt, metadata.probe_contract.group_size, line_number)?;
        let task_id = attempt.task_id.clone();
        let group = groups
            .entry(task_id.clone())
            .or_insert_with(|| GroupAccumulator {
                oracle_passed: attempt.oracle_passed,
                noop_passed: attempt.noop_passed,
                infrastructure_valid: attempt.infrastructure_valid,
                attempts: BTreeMap::new(),
            });
        if group.oracle_passed != attempt.oracle_passed || group.noop_passed != attempt.noop_passed
        {
            return Err(format!(
                "task {task_id} has inconsistent oracle or no-op results across attempts"
            ));
        }
        group.infrastructure_valid &= attempt.infrastructure_valid;
        let sample_index = attempt.sample_index;
        if group.attempts.insert(sample_index, attempt).is_some() {
            return Err(format!(
                "task {task_id} contains duplicate sample_index {sample_index}"
            ));
        }
        attempt_count += 1;
    }

    if attempt_count == 0 {
        return Err(format!("{} contains no attempts", attempts_path.display()));
    }

    let mut probe_groups = Vec::with_capacity(groups.len());
    let mut attempts_hasher = Sha256::new();
    for (task_id, group) in groups {
        for attempt in group.attempts.values() {
            let encoded = serde_json::to_vec(attempt)
                .map_err(|error| format!("could not canonicalize probe attempt: {error}"))?;
            attempts_hasher.update(encoded);
            attempts_hasher.update(b"\n");
        }
        probe_groups.push(finalize_group(
            task_id,
            group,
            metadata.probe_contract.group_size,
        )?);
    }

    let probe = ProbeInput {
        environment_id: metadata.environment_id.clone(),
        policy_id: metadata.policy_id.clone(),
        policy_revision: metadata.policy_revision.clone(),
        source_license: metadata.source_license.clone(),
        source_revision: metadata.source_revision.clone(),
        source_uri: metadata.source_uri.clone(),
        probe_contract: ProbeContract {
            group_size: metadata.probe_contract.group_size,
            views: 1,
            temperature: metadata.probe_contract.temperature,
            max_new_tokens: metadata.probe_contract.max_new_tokens,
        },
        groups: probe_groups,
    };
    let digest_input = json!({
        "schema_version": RUN_SCHEMA,
        "metadata": metadata_value,
        "attempts_sha256": format!("sha256:{:x}", attempts_hasher.finalize()),
        "attempt_count": attempt_count,
    });
    Ok(LoadedBundle {
        probe,
        digest_input,
        attempt_count,
    })
}

fn validate_metadata(metadata: &RunMetadata) -> Result<(), String> {
    if metadata.schema_version != RUN_SCHEMA {
        return Err(format!(
            "unsupported probe-run schema_version: {}",
            metadata.schema_version
        ));
    }
    require_text("environment_id", &metadata.environment_id)?;
    require_text("policy_id", &metadata.policy_id)?;
    require_text("policy_revision", &metadata.policy_revision)?;
    require_text("source_license", &metadata.source_license)?;
    require_text("source_revision", &metadata.source_revision)?;
    require_text("source_uri", &metadata.source_uri)?;
    if metadata.probe_contract.group_size < 2 {
        return Err("probe_contract.group_size must be at least 2".into());
    }
    if metadata.probe_contract.max_new_tokens == 0 {
        return Err("probe_contract.max_new_tokens must be positive".into());
    }
    if !metadata.probe_contract.temperature.is_finite() || metadata.probe_contract.temperature < 0.0
    {
        return Err("probe_contract.temperature must be finite and non-negative".into());
    }
    if metadata.probe_contract.advantage_estimator != ADVANTAGE_ESTIMATOR {
        return Err(format!(
            "unsupported advantage_estimator: {}",
            metadata.probe_contract.advantage_estimator
        ));
    }
    Ok(())
}

fn validate_attempt(attempt: &Attempt, group_size: u64, line_number: u64) -> Result<(), String> {
    if attempt.schema_version != ATTEMPT_SCHEMA {
        return Err(format!(
            "attempt line {line_number} uses unsupported schema_version {}",
            attempt.schema_version
        ));
    }
    require_text("attempt.task_id", &attempt.task_id)?;
    if attempt.sample_index >= group_size {
        return Err(format!(
            "task {} sample_index {} is outside group_size {group_size}",
            attempt.task_id, attempt.sample_index
        ));
    }
    if let Some(reward) = attempt.reward {
        if !reward.is_finite() {
            return Err(format!("task {} has a non-finite reward", attempt.task_id));
        }
    } else if attempt.infrastructure_valid {
        return Err(format!(
            "task {} sample {} is infrastructure-valid but has no reward",
            attempt.task_id, attempt.sample_index
        ));
    }
    if !attempt.infrastructure_valid && attempt.loss_admitted {
        return Err(format!(
            "task {} sample {} cannot be admitted after an infrastructure failure",
            attempt.task_id, attempt.sample_index
        ));
    }
    Ok(())
}

fn finalize_group(
    task_id: String,
    group: GroupAccumulator,
    group_size: u64,
) -> Result<ProbeGroup, String> {
    if group.attempts.len() as u64 != group_size {
        return Err(format!(
            "task {task_id} has {} attempts; expected exactly {group_size}",
            group.attempts.len()
        ));
    }
    let expected: BTreeSet<u64> = (0..group_size).collect();
    let observed: BTreeSet<u64> = group.attempts.keys().copied().collect();
    if observed != expected {
        return Err(format!(
            "task {task_id} sample indices must cover 0 through {}",
            group_size - 1
        ));
    }

    let generated_action_tokens = group
        .attempts
        .values()
        .map(|attempt| attempt.generated_action_tokens)
        .sum();
    let rewards: Vec<f64> = group
        .attempts
        .values()
        .filter_map(|attempt| attempt.reward)
        .collect();
    let admitted_advantage_mass = if group.infrastructure_valid {
        let reward_sum: f64 = rewards.iter().sum();
        group
            .attempts
            .values()
            .filter(|attempt| attempt.loss_admitted)
            .map(|attempt| {
                let reward = attempt
                    .reward
                    .expect("valid attempts have rewards after validation");
                let other_mean = (reward_sum - reward) / (group_size - 1) as f64;
                (reward - other_mean).abs()
            })
            .sum()
    } else {
        0.0
    };

    Ok(ProbeGroup {
        task_id,
        oracle_passed: group.oracle_passed,
        noop_passed: group.noop_passed,
        infrastructure_valid: group.infrastructure_valid,
        rewards,
        admitted_advantage_mass,
        generated_action_tokens,
    })
}

pub(super) fn is_bundle(path: &Path) -> bool {
    path.is_dir()
}
