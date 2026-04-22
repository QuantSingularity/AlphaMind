import { useQuery } from "@tanstack/react-query";
import apiService from "../services/api";

export const usePortfolioPerformance = (timeframe = "1M") => {
  return useQuery({
    queryKey: ["portfolio-performance", timeframe],
    queryFn: () => apiService.getPortfolioPerformance(timeframe),
    staleTime: 30_000,
    refetchInterval: 60_000,
  });
};

export const useRiskMetrics = (portfolioId?: string) => {
  return useQuery({
    queryKey: ["risk-metrics", portfolioId],
    queryFn: () => apiService.getRiskMetrics(portfolioId),
    staleTime: 30_000,
  });
};

export const useStressScenarios = () => {
  return useQuery({
    queryKey: ["stress-scenarios"],
    queryFn: () => apiService.getStressScenarios(),
    staleTime: 300_000, // 5 min — stress data rarely changes
  });
};

export const useCorrelationMatrix = () => {
  return useQuery({
    queryKey: ["correlation-matrix"],
    queryFn: () => apiService.getCorrelationMatrix(),
    staleTime: 300_000,
  });
};

export const useRiskRadar = () => {
  return useQuery({
    queryKey: ["risk-radar"],
    queryFn: () => apiService.getRiskRadar(),
    staleTime: 60_000,
  });
};
