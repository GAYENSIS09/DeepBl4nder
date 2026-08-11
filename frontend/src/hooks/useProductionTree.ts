'use client';

import useSWR from 'swr';

import { fetchProductionTree, sortProductions, type ProductionTree } from '@/lib/productions';

export function useProductionTree(refreshInterval = 4000) {
  const { data, error, isLoading, mutate } = useSWR<ProductionTree>('production-tree', fetchProductionTree, {
    refreshInterval,
  });

  const productions = data ? sortProductions(data.productions) : [];

  return {
    tree: data,
    productions,
    error,
    isLoading,
    mutate,
  };
}
