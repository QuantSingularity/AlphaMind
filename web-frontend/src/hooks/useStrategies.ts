import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import apiService from "../services/api";
import type { Strategy } from "../types";

export const useStrategies = () => {
  return useQuery({
    queryKey: ["strategies"],
    queryFn: () => apiService.getStrategies(),
    staleTime: 30000, // 30 seconds
  });
};

export const useStrategy = (id: string) => {
  return useQuery({
    queryKey: ["strategy", id],
    queryFn: () => apiService.getStrategy(id),
    enabled: !!id,
  });
};

export const useCreateStrategy = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (strategy: Partial<Strategy>) =>
      apiService.createStrategy(strategy),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["strategies"] });
    },
  });
};

export const useUpdateStrategy = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      id,
      strategy,
    }: {
      id: string;
      strategy: Partial<Strategy>;
    }) => apiService.updateStrategy(id, strategy),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ["strategies"] });
      queryClient.invalidateQueries({ queryKey: ["strategy", variables.id] });
    },
  });
};

export const useDeleteStrategy = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => apiService.deleteStrategy(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["strategies"] });
    },
  });
};

export const useActivateStrategy = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => apiService.activateStrategy(id),
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: ["strategies"] });
      queryClient.invalidateQueries({ queryKey: ["strategy", id] });
    },
  });
};

export const useDeactivateStrategy = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => apiService.deactivateStrategy(id),
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: ["strategies"] });
      queryClient.invalidateQueries({ queryKey: ["strategy", id] });
    },
  });
};

export const useStrategyEquityCurve = (id: string) => {
  return useQuery({
    queryKey: ["strategy-equity-curve", id],
    queryFn: () => apiService.getStrategyEquityCurve(id),
    enabled: !!id,
    staleTime: 60_000,
  });
};
