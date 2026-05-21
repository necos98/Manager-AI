import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as api from "./api";
import type { QuestionAnswer } from "@/shared/types";

export const questionKeys = {
  all: ["questions"] as const,
  pending: ["questions", "pending"] as const,
  count: ["questions", "count"] as const,
};

export function useQuestions(projectId?: string, issueId?: string) {
  return useQuery({
    queryKey: [...questionKeys.all, projectId, issueId],
    queryFn: () => api.fetchQuestions(projectId, issueId),
  });
}

export function usePendingQuestions(projectId?: string, issueId?: string) {
  return useQuery({
    queryKey: [...questionKeys.pending, projectId, issueId],
    queryFn: () => api.fetchPendingQuestions(projectId, issueId),
    refetchInterval: 30_000,
  });
}

export function usePendingCount() {
  return useQuery({
    queryKey: questionKeys.count,
    queryFn: api.fetchPendingCount,
    refetchInterval: 10_000,
  });
}

export function useAnswerQuestion() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ questionId, data }: { questionId: string; data: QuestionAnswer }) =>
      api.answerQuestion(questionId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: questionKeys.all });
      queryClient.invalidateQueries({ queryKey: questionKeys.pending });
      queryClient.invalidateQueries({ queryKey: questionKeys.count });
    },
  });
}
