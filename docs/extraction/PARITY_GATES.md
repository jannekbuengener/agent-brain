# Parity-Gates — welche Claire-Tests schützen welchen Slice?

**Zweck:** Bestehende Claire-Verträge werden nicht nach Gefühl neu implementiert. Die vorhandene Testfläche wird als Charakterisierungs-, Regression- und späteres Parity-Netz wiederverwendet.

## 1. Grundregel

Für einen späteren Slice gilt:

1. relevante Claire-Tests zuerst als **bestehendes Verhalten** verstehen,
2. portable Agent-Brain-Tests für den generischen Contract anlegen,
3. Claire-spezifische Tests für Adapter/Policy in Claire behalten,
4. beim Cutover alte und neue Pfade mit denselben relevanten Fixtures/Erwartungen vergleichen,
5. Tests des deferred Memory-Write-Pfads **nicht** still in den read-only Core ziehen.

## 2. SurrealDB-Testfläche

Beim Audit wurden **87 Tests** unter `tests/unit/surrealdb/` primär einem Gate zugeordnet.

### Slice 0 — Extraction Canon / Ownership

- `test_context_data_model_ownership_matrix.py`

### Slice 2 — Portable Foundation

- `test_sensitive_output.py`

### Slice 3 — Shared Source / Index / Evidence Contracts

- `test_context_graph_contract.py`
- `test_db_record_evidence_contract.py`
- `test_wave14_context_record_schemas.py`

### Slice 4 — Context Package / Briefing

- `test_context_package_v2.py`
- `test_context_required_reads.py`
- `test_context_self_explanation.py`
- `test_context_validation_plan.py`

`test_context_required_reads.py` schützt dabei zwei Dinge getrennt: den generischen Resolver-Contract und die später in Claire verbleibende konkrete Read-Policy.

### Slice 5 — Repository Ingestion / Connectors

- `test_context_indexer.py`
- `test_context_symbol_extraction.py`
- `test_ledger_importer.py`

### Slice 6 — Knowledge Build / Seed / Import

- `test_context_import_apply.py`
- `test_context_import_audit.py`
- `test_context_import_config.py`
- `test_context_import_jsonl_validation.py`
- `test_context_import_plan.py`
- `test_context_import_reconcile.py`
- `test_context_import_tombstones.py`
- `test_context_importer_sensitive_output.py`
- `test_context_importer.py`
- `test_knowledge_refresh_report.py`
- `test_local_runtime.py`
- `test_surrealdb_local_apply_adapter.py`

### Slice 7 — Hybrid Retrieval / Knowledge Reasoning

- `test_context_fulltext_bm25_contract.py`
- `test_context_impact_radar.py`
- `test_context_stop_resolver.py`
- `test_graph_vector_proof_cli.py`
- `test_graph_vector_proof_red_3486.py`
- `test_hybrid_retrieval_followup_red_3487.py`
- `test_hybrid_retrieval_ranking.py`
- `test_hybrid_retrieval_regression.py`
- `test_impact_radar_contract.py`

Die `*_red_3486/3487`-Tests bleiben zusätzlich Kandidaten für den späteren Slice-14-Parity-Lauf.

### Slice 8 — Evidence / Decisions / Trust / Drift

- `test_agent_os_readiness.py`
- `test_claim_evidence_at_rest.py`
- `test_claim_evidence_proof_runtime_contract.py`
- `test_context_drift_stale_contradiction_contract.py`
- `test_contradiction_cli.py`
- `test_contradiction_scan.py`
- `test_decision_history_query_v1.py`
- `test_decision_replay_builder_v1.py`
- `test_decision_replay_builder_v2.py`
- `test_drift_report.py`
- `test_drift_stale_contradiction_regression.py`
- `test_evidence_resolver_regression.py`
- `test_negative_controls_regression.py`
- `test_quality_scoring.py`
- `test_scope_drift_blocking.py`
- `test_scope_drift_cli.py`
- `test_scope_drift_firewall.py`
- `test_stale_context_cli.py`
- `test_stale_fixtures.py`
- `test_stale_knowledge_scan.py`
- `test_stale_refresh_plan.py`
- `test_trust_threshold_contract.py`

### Slice 9 — SurrealDB Read Runtime

- `test_context_query_adapter.py`
- `test_context_query_builders.py`
- `test_context_query_classifier.py`
- `test_context_query_cli.py`
- `test_context_query_config.py`
- `test_context_query_search.py`
- `test_context_readonly_query_harness.py`
- `test_context_smoke_db_contracts.py`
- `test_local_query_config_init.py`

### Slice 10 — Memory Read Side / Rediscovery

- `test_agent_memory_contract.py`
- `test_memory_contract.py`
- `test_memory_cross_session_rediscovery_contract.py`
- `test_memory_db_proof_runtime_contract.py`
- `test_memory_db_read_proof.py`
- `test_memory_db_stale_scan.py`
- `test_memory_freshness.py`
- `test_memory_read_characterization.py`

### Slice 12 — CLI / Protocol Surface

- `test_context_invocation_evidence_json.py`
- `test_context_live_invocation_harness.py`
- `test_decision_mcp_tools_v1.py`
- `test_wave14_services_v1.py`

`test_context_live_invocation_harness.py` wird später zusätzlich als Slice-14-Parity-Evidence wiederverwendet.

### Slice 13 — Claire Adapter / Consumer Cutover

- `test_context_certify.py`
- `test_context_onboarding_doctor.py`
- `test_control_room_signal_layer.py`
- `test_control_room_view_builder.py`

Diese Tests gehören primär zur Claire-Consumer-/Presentation-Seite und werden nicht als generischer Brain-Core-Contract missverstanden.

### DEFER — Memory Write / Audit Trail

Diese Tests bleiben während des Extraction-Epics Claire-seitige Schutz- und Referenztests. Sie autorisieren keine Übernahme des Write-Pfads:

- `test_audit_observation_from_gate.py`
- `test_audit_trail_t4_proof_contract.py`
- `test_memory_db_write_smoke.py`
- `test_memory_write_gate.py`
- `test_memory_write_path_productive.py`
- `test_memory_write_path_t4.py`
- `test_memory_write_path_v1.py`

## 3. MCP-/Protocol-Testfläche

Zusätzlich wurden **31 Tests** unter `tests/unit/tools/mcp/` primär zugeordnet.

### Slice 4 — Context / Briefing

- `test_mcp_briefing_tool.py`
- `test_context_package_handler.py`
- `test_context_briefing_graph_followup.py`
- `test_mcp_briefing_enrichment.py`

### Slice 5 — Repository Registry / Connectors

- `test_cross_repo_root_inventory.py`

### Slice 7 — Retrieval

- `test_mcp_impact_tool.py`
- `test_context_briefing_vector_followup_red_3486.py`
- `test_context_briefing_hybrid_followup_red_3487.py`

### Slice 8 — Evidence / Trust / Drift

- `test_scope_drift_tools.py`
- `test_quality_scoring_tools.py`
- `test_mcp_stale_context_tool.py`
- `test_mcp_contradiction_tool.py`
- `test_mcp_briefing_evidence_claim_trust_red_3488.py`
- `test_agent_os_readiness_tools.py`
- `test_decision_replay_status_proof_red_3489.py`

### Slice 9 — SurrealDB Read / guarded adapter

- `test_wave14_smoke_helpers.py`
- `test_wave14_query_contracts.py`
- `test_mcp_wave14_surrealdb_mode.py`

### Slice 10 — Memory output

- `test_memory_output_contract.py`

### Slice 12 — Protocol / MCP Surface

- `test_show_handlers.py`
- `test_mcp_wave14_tools.py`
- `test_permission_guard.py`
- `test_mcp_server_stdio.py`
- `test_output_contracts.py`
- `test_context_bridge.py`
- `test_error_cases.py`

### Slice 13 — Claire Adapter / Presentation

- `test_context_readiness_root.py`
- `test_control_room_tools.py`

### Slice 14 — Claire Parity / E2E Sensory Proof

- `test_default_sensory_loop_red_3492.py`
- `test_end_to_end_sensory_proof_red_3494.py`

Diese beiden sind besonders wichtige End-to-End-Referenzen für den späteren Claire-Cutover.

### DEFER — Memory Write Intent MCP

- `test_memory_write_intent_tool.py`

## 4. Weitere explizite Gates

### MCP Access Boundary

Unter `tests/unit/mcp/`:

- `test_mcp_access_boundary_matrix.py`
- `test_mcp_access_boundary_safety.py`

**Primär:** Slice 12.  
**Sekundär:** Slice 14, um zu beweisen, dass der neue Protocol-Pfad keine Write-/Trading-Autorität eröffnet.

### Agent-Brain-Adoption Contract

- `tests/unit/agents/test_agent_brain_adoption_contract.py`

**Primär:** Slice 13/14. Der Test schützt die Claire-Adoption und die repo-first/fail-closed Haltung beim Consumer-Cutover.

### Tool Inventory

- `tests/unit/tools/test_context_tool_inventory.py`

**Primär:** Slice 12. Nach der Extraktion muss das Tool-Inventar neu zwischen Agent Brain und Claire-Adapter aufgeteilt werden, ohne Tools still verschwinden zu lassen.

## 5. Cross-Slice Parity-Pack für Slice 14

Slice 14 soll nicht die komplette Claire-Testwelt blind wiederholen. Sein fokussierter Parity-Pack muss mindestens enthalten:

1. Context Package / Briefing
2. Retrieval inkl. RED-Followups 3486/3487
3. Evidence/Claim/Trust RED 3488
4. Decision Replay RED 3489
5. Default Sensory Loop 3492
6. End-to-End Sensory Proof 3494
7. Agent-Brain-Adoption Contract
8. MCP Access Boundary Safety
9. Memory Read / Freshness / Rediscovery
10. Query Adapter Source-Label / forged-DB-claim negative controls
11. Claire Control-Room-/Readiness-Consumer-Smokes, soweit sie den neuen Brain-Pfad konsumieren

## 6. Test-Ownership-Regel

Ein bestehender Claire-Test wird nur dann tatsächlich **verschoben**, wenn sein Contract produktneutral ist. Ansonsten:

- generischer Contract-Test → Agent Brain,
- Claire Policy-/Adapter-Test → Claire,
- Cross-Repo-Parity-Test → dort, wo beide Seiten kontrolliert geprüft werden können,
- historischer Write-/Proof-Test → bleibt Claire oder späteres Write-Epic.

Damit bedeutet „Parity-Gate zugeordnet“ ausdrücklich **nicht** automatisch „Datei kopieren“.