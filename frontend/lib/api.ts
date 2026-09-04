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
  const response = await fetch(
    `${API_URL}${path}`,
    options
  );

  if (!response.ok) {
    let message = "API request failed.";

    try {
      const body = await response.json();

      if (typeof body?.detail === "string") {
        message = body.detail;
      }
    } catch {
      // Keep the generic message when the response
      // does not contain JSON.
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