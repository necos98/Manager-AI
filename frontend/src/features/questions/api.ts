import { apiGet, apiPost } from "@/shared/api/client";
import type { Question, QuestionAnswer } from "@/shared/types";

export function fetchQuestions(projectId?: string, issueId?: string, status?: string): Promise<Question[]> {
  const params = new URLSearchParams();
  if (projectId) params.set("project_id", projectId);
  if (issueId) params.set("issue_id", issueId);
  if (status) params.set("status", status);
  return apiGet<Question[]>(`/questions?${params.toString()}`);
}

export function fetchPendingQuestions(projectId?: string, issueId?: string): Promise<Question[]> {
  const params = new URLSearchParams();
  if (projectId) params.set("project_id", projectId);
  if (issueId) params.set("issue_id", issueId);
  return apiGet<Question[]>(`/questions/pending?${params.toString()}`);
}

export function fetchPendingCount(): Promise<{ count: number }> {
  return apiGet<{ count: number }>("/questions/count");
}

export function answerQuestion(questionId: string, data: QuestionAnswer): Promise<Question> {
  return apiPost<Question>(`/questions/${questionId}/answer`, data);
}
