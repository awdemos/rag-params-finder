import { useCallback, useEffect, useState } from 'react';
import { getPromptLibraries, queryPrompts } from '../services/apiClient';
import { PromptResult } from '../types';

function TagBadge({ tag }: { tag: string }) {
  return (
    <span className="inline-flex px-2 py-0.5 text-xs font-medium rounded bg-slate-100 text-slate-600">
      {tag}
    </span>
  );
}

function PromptCard({ result }: { result: PromptResult }) {
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
        <div className="flex-1 min-w-0">
          <h3 className="text-base font-bold text-slate-900 mb-1">
            {result.title}
          </h3>
          {result.description && (
            <p className="text-xs text-slate-500 mb-2">{result.description}</p>
          )}
          {result.tags.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {result.tags.map((tag) => (
                <TagBadge key={tag} tag={tag} />
              ))}
            </div>
          )}
        </div>
        <span className="text-sm font-bold text-slate-800 ml-4 shrink-0">
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

export default function PromptsScreen() {
  const [searchText, setSearchText] = useState('');
  const [selectedLibrary, setSelectedLibrary] = useState('');
  const [libraries, setLibraries] = useState<string[]>([]);
  const [results, setResults] = useState<PromptResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasSearched, setHasSearched] = useState(false);

  const loadLibraries = useCallback(async () => {
    try {
      const libs = await getPromptLibraries();
      setLibraries(libs.map((l) => l.name));
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load prompt libraries');
    }
  }, []);

  useEffect(() => {
    loadLibraries();
  }, [loadLibraries]);

  async function handleSearch() {
    if (!searchText.trim()) return;
    setLoading(true);
    setHasSearched(true);
    try {
      const response = await queryPrompts(searchText.trim(), selectedLibrary || undefined);
      setResults(response.results || []);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to query prompts');
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

  const isEmpty = libraries.length === 0;

  return (
    <div className="min-h-screen bg-slate-50 p-8">
      <div className="max-w-7xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-slate-900 mb-2">Prompts</h1>
          <p className="text-slate-600">
            Search across indexed prompt libraries
          </p>
        </div>

        {error && (
          <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
            {error}
          </div>
        )}

        {isEmpty ? (
          <div className="bg-white rounded-xl shadow-sm p-12 text-center border border-slate-200">
            <div className="text-slate-400 text-lg mb-2">No prompts indexed</div>
            <div className="text-slate-500 text-sm">
              Prompts will appear here once they are indexed by the backend.
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
                  placeholder="Search prompts..."
                  className="w-full px-4 py-3 rounded-lg border border-slate-300 bg-white text-sm text-slate-700 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                />
              </div>
              <select
                value={selectedLibrary}
                onChange={(e) => setSelectedLibrary(e.target.value)}
                className="px-4 py-3 rounded-lg border border-slate-300 bg-white text-sm text-slate-700 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
              >
                <option value="">All libraries</option>
                {libraries.map((lib) => (
                  <option key={lib} value={lib}>
                    {lib}
                  </option>
                ))}
              </select>
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
                  Try a different search term or library.
                </div>
              </div>
            )}

            {results.length > 0 && (
              <div className="space-y-4">
                {results.map((result, idx) => (
                  <PromptCard key={`${result.title}-${idx}`} result={result} />
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
