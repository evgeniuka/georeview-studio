from __future__ import annotations

import json
from pathlib import Path


SCORING_RULES_STORE_VERSION = "scoring_rules_store_v001"


def read_json(path: Path) -> dict:
    try:
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def parse_int(value: object, default: int = 0) -> int:
    try:
        if value in (None, ""):
            return default
        return int(float(value))
    except (TypeError, ValueError):
        return default


def parse_flags(value: object) -> list[str]:
    if value in (None, ""):
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    try:
        parsed = json.loads(str(value))
        if isinstance(parsed, list):
            return [str(item) for item in parsed]
    except json.JSONDecodeError:
        pass
    return [item.strip() for item in str(value).split(";") if item.strip()]


class ScoringRulesStore:
    def __init__(self, config_path: Path, profile_dashboard: object) -> None:
        self.config_path = config_path
        self.profile_dashboard = profile_dashboard

    def config(self) -> dict:
        payload = read_json(self.config_path)
        if not payload:
            return {"error": "scoring_rules_not_found", "config_path": str(self.config_path), "source_gis_modified": False}
        return payload

    def overview(self) -> dict:
        config = self.config()
        if config.get("error"):
            return config
        profiles = []
        for profile_id, profile in config.get("profiles", {}).items():
            rules = self.expanded_rules(profile_id, config)
            scoring_rules = [rule for rule in rules if parse_int(rule.get("points")) > 0]
            context_rules = [rule for rule in rules if parse_int(rule.get("points")) == 0]
            profiles.append({
                "profile_id": profile_id,
                "profile_name": profile.get("profile_name"),
                "score_field": profile.get("score_field"),
                "rule_group_count": len(profile.get("rule_groups", [])),
                "scoring_rule_count": len(scoring_rules),
                "context_rule_count": len(context_rules),
            })
        return {
            "ok": True,
            "scoring_rules_store_version": SCORING_RULES_STORE_VERSION,
            "scoring_rules_version": config.get("scoring_rules_version"),
            "config_path": str(self.config_path),
            "scoring_policy": config.get("scoring_policy"),
            "profiles": profiles,
            "profile_count": len(profiles),
            "rule_group_count": len(config.get("rule_groups", {})),
            "claim_boundaries": config.get("claim_boundaries", []),
            "source_gis_modified": False,
        }

    def profile(self, profile_id: str) -> dict:
        config = self.config()
        if config.get("error"):
            return config
        normalized_id = self.normalize_profile_id(profile_id, config)
        if not normalized_id:
            return {"ok": False, "error": "scoring_profile_not_found", "profile_id": profile_id, "source_gis_modified": False}
        profile = config["profiles"][normalized_id]
        rules = self.expanded_rules(normalized_id, config)
        return {
            "ok": True,
            "scoring_rules_store_version": SCORING_RULES_STORE_VERSION,
            "scoring_rules_version": config.get("scoring_rules_version"),
            "profile_id": normalized_id,
            "profile_name": profile.get("profile_name"),
            "score_field": profile.get("score_field"),
            "rule_groups": profile.get("rule_groups", []),
            "rules": rules,
            "scoring_rules": [rule for rule in rules if parse_int(rule.get("points")) > 0],
            "context_rules": [rule for rule in rules if parse_int(rule.get("points")) == 0],
            "scoring_policy": config.get("scoring_policy"),
            "claim_boundaries": config.get("claim_boundaries", []),
            "source_gis_modified": False,
        }

    def audit(self, profile_id: str, limit: int = 50, min_score: int = 0, only_mismatches: bool = False) -> dict:
        profile_payload = self.profile(profile_id)
        if profile_payload.get("error"):
            return profile_payload
        normalized_id = profile_payload["profile_id"]
        results = self.profile_dashboard.results(normalized_id, limit=0, min_score=min_score)
        if results.get("error"):
            return results
        rows = results.get("rows", [])
        audits = []
        exact = 0
        max_abs_delta = 0
        mismatch_count = 0
        for row in rows:
            evaluated = self.evaluate_row(row, profile_payload["rules"])
            actual = parse_int(row.get("primary_score"))
            delta = actual - evaluated["expected_score"]
            status = "match" if delta == 0 else "mismatch"
            if delta == 0:
                exact += 1
            else:
                mismatch_count += 1
            max_abs_delta = max(max_abs_delta, abs(delta))
            item = {
                "profile_id": normalized_id,
                "result_id": row.get("result_id"),
                "entity_type": row.get("entity_type"),
                "name": row.get("name"),
                "actual_score": actual,
                "expected_score": evaluated["expected_score"],
                "delta": delta,
                "status": status,
                "active_rule_ids": evaluated["active_rule_ids"],
                "active_points": evaluated["active_points"],
                "context_rule_ids": evaluated["context_rule_ids"],
                "flags": row.get("flags", []),
                "data_quality_flags": row.get("data_quality_flags", []),
                "review_wording": row.get("review_wording"),
                "source_gis_modified": False,
            }
            if not only_mismatches or status == "mismatch":
                audits.append(item)
        visible_limit = max(1, min(int(limit or 50), 500))
        return {
            "ok": True,
            "scoring_rules_store_version": SCORING_RULES_STORE_VERSION,
            "scoring_rules_version": profile_payload.get("scoring_rules_version"),
            "profile_id": normalized_id,
            "profile_name": profile_payload.get("profile_name"),
            "score_field": profile_payload.get("score_field"),
            "rows_audited": len(rows),
            "exact_match_count": exact,
            "mismatch_count": mismatch_count,
            "max_abs_delta": max_abs_delta,
            "row_count": min(len(audits), visible_limit),
            "rows": audits[:visible_limit],
            "scoring_rule_count": len(profile_payload.get("scoring_rules", [])),
            "context_rule_count": len(profile_payload.get("context_rules", [])),
            "scoring_policy": profile_payload.get("scoring_policy"),
            "source_gis_modified": False,
        }

    @staticmethod
    def evaluate_row(row: dict, rules: list[dict]) -> dict:
        flags = set(parse_flags(row.get("flags")))
        expected_score = 0
        active_rule_ids = []
        active_points = []
        context_rule_ids = []
        for rule in rules:
            if not ScoringRulesStore.rule_matches(rule, flags, row):
                continue
            points = parse_int(rule.get("points"))
            if points > 0:
                expected_score += points
                active_rule_ids.append(rule.get("rule_id"))
                active_points.append({"rule_id": rule.get("rule_id"), "points": points})
            else:
                context_rule_ids.append(rule.get("rule_id"))
        return {
            "expected_score": expected_score,
            "active_rule_ids": active_rule_ids,
            "active_points": active_points,
            "context_rule_ids": context_rule_ids,
        }

    @staticmethod
    def rule_matches(rule: dict, flags: set[str], row: dict) -> bool:
        return ScoringRulesStore.condition_matches(rule.get("condition", {}), flags, row)

    @staticmethod
    def condition_matches(condition: dict, flags: set[str], row: dict) -> bool:
        condition_type = condition.get("type")
        if condition_type == "all":
            return all(ScoringRulesStore.condition_matches(item, flags, row) for item in condition.get("conditions", []))
        if condition_type == "flag_present":
            return str(condition.get("flag") or "") in flags
        if condition_type == "field_equals":
            return str(row.get(condition.get("field"), "")).lower() == str(condition.get("value"), "").lower()
        if condition_type == "field_gt":
            return ScoringRulesStore.numeric_value(row.get(condition.get("field"))) > ScoringRulesStore.numeric_value(condition.get("value"))
        if condition_type == "field_gte":
            return ScoringRulesStore.numeric_value(row.get(condition.get("field"))) >= ScoringRulesStore.numeric_value(condition.get("value"))
        return False

    @staticmethod
    def numeric_value(value: object) -> float:
        try:
            if value in (None, ""):
                return 0.0
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    def expanded_rules(self, profile_id: str, config: dict | None = None) -> list[dict]:
        config = config or self.config()
        profile = config.get("profiles", {}).get(profile_id, {})
        groups = config.get("rule_groups", {})
        rules: list[dict] = []
        for group_id in profile.get("rule_groups", []):
            group = groups.get(group_id, {})
            for rule in group.get("rules", []):
                expanded = dict(rule)
                expanded["rule_group"] = group_id
                expanded["rule_group_label"] = group.get("label")
                rules.append(expanded)
        return rules

    @staticmethod
    def normalize_profile_id(profile_id: str, config: dict) -> str:
        aliases = {
            "safe_access": "safe_access_pedestrian_review",
            "transit_walk_access": "transit_stop_walk_access",
            "public_space_access": "park_playground_access",
        }
        candidate = aliases.get(str(profile_id or ""), str(profile_id or ""))
        return candidate if candidate in config.get("profiles", {}) else ""
