import { useState, useEffect } from 'react';
import type { Identity } from '../types';
import * as api from '../api/client';

interface ConfigPanelProps {
  writerId: string;
}

export default function ConfigPanel({ writerId }: ConfigPanelProps) {
  const [identity, setIdentity] = useState<Identity | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadIdentity();
  }, [writerId]);

  const loadIdentity = async () => {
    setLoading(true);
    try {
      const data = await api.getIdentity(writerId);
      setIdentity(data);
    } catch {
      setIdentity(null);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="config-panel">
        <h3>Configuration</h3>
        <div className="config-loading">Loading identity...</div>
      </div>
    );
  }

  if (!identity) {
    return (
      <div className="config-panel">
        <h3>Configuration</h3>
        <div className="config-empty">No identity data available.</div>
      </div>
    );
  }

  return (
    <div className="config-panel">
      <h3>Configuration</h3>

      <section className="config-section">
        <h4>Personality</h4>
        <div className="config-tags">
          {Object.entries(identity.personality).map(([key, value]) => (
            <span key={key} className="config-tag">
              {key}: {String(value)}
            </span>
          ))}
          {Object.keys(identity.personality).length === 0 && (
            <span className="config-empty-text">No traits defined</span>
          )}
        </div>
      </section>

      <section className="config-section">
        <h4>Emotions</h4>
        <div className="config-tags">
          {Object.entries(identity.emotions).map(([key, value]) => (
            <span key={key} className="config-tag config-tag--emotion">
              {key}: {String(value)}
            </span>
          ))}
          {Object.keys(identity.emotions).length === 0 && (
            <span className="config-empty-text">No emotions defined</span>
          )}
        </div>
      </section>

      <section className="config-section">
        <h4>Topics</h4>
        <div className="config-tags">
          {identity.topics.map((topic, i) => (
            <span key={i} className="config-tag config-tag--topic">
              {topic}
            </span>
          ))}
          {identity.topics.length === 0 && (
            <span className="config-empty-text">No topics defined</span>
          )}
        </div>
      </section>

      <section className="config-section">
        <h4>Constraints</h4>
        <div className="config-constraints">
          {Object.entries(identity.constraints).map(([key, value]) => (
            <div key={key} className="config-constraint">
              <span className="config-constraint-key">{key}:</span>
              <span className="config-constraint-value">{value}</span>
            </div>
          ))}
          {Object.keys(identity.constraints).length === 0 && (
            <span className="config-empty-text">No constraints set</span>
          )}
        </div>
      </section>

      <section className="config-section">
        <h4>Lifelong Objectives</h4>
        <ul className="config-objectives">
          {identity.lifelong_objectives.map((obj, i) => (
            <li key={i}>{obj}</li>
          ))}
          {identity.lifelong_objectives.length === 0 && (
            <li className="config-empty-text">No objectives defined</li>
          )}
        </ul>
      </section>

      <section className="config-section">
        <h4>Memories</h4>
        <div className="config-memories">
          {identity.memories.map((memory, i) => (
            <div key={i} className="config-memory">
              {memory}
            </div>
          ))}
          {identity.memories.length === 0 && (
            <span className="config-empty-text">No memories yet</span>
          )}
        </div>
      </section>
    </div>
  );
}
