import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import apiService from "../services/api";
import type { BacktestResult } from "../types";

export const useRunBacktest = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      strategyId,
      startDate,
      endDate,
      initialCapital,
    }: {
      strategyId: string;
      startDate: string;
      endDate: string;
      initialCapital: number;
    }) =>
      apiService.runBacktest(strategyId, startDate, endDate, initialCapital),
    onSuccess: (result: BacktestResult) => {
      queryClient.invalidateQueries({
        queryKey: ["backtest-results", result.strategyId],
      });
    },
  });
};

export const useBacktestResults = (strategyId: string) => {
  return useQuery({
    queryKey: ["backtest-results", strategyId],
    queryFn: () => apiService.getBacktestResults(strategyId),
    enabled: !!strategyId,
  });
};
