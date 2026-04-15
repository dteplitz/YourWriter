import { useState, useEffect } from 'react';
import type { EvolutionEntry, EvolutionDetectedEvent, EvolutionChange } from '../types';
import * as api from '../api/client';

interface EvolutionFeedProps {
  writerId: string;
  autoEvolutionEvent?: EvolutionDetectedEvent | null;
  onOpenSession?: (sessionId: number) => void;
}

interface AutoEvolutionFeedEntry {
  type: 'auto';
  id: string;
  reasoning: string;
  changes: EvolutionChange[];
  timestamp: string;
}

export default function EvolutionFeed({
  writerId,
  autoEvolutionEvent,
  onOpenSession,
}: EvolutionFeedProps) {
  const [entries, setEntries] = useState<EvolutionEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [autoEntries, setAutoEntries] = useState<AutoEvolutionFeedEntry[]>([]);

  useEffect(() => {
    loadEvolution();
  }, [writerId]);

  // When a new auto-evolution event arrives, prepend it to the auto entries list
  useEffect(() => {
    if (!autoEvolutionEvent) return;
    const newEntry: AutoEvolutionFeedEntry = {
      type: 'auto',
      id: `auto-${Date.now()}`,
      reasoning: autoEvolutionEvent.reasoning,
      changes: autoEvolutionEvent.changes,
      timestamp: new Date().toISOString(),
    };
    setAutoEntries((prev) => [newEntry, ...prev]);
  }, [autoEvolutionEvent]);

  const loadEvolution = async () => {
    setLoading(true);
    try {
      const data = await api.getEvolutionLog(writerId);
      setEntries(data);
    } catch {
      setEntries([]);
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleString();
  };

  const hasAnyEntries = autoEntries.length > 0 || entries.length > 0;

  return (
    <div className="evolution-feed">
      <h3>Evolution Timeline</h3>
      {loading && <div className="evolution-loading">Loading...</div>}
      {!loading && !hasAnyEntries && (
        <div className="evolution-empty">
          No evolution entries yet. Your writer will evolve as you interact with
          it.
        </div>
      )}
      <div className="evolution-entries">
        {/* Auto-evolution entries — prepended, visually distinct */}
        {autoEntries.map((entry) => (
          <div key={entry.id} className="evolution-entry evolution-entry--auto">
            <div className="evolution-entry-header">
              <span className="evolution-field">
                <span className="evolution-auto-chip">⚡ auto</span>
              </span>
              <span className="evolution-date">{formatDate(entry.timestamp)}</span>
            </div>
            <div className="evolution-reason" style={{ marginBottom: '0.4rem' }}>
              {entry.reasoning}
            </div>
            {entry.changes.map((change, i) => (
              <div key={i} className="evolution-auto-change">
                <span className="evolution-auto-field">{change.field}</span>
                {change.key && (
                  <span className="evolution-auto-key">.{change.key}</span>
                )}
                <span className={`evolution-auto-action evolution-auto-action--${change.action}`}>
                  {change.action}
                </span>
                {change.reason && (
                  <span className="evolution-auto-reason">{change.reason}</span>
                )}
              </div>
            ))}
          </div>
        ))}

        {/* Persisted evolution log entries (manual edits by user) */}
        {entries.map((entry) => (
          <div key={entry.id} className="evolution-entry">
            <div className="evolution-entry-header">
              <span className="evolution-field">{entry.field_changed}</span>
              <span className="evolution-date">
                {formatDate(entry.created_at)}
              </span>
            </div>
            <div className="evolution-change">
              <div className="evolution-old">
                <span className="evolution-label">Before:</span>
                <span>{entry.old_value}</span>
              </div>
              <div className="evolution-new">
                <span className="evolution-label">After:</span>
                <span>{entry.new_value}</span>
              </div>
            </div>
            <div className="evolution-reason">
              <span className="evolution-label">Reason:</span> {entry.reason}
            </div>
            {entry.source_session_id && onOpenSession && (
              <button
                type="button"
                className="evolution-session-chip"
                onClick={() => onOpenSession(entry.source_session_id!)}
              >
                Sesion #{entry.source_session_id}
              </button>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
