'use client';

import useSWR from 'swr';
import { useState, useEffect } from 'react';
import { StatusPanel } from '@/components/StatusPanel';
import { PipelineForm } from '@/components/PipelineForm';
import { EventStream } from '@/components/EventStream';
import { BudgetPanel } from '@/components/BudgetPanel';

const fetcher = (url: string) => fetch(url).then((r) => r.json());

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function Home() {
  const { data: status, error: statusError } = useSWR(`${API_URL}/status`, fetcher, { refreshInterval: 30000 });
  const { data: budget } = useSWR(`${API_URL}/budget`, fetcher, { refreshInterval: 5000 });
  const [activeTab, setActiveTab] = useState<'status' | 'pipeline' | 'events' | 'budget'>('status');

  return (
    <div className="max-w-6xl mx-auto p-4 md:p-8">
      <header className="mb-8">
        <h1 className="text-3xl md:text-4xl font-bold text-white">DeepBlender</h1>
        <p className="text-gray-400 mt-1">
          Production audiovisuelle assistée par agents IA <code className="bg-gray-800 px-1 rounded">NOOA</code> + Blender
        </p>
      </header>

      <nav className="flex gap-2 mb-6 border-b border-gray-800 pb-2" role="tablist">
        <button
          role="tab"
          aria-selected={activeTab === 'status'}
          onClick={() => setActiveTab('status')}
          className={`px-4 py-2 rounded-t-lg text-sm font-medium transition-colors ${
            activeTab === 'status'
              ? 'bg-gray-800 text-white'
              : 'text-gray-400 hover:text-gray-200'
          }`}
        >
          Statut
        </button>
        <button
          role="tab"
          aria-selected={activeTab === 'pipeline'}
          onClick={() => setActiveTab('pipeline')}
          className={`px-4 py-2 rounded-t-lg text-sm font-medium transition-colors ${
            activeTab === 'pipeline'
              ? 'bg-gray-800 text-white'
              : 'text-gray-400 hover:text-gray-200'
          }`}
        >
          Pipeline
        </button>
        <button
          role="tab"
          aria-selected={activeTab === 'events'}
          onClick={() => setActiveTab('events')}
          className={`px-4 py-2 rounded-t-lg text-sm font-medium transition-colors ${
            activeTab === 'events'
              ? 'bg-gray-800 text-white'
              : 'text-gray-400 hover:text-gray-200'
          }`}
        >
          Événements (SSE)
        </button>
        <button
          role="tab"
          aria-selected={activeTab === 'budget'}
          onClick={() => setActiveTab('budget')}
          className={`px-4 py-2 rounded-t-lg text-sm font-medium transition-colors ${
            activeTab === 'budget'
              ? 'bg-gray-800 text-white'
              : 'text-gray-400 hover:text-gray-200'
          }`}
        >
          Budget
        </button>
      </nav>

      {statusError && (
        <div className="mb-4 p-4 bg-red-900/30 border border-red-700 rounded-lg text-red-300">
          Impossible de se connecter à l'API ({API_URL}). Vérifiez que le serveur DeepBlender tourne.
        </div>
      )}

      {activeTab === 'status' && <StatusPanel status={status} />}
      {activeTab === 'pipeline' && <PipelineForm />}
      {activeTab === 'events' && <EventStream />}
      {activeTab === 'budget' && <BudgetPanel budget={budget} />}
    </div>
  );
}