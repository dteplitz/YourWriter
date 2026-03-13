import { useState, useEffect } from 'react';
import type { EvolutionEntry } from '../types';
import * as api from '../api/client';

interface EvolutionFeedProps {
  writerId: string;
}

export default function EvolutionFeed({ writerId }: EvolutionFeedProps) {
  const [entries, setEntries] = useState<EvolutionEntry[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadEvolution();
  }, [writerId]);

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

  return (
    <div className="evolution-feed">
      <h3>Evolution Timeline</h3>
      {loading && <div className="evolution-loading">Loading...</div>}
      {!loading && entries.length === 0 && (
        <div className="evolution-empty">
          No evolution entries yet. Your writer will evolve as you interact with
          it.
        </div>
      )}
      <div className="evolution-entries">
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
          </div>
        ))}
      </div>
    </div>
  );
}
