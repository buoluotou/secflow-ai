/** SecFlow AI API type definitions — mirror backend schemas. */

export interface User {
  id: string
  username: string
  email?: string
  full_name?: string
  role: string
  organization_id?: string
}

export interface Project {
  id: string
  name: string
  description?: string
  status: string
  organization_id?: string
  created_at?: string
}

export interface Asset {
  id: string
  project_id: string
  name: string
  hostname?: string
  ip?: string
  domain?: string
  asset_type: string
  environment: string
  criticality: number
  owner?: string
  tags: string[]
  status: string
  created_at?: string
}

export interface SecurityEvent {
  id: string
  source: string
  event_type?: string
  timestamp?: string
  project_id?: string
  asset_id?: string
  user?: string
  src_ip?: string
  src_port?: number
  dst_ip?: string
  dst_port?: number
  severity: string
  confidence: number
  indicators: string[]
  techniques: string[]
  external_id?: string
}

export interface Finding {
  id: string
  project_id?: string
  asset_id?: string
  source: string
  template_id?: string
  title: string
  description?: string
  severity: string
  cvss?: number
  cwe?: string
  evidence?: string
  remediation?: string
  status: string
  first_seen?: string
  last_seen?: string
}

export interface IOC {
  id: string
  type: string
  value: string
  source: string
  confidence: number
  tags: string[]
  first_seen?: string
  last_seen?: string
}

export interface Incident {
  id: string
  project_id: string
  title: string
  description?: string
  status: string
  severity: string
  confidence: number
  attack_stage?: string
  detected_at?: string
  closed_at?: string
  assigned_to?: string
  related_event_ids: string[]
  related_finding_ids: string[]
  related_ioc_ids: string[]
  evidence_ids: string[]
  correlation_reason?: string
  ai_decision?: string
  human_decision?: string
  reviewer?: string
  review_comment?: string
  reviewed_at?: string
  created_at?: string
}

export interface ScanJob {
  id: string
  project_id?: string
  scan_type: string
  targets: string[]
  options: Record<string, unknown>
  status: string
  started_at?: string
  finished_at?: string
  result_summary: Record<string, unknown>
  error?: string
  created_by?: string
  created_at?: string
}

/** Typed view of AI agent outputs (triage/threat/vuln/report). */
export interface AgentOutput {
  classification?: string
  severity?: string
  confidence?: number
  attack_stage?: string
  mitre_techniques?: string[]
  evidence_ids?: string[]
  reasoning_summary?: string
  recommendations?: string[]
  malicious?: boolean
  tags?: string[]
  related_entities?: string[]
  authenticity?: string
  remediation_priority?: string
  impact_scope?: string[]
  exploit_risk?: number
  summary?: string
  timeline_narrative?: string
  [key: string]: unknown
}

export interface AIAnalysis {
  id: string
  incident_id?: string
  agent_type: string
  input: Record<string, unknown>
  output: AgentOutput
  status: string
  model?: string
  prompt_version?: string
  error?: string
  created_at?: string
}

export interface RiskAssessment {
  id: string
  incident_id?: string
  finding_id?: string
  risk_score: number
  risk_level: string
  factors: Record<string, unknown>
  created_at?: string
}

export interface Report {
  id: string
  project_id?: string
  incident_id?: string
  report_type: string
  title: string
  status: string
  content_pdf_path?: string
  created_by?: string
  created_at?: string
}

export interface AuditLog {
  id: string
  user_id?: string
  username?: string
  action: string
  resource_type?: string
  resource_id?: string
  detail: Record<string, unknown>
  ip?: string
  timestamp?: string
}

export interface HealthStatus {
  ok: boolean
  status_code?: number
  error?: string
  provider?: string
  detail?: string
}
