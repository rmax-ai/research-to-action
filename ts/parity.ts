import { z } from "zod";

const v = z.literal(1);
const id = z.string().min(1);
const nullableId = id.nullable();

export const VersionEnvelopeSchema = z.object({
  schema_version: v,
  payload_type: z.string().min(1),
  payload: z.record(z.unknown()),
}).strict();

export const ClaimTypeSchema = z.enum(["FACT", "DERIVED", "INFERRED", "HUMAN_DECISION"]);
export type ClaimType = z.infer<typeof ClaimTypeSchema>;

const ClinicalCriterionSchema = z.object({
  criterion_id: id, concept: z.string(), operator: z.string(),
  value: z.union([z.string(), z.number(), z.boolean(), z.null()]),
  values: z.array(z.string()), description: z.string().nullable(),
  timing_relation: z.string().nullable(), required: z.boolean(),
}).strict();
const AssetRequirementSchema = z.object({
  asset_id: id, asset_type: z.string(), modality: z.string().nullable(),
  required: z.boolean(), timing_relation: z.string().nullable(),
  quantity: z.number().int().positive().nullable(), acceptable_substitutes: z.array(z.string()),
}).strict();

export const ResearchRequestSchema = z.object({
  schema_version: v, request_id: id, revision: z.number().int().positive(),
  parent_request_id: nullableId, original_intent: z.string(),
  clinical_criteria: z.array(ClinicalCriterionSchema),
  asset_requirements: z.array(AssetRequirementSchema),
  purpose_of_use: z.record(z.unknown()), requested_quantity: z.number().int().positive(),
  minimum_follow_up_months: z.number().int().nonnegative().nullable(),
  optimization_preference: z.string().nullable(), ontology_mappings: z.array(z.record(z.unknown())),
  unresolved_ambiguities: z.array(z.string()),
}).strict();
export type ResearchRequest = z.infer<typeof ResearchRequestSchema>;

export const ExecutionPlanSchema = z.object({
  schema_version: v, plan_id: id, request_id: id, request_revision: z.number().int().positive(),
  steps: z.array(z.string()), tool_names: z.array(z.string()), assumptions: z.array(z.string()),
  workflow_version: z.string(), config_version: z.string(), ontology_version: z.string(),
  policy_version: z.string(), plan_hash: z.string().nullable(),
}).strict();
export type ExecutionPlan = z.infer<typeof ExecutionPlanSchema>;

export const EvidenceRefSchema = z.object({
  schema_version: v, evidence_id: nullableId, source: z.string(), source_version: z.string(),
  source_hash: z.string(), locator: z.string().nullable(), record_id: z.string().nullable(),
  parent_evidence_id: nullableId, drill_down_refs: z.array(z.string()),
  transformations: z.array(z.string()),
}).strict();
export type EvidenceRef = z.infer<typeof EvidenceRefSchema>;

export const ClaimSchema = z.object({
  schema_version: v, claim_id: id, claim_type: ClaimTypeSchema, subject: z.string(),
  predicate: z.string(), value: z.unknown(), evidence_refs: z.array(EvidenceRefSchema),
  confidence: z.number().min(0).max(1).nullable(), explanation: z.string().nullable(),
}).strict();
export type Claim = z.infer<typeof ClaimSchema>;

export const ToolEventSchema = z.object({
  schema_version: v, event_id: nullableId, run_id: id, sequence: z.number().int().positive(),
  tool_name: z.string(), idempotency_key: id,
  status: z.enum(["STARTED", "SUCCEEDED", "FAILED", "SKIPPED"]),
  input_digest: id, output_digest: nullableId, attempt: z.number().int().positive(),
  error_code: z.string().nullable(),
}).strict();
export type ToolEvent = z.infer<typeof ToolEventSchema>;

export const ParityObjectSchema = z.union([
  ResearchRequestSchema, ExecutionPlanSchema, EvidenceRefSchema, ClaimSchema, ToolEventSchema,
]);
