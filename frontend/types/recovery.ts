export type RecoveryCase = {
  id: number;
  payment_id: number;
  transaction_id: string;
  amount: number;
  status: string;
  recoverability: string;
  recommended_action: string | null;
  approved_action: string | null;
  amount_at_risk: number;
  amount_recovered: number;
};

export type Payment = {
  payment_id: number;
  transaction_id: string;
  amount: number;
  payment_status: string;
  failure_reason: string;
  recovery_case: RecoveryCase | null;
};

export type ExecutionResult = {
  payment_id: number;
  transaction_id: string;
  recovery_case_id: number;
  ai_action: string;
  approved_action: string | null;
  confidence: number;
  allowed: boolean;
  status: string;
  amount_recovered: number;
  reason: string;
};

export type BatchRecoveryRequest = {
  batch_size: number;
  delay_seconds: number;
  max_revenue_at_risk: number;
  max_consecutive_errors: number;
};

export type BatchRecoveryResult = {
  cases_found: number;
  cases_processed: number;
  successful_recoveries: number;
  failed_recoveries: number;
  policy_blocked: number;
  deferred: number;
  not_selected: number;
  revenue_at_risk: number;
  revenue_recovered: number;
  recovery_rate: number;
  revenue_recovery_rate: number;
  stop_reason: string;
};