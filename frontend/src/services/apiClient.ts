import {
  Experiment,
  ExploreResponse,
  PromptLibrary,
  PromptQueryResponse,
  SessionQueryResponse,
} from '../types';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8001';

export async function getExperiments(): Promise<Experiment[]> {
  const response = await fetch(`${API_BASE_URL}/experiments`);
  if (!response.ok) {
    throw new Error('Failed to fetch experiments');
  }
  const data = await response.json();
  return data.experiments || [];
}

export async function getExperiment(experimentId: string): Promise<Experiment> {
  const response = await fetch(`${API_BASE_URL}/experiments/${experimentId}`);
  if (!response.ok) {
    throw new Error('Failed to fetch experiment');
  }
  return response.json();
}

export async function getExperimentExplore(
  experimentId: string,
  query?: string,
): Promise<ExploreResponse> {
  const params = query ? `?query=${encodeURIComponent(query)}` : '';
  const response = await fetch(`${API_BASE_URL}/experiments/${experimentId}/explore${params}`);
  if (!response.ok) {
    throw new Error('Failed to fetch experiment explore data');
  }
  return response.json();
}

export async function cancelExperiment(experimentId: string): Promise<{ status: string; message: string }> {
  const response = await fetch(`${API_BASE_URL}/experiments/${experimentId}/cancel`, {
    method: 'POST',
  });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.detail || 'Failed to cancel experiment');
  }
  return response.json();
}

// Sessions

export async function querySessions(text: string): Promise<SessionQueryResponse> {
  const response = await fetch(`${API_BASE_URL}/sessions/query`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text }),
  });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.detail || 'Failed to query sessions');
  }
  return response.json();
}

export async function getIndexedSessions(): Promise<string[]> {
  const response = await fetch(`${API_BASE_URL}/sessions/indexed`);
  if (!response.ok) {
    throw new Error('Failed to fetch indexed sessions');
  }
  const data = await response.json();
  return data.sessions || [];
}

// Prompts

export async function queryPrompts(text: string, library?: string): Promise<PromptQueryResponse> {
  const response = await fetch(`${API_BASE_URL}/prompts/query`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text, library }),
  });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.detail || 'Failed to query prompts');
  }
  return response.json();
}

export async function getPromptLibraries(): Promise<PromptLibrary[]> {
  const response = await fetch(`${API_BASE_URL}/prompts/libraries`);
  if (!response.ok) {
    throw new Error('Failed to fetch prompt libraries');
  }
  const data = await response.json();
  return data.libraries || [];
}
