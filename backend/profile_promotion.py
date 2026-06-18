from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


PROFILE_PROMOTION_VERSION = "profile_promotion_wizard_v001"
PROFILE_ACCEPTANCE_VERSION = "profile_acceptance_workflow_v001"
PROFILE_APPLICATION_PLAN_VERSION = "profile_application_plan_v001"
PROFILE_CONTRACT_DIFF_VERSION = "profile_contract_diff_review_v001"
PROFILE_CONFIG_APPLY_PROPOSAL_VERSION = "profile_config_apply_proposal_v001"
PROFILE_CONTRACT_REGRESSION_PREVIEW_VERSION = "profile_contract_regression_preview_v001"
REVIEW_WORDING = "This location has infrastructure risk indicators and should be reviewed on-site."


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def safe_token(value: object, fallback: str = "profile_promotion") -> str:
    chars = []
    for char in str(value or ""):
        if char.isalnum() or char in {"_", "-"}:
            chars.append(char)
        else:
            chars.append("_")
    token = "_".join(part for part in "".join(chars).split("_") if part)
    return token[:140] or fallback


def read_json(path: Path) -> dict:
    try:
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def read_csv_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def unique(values: list[object]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if text and text not in seen:
            seen.add(text)
            result.append(text)
    return result


class ProfilePromotionWizard:
    def __init__(self, output_root: Path, workspaces_dir: Path, template_authoring: object, mapper_config_path: Path, review_wording: str) -> None:
        self.output_root = output_root
        self.workspaces_dir = workspaces_dir
        self.template_authoring = template_authoring
        self.mapper_config_path = mapper_config_path
        self.review_wording = review_wording
        self.promotions_dir = output_root / "georeview_studio_profile_promotions"

    def status(self) -> dict:
        candidates = self.candidates(500)
        proposals = self.list_proposals(500)
        decisions = self.list_decisions(500)
        application_plans = self.list_application_plans(500)
        application_candidates = self.application_candidates(500)
        contract_diffs = self.list_contract_diffs(500)
        contract_diff_candidates = self.contract_diff_candidates(500)
        config_apply_proposals = self.list_config_apply_proposals(500)
        config_apply_candidates = self.config_apply_candidates(500)
        regression_previews = self.list_contract_regression_previews(500)
        regression_candidates = self.contract_regression_candidates(500)
        promotable = [row for row in candidates if row.get("recommendation") == "ready_for_promotion_proposal"]
        pending = [row for row in self.review_queue(500) if row.get("decision_status") == "pending_review"]
        return {
            "ok": True,
            "profile_promotion_version": PROFILE_PROMOTION_VERSION,
            "profile_acceptance_version": PROFILE_ACCEPTANCE_VERSION,
            "profile_application_plan_version": PROFILE_APPLICATION_PLAN_VERSION,
            "profile_contract_diff_review_version": PROFILE_CONTRACT_DIFF_VERSION,
            "profile_config_apply_proposal_version": PROFILE_CONFIG_APPLY_PROPOSAL_VERSION,
            "profile_contract_regression_preview_version": PROFILE_CONTRACT_REGRESSION_PREVIEW_VERSION,
            "mode": "proposal_diff_acceptance_apply_proposal_and_regression_preview_no_config_mutation",
            "candidate_count": len(candidates),
            "promotable_candidate_count": len(promotable),
            "proposal_count": len(proposals),
            "decision_count": len(decisions),
            "accepted_decision_count": sum(1 for row in decisions if row.get("decision_status") == "approved"),
            "rejected_decision_count": sum(1 for row in decisions if row.get("decision_status") == "rejected"),
            "pending_review_count": len(pending),
            "application_candidate_count": len(application_candidates),
            "application_plan_count": len(application_plans),
            "contract_diff_candidate_count": len(contract_diff_candidates),
            "contract_diff_count": len(contract_diffs),
            "config_apply_candidate_count": len(config_apply_candidates),
            "config_apply_proposal_count": len(config_apply_proposals),
            "regression_candidate_count": len(regression_candidates),
            "regression_preview_count": len(regression_previews),
            "promotions_dir": str(self.promotions_dir),
            "default_action": "create_regression_preview_after_guarded_apply_proposal",
            "policy": {
                "writes_only_under_analysis_output": True,
                "does_not_modify_profile_mapper_config": True,
                "does_not_modify_source_gis": True,
                "requires_manual_review_before_config_change": True,
                "approval_does_not_apply_config_change": True,
                "application_plan_does_not_apply_config_change": True,
                "contract_diff_does_not_apply_config_change": True,
                "config_apply_proposal_does_not_apply_config_change": True,
                "regression_preview_does_not_apply_config_change": True,
                "missing_tags_remain_data_quality_flags": True,
            },
            "approved_review_wording": self.review_wording,
            "source_gis_modified": False,
        }

    def candidates(self, limit: int = 50) -> list[dict]:
        rows = []
        if not self.workspaces_dir.exists():
            return rows
        for manifest_path in self.workspaces_dir.glob("*/manifest.json"):
            manifest = read_json(manifest_path)
            if not manifest.get("authored_profile_workspace"):
                continue
            rows.append(self.candidate_from_manifest(manifest_path.parent, manifest))
        rows.sort(key=lambda row: str(row.get("created_at_utc") or ""), reverse=True)
        return rows[: max(1, min(int(limit or 50), 500))]

    def candidate(self, workspace_id: str) -> dict:
        clean = safe_token(workspace_id, "")
        manifest_path = self.workspaces_dir / clean / "manifest.json"
        manifest = read_json(manifest_path)
        if not manifest or not manifest.get("authored_profile_workspace"):
            return {"ok": False, "error": "profile_promotion_candidate_not_found", "workspace_id": workspace_id, "source_gis_modified": False}
        return self.candidate_from_manifest(manifest_path.parent, manifest)

    def propose(self, body: dict | None = None) -> dict:
        body = body or {}
        workspace_id = str(body.get("workspace_id") or "")
        if not workspace_id:
            ready = [row for row in self.candidates(500) if row.get("recommendation") == "ready_for_promotion_proposal"]
            if ready:
                workspace_id = str(ready[0].get("workspace_id") or "")
        if not workspace_id:
            return {"ok": False, "error": "profile_promotion_workspace_missing", "detail": "workspace_id is required when no ready candidate exists", "source_gis_modified": False}

        candidate = self.candidate(workspace_id)
        if candidate.get("error"):
            return candidate
        if candidate.get("recommendation") != "ready_for_promotion_proposal":
            return {
                "ok": False,
                "error": "profile_promotion_candidate_not_ready",
                "workspace_id": workspace_id,
                "blockers": candidate.get("blockers", []),
                "source_gis_modified": False,
            }

        draft = self.draft_for_candidate(candidate)
        manifest = read_json(self.workspaces_dir / safe_token(workspace_id, "") / "manifest.json")
        existing_contract = self.existing_contract(str(candidate.get("profile_id") or ""))
        promoted_contract = self.promoted_contract(candidate, draft, existing_contract)
        proposal_action = "update_existing_contract_preview" if existing_contract else "add_contract_preview"
        created_at = utc_now()
        proposal_id = safe_token(f"profile_promotion_{candidate.get('profile_id')}_{workspace_id}_{created_at}", "profile_promotion_proposal")
        proposal_dir = self.promotions_dir / proposal_id
        contract_path = proposal_dir / "profile_contract_proposal.json"
        patch_path = proposal_dir / "mapper_contract_patch_preview.json"
        report_path = proposal_dir / "promotion_report.md"
        proposal_path = proposal_dir / "promotion_proposal.json"

        patch_preview = {
            "ok": True,
            "operation": "replace_contract" if existing_contract else "append_contract",
            "target_config": str(self.mapper_config_path),
            "profile_id": candidate.get("profile_id"),
            "mutates_config": False,
            "requires_manual_review": True,
            "contract": promoted_contract,
            "source_gis_modified": False,
        }
        proposal = {
            "ok": True,
            "profile_promotion_version": PROFILE_PROMOTION_VERSION,
            "proposal_id": proposal_id,
            "created_at_utc": created_at,
            "status": "ready_for_manual_review",
            "proposal_action": proposal_action,
            "workspace_id": workspace_id,
            "profile_id": candidate.get("profile_id"),
            "template_id": candidate.get("template_id"),
            "draft_id": candidate.get("draft_id"),
            "candidate": candidate,
            "promoted_contract": promoted_contract,
            "mapper_contract_patch_preview": patch_preview,
            "approval_required_before_config_change": True,
            "files": {
                "proposal": str(proposal_path),
                "profile_contract_proposal": str(contract_path),
                "mapper_contract_patch_preview": str(patch_path),
                "promotion_report": str(report_path),
                "source_manifest": str(self.workspaces_dir / safe_token(workspace_id, "") / "manifest.json"),
            },
            "source_files": manifest.get("source_files", {}),
            "claim_boundaries": [
                "This proposal is evidence for manual profile review.",
                "It does not modify profile mapper config.",
                "It does not modify source GIS files.",
                "Missing OSM tags remain data-quality flags.",
                self.review_wording,
            ],
            "source_gis_modified": False,
        }
        write_json(contract_path, promoted_contract)
        write_json(patch_path, patch_preview)
        report_path.write_text(self.proposal_markdown(proposal), encoding="utf-8")
        write_json(proposal_path, proposal)
        return {"ok": True, "proposal": proposal, "source_gis_modified": False}

    def list_proposals(self, limit: int = 50) -> list[dict]:
        rows = []
        if not self.promotions_dir.exists():
            return rows
        for path in self.promotions_dir.glob("*/promotion_proposal.json"):
            payload = read_json(path)
            if payload.get("profile_promotion_version") != PROFILE_PROMOTION_VERSION:
                continue
            latest_decision = self.latest_decision(str(payload.get("proposal_id") or ""))
            rows.append({
                "proposal_id": payload.get("proposal_id"),
                "profile_id": payload.get("profile_id"),
                "workspace_id": payload.get("workspace_id"),
                "status": payload.get("status"),
                "proposal_action": payload.get("proposal_action"),
                "decision_status": latest_decision.get("decision_status", "pending_review"),
                "decision_id": latest_decision.get("decision_id", ""),
                "created_at_utc": payload.get("created_at_utc"),
                "approval_required_before_config_change": payload.get("approval_required_before_config_change") is True,
                "source_gis_modified": False,
            })
        rows.sort(key=lambda row: str(row.get("created_at_utc") or ""), reverse=True)
        return rows[: max(1, min(int(limit or 50), 500))]

    def detail(self, proposal_id: str) -> dict:
        clean = safe_token(proposal_id, "")
        path = self.promotions_dir / clean / "promotion_proposal.json"
        payload = read_json(path)
        if not payload:
            return {"ok": False, "error": "profile_promotion_proposal_not_found", "proposal_id": proposal_id, "source_gis_modified": False}
        latest_decision = self.latest_decision(proposal_id)
        payload["decision_status"] = latest_decision.get("decision_status", "pending_review")
        payload["latest_decision"] = latest_decision
        return payload

    def review_queue(self, limit: int = 50) -> list[dict]:
        rows = []
        for proposal in self.list_proposals(500):
            latest_decision = self.latest_decision(str(proposal.get("proposal_id") or ""))
            decision_status = latest_decision.get("decision_status", "pending_review")
            rows.append({
                "proposal_id": proposal.get("proposal_id"),
                "profile_id": proposal.get("profile_id"),
                "workspace_id": proposal.get("workspace_id"),
                "proposal_action": proposal.get("proposal_action"),
                "proposal_status": proposal.get("status"),
                "decision_status": decision_status,
                "decision_id": latest_decision.get("decision_id", ""),
                "reviewer": latest_decision.get("reviewer", ""),
                "created_at_utc": proposal.get("created_at_utc"),
                "next_step": self.next_review_step(decision_status),
                "mutates_config": False,
                "source_gis_modified": False,
            })
        rows.sort(key=lambda row: (0 if row.get("decision_status") == "pending_review" else 1, str(row.get("created_at_utc") or "")), reverse=False)
        return rows[: max(1, min(int(limit or 50), 500))]

    def decide(self, proposal_id: str, body: dict | None = None) -> dict:
        body = body or {}
        proposal = self.detail(proposal_id)
        if proposal.get("error"):
            return proposal
        requested = str(body.get("decision") or body.get("action") or "").strip().lower()
        status_map = {
            "approve": "approved",
            "approved": "approved",
            "accept": "approved",
            "accepted": "approved",
            "reject": "rejected",
            "rejected": "rejected",
            "decline": "rejected",
        }
        decision_status = status_map.get(requested, "")
        if not decision_status:
            return {
                "ok": False,
                "error": "profile_acceptance_decision_invalid",
                "proposal_id": proposal_id,
                "allowed_decisions": ["approve", "reject"],
                "source_gis_modified": False,
            }
        reviewer = safe_token(body.get("reviewer") or "local_reviewer", "local_reviewer")
        notes = str(body.get("notes") or "")
        created_at = utc_now()
        proposal_dir = self.promotions_dir / safe_token(proposal_id, "")
        decisions_dir = proposal_dir / "acceptance_decisions"
        existing_decisions = [path for path in decisions_dir.glob("*.json") if not path.name.endswith("_accepted_contract_snapshot.json")] if decisions_dir.exists() else []
        created_token = safe_token(created_at, "timestamp")
        profile_token = safe_token(proposal.get("profile_id") or "profile", "profile")
        decision_id = safe_token(f"profile_acceptance_{created_token}_{len(existing_decisions) + 1}_{decision_status}_{profile_token}", "profile_acceptance_decision")
        decision_path = decisions_dir / f"{decision_id}.json"
        report_path = decisions_dir / f"{decision_id}.md"
        accepted_contract_path = ""
        if decision_status == "approved":
            accepted_contract_path = str(decisions_dir / f"{decision_id}_accepted_contract_snapshot.json")
        decision = {
            "ok": True,
            "profile_acceptance_version": PROFILE_ACCEPTANCE_VERSION,
            "decision_id": decision_id,
            "proposal_id": proposal_id,
            "profile_id": proposal.get("profile_id"),
            "workspace_id": proposal.get("workspace_id"),
            "decision_status": decision_status,
            "reviewer": reviewer,
            "notes": notes,
            "created_at_utc": created_at,
            "mutates_config": False,
            "mutates_source_gis": False,
            "approval_required_for_config_mutation": True,
            "manual_followup_required": decision_status == "approved",
            "files": {
                "decision": str(decision_path),
                "decision_report": str(report_path),
                "accepted_contract_snapshot": accepted_contract_path,
                "proposal": str(proposal_dir / "promotion_proposal.json"),
            },
            "claim_boundaries": [
                "This decision records manual review evidence only.",
                "It does not modify profile mapper config.",
                "It does not modify source GIS files.",
                "A separate explicit implementation task is required before any config mutation.",
                self.review_wording,
            ],
            "source_gis_modified": False,
        }
        write_json(decision_path, decision)
        if accepted_contract_path:
            write_json(Path(accepted_contract_path), proposal.get("promoted_contract", {}))
        report_path.write_text(self.decision_markdown(decision), encoding="utf-8")
        write_json(proposal_dir / "latest_decision.json", decision)
        return {"ok": True, "decision": decision, "source_gis_modified": False}

    def list_decisions(self, limit: int = 50) -> list[dict]:
        rows = []
        if not self.promotions_dir.exists():
            return rows
        for path in self.promotions_dir.glob("*/acceptance_decisions/*.json"):
            if path.name.endswith("_accepted_contract_snapshot.json"):
                continue
            payload = read_json(path)
            if payload.get("profile_acceptance_version") != PROFILE_ACCEPTANCE_VERSION:
                continue
            rows.append({
                "decision_id": payload.get("decision_id"),
                "proposal_id": payload.get("proposal_id"),
                "profile_id": payload.get("profile_id"),
                "workspace_id": payload.get("workspace_id"),
                "decision_status": payload.get("decision_status"),
                "reviewer": payload.get("reviewer"),
                "created_at_utc": payload.get("created_at_utc"),
                "mutates_config": False,
                "source_gis_modified": False,
            })
        rows.sort(key=lambda row: str(row.get("created_at_utc") or ""), reverse=True)
        return rows[: max(1, min(int(limit or 50), 500))]

    def latest_decision(self, proposal_id: str) -> dict:
        proposal_dir = self.promotions_dir / safe_token(proposal_id, "")
        latest = read_json(proposal_dir / "latest_decision.json")
        if latest.get("profile_acceptance_version") == PROFILE_ACCEPTANCE_VERSION:
            return latest
        decisions = []
        for path in (proposal_dir / "acceptance_decisions").glob("*.json") if (proposal_dir / "acceptance_decisions").exists() else []:
            if path.name.endswith("_accepted_contract_snapshot.json"):
                continue
            payload = read_json(path)
            if payload.get("profile_acceptance_version") == PROFILE_ACCEPTANCE_VERSION:
                decisions.append(payload)
        if not decisions:
            return {"ok": False, "error": "profile_acceptance_decision_not_found", "proposal_id": proposal_id, "decision_status": "pending_review", "source_gis_modified": False}
        return sorted(decisions, key=lambda row: str(row.get("created_at_utc") or ""), reverse=True)[0]

    @staticmethod
    def next_review_step(decision_status: str) -> str:
        if decision_status == "approved":
            return "Use the accepted contract snapshot in a separate explicit config-change task."
        if decision_status == "rejected":
            return "Revise the template or rerun authored audit before another proposal."
        return "Review the promotion proposal and record approve or reject decision."

    def contract_diff_candidates(self, limit: int = 50) -> list[dict]:
        rows = []
        for proposal_row in self.list_proposals(500):
            proposal = self.detail(str(proposal_row.get("proposal_id") or ""))
            if proposal.get("error"):
                continue
            proposed_contract = dict(proposal.get("promoted_contract") or {})
            profile_id = str(proposal.get("profile_id") or proposed_contract.get("profile_id") or "")
            current_contract = self.existing_contract(profile_id)
            latest_diff = self.latest_contract_diff(str(proposal.get("proposal_id") or ""))
            diff_summary = self.contract_field_diff_summary(current_contract, proposed_contract)
            rows.append({
                "proposal_id": proposal.get("proposal_id"),
                "profile_id": profile_id,
                "workspace_id": proposal.get("workspace_id"),
                "proposal_action": proposal.get("proposal_action"),
                "decision_status": proposal.get("decision_status", "pending_review"),
                "current_contract_found": bool(current_contract),
                "field_count": diff_summary.get("field_count", 0),
                "changed_count": diff_summary.get("changed_count", 0),
                "added_count": diff_summary.get("added_count", 0),
                "removed_count": diff_summary.get("removed_count", 0),
                "unchanged_count": diff_summary.get("unchanged_count", 0),
                "latest_contract_diff_id": latest_diff.get("diff_id", ""),
                "diff_status": "diff_created" if latest_diff.get("diff_id") else "ready_for_contract_diff",
                "next_step": "Create contract diff review." if not latest_diff.get("diff_id") else "Review latest contract diff.",
                "mutates_config": False,
                "source_gis_modified": False,
            })
        rows.sort(key=lambda row: str(row.get("proposal_id") or ""), reverse=True)
        return rows[: max(1, min(int(limit or 50), 500))]

    def create_contract_diff(self, body: dict | None = None) -> dict:
        body = body or {}
        proposal_id = str(body.get("proposal_id") or "")
        if not proposal_id:
            candidates = [row for row in self.contract_diff_candidates(500) if row.get("diff_status") == "ready_for_contract_diff"]
            if not candidates:
                candidates = self.contract_diff_candidates(500)
            if candidates:
                proposal_id = str(candidates[0].get("proposal_id") or "")
        if not proposal_id:
            return {"ok": False, "error": "profile_contract_diff_not_ready", "detail": "No profile promotion proposal is available", "source_gis_modified": False}

        proposal = self.detail(proposal_id)
        if proposal.get("error"):
            return proposal
        proposed_contract = dict(proposal.get("promoted_contract") or {})
        profile_id = str(proposal.get("profile_id") or proposed_contract.get("profile_id") or "")
        if not proposed_contract:
            return {"ok": False, "error": "profile_contract_diff_not_ready", "proposal_id": proposal_id, "detail": "Proposal has no promoted contract", "source_gis_modified": False}

        current_contract = self.existing_contract(profile_id)
        operation = "replace_contract" if current_contract else "append_contract"
        diff_summary = self.contract_field_diff_summary(current_contract, proposed_contract)
        created_at = utc_now()
        proposal_dir = self.promotions_dir / safe_token(proposal_id, "")
        diffs_dir = proposal_dir / "contract_diffs"
        existing_diffs = list(diffs_dir.glob("profile_contract_diff_*.json")) if diffs_dir.exists() else []
        diff_id = safe_token(f"profile_contract_diff_{safe_token(created_at, 'timestamp')}_{len(existing_diffs) + 1}_{profile_id}", "profile_contract_diff")
        diff_path = diffs_dir / f"{diff_id}.json"
        review_path = diffs_dir / f"{diff_id}_review.md"

        diff = {
            "ok": True,
            "profile_contract_diff_review_version": PROFILE_CONTRACT_DIFF_VERSION,
            "diff_id": diff_id,
            "created_at_utc": created_at,
            "diff_status": "ready_for_manual_review",
            "proposal_id": proposal_id,
            "profile_id": profile_id,
            "workspace_id": proposal.get("workspace_id"),
            "operation": operation,
            "current_contract_found": bool(current_contract),
            "target_config": str(self.mapper_config_path),
            "summary": diff_summary,
            "review_checks": [
                {"check": "proposal_contract_present", "passed": bool(proposed_contract), "evidence": profile_id},
                {"check": "current_contract_loaded", "passed": True, "evidence": "found" if current_contract else "new profile append"},
                {"check": "diff_has_reviewable_fields", "passed": diff_summary.get("field_count", 0) > 0, "evidence": f"{diff_summary.get('field_count', 0)} total fields"},
                {"check": "config_mutation_disabled", "passed": True, "evidence": "diff review writes review artifacts only"},
                {"check": "source_gis_read_only", "passed": True, "evidence": "source_gis_modified=false"},
            ],
            "files": {
                "contract_diff": str(diff_path),
                "review_markdown": str(review_path),
                "proposal": str(proposal_dir / "promotion_proposal.json"),
            },
            "mutates_config": False,
            "requires_manual_review_before_config_change": True,
            "source_gis_modified": False,
            "claim_boundaries": [
                "This diff is evidence for manual profile contract review.",
                "It does not modify profile mapper config.",
                "It does not modify source GIS files.",
                "Missing OSM tags remain data-quality flags.",
                self.review_wording,
            ],
        }
        write_json(diff_path, diff)
        review_path.write_text(self.contract_diff_markdown(diff), encoding="utf-8")
        write_json(proposal_dir / "latest_contract_diff.json", diff)
        return {"ok": True, "contract_diff": diff, "source_gis_modified": False}

    def list_contract_diffs(self, limit: int = 50) -> list[dict]:
        rows = []
        if not self.promotions_dir.exists():
            return rows
        for path in self.promotions_dir.glob("*/contract_diffs/profile_contract_diff_*.json"):
            payload = read_json(path)
            if payload.get("profile_contract_diff_review_version") != PROFILE_CONTRACT_DIFF_VERSION:
                continue
            summary = payload.get("summary", {})
            rows.append({
                "diff_id": payload.get("diff_id"),
                "proposal_id": payload.get("proposal_id"),
                "profile_id": payload.get("profile_id"),
                "operation": payload.get("operation"),
                "diff_status": payload.get("diff_status"),
                "field_count": summary.get("field_count", 0),
                "changed_count": summary.get("changed_count", 0),
                "added_count": summary.get("added_count", 0),
                "removed_count": summary.get("removed_count", 0),
                "created_at_utc": payload.get("created_at_utc"),
                "mutates_config": False,
                "source_gis_modified": False,
            })
        rows.sort(key=lambda row: str(row.get("created_at_utc") or ""), reverse=True)
        return rows[: max(1, min(int(limit or 50), 500))]

    def contract_diff_detail(self, diff_id: str) -> dict:
        clean = safe_token(diff_id, "")
        for path in self.promotions_dir.glob(f"*/contract_diffs/{clean}.json"):
            payload = read_json(path)
            if payload.get("profile_contract_diff_review_version") == PROFILE_CONTRACT_DIFF_VERSION:
                return payload
        return {"ok": False, "error": "profile_contract_diff_not_found", "diff_id": diff_id, "source_gis_modified": False}

    def latest_contract_diff(self, proposal_id: str) -> dict:
        proposal_dir = self.promotions_dir / safe_token(proposal_id, "")
        latest = read_json(proposal_dir / "latest_contract_diff.json")
        if latest.get("profile_contract_diff_review_version") == PROFILE_CONTRACT_DIFF_VERSION:
            return latest
        diffs = []
        for path in (proposal_dir / "contract_diffs").glob("profile_contract_diff_*.json") if (proposal_dir / "contract_diffs").exists() else []:
            payload = read_json(path)
            if payload.get("profile_contract_diff_review_version") == PROFILE_CONTRACT_DIFF_VERSION:
                diffs.append(payload)
        if not diffs:
            return {"ok": False, "error": "profile_contract_diff_not_found", "proposal_id": proposal_id, "source_gis_modified": False}
        return sorted(diffs, key=lambda row: str(row.get("created_at_utc") or ""), reverse=True)[0]

    @staticmethod
    def value_kind(value: object) -> str:
        if isinstance(value, dict):
            return f"object:{len(value)}"
        if isinstance(value, list):
            return f"array:{len(value)}"
        if value is None:
            return "null"
        return type(value).__name__

    @classmethod
    def contract_field_diff_summary(cls, current_contract: dict, proposed_contract: dict) -> dict:
        fields = sorted(set(current_contract) | set(proposed_contract))
        groups: dict[str, list[dict]] = {
            "added_fields": [],
            "removed_fields": [],
            "changed_fields": [],
            "unchanged_fields": [],
        }
        for field in fields:
            current_has = field in current_contract
            proposed_has = field in proposed_contract
            current_value = current_contract.get(field)
            proposed_value = proposed_contract.get(field)
            item = {
                "field": field,
                "current_value": current_value,
                "proposed_value": proposed_value,
                "current_kind": cls.value_kind(current_value),
                "proposed_kind": cls.value_kind(proposed_value),
            }
            if not current_has and proposed_has:
                groups["added_fields"].append(item)
            elif current_has and not proposed_has:
                groups["removed_fields"].append(item)
            elif current_value != proposed_value:
                groups["changed_fields"].append(item)
            else:
                groups["unchanged_fields"].append(item)
        review_priority = [
            item.get("field")
            for item in groups["changed_fields"] + groups["added_fields"] + groups["removed_fields"]
            if item.get("field") in {"profile_id", "mapper_type", "required_layers", "required_tags", "output_schema", "scoring_rules", "claim_boundaries", "missing_data_policy", "implementation_entrypoint", "status"}
        ]
        return {
            "field_count": len(fields),
            "added_count": len(groups["added_fields"]),
            "removed_count": len(groups["removed_fields"]),
            "changed_count": len(groups["changed_fields"]),
            "unchanged_count": len(groups["unchanged_fields"]),
            "review_priority_fields": review_priority,
            "field_groups": groups,
        }

    def config_apply_candidates(self, limit: int = 50) -> list[dict]:
        rows = []
        for plan_row in self.list_application_plans(500):
            plan = self.application_plan_detail(str(plan_row.get("plan_id") or ""))
            if plan.get("error") or plan.get("plan_status") != "ready_for_manual_implementation":
                continue
            proposal_id = str(plan.get("proposal_id") or "")
            latest_apply = self.latest_config_apply_proposal(proposal_id)
            latest_diff = self.latest_contract_diff(proposal_id)
            rows.append({
                "proposal_id": proposal_id,
                "application_plan_id": plan.get("plan_id"),
                "decision_id": plan.get("decision_id"),
                "profile_id": plan.get("profile_id"),
                "operation": plan.get("operation"),
                "latest_contract_diff_id": latest_diff.get("diff_id", ""),
                "latest_config_apply_proposal_id": latest_apply.get("apply_id", ""),
                "apply_status": "apply_proposal_created" if latest_apply.get("apply_id") else "ready_for_apply_proposal",
                "next_step": "Review latest guarded apply proposal." if latest_apply.get("apply_id") else "Create guarded config apply proposal.",
                "mutates_config": False,
                "source_gis_modified": False,
            })
        rows.sort(key=lambda row: str(row.get("application_plan_id") or ""), reverse=True)
        return rows[: max(1, min(int(limit or 50), 500))]

    def create_config_apply_proposal(self, body: dict | None = None) -> dict:
        body = body or {}
        plan_id = str(body.get("application_plan_id") or body.get("plan_id") or "")
        proposal_id = str(body.get("proposal_id") or "")
        if not plan_id and not proposal_id:
            candidates = [row for row in self.config_apply_candidates(500) if row.get("apply_status") == "ready_for_apply_proposal"]
            if not candidates:
                candidates = self.config_apply_candidates(500)
            if candidates:
                plan_id = str(candidates[0].get("application_plan_id") or "")
                proposal_id = str(candidates[0].get("proposal_id") or "")

        plan = self.application_plan_detail(plan_id) if plan_id else {}
        if not plan or plan.get("error"):
            if proposal_id:
                plan = self.latest_application_plan(proposal_id)
        if not plan or plan.get("error") or plan.get("plan_status") != "ready_for_manual_implementation":
            return {"ok": False, "error": "profile_config_apply_proposal_not_ready", "detail": "A ready application plan is required", "source_gis_modified": False}

        proposal_id = str(plan.get("proposal_id") or proposal_id)
        proposal = self.detail(proposal_id)
        if proposal.get("error"):
            return proposal
        proposed_contract = dict(proposal.get("promoted_contract") or plan.get("config_patch_preview", {}).get("proposed_contract") or {})
        profile_id = str(proposal.get("profile_id") or plan.get("profile_id") or proposed_contract.get("profile_id") or "")
        if not proposed_contract or not profile_id:
            return {"ok": False, "error": "profile_config_apply_proposal_not_ready", "proposal_id": proposal_id, "detail": "Proposed contract is missing", "source_gis_modified": False}

        current_config = self.mapper_config()
        proposed_config, operation, contract_count_before, contract_count_after = self.proposed_mapper_config(profile_id, proposed_contract)
        proposed_config_text = json.dumps(proposed_config, ensure_ascii=False, indent=2)
        current_config_sha256 = self.file_sha256(self.mapper_config_path)
        proposed_config_sha256 = hashlib.sha256(proposed_config_text.encode("utf-8")).hexdigest()
        latest_diff = self.latest_contract_diff(proposal_id)
        created_at = utc_now()
        proposal_dir = self.promotions_dir / safe_token(proposal_id, "")
        apply_dir = proposal_dir / "config_apply_proposals"
        existing = list(apply_dir.glob("profile_config_apply_proposal_*.json")) if apply_dir.exists() else []
        apply_id = safe_token(f"profile_config_apply_proposal_{safe_token(created_at, 'timestamp')}_{len(existing) + 1}_{profile_id}", "profile_config_apply_proposal")
        apply_path = apply_dir / f"{apply_id}.json"
        preview_path = apply_dir / f"{apply_id}_proposed_config_preview.json"
        checklist_path = apply_dir / f"{apply_id}_manual_approval_checklist.md"

        gates = [
            {"gate": "application_plan_ready", "passed": True, "evidence": str(plan.get("plan_id") or "")},
            {"gate": "contract_diff_available", "passed": bool(latest_diff.get("diff_id")), "evidence": str(latest_diff.get("diff_id") or "missing")},
            {"gate": "target_config_exists", "passed": self.mapper_config_path.exists(), "evidence": str(self.mapper_config_path)},
            {"gate": "current_config_hash_recorded", "passed": bool(current_config_sha256), "evidence": current_config_sha256[:12]},
            {"gate": "proposed_config_preview_written", "passed": True, "evidence": str(preview_path)},
            {"gate": "config_mutation_disabled", "passed": True, "evidence": "apply proposal writes preview artifacts only"},
            {"gate": "source_gis_read_only", "passed": True, "evidence": "source_gis_modified=false"},
        ]
        apply_proposal = {
            "ok": True,
            "profile_config_apply_proposal_version": PROFILE_CONFIG_APPLY_PROPOSAL_VERSION,
            "apply_id": apply_id,
            "created_at_utc": created_at,
            "apply_status": "ready_for_explicit_approval",
            "proposal_id": proposal_id,
            "application_plan_id": plan.get("plan_id"),
            "contract_diff_id": latest_diff.get("diff_id", ""),
            "decision_id": plan.get("decision_id"),
            "profile_id": profile_id,
            "operation": operation,
            "target_config": str(self.mapper_config_path),
            "target_config_exists": self.mapper_config_path.exists(),
            "current_config_sha256": current_config_sha256,
            "proposed_config_sha256": proposed_config_sha256,
            "contract_count_before": contract_count_before,
            "contract_count_after": contract_count_after,
            "field_change_count": plan.get("field_change_count", 0),
            "gates": gates,
            "approval_requirements": [
                "Review the contract diff and application plan.",
                "Confirm the target config hash still matches current_config_sha256.",
                "Apply the proposed config only in a separate explicit config-change task.",
                "Run validation and API contract tests after any real config change.",
            ],
            "validation_commands": [
                ".\\scripts\\validate.ps1",
                ".\\scripts\\test_api_contract.ps1",
            ],
            "files": {
                "config_apply_proposal": str(apply_path),
                "proposed_config_preview": str(preview_path),
                "manual_approval_checklist": str(checklist_path),
                "application_plan": str(plan.get("files", {}).get("application_plan") or ""),
                "contract_diff": str(latest_diff.get("files", {}).get("contract_diff") or ""),
            },
            "mutates_config": False,
            "proposed_config_preview_mutates_config": False,
            "requires_separate_explicit_config_change_task": True,
            "source_gis_modified": False,
            "claim_boundaries": [
                "This apply proposal is evidence for a later explicit config-change task.",
                "It does not modify profile mapper config.",
                "It does not modify source GIS files.",
                "Missing OSM tags remain data-quality flags.",
                self.review_wording,
            ],
        }
        write_json(apply_path, apply_proposal)
        preview_path.write_text(proposed_config_text, encoding="utf-8")
        checklist_path.write_text(self.config_apply_proposal_markdown(apply_proposal), encoding="utf-8")
        write_json(proposal_dir / "latest_config_apply_proposal.json", apply_proposal)
        return {"ok": True, "config_apply_proposal": apply_proposal, "source_gis_modified": False}

    def list_config_apply_proposals(self, limit: int = 50) -> list[dict]:
        rows = []
        if not self.promotions_dir.exists():
            return rows
        for path in self.promotions_dir.glob("*/config_apply_proposals/profile_config_apply_proposal_*.json"):
            if path.name.endswith("_proposed_config_preview.json"):
                continue
            payload = read_json(path)
            if payload.get("profile_config_apply_proposal_version") != PROFILE_CONFIG_APPLY_PROPOSAL_VERSION:
                continue
            rows.append({
                "apply_id": payload.get("apply_id"),
                "proposal_id": payload.get("proposal_id"),
                "application_plan_id": payload.get("application_plan_id"),
                "contract_diff_id": payload.get("contract_diff_id"),
                "profile_id": payload.get("profile_id"),
                "operation": payload.get("operation"),
                "apply_status": payload.get("apply_status"),
                "contract_count_before": payload.get("contract_count_before"),
                "contract_count_after": payload.get("contract_count_after"),
                "created_at_utc": payload.get("created_at_utc"),
                "mutates_config": False,
                "source_gis_modified": False,
            })
        rows.sort(key=lambda row: str(row.get("created_at_utc") or ""), reverse=True)
        return rows[: max(1, min(int(limit or 50), 500))]

    def config_apply_proposal_detail(self, apply_id: str) -> dict:
        clean = safe_token(apply_id, "")
        for path in self.promotions_dir.glob(f"*/config_apply_proposals/{clean}.json"):
            payload = read_json(path)
            if payload.get("profile_config_apply_proposal_version") == PROFILE_CONFIG_APPLY_PROPOSAL_VERSION:
                return payload
        return {"ok": False, "error": "profile_config_apply_proposal_not_found", "apply_id": apply_id, "source_gis_modified": False}

    def latest_config_apply_proposal(self, proposal_id: str) -> dict:
        proposal_dir = self.promotions_dir / safe_token(proposal_id, "")
        latest = read_json(proposal_dir / "latest_config_apply_proposal.json")
        if latest.get("profile_config_apply_proposal_version") == PROFILE_CONFIG_APPLY_PROPOSAL_VERSION:
            return latest
        proposals = []
        for path in (proposal_dir / "config_apply_proposals").glob("profile_config_apply_proposal_*.json") if (proposal_dir / "config_apply_proposals").exists() else []:
            if path.name.endswith("_proposed_config_preview.json"):
                continue
            payload = read_json(path)
            if payload.get("profile_config_apply_proposal_version") == PROFILE_CONFIG_APPLY_PROPOSAL_VERSION:
                proposals.append(payload)
        if not proposals:
            return {"ok": False, "error": "profile_config_apply_proposal_not_found", "proposal_id": proposal_id, "source_gis_modified": False}
        return sorted(proposals, key=lambda row: str(row.get("created_at_utc") or ""), reverse=True)[0]

    def file_sha256(self, path: Path) -> str:
        try:
            if not path.exists():
                return ""
            return hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError:
            return ""

    def text_file_sha256(self, path: Path) -> str:
        try:
            if not path.exists():
                return ""
            return hashlib.sha256(path.read_text(encoding="utf-8").encode("utf-8")).hexdigest()
        except OSError:
            return ""

    def proposed_mapper_config(self, profile_id: str, proposed_contract: dict) -> tuple[dict, str, int, int]:
        current_config = dict(self.mapper_config())
        contracts = current_config.get("contracts", [])
        if not isinstance(contracts, list):
            contracts = []
        contract_count_before = len(contracts)
        operation = "append_contract"
        next_contracts = []
        replaced = False
        for contract in contracts:
            if str(contract.get("profile_id") or "") == str(profile_id or ""):
                next_contracts.append(proposed_contract)
                replaced = True
                operation = "replace_contract"
            else:
                next_contracts.append(contract)
        if not replaced:
            next_contracts.append(proposed_contract)
        proposed_config = dict(current_config)
        proposed_config["contracts"] = next_contracts
        return proposed_config, operation, contract_count_before, len(next_contracts)

    def contract_regression_candidates(self, limit: int = 50) -> list[dict]:
        rows = []
        for apply_row in self.list_config_apply_proposals(500):
            apply_proposal = self.config_apply_proposal_detail(str(apply_row.get("apply_id") or ""))
            if apply_proposal.get("error"):
                continue
            latest_preview = self.latest_contract_regression_preview(str(apply_proposal.get("apply_id") or ""))
            rows.append({
                "apply_id": apply_proposal.get("apply_id"),
                "proposal_id": apply_proposal.get("proposal_id"),
                "application_plan_id": apply_proposal.get("application_plan_id"),
                "contract_diff_id": apply_proposal.get("contract_diff_id"),
                "profile_id": apply_proposal.get("profile_id"),
                "operation": apply_proposal.get("operation"),
                "apply_status": apply_proposal.get("apply_status"),
                "latest_regression_preview_id": latest_preview.get("preview_id", ""),
                "regression_status": "preview_created" if latest_preview.get("preview_id") else "ready_for_regression_preview",
                "next_step": "Review latest regression preview." if latest_preview.get("preview_id") else "Create profile contract regression preview.",
                "mutates_config": False,
                "source_gis_modified": False,
            })
        rows.sort(key=lambda row: str(row.get("apply_id") or ""), reverse=True)
        return rows[: max(1, min(int(limit or 50), 500))]

    def create_contract_regression_preview(self, body: dict | None = None) -> dict:
        body = body or {}
        apply_id = str(body.get("apply_id") or body.get("config_apply_proposal_id") or "")
        proposal_id = str(body.get("proposal_id") or "")
        if not apply_id and not proposal_id:
            candidates = [row for row in self.contract_regression_candidates(500) if row.get("regression_status") == "ready_for_regression_preview"]
            if not candidates:
                candidates = self.contract_regression_candidates(500)
            if candidates:
                apply_id = str(candidates[0].get("apply_id") or "")
                proposal_id = str(candidates[0].get("proposal_id") or "")

        apply_proposal = self.config_apply_proposal_detail(apply_id) if apply_id else {}
        if not apply_proposal or apply_proposal.get("error"):
            if proposal_id:
                apply_proposal = self.latest_config_apply_proposal(proposal_id)
        if not apply_proposal or apply_proposal.get("error"):
            return {"ok": False, "error": "profile_contract_regression_preview_not_ready", "detail": "A guarded config apply proposal is required", "source_gis_modified": False}

        proposal_id = str(apply_proposal.get("proposal_id") or proposal_id)
        profile_id = str(apply_proposal.get("profile_id") or "")
        preview_path = Path(str(apply_proposal.get("files", {}).get("proposed_config_preview") or ""))
        proposed_config = read_json(preview_path)
        if not proposed_config:
            return {"ok": False, "error": "profile_contract_regression_preview_not_ready", "detail": "Proposed config preview is missing or invalid", "source_gis_modified": False}

        current_config = self.mapper_config()
        checks = self.contract_regression_checks(current_config, proposed_config, apply_proposal, preview_path)
        failed_checks = [row for row in checks if not row.get("passed")]
        warnings = self.contract_regression_warnings(proposed_config, profile_id)
        created_at = utc_now()
        proposal_dir = self.promotions_dir / safe_token(proposal_id, "")
        preview_dir = proposal_dir / "regression_previews"
        existing = list(preview_dir.glob("profile_contract_regression_preview_*.json")) if preview_dir.exists() else []
        preview_id = safe_token(f"profile_contract_regression_preview_{safe_token(created_at, 'timestamp')}_{len(existing) + 1}_{profile_id}", "profile_contract_regression_preview")
        preview_file = preview_dir / f"{preview_id}.json"
        report_file = preview_dir / f"{preview_id}_report.md"
        preview = {
            "ok": True,
            "profile_contract_regression_preview_version": PROFILE_CONTRACT_REGRESSION_PREVIEW_VERSION,
            "preview_id": preview_id,
            "created_at_utc": created_at,
            "regression_status": "passed" if not failed_checks else "needs_review",
            "apply_id": apply_proposal.get("apply_id"),
            "proposal_id": proposal_id,
            "application_plan_id": apply_proposal.get("application_plan_id"),
            "contract_diff_id": apply_proposal.get("contract_diff_id"),
            "profile_id": profile_id,
            "operation": apply_proposal.get("operation"),
            "target_config": apply_proposal.get("target_config"),
            "current_config_sha256": apply_proposal.get("current_config_sha256"),
            "proposed_config_sha256": apply_proposal.get("proposed_config_sha256"),
            "check_count": len(checks),
            "failed_check_count": len(failed_checks),
            "warning_count": len(warnings),
            "checks": checks,
            "warnings": warnings,
            "contract_count_before": len(current_config.get("contracts", [])),
            "contract_count_after": len(proposed_config.get("contracts", [])),
            "files": {
                "regression_preview": str(preview_file),
                "regression_report": str(report_file),
                "config_apply_proposal": str(apply_proposal.get("files", {}).get("config_apply_proposal") or ""),
                "proposed_config_preview": str(preview_path),
            },
            "mutates_config": False,
            "source_gis_modified": False,
            "claim_boundaries": [
                "This regression preview validates a proposed mapper config before a separate explicit config-change task.",
                "It does not modify profile mapper config.",
                "It does not modify source GIS files.",
                "Missing OSM tags remain data-quality flags.",
                self.review_wording,
            ],
        }
        write_json(preview_file, preview)
        report_file.write_text(self.contract_regression_preview_markdown(preview), encoding="utf-8")
        write_json(proposal_dir / "latest_contract_regression_preview.json", preview)
        return {"ok": True, "regression_preview": preview, "source_gis_modified": False}

    def list_contract_regression_previews(self, limit: int = 50) -> list[dict]:
        rows = []
        if not self.promotions_dir.exists():
            return rows
        for path in self.promotions_dir.glob("*/regression_previews/profile_contract_regression_preview_*.json"):
            payload = read_json(path)
            if payload.get("profile_contract_regression_preview_version") != PROFILE_CONTRACT_REGRESSION_PREVIEW_VERSION:
                continue
            rows.append({
                "preview_id": payload.get("preview_id"),
                "apply_id": payload.get("apply_id"),
                "proposal_id": payload.get("proposal_id"),
                "profile_id": payload.get("profile_id"),
                "operation": payload.get("operation"),
                "regression_status": payload.get("regression_status"),
                "check_count": payload.get("check_count"),
                "failed_check_count": payload.get("failed_check_count"),
                "created_at_utc": payload.get("created_at_utc"),
                "mutates_config": False,
                "source_gis_modified": False,
            })
        rows.sort(key=lambda row: str(row.get("created_at_utc") or ""), reverse=True)
        return rows[: max(1, min(int(limit or 50), 500))]

    def contract_regression_preview_detail(self, preview_id: str) -> dict:
        clean = safe_token(preview_id, "")
        for path in self.promotions_dir.glob(f"*/regression_previews/{clean}.json"):
            payload = read_json(path)
            if payload.get("profile_contract_regression_preview_version") == PROFILE_CONTRACT_REGRESSION_PREVIEW_VERSION:
                return payload
        return {"ok": False, "error": "profile_contract_regression_preview_not_found", "preview_id": preview_id, "source_gis_modified": False}

    def latest_contract_regression_preview(self, apply_id: str = "", proposal_id: str = "") -> dict:
        if not proposal_id and apply_id:
            apply_proposal = self.config_apply_proposal_detail(apply_id)
            proposal_id = str(apply_proposal.get("proposal_id") or "")
        proposal_dir = self.promotions_dir / safe_token(proposal_id, "")
        latest = read_json(proposal_dir / "latest_contract_regression_preview.json")
        if latest.get("profile_contract_regression_preview_version") == PROFILE_CONTRACT_REGRESSION_PREVIEW_VERSION and (not apply_id or latest.get("apply_id") == apply_id):
            return latest
        previews = []
        for path in (proposal_dir / "regression_previews").glob("profile_contract_regression_preview_*.json") if (proposal_dir / "regression_previews").exists() else []:
            payload = read_json(path)
            if payload.get("profile_contract_regression_preview_version") == PROFILE_CONTRACT_REGRESSION_PREVIEW_VERSION and (not apply_id or payload.get("apply_id") == apply_id):
                previews.append(payload)
        if not previews:
            return {"ok": False, "error": "profile_contract_regression_preview_not_found", "apply_id": apply_id, "source_gis_modified": False}
        return sorted(previews, key=lambda row: str(row.get("created_at_utc") or ""), reverse=True)[0]

    def contract_regression_checks(self, current_config: dict, proposed_config: dict, apply_proposal: dict, preview_path: Path) -> list[dict]:
        current_contracts = current_config.get("contracts", []) if isinstance(current_config.get("contracts", []), list) else []
        proposed_contracts = proposed_config.get("contracts", []) if isinstance(proposed_config.get("contracts", []), list) else []
        required_fields = proposed_config.get("required_contract_fields") or current_config.get("required_contract_fields") or []
        proposed_ids = [str(contract.get("profile_id") or "") for contract in proposed_contracts]
        current_ids = [str(contract.get("profile_id") or "") for contract in current_contracts]
        duplicate_ids = sorted({profile_id for profile_id in proposed_ids if profile_id and proposed_ids.count(profile_id) > 1})
        missing_current_ids = sorted(profile_id for profile_id in current_ids if profile_id and profile_id not in proposed_ids)
        invalid_contracts = [
            {
                "profile_id": contract.get("profile_id"),
                "missing_fields": [field for field in required_fields if field not in contract],
            }
            for contract in proposed_contracts
        ]
        invalid_contracts = [row for row in invalid_contracts if row.get("missing_fields")]
        profile_id = str(apply_proposal.get("profile_id") or "")
        target_contract = next((contract for contract in proposed_contracts if str(contract.get("profile_id") or "") == profile_id), {})
        preview_hash = self.text_file_sha256(preview_path)
        target_text = json.dumps(target_contract, ensure_ascii=False)
        return [
            {"check": "proposed_config_parseable", "passed": bool(proposed_config), "evidence": str(preview_path)},
            {"check": "proposed_hash_matches_apply_proposal", "passed": preview_hash == apply_proposal.get("proposed_config_sha256"), "evidence": preview_hash[:12]},
            {"check": "required_contract_fields_preserved", "passed": bool(required_fields), "evidence": f"{len(required_fields)} required fields"},
            {"check": "all_contracts_have_required_fields", "passed": not invalid_contracts, "evidence": invalid_contracts[:5]},
            {"check": "no_duplicate_profile_ids", "passed": not duplicate_ids, "evidence": duplicate_ids},
            {"check": "existing_profiles_preserved", "passed": not missing_current_ids, "evidence": missing_current_ids},
            {"check": "promoted_profile_present", "passed": bool(target_contract), "evidence": profile_id},
            {"check": "contract_count_not_decreased", "passed": len(proposed_contracts) >= len(current_contracts), "evidence": f"{len(current_contracts)} -> {len(proposed_contracts)}"},
            {"check": "approved_review_wording_preserved", "passed": self.review_wording in target_text, "evidence": "approved wording found" if self.review_wording in target_text else "missing"},
            {"check": "missing_data_policy_present", "passed": bool(target_contract.get("missing_data_policy")), "evidence": str(target_contract.get("missing_data_policy") or "")[:120]},
            {"check": "config_mutation_disabled", "passed": True, "evidence": "regression preview writes artifacts only"},
            {"check": "source_gis_read_only", "passed": True, "evidence": "source_gis_modified=false"},
        ]

    @staticmethod
    def contract_regression_warnings(proposed_config: dict, profile_id: str) -> list[str]:
        contracts = proposed_config.get("contracts", []) if isinstance(proposed_config.get("contracts", []), list) else []
        target_contract = next((contract for contract in contracts if str(contract.get("profile_id") or "") == profile_id), {})
        warnings = ["regression_preview_is_not_runtime_execution"]
        if target_contract.get("runner_status") not in {"implemented", "authored_audit_available"}:
            warnings.append("promoted_profile_runner_may_still_need_dedicated_implementation")
        if target_contract.get("status") != "profile_ready":
            warnings.append("promoted_profile_status_should_be_reviewed")
        return warnings

    def application_candidates(self, limit: int = 50) -> list[dict]:
        rows = []
        for decision in self.list_decisions(500):
            if decision.get("decision_status") != "approved":
                continue
            proposal = self.detail(str(decision.get("proposal_id") or ""))
            if proposal.get("error"):
                continue
            latest_plan = self.latest_application_plan(str(proposal.get("proposal_id") or ""))
            latest_diff = self.latest_contract_diff(str(proposal.get("proposal_id") or ""))
            rows.append({
                "proposal_id": proposal.get("proposal_id"),
                "decision_id": decision.get("decision_id"),
                "profile_id": proposal.get("profile_id"),
                "workspace_id": proposal.get("workspace_id"),
                "proposal_action": proposal.get("proposal_action"),
                "decision_status": decision.get("decision_status"),
                "latest_application_plan_id": latest_plan.get("plan_id", ""),
                "latest_contract_diff_id": latest_diff.get("diff_id", ""),
                "application_status": "planned" if latest_plan.get("plan_id") else "ready_for_application_plan",
                "next_step": "Create guarded application plan." if not latest_plan.get("plan_id") else "Review existing application plan.",
                "mutates_config": False,
                "source_gis_modified": False,
            })
        rows.sort(key=lambda row: str(row.get("decision_id") or ""), reverse=True)
        return rows[: max(1, min(int(limit or 50), 500))]

    def create_application_plan(self, body: dict | None = None) -> dict:
        body = body or {}
        proposal_id = str(body.get("proposal_id") or "")
        decision_id = str(body.get("decision_id") or "")
        if not proposal_id:
            candidates = [row for row in self.application_candidates(500) if row.get("application_status") == "ready_for_application_plan"]
            if not candidates:
                candidates = self.application_candidates(500)
            if candidates:
                proposal_id = str(candidates[0].get("proposal_id") or "")
                decision_id = decision_id or str(candidates[0].get("decision_id") or "")
        if not proposal_id:
            return {"ok": False, "error": "profile_application_plan_not_ready", "detail": "No approved promotion decision is available", "source_gis_modified": False}

        proposal = self.detail(proposal_id)
        if proposal.get("error"):
            return proposal
        decision = self.decision_by_id(decision_id) if decision_id else self.latest_decision(proposal_id)
        if decision.get("decision_status") != "approved":
            return {
                "ok": False,
                "error": "profile_application_plan_not_ready",
                "proposal_id": proposal_id,
                "decision_status": decision.get("decision_status", "pending_review"),
                "source_gis_modified": False,
            }

        proposed_contract = dict(proposal.get("promoted_contract") or {})
        profile_id = str(proposal.get("profile_id") or proposed_contract.get("profile_id") or "")
        current_contract = self.existing_contract(profile_id)
        operation = "replace_contract" if current_contract else "append_contract"
        field_changes = self.contract_field_changes(current_contract, proposed_contract)
        latest_diff = self.latest_contract_diff(proposal_id)
        created_at = utc_now()
        proposal_dir = self.promotions_dir / safe_token(proposal_id, "")
        plans_dir = proposal_dir / "application_plans"
        existing_plans = list(plans_dir.glob("profile_application_plan_*.json")) if plans_dir.exists() else []
        created_token = safe_token(created_at, "timestamp")
        profile_token = safe_token(profile_id or "profile", "profile")
        plan_id = safe_token(f"profile_application_plan_{created_token}_{len(existing_plans) + 1}_{profile_token}", "profile_application_plan")
        plan_path = plans_dir / f"{plan_id}.json"
        patch_path = plans_dir / f"{plan_id}_config_patch_preview.json"
        checklist_path = plans_dir / f"{plan_id}_manual_checklist.md"

        gates = [
            {"gate": "approved_decision_present", "passed": True, "evidence": str(decision.get("decision_id") or "")},
            {"gate": "target_config_exists", "passed": self.mapper_config_path.exists(), "evidence": str(self.mapper_config_path)},
            {"gate": "proposed_contract_present", "passed": bool(proposed_contract), "evidence": str(proposed_contract.get("profile_id") or "")},
            {"gate": "config_mutation_disabled", "passed": True, "evidence": "application plan writes preview artifacts only"},
            {"gate": "source_gis_read_only", "passed": True, "evidence": "source_gis_modified=false"},
        ]
        patch_preview = {
            "ok": True,
            "profile_application_plan_version": PROFILE_APPLICATION_PLAN_VERSION,
            "plan_id": plan_id,
            "operation": operation,
            "target_config": str(self.mapper_config_path),
            "profile_id": profile_id,
            "current_contract_found": bool(current_contract),
            "field_change_count": len(field_changes),
            "field_changes": field_changes,
            "proposed_contract": proposed_contract,
            "mutates_config": False,
            "requires_explicit_apply_task": True,
            "source_gis_modified": False,
        }
        plan = {
            "ok": True,
            "profile_application_plan_version": PROFILE_APPLICATION_PLAN_VERSION,
            "plan_id": plan_id,
            "created_at_utc": created_at,
            "plan_status": "ready_for_manual_implementation",
            "proposal_id": proposal_id,
            "decision_id": decision.get("decision_id"),
            "profile_id": profile_id,
            "operation": operation,
            "gates": gates,
            "field_change_count": len(field_changes),
            "latest_contract_diff_id": latest_diff.get("diff_id", ""),
            "config_patch_preview": patch_preview,
            "manual_steps": [
                "Review the accepted contract snapshot and patch preview.",
                "Open profile_mapper_contracts_v001.json in a separate explicit implementation task.",
                "Apply the contract replacement or append operation manually.",
                "Run validation and API contract tests after any config change.",
                "Keep source GIS files read-only.",
            ],
            "validation_commands": [
                ".\\scripts\\validate.ps1",
                ".\\scripts\\test_api_contract.ps1",
            ],
            "files": {
                "application_plan": str(plan_path),
                "config_patch_preview": str(patch_path),
                "manual_checklist": str(checklist_path),
                "proposal": str(proposal_dir / "promotion_proposal.json"),
                "latest_decision": str(proposal_dir / "latest_decision.json"),
            },
            "mutates_config": False,
            "source_gis_modified": False,
            "claim_boundaries": [
                "This plan is evidence for a later explicit config-change task.",
                "It does not modify profile mapper config.",
                "It does not modify source GIS files.",
                "Missing OSM tags remain data-quality flags.",
                self.review_wording,
            ],
        }
        write_json(plan_path, plan)
        write_json(patch_path, patch_preview)
        checklist_path.write_text(self.application_plan_markdown(plan), encoding="utf-8")
        write_json(proposal_dir / "latest_application_plan.json", plan)
        return {"ok": True, "application_plan": plan, "source_gis_modified": False}

    def list_application_plans(self, limit: int = 50) -> list[dict]:
        rows = []
        if not self.promotions_dir.exists():
            return rows
        for path in self.promotions_dir.glob("*/application_plans/profile_application_plan_*.json"):
            if path.name.endswith("_config_patch_preview.json"):
                continue
            payload = read_json(path)
            if payload.get("profile_application_plan_version") != PROFILE_APPLICATION_PLAN_VERSION:
                continue
            rows.append({
                "plan_id": payload.get("plan_id"),
                "proposal_id": payload.get("proposal_id"),
                "decision_id": payload.get("decision_id"),
                "profile_id": payload.get("profile_id"),
                "operation": payload.get("operation"),
                "plan_status": payload.get("plan_status"),
                "field_change_count": payload.get("field_change_count"),
                "created_at_utc": payload.get("created_at_utc"),
                "mutates_config": False,
                "source_gis_modified": False,
            })
        rows.sort(key=lambda row: str(row.get("created_at_utc") or ""), reverse=True)
        return rows[: max(1, min(int(limit or 50), 500))]

    def application_plan_detail(self, plan_id: str) -> dict:
        clean = safe_token(plan_id, "")
        for path in self.promotions_dir.glob(f"*/application_plans/{clean}.json"):
            payload = read_json(path)
            if payload.get("profile_application_plan_version") == PROFILE_APPLICATION_PLAN_VERSION:
                return payload
        return {"ok": False, "error": "profile_application_plan_not_found", "plan_id": plan_id, "source_gis_modified": False}

    def latest_application_plan(self, proposal_id: str) -> dict:
        proposal_dir = self.promotions_dir / safe_token(proposal_id, "")
        latest = read_json(proposal_dir / "latest_application_plan.json")
        if latest.get("profile_application_plan_version") == PROFILE_APPLICATION_PLAN_VERSION:
            return latest
        plans = []
        for path in (proposal_dir / "application_plans").glob("profile_application_plan_*.json") if (proposal_dir / "application_plans").exists() else []:
            if path.name.endswith("_config_patch_preview.json"):
                continue
            payload = read_json(path)
            if payload.get("profile_application_plan_version") == PROFILE_APPLICATION_PLAN_VERSION:
                plans.append(payload)
        if not plans:
            return {"ok": False, "error": "profile_application_plan_not_found", "proposal_id": proposal_id, "source_gis_modified": False}
        return sorted(plans, key=lambda row: str(row.get("created_at_utc") or ""), reverse=True)[0]

    def decision_by_id(self, decision_id: str) -> dict:
        clean = safe_token(decision_id, "")
        for path in self.promotions_dir.glob(f"*/acceptance_decisions/{clean}.json"):
            payload = read_json(path)
            if payload.get("profile_acceptance_version") == PROFILE_ACCEPTANCE_VERSION:
                return payload
        return {"ok": False, "error": "profile_acceptance_decision_not_found", "decision_id": decision_id, "decision_status": "missing", "source_gis_modified": False}

    @staticmethod
    def contract_field_changes(current_contract: dict, proposed_contract: dict) -> list[dict]:
        fields = sorted(set(current_contract) | set(proposed_contract))
        changes = []
        for field in fields:
            current_value = current_contract.get(field)
            proposed_value = proposed_contract.get(field)
            if current_value == proposed_value:
                continue
            changes.append({
                "field": field,
                "current_value": current_value,
                "proposed_value": proposed_value,
            })
        return changes

    def candidate_from_manifest(self, workspace_dir: Path, manifest: dict) -> dict:
        workspace_id = str(manifest.get("workspace_id") or workspace_dir.name)
        profile_id = str(manifest.get("profile_id") or "")
        summary = read_json(workspace_dir / "reports" / "authored_profile_summary.json")
        counts = summary.get("counts", {}) if isinstance(summary, dict) else {}
        result_rows = int(counts.get("result_rows") or self.count_csv_rows(workspace_dir / "tables" / "authored_profile_results.csv"))
        source_evidence_rows = int(counts.get("source_evidence_rows") or self.count_csv_rows(workspace_dir / "tables" / "authored_profile_source_evidence.csv"))
        missing_required_tags = int(counts.get("missing_required_tags") or 0)
        required_tags = int(counts.get("required_tags") or 0)
        draft = self.draft_for_manifest(manifest)
        existing_contract = self.existing_contract(profile_id)
        gates = [
            {"gate": "result_rows_present", "passed": result_rows > 0, "evidence": f"{result_rows} authored result rows"},
            {"gate": "source_evidence_present", "passed": source_evidence_rows > 0, "evidence": f"{source_evidence_rows} source evidence rows"},
            {"gate": "required_tags_satisfied", "passed": missing_required_tags == 0, "evidence": f"{missing_required_tags} missing required tags from {required_tags} required tags"},
            {"gate": "draft_contract_available", "passed": bool(draft.get("contract")), "evidence": str(manifest.get("draft_id") or "")},
            {"gate": "source_gis_read_only", "passed": manifest.get("source_gis_modified") is False and summary.get("source_gis_modified") is False, "evidence": "source_gis_modified=false in manifest and summary"},
            {"gate": "approved_wording_present", "passed": self.review_wording in json.dumps(summary, ensure_ascii=False) or self.review_wording in json.dumps(manifest, ensure_ascii=False), "evidence": "approved review wording found in authored evidence"},
        ]
        blockers = [gate["gate"] for gate in gates if not gate["passed"]]
        warnings = []
        if existing_contract:
            warnings.append("profile_id_already_exists_in_profile_mapper_config")
        if summary.get("limitations"):
            warnings.append("limitations_require_manual_review")
        return {
            "ok": True,
            "profile_promotion_version": PROFILE_PROMOTION_VERSION,
            "workspace_id": workspace_id,
            "profile_id": profile_id,
            "template_id": manifest.get("template_id"),
            "draft_id": manifest.get("draft_id"),
            "dataset_id": manifest.get("dataset_id"),
            "created_at_utc": manifest.get("created_at_utc"),
            "result_rows": result_rows,
            "source_evidence_rows": source_evidence_rows,
            "required_tags": required_tags,
            "missing_required_tags": missing_required_tags,
            "existing_mapper_contract_status": existing_contract.get("status", "") if existing_contract else "",
            "already_in_mapper_config": bool(existing_contract),
            "gates": gates,
            "blockers": blockers,
            "warnings": warnings,
            "recommendation": "ready_for_promotion_proposal" if not blockers else "needs_more_evidence",
            "next_step": "Create a reviewable promotion proposal." if not blockers else "Fix blockers or rerun authored audit before proposing promotion.",
            "source_gis_modified": False,
        }

    def draft_for_candidate(self, candidate: dict) -> dict:
        manifest = read_json(self.workspaces_dir / safe_token(candidate.get("workspace_id"), "") / "manifest.json")
        return self.draft_for_manifest(manifest)

    def draft_for_manifest(self, manifest: dict) -> dict:
        draft_id = str(manifest.get("draft_id") or "")
        if not draft_id:
            return {}
        try:
            draft = self.template_authoring.detail(draft_id)
            return draft if isinstance(draft, dict) else {}
        except Exception:
            draft_path = Path(str(manifest.get("source_files", {}).get("template_draft") or ""))
            return read_json(draft_path)

    def mapper_config(self) -> dict:
        return read_json(self.mapper_config_path)

    def existing_contract(self, profile_id: str) -> dict:
        for contract in self.mapper_config().get("contracts", []):
            if str(contract.get("profile_id") or "") == str(profile_id or ""):
                return dict(contract)
        return {}

    def promoted_contract(self, candidate: dict, draft: dict, existing_contract: dict) -> dict:
        draft_contract = dict(draft.get("contract") or {})
        contract = dict(existing_contract or draft_contract)
        if draft_contract:
            contract.update({key: value for key, value in draft_contract.items() if value not in (None, "", [], {})})
        contract["profile_id"] = str(candidate.get("profile_id") or contract.get("profile_id") or "")
        contract["status"] = "profile_ready"
        contract["runner_status"] = "authored_audit_available"
        contract["mapper_type"] = "authored_profile_evidence_contract"
        contract["result_contract"] = "profile_dashboard_contract_v001"
        contract["implementation_entrypoint"] = "AuthoredProfileRunner.ensure_workspace"
        contract["claim_boundaries"] = unique(list(contract.get("claim_boundaries") or []) + [
            "authored tag and layer evidence audit",
            "manual review required before dedicated scoring",
            self.review_wording,
        ])
        contract["missing_data_policy"] = "Missing OSM tags are data-quality flags, not proof that infrastructure is absent."
        contract["promotion_evidence"] = {
            "workspace_id": candidate.get("workspace_id"),
            "draft_id": candidate.get("draft_id"),
            "result_rows": candidate.get("result_rows"),
            "source_evidence_rows": candidate.get("source_evidence_rows"),
            "required_tags": candidate.get("required_tags"),
            "missing_required_tags": candidate.get("missing_required_tags"),
            "proposal_only": True,
            "source_gis_modified": False,
        }
        return contract

    @staticmethod
    def count_csv_rows(path: Path) -> int:
        rows = read_csv_rows(path)
        return len(rows)

    def proposal_markdown(self, proposal: dict) -> str:
        candidate = proposal.get("candidate", {})
        return "\n".join([
            "# Profile Promotion Proposal",
            "",
            f"Proposal id: `{proposal.get('proposal_id')}`",
            f"Profile id: `{proposal.get('profile_id')}`",
            f"Workspace id: `{proposal.get('workspace_id')}`",
            f"Status: `{proposal.get('status')}`",
            "",
            "## Evidence Gates",
            "",
            *[
                f"- {gate.get('gate')}: {'passed' if gate.get('passed') else 'blocked'} - {gate.get('evidence')}"
                for gate in candidate.get("gates", [])
            ],
            "",
            "## Boundary",
            "",
            "- This proposal does not modify profile mapper config.",
            "- Source GIS files remain read-only.",
            "- Missing OSM tags remain data-quality flags.",
            f"- {self.review_wording}",
            "",
            "## Manual Review Checklist",
            "",
            "1. Review the proposed profile contract fields.",
            "2. Confirm that the authored audit is enough for a reusable profile contract.",
            "3. Decide whether a dedicated runner and scoring profile are needed.",
            "4. Record an approve/reject decision with the Proposal Acceptance Workflow.",
            "5. Add tests before applying any config change in a separate explicit task.",
        ])

    def decision_markdown(self, decision: dict) -> str:
        return "\n".join([
            "# Profile Promotion Decision",
            "",
            f"Decision id: `{decision.get('decision_id')}`",
            f"Proposal id: `{decision.get('proposal_id')}`",
            f"Profile id: `{decision.get('profile_id')}`",
            f"Decision: `{decision.get('decision_status')}`",
            f"Reviewer: `{decision.get('reviewer')}`",
            "",
            "## Notes",
            "",
            str(decision.get("notes") or ""),
            "",
            "## Boundary",
            "",
            "- This decision does not modify profile mapper config.",
            "- Source GIS files remain read-only.",
            "- A separate explicit implementation task is required before any config mutation.",
            f"- {self.review_wording}",
        ])

    def contract_regression_preview_markdown(self, preview: dict) -> str:
        return "\n".join([
            "# Profile Contract Regression Preview",
            "",
            f"Preview id: `{preview.get('preview_id')}`",
            f"Apply proposal id: `{preview.get('apply_id')}`",
            f"Profile id: `{preview.get('profile_id')}`",
            f"Regression status: `{preview.get('regression_status')}`",
            f"Failed checks: `{preview.get('failed_check_count')}`",
            "",
            "## Checks",
            "",
            *[
                f"- {check.get('check')}: {'passed' if check.get('passed') else 'blocked'} - {check.get('evidence')}"
                for check in preview.get("checks", [])
            ],
            "",
            "## Warnings",
            "",
            *[f"- {warning}" for warning in preview.get("warnings", [])],
            "",
            "## Boundary",
            "",
            "- This regression preview does not modify profile mapper config.",
            "- Source GIS files remain read-only.",
            "- Any real config change requires a separate explicit config-change task.",
            f"- {self.review_wording}",
        ])

    def config_apply_proposal_markdown(self, proposal: dict) -> str:
        return "\n".join([
            "# Guarded Config Apply Proposal",
            "",
            f"Apply proposal id: `{proposal.get('apply_id')}`",
            f"Proposal id: `{proposal.get('proposal_id')}`",
            f"Application plan id: `{proposal.get('application_plan_id')}`",
            f"Contract diff id: `{proposal.get('contract_diff_id')}`",
            f"Profile id: `{proposal.get('profile_id')}`",
            f"Operation: `{proposal.get('operation')}`",
            f"Apply status: `{proposal.get('apply_status')}`",
            "",
            "## Hashes",
            "",
            f"- Current config SHA-256: `{proposal.get('current_config_sha256')}`",
            f"- Proposed config SHA-256: `{proposal.get('proposed_config_sha256')}`",
            "",
            "## Gates",
            "",
            *[
                f"- {gate.get('gate')}: {'passed' if gate.get('passed') else 'blocked'} - {gate.get('evidence')}"
                for gate in proposal.get("gates", [])
            ],
            "",
            "## Approval Requirements",
            "",
            *[f"{index + 1}. {step}" for index, step in enumerate(proposal.get("approval_requirements", []))],
            "",
            "## Boundary",
            "",
            "- This apply proposal does not modify profile mapper config.",
            "- Source GIS files remain read-only.",
            "- Any real config change requires a separate explicit config-change task.",
            f"- {self.review_wording}",
        ])

    def contract_diff_markdown(self, diff: dict) -> str:
        summary = diff.get("summary", {})
        groups = summary.get("field_groups", {})
        changed = groups.get("changed_fields", [])
        added = groups.get("added_fields", [])
        removed = groups.get("removed_fields", [])
        priority = summary.get("review_priority_fields", [])
        lines = [
            "# Profile Contract Diff Review",
            "",
            f"Diff id: `{diff.get('diff_id')}`",
            f"Proposal id: `{diff.get('proposal_id')}`",
            f"Profile id: `{diff.get('profile_id')}`",
            f"Operation: `{diff.get('operation')}`",
            "",
            "## Summary",
            "",
            f"- Added fields: {summary.get('added_count', 0)}",
            f"- Removed fields: {summary.get('removed_count', 0)}",
            f"- Changed fields: {summary.get('changed_count', 0)}",
            f"- Unchanged fields: {summary.get('unchanged_count', 0)}",
            f"- Review priority fields: {', '.join(priority) if priority else 'none'}",
            "",
            "## Changed Fields",
            "",
        ]
        lines.extend([f"- {item.get('field')}: {item.get('current_kind')} -> {item.get('proposed_kind')}" for item in changed[:20]] or ["- none"])
        lines.extend(["", "## Added Fields", ""])
        lines.extend([f"- {item.get('field')}: {item.get('proposed_kind')}" for item in added[:20]] or ["- none"])
        lines.extend(["", "## Removed Fields", ""])
        lines.extend([f"- {item.get('field')}: {item.get('current_kind')}" for item in removed[:20]] or ["- none"])
        lines.extend([
            "",
            "## Boundary",
            "",
            "- This diff review does not modify profile mapper config.",
            "- Source GIS files remain read-only.",
            "- Use this artifact before any separate explicit config-change task.",
            f"- {self.review_wording}",
        ])
        return "\n".join(lines)

    def application_plan_markdown(self, plan: dict) -> str:
        return "\n".join([
            "# Accepted Contract Application Plan",
            "",
            f"Plan id: `{plan.get('plan_id')}`",
            f"Proposal id: `{plan.get('proposal_id')}`",
            f"Decision id: `{plan.get('decision_id')}`",
            f"Profile id: `{plan.get('profile_id')}`",
            f"Operation: `{plan.get('operation')}`",
            "",
            "## Gates",
            "",
            *[
                f"- {gate.get('gate')}: {'passed' if gate.get('passed') else 'blocked'} - {gate.get('evidence')}"
                for gate in plan.get("gates", [])
            ],
            "",
            "## Manual Steps",
            "",
            *[f"{index + 1}. {step}" for index, step in enumerate(plan.get("manual_steps", []))],
            "",
            "## Boundary",
            "",
            "- This application plan does not modify profile mapper config.",
            "- Source GIS files remain read-only.",
            "- Apply any config changes only in a separate explicit implementation task.",
            f"- {self.review_wording}",
        ])
