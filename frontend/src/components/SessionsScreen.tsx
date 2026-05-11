import { useCallback, useEffect, useState } from 'react';
import { getIndexedSessions, querySessions } from '../services/apiClient';
import { SessionResult } from '../types';

function SourceBadge({ source }: { source: string }) {
  const colors: Record<string, string> = {
    cli: 'bg-blue-100 text-blue-700',
    web: 'bg-purple-100 text-purple-700',
    api: 'bg-green-100 text-green-700',
    slack: 'bg-orange-100 text-orange-700',
    discord: 'bg-indigo-100 text-indigo-700',
    default: 'bg-slate-100 text-slate-700',
  };
  const colorClass = colors[source.toLowerCase()] || colors.default;
  return (
    <span className={`inline-flex px-2 py-1 text-xs font-bold rounded ${colorClass}`}>
      {source}
    </span>
  );
}

function SessionCard({ result }: { result: SessionResult }) {
  const [expanded, setExpanded] = useState(false);
  const truncatedText = result.text.length > 200
    ? result.text.slice(0, 200) + '...'
    : result.text;

  return (
    <div
      className="bg-white rounded-xl shadow-sm border border-slate-200 p-5 hover:shadow-md hover:border-slate-300 transition-all cursor-pointer"
      onClick={() => setExpanded(!expanded)}
    >
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-3">
          <span className="text-sm font-mono text-slate-700 font-semibold">
            {result.session_id.slice(0, 16)}...
          </span>
          <SourceBadge source={result.source} />
        </div>
        <span className="text-sm font-bold text-slate-800">
          {result.score.toFixed(3)}
        </span>
      </div>
      <p className="text-sm text-slate-600 leading-relaxed">
        {expanded ? result.text : truncatedText}
      </p>
      {result.text.length > 200 && (
        <div className="mt-2 text-xs text-slate-400">
          {expanded ? 'Click to collapse' : 'Click to expand'}
        </div>
      )}
    </div>
  );
}

export default function SessionsScreen() {
  const [searchText, setSearchText] = useState('');
  const [results, setResults] = useState<SessionResult[]>([]);
  const [indexedSessions, setIndexedSessions] = useState<string[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasSearched, setHasSearched] = useState(false);

  const loadIndexed = useCallback(async () => {
    try {
      const sessions = await getIndexedSessions();
      setIndexedSessions(sessions);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load indexed sessions');
    }
  }, []);

  useEffect(() => {
    loadIndexed();
    const interval = setInterval(loadIndexed, 2000);
    return () => clearInterval(interval);
  }, [loadIndexed]);

  async function handleSearch() {
    if (!searchText.trim()) return;
    setLoading(true);
    setHasSearched(true);
    try {
      const response = await querySessions(searchText.trim());
      setResults(response.results || []);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to query sessions');
      setResults([]);
    } finally {
      setLoading(false);
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      handleSearch();
    }
  };

  const isEmpty = indexedSessions !== null && indexedSessions.length === 0;

  return (
    <div className="min-h-screen bg-slate-50 p-8">
      <div className="max-w-7xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-slate-900 mb-2">Sessions</h1>
          <p className="text-slate-600">
            Search across indexed conversation sessions
            {indexedSessions !== null && (
              <span className="ml-2 text-xs text-slate-400">
                ({indexedSessions.length} indexed)
              </span>
            )}
          </p>
        </div>

        {error && (
          <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
            {error}
          </div>
        )}

        {isEmpty ? (
          <div className="bg-white rounded-xl shadow-sm p-12 text-center border border-slate-200">
            <div className="text-slate-400 text-lg mb-2">No sessions indexed</div>
            <div className="text-slate-500 text-sm">
              Sessions will appear here once they are indexed by the backend.
            </div>
          </div>
        ) : (
          <>
            <div className="mb-6 flex items-center gap-3">
              <div className="flex-1">
                <input
                  type="text"
                  value={searchText}
                  onChange={(e) => setSearchText(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Search sessions..."
                  className="w-full px-4 py-3 rounded-lg border border-slate-300 bg-white text-sm text-slate-700 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                />
              </div>
              <button
                onClick={handleSearch}
                disabled={loading || !searchText.trim()}
                className="px-6 py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 text-white text-sm font-semibold rounded-lg transition-colors"
              >
                {loading ? 'Searching...' : 'Search'}
              </button>
            </div>

            {loading && !hasSearched && (
              <div className="flex items-center justify-center py-20">
                <div className="text-slate-500">Loading...</div>
              </div>
            )}

            {hasSearched && !loading && results.length === 0 && (
              <div className="bg-white rounded-xl shadow-sm p-12 text-center border border-slate-200">
                <div className="text-slate-400 text-lg">No results found</div>
                <div className="text-slate-500 text-sm mt-1">
                  Try a different search term.
                </div>
              </div>
            )}

            {results.length > 0 && (
              <div className="space-y-4">
                {results.map((result, idx) => (
                  <SessionCard key={`${result.session_id}-${idx}`} result={result} />
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
