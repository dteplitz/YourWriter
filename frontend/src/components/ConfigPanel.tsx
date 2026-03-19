import { useState, useEffect, useCallback, useRef } from 'react';
import type { Identity, EvolutionDetectedEvent } from '../types';
import * as api from '../api/client';
import { EmotionBar } from './EmotionBar';
import { TraitBadge } from './TraitBadge';
import { ConstraintCard } from './ConstraintCard';
import '../config-panel.css';

interface ConfigPanelProps {
  writerId: string;
  onIdentityLoaded?: (identity: Identity) => void;
  pendingEvolution?: EvolutionDetectedEvent | null;
  onEvolutionAccepted?: () => void;
  onEvolutionRollback?: () => void;
}

type KVPair = { key: string; value: string };

function recordToKVPairs(record: Record<string, unknown>): KVPair[] {
  return Object.entries(record).map(([key, value]) => ({
    key,
    value: String(value),
  }));
}

function kvPairsToRecord(pairs: KVPair[]): Record<string, string> {
  const result: Record<string, string> = {};
  for (const { key, value } of pairs) {
    if (key.trim() !== '') {
      result[key.trim()] = value;
    }
  }
  return result;
}

function computeChangedKeys(
  prevPersonality: Record<string, unknown>,
  nextPersonality: Record<string, unknown>,
  prevConstraints: Record<string, unknown>,
  nextConstraints: Record<string, unknown>,
  prevEmotions: Record<string, unknown> = {},
  nextEmotions: Record<string, unknown> = {}
): Set<string> {
  const changed = new Set<string>();

  const allPersonalityKeys = new Set([
    ...Object.keys(prevPersonality),
    ...Object.keys(nextPersonality),
  ]);
  for (const k of allPersonalityKeys) {
    if (String(prevPersonality[k] ?? '') !== String(nextPersonality[k] ?? '')) {
      changed.add(`personality.${k}`);
    }
  }

  const allConstraintKeys = new Set([
    ...Object.keys(prevConstraints),
    ...Object.keys(nextConstraints),
  ]);
  for (const k of allConstraintKeys) {
    if (String(prevConstraints[k] ?? '') !== String(nextConstraints[k] ?? '')) {
      changed.add(`constraints.${k}`);
    }
  }

  const allEmotionKeys = new Set([
    ...Object.keys(prevEmotions),
    ...Object.keys(nextEmotions),
  ]);
  for (const k of allEmotionKeys) {
    if (String(prevEmotions[k] ?? '') !== String(nextEmotions[k] ?? '')) {
      changed.add(`emotions.${k}`);
    }
  }

  return changed;
}

interface KVTableProps {
  pairs: KVPair[];
  onChange: (pairs: KVPair[]) => void;
  addLabel: string;
}

function KVTable({ pairs, onChange, addLabel }: KVTableProps) {
  const handleKeyChange = (index: number, newKey: string) => {
    const next = pairs.map((p, i) => (i === index ? { ...p, key: newKey } : p));
    onChange(next);
  };

  const handleValueChange = (index: number, newValue: string) => {
    const next = pairs.map((p, i) =>
      i === index ? { ...p, value: newValue } : p
    );
    onChange(next);
  };

  const handleRemove = (index: number) => {
    onChange(pairs.filter((_, i) => i !== index));
  };

  const handleAdd = () => {
    onChange([...pairs, { key: '', value: '' }]);
  };

  return (
    <div className="config-kv-table">
      {pairs.map((pair, i) => (
        <div key={i} className="config-kv-row">
          <input
            className="config-kv-input"
            placeholder="key"
            value={pair.key}
            onChange={(e) => handleKeyChange(i, e.target.value)}
          />
          <input
            className="config-kv-input"
            placeholder="value"
            value={pair.value}
            onChange={(e) => handleValueChange(i, e.target.value)}
          />
          <button
            type="button"
            className="config-kv-remove"
            onClick={() => handleRemove(i)}
            aria-label="Remove row"
          >
            ×
          </button>
        </div>
      ))}
      <button type="button" className="config-add-row" onClick={handleAdd}>
        + {addLabel}
      </button>
    </div>
  );
}

export default function ConfigPanel({
  writerId,
  onIdentityLoaded,
  pendingEvolution,
  onEvolutionAccepted,
  onEvolutionRollback,
}: ConfigPanelProps) {
  const [identity, setIdentity] = useState<Identity | null>(null);
  const [loading, setLoading] = useState(true);

  // Edit mode state
  const [editMode, setEditMode] = useState(false);
  const [editedPersonality, setEditedPersonality] = useState<KVPair[]>([]);
  const [editedConstraints, setEditedConstraints] = useState<KVPair[]>([]);

  // Save state
  const [saving, setSaving] = useState(false);
  const [showSaved, setShowSaved] = useState(false);

  // Animation state
  const [changedKeys, setChangedKeys] = useState<Set<string>>(new Set());
  const [versionBump, setVersionBump] = useState(false);

  // Undo banner state (30s window after evolution)
  const [showUndoBanner, setShowUndoBanner] = useState(false);
  const [rollingBack, setRollingBack] = useState(false);
  const undoTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    loadIdentity();
  }, [writerId]);

  // Clear changed key highlights after 1500ms
  useEffect(() => {
    if (changedKeys.size === 0) return;
    const timer = setTimeout(() => setChangedKeys(new Set()), 1500);
    return () => clearTimeout(timer);
  }, [changedKeys]);

  // Clear version bump animation
  useEffect(() => {
    if (!versionBump) return;
    const timer = setTimeout(() => setVersionBump(false), 400);
    return () => clearTimeout(timer);
  }, [versionBump]);

  // React to incoming pendingEvolution: animate diff, reload identity, show undo banner for 30s
  useEffect(() => {
    if (!pendingEvolution || !identity) return;

    // Compute changed keys from the evolution event so diff animation fires
    const changed = new Set<string>();
    for (const change of pendingEvolution.changes) {
      if (change.key) {
        changed.add(`${change.field}.${change.key}`);
      } else {
        changed.add(change.field);
      }
    }
    setChangedKeys(changed);
    setVersionBump(true);

    // Silently refresh identity so the panel shows evolved values (v2, new emotions, etc.)
    // Do NOT call loadIdentity() — that sets loading=true which would hide the Undo banner.
    api.getIdentity(writerId).then((data) => {
      setIdentity(data);
      onIdentityLoaded?.(data);
    }).catch(() => {});

    // Show undo banner, auto-dismiss after 30s
    setShowUndoBanner(true);
    if (undoTimerRef.current) clearTimeout(undoTimerRef.current);
    undoTimerRef.current = setTimeout(() => {
      setShowUndoBanner(false);
      onEvolutionAccepted?.();
    }, 30000);

    return () => {
      if (undoTimerRef.current) clearTimeout(undoTimerRef.current);
    };
  }, [pendingEvolution]);

  // Cleanup undo timer on unmount
  useEffect(() => {
    return () => {
      if (undoTimerRef.current) clearTimeout(undoTimerRef.current);
    };
  }, []);

  const loadIdentity = async () => {
    setLoading(true);
    try {
      const data = await api.getIdentity(writerId);
      setIdentity(data);
      onIdentityLoaded?.(data);
    } catch {
      setIdentity(null);
    } finally {
      setLoading(false);
    }
  };

  const enterEditMode = useCallback(() => {
    if (!identity) return;
    setEditedPersonality(recordToKVPairs(identity.personality));
    setEditedConstraints(recordToKVPairs(identity.constraints));
    setEditMode(true);
  }, [identity]);

  const cancelEdit = useCallback(() => {
    setEditMode(false);
    setEditedPersonality([]);
    setEditedConstraints([]);
  }, []);

  const isDirty = useCallback(() => {
    if (!identity) return false;
    const currentPersonality = kvPairsToRecord(editedPersonality);
    const currentConstraints = kvPairsToRecord(editedConstraints);
    // Normalize both sides to string values before comparing (identity stores numbers/booleans)
    const normalize = (rec: Record<string, unknown>) =>
      JSON.stringify(Object.fromEntries(Object.entries(rec).sort().map(([k, v]) => [k, String(v)])));
    return (
      normalize(currentPersonality) !== normalize(identity.personality) ||
      normalize(currentConstraints) !== normalize(identity.constraints)
    );
  }, [identity, editedPersonality, editedConstraints]);

  const handleSave = async () => {
    if (!identity) return;
    setSaving(true);

    const prevIdentity = identity;
    const newPersonality = kvPairsToRecord(editedPersonality);
    const newConstraints = kvPairsToRecord(editedConstraints);

    try {
      const [updatedFromIdentity, updatedFromConstraints] = await Promise.all([
        api.updateIdentity(writerId, { personality: newPersonality }),
        api.updateConstraints(writerId, { constraints: newConstraints }),
      ]);

      // Merge both responses: personality from first call, constraints + version from second
      // (constraints call creates the later version, so its version number is canonical)
      const finalIdentity = {
        ...updatedFromIdentity,
        constraints: updatedFromConstraints.constraints,
        version: updatedFromConstraints.version,
      };

      const changed = computeChangedKeys(
        prevIdentity.personality,
        finalIdentity.personality,
        prevIdentity.constraints,
        finalIdentity.constraints,
        prevIdentity.emotions,
        finalIdentity.emotions
      );

      setIdentity(finalIdentity);
      setChangedKeys(changed);
      setVersionBump(true);
      setEditMode(false);
      setEditedPersonality([]);
      setEditedConstraints([]);
      setShowSaved(true);
      setTimeout(() => setShowSaved(false), 2000);
    } catch (err) {
      console.error('Failed to save identity:', err);
    } finally {
      setSaving(false);
    }
  };

  const handleRollback = async () => {
    if (!identity || rollingBack) return;
    setRollingBack(true);

    // Clear the undo timer — we're acting before the 30s expires
    if (undoTimerRef.current) clearTimeout(undoTimerRef.current);

    try {
      const rolledBackIdentity = await api.rollbackIdentity(identity.writer_id);

      // Animate diff between current and rolled-back identity
      const changed = computeChangedKeys(
        identity.personality,
        rolledBackIdentity.personality,
        identity.constraints,
        rolledBackIdentity.constraints,
        identity.emotions,
        rolledBackIdentity.emotions
      );

      setIdentity(rolledBackIdentity);
      onIdentityLoaded?.(rolledBackIdentity);
      setChangedKeys(changed);
      setVersionBump(true);
      setShowUndoBanner(false);
      onEvolutionRollback?.();
    } catch (err) {
      console.error('Failed to rollback identity:', err);
    } finally {
      setRollingBack(false);
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

  const dirty = editMode && isDirty();

  return (
    <div className="config-panel">
      <div className="config-panel-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <h3>Configuration</h3>
          <span
            className={`config-version-badge${versionBump ? ' config-version--bump' : ''}`}
          >
            v{identity.version}
          </span>
          {dirty && <span className="config-dirty-dot" title="Unsaved changes" />}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          {showSaved && <span className="config-save-indicator">Saved ✓</span>}
          {!editMode && (
            <button
              type="button"
              className="config-edit-btn"
              onClick={enterEditMode}
            >
              Edit
            </button>
          )}
        </div>
      </div>

      {/* Evolution undo banner */}
      {showUndoBanner && (
        <div className="config-evolution-banner">
          <span className="config-evolution-banner-text">
            ⚡ Writer evolved automatically
          </span>
          <button
            type="button"
            className="config-evolution-undo-btn"
            onClick={handleRollback}
            disabled={rollingBack}
          >
            {rollingBack ? 'Undoing...' : 'Undo'}
          </button>
        </div>
      )}

      {/* Personality */}
      <section className="config-section">
        <h4>Personality</h4>
        {editMode ? (
          <KVTable
            pairs={editedPersonality}
            onChange={setEditedPersonality}
            addLabel="Add trait"
          />
        ) : (
          <div className="config-tags">
            {Object.entries(identity.personality).map(([key, value]) => (
              <TraitBadge
                key={key}
                name={key}
                value={value}
                isChanged={changedKeys.has(`personality.${key}`)}
              />
            ))}
            {Object.keys(identity.personality).length === 0 && (
              <span className="config-empty-text">No traits defined</span>
            )}
          </div>
        )}
      </section>

      {/* Emotions — read-only, evolves automatically */}
      <section className="config-section">
        <h4>
          Emotions{' '}
          <span className="config-auto-badge">Evolves automatically</span>
        </h4>
        <div className="config-emotion-bars">
          {Object.entries(identity.emotions).map(([key, value]) =>
            typeof value === 'number' ? (
              <EmotionBar
                key={key}
                name={key}
                value={value}
                isChanged={changedKeys.has(`emotions.${key}`)}
              />
            ) : (
              <span key={key} className="config-tag config-tag--emotion">
                {key}: {String(value)}
              </span>
            )
          )}
          {Object.keys(identity.emotions).length === 0 && (
            <span className="config-empty-text">No emotions defined</span>
          )}
        </div>
      </section>

      {/* Topics — always read-only, no badge */}
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

      {/* Constraints */}
      <section className="config-section">
        <h4>Constraints</h4>
        {editMode ? (
          <KVTable
            pairs={editedConstraints}
            onChange={setEditedConstraints}
            addLabel="Add constraint"
          />
        ) : (
          <div className="config-constraints">
            {Object.entries(identity.constraints).map(([key, value]) => (
              <ConstraintCard
                key={key}
                name={key}
                value={value}
                isChanged={changedKeys.has(`constraints.${key}`)}
              />
            ))}
            {Object.keys(identity.constraints).length === 0 && (
              <span className="config-empty-text">No constraints set</span>
            )}
          </div>
        )}
      </section>

      {/* Lifelong Objectives — read-only, evolves automatically */}
      <section className="config-section">
        <h4>
          Lifelong Objectives{' '}
          <span className="config-auto-badge">Evolves automatically</span>
        </h4>
        <ul className="config-objectives">
          {identity.lifelong_objectives.map((obj, i) => (
            <li key={i}>{obj}</li>
          ))}
          {identity.lifelong_objectives.length === 0 && (
            <li className="config-empty-text">No objectives defined</li>
          )}
        </ul>
      </section>

      {/* Memories — always read-only, no badge */}
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

      {/* Edit mode actions */}
      {editMode && (
        <div className="config-actions">
          <button
            type="button"
            className="btn btn-primary"
            onClick={handleSave}
            disabled={saving || !dirty}
          >
            {saving ? 'Saving...' : 'Save Changes'}
          </button>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={cancelEdit}
            disabled={saving}
          >
            Cancel
          </button>
        </div>
      )}
    </div>
  );
}
