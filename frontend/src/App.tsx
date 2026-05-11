import { useState } from 'react';
import ExperimentsScreen from './components/ExperimentsScreen';
import ExperimentDetailScreen from './components/ExperimentDetailScreen';
import SearchExplorerScreen from './components/SearchExplorerScreen';
import SessionsScreen from './components/SessionsScreen';
import PromptsScreen from './components/PromptsScreen';

type Tab = 'experiments' | 'sessions' | 'prompts';

type Screen =
  | { kind: 'list' }
  | { kind: 'detail'; experimentId: string }
  | { kind: 'explore'; experimentId: string };

const TAB_CONFIG: { id: Tab; label: string }[] = [
  { id: 'experiments', label: 'Experiments' },
  { id: 'sessions', label: 'Sessions' },
  { id: 'prompts', label: 'Prompts' },
];

function TabBar({ activeTab, onChange }: { activeTab: Tab; onChange: (tab: Tab) => void }) {
  return (
    <div className="sticky top-0 z-50 bg-slate-900 border-b border-slate-700">
      <div className="max-w-7xl mx-auto px-8">
        <div className="flex items-center gap-1">
          <div className="flex items-center gap-2 mr-6 py-3">
            <div className="w-7 h-7 rounded-lg bg-blue-600 flex items-center justify-center">
              <span className="text-white text-xs font-bold">R</span>
            </div>
            <span className="text-white font-bold text-sm">RAG Params Finder</span>
          </div>
          {TAB_CONFIG.map((tab) => (
            <button
              key={tab.id}
              onClick={() => onChange(tab.id)}
              className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                activeTab === tab.id
                  ? 'border-blue-500 text-white'
                  : 'border-transparent text-slate-400 hover:text-slate-200'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

export default function App() {
  const [activeTab, setActiveTab] = useState<Tab>('experiments');
  const [screen, setScreen] = useState<Screen>({ kind: 'list' });

  function handleTabChange(tab: Tab) {
    setActiveTab(tab);
    if (tab === 'experiments') {
      setScreen({ kind: 'list' });
    }
  }

  function renderContent() {
    if (activeTab === 'sessions') {
      return <SessionsScreen />;
    }

    if (activeTab === 'prompts') {
      return <PromptsScreen />;
    }

    if (screen.kind === 'explore') {
      return (
        <SearchExplorerScreen
          experimentId={screen.experimentId}
          onBack={() => setScreen({ kind: 'detail', experimentId: screen.experimentId })}
        />
      );
    }

    if (screen.kind === 'detail') {
      return (
        <ExperimentDetailScreen
          experimentId={screen.experimentId}
          onBack={() => setScreen({ kind: 'list' })}
          onExplore={() => setScreen({ kind: 'explore', experimentId: screen.experimentId })}
        />
      );
    }

    return (
      <ExperimentsScreen
        onSelect={(id) => setScreen({ kind: 'detail', experimentId: id })}
      />
    );
  }

  return (
    <div className="min-h-screen bg-slate-50">
      <TabBar activeTab={activeTab} onChange={handleTabChange} />
      {renderContent()}
    </div>
  );
}
