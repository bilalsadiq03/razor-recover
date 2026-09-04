import type {
  ExecutionResult,
  Payment,
  RecoveryCase,
} from "@/types/recovery";

const API_URL =
  process.env.NEXT_PUBLIC_API_URL ??
  "http://127.0.0.1:8000";

async function request<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  let response: Response;

  try {
    response = await fetch(
      `${API_URL}${path}`,
      {
        ...options,
        headers: {
          "Content-Type": "application/json",
          ...options?.headers,
        },
      }
    );
  } catch {
    throw new Error(
      "Unable to connect to the RazorRecover API."
    );
  }

  if (!response.ok) {
    let message = "API request failed.";

    try {
      const body: unknown = await response.json();

      if (
        typeof body === "object" &&
        body !== null &&
        "detail" in body &&
        typeof body.detail === "string"
      ) {
        message = body.detail;
      }
    } catch {
      // Use the generic message when the response
      // does not contain a JSON error body.
    }

    throw new Error(message);
  }

  return response.json() as Promise<T>;
}

export async function getRecoveryCases(
  limit = 50
): Promise<RecoveryCase[]> {
  return request<RecoveryCase[]>(
    `/api/recovery?limit=${limit}`
  );
}

export async function getPayment(
  paymentId: number
): Promise<Payment> {
  return request<Payment>(
    `/api/recovery/${paymentId}`
  );
}

export async function executeRecovery(
  paymentId: number
): Promise<ExecutionResult> {
  return request<ExecutionResult>(
    `/api/recovery/${paymentId}/execute`,
    {
      method: "POST",
    }
  );
}

export type BatchRecoveryRequest = {
  batch_size: number;
  delay_seconds: number;
  max_revenue_at_risk: number;
  max_consecutive_errors: number;
};

export type BatchRecoveryResponse = {
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

export async function executeBatchRecovery(
  payload: BatchRecoveryRequest
): Promise<BatchRecoveryResponse> {
  return request<BatchRecoveryResponse>(
    "/api/recovery/batch",
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    }
  );
}