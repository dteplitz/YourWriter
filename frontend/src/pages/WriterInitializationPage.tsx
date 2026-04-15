import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import * as api from '../api/client';
import { ConstraintCard } from '../components/ConstraintCard';
import { EmotionBar } from '../components/EmotionBar';
import { TraitBadge } from '../components/TraitBadge';
import type { WriterInitializationPreview } from '../types';
import '../config-panel.css';
import '../writer-init.css';

const STORAGE_KEY = 'writer-initialization-draft-v1';

interface StoredWriterInitializationDraft {
  description: string;
  preview: WriterInitializationPreview | null;
}

function readDraft(): StoredWriterInitializationDraft {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    if (!raw) {
      return { description: '', preview: null };
    }
    const parsed = JSON.parse(raw) as StoredWriterInitializationDraft;
    return {
      description: parsed.description ?? '',
      preview: parsed.preview ?? null,
    };
  } catch {
    return { description: '', preview: null };
  }
}

function writeDraft(draft: StoredWriterInitializationDraft) {
  if (!draft.description.trim() && !draft.preview) {
    sessionStorage.removeItem(STORAGE_KEY);
    return;
  }
  sessionStorage.setItem(STORAGE_KEY, JSON.stringify(draft));
}

export default function WriterInitializationPage() {
  const navigate = useNavigate();
  const [description, setDescription] = useState('');
  const [preview, setPreview] = useState<WriterInitializationPreview | null>(null);
  const [generating, setGenerating] = useState(false);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    const draft = readDraft();
    setDescription(draft.description);
    setPreview(draft.preview);
  }, []);

  useEffect(() => {
    writeDraft({ description, preview });
  }, [description, preview]);

  const hasDescription = description.trim().length > 0;
  const sortedEmotions = useMemo(
    () =>
      preview
        ? Object.entries(preview.emotions).sort((a, b) => b[1] - a[1])
        : [],
    [preview],
  );

  const handleCancel = () => {
    sessionStorage.removeItem(STORAGE_KEY);
    navigate('/');
  };

  const handleGenerate = async () => {
    if (!hasDescription) return;
    setGenerating(true);
    setError('');
    try {
      const nextPreview = await api.initializeWriterPreview(description.trim());
      setPreview(nextPreview);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate writer preview');
    } finally {
      setGenerating(false);
    }
  };

  const handleCreate = async () => {
    if (!preview) return;
    setCreating(true);
    setError('');
    try {
      const writer = await api.createWriterFromPreview(preview);
      sessionStorage.removeItem(STORAGE_KEY);
      navigate(`/writer/${writer.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create writer');
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="writer-init-page">
      <div className="writer-init-shell">
        <div className="writer-init-header">
          <div>
            <div className="writer-init-eyebrow">Create Writer</div>
            <h2 className="writer-init-title">
              {preview
                ? 'Esta sería la primera versión de tu writer.'
                : 'Describí el artista que querés crear.'}
            </h2>
            <p className="writer-init-subtitle">
              {preview
                ? 'Revisá la síntesis inicial. Si te convence, creamos el writer y después lo seguís moldeando en el chat.'
                : 'No hace falta llenar campos. Escribí en texto libre cómo imaginás su voz, qué escribe, qué límites querés que respete o qué obsesiones lo mueven.'}
            </p>
          </div>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={handleCancel}
            disabled={generating || creating}
          >
            Cancelar
          </button>
        </div>

        {error && <div className="form-error">{error}</div>}

        {!preview ? (
          <div className="writer-init-compose">
            <section className="writer-init-card writer-init-card--main">
              <label className="writer-init-label" htmlFor="writer-init-description">
                Texto libre
              </label>
              <textarea
                id="writer-init-description"
                className="writer-init-textarea"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Ej.: Quiero una ensayista de tecnología y vida cotidiana, melancólica pero no solemne, con humor seco y frases limpias..."
                rows={12}
                disabled={generating}
              />
              <div className="writer-init-actions">
                <div className="writer-init-hint">
                  El sistema va a generar una primera configuración del Artist Profile a partir de tu descripción.
                </div>
                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={handleGenerate}
                  disabled={!hasDescription || generating}
                >
                  {generating ? 'Generando...' : 'Generar configuración'}
                </button>
              </div>
            </section>

            <aside className="writer-init-card writer-init-card--side">
              <h3>Qué nos sirve leer</h3>
              <ul className="writer-init-bullets">
                <li>Qué tipo de piezas querés que escriba</li>
                <li>Cómo debería sonar su voz</li>
                <li>Qué emociones o tensiones lo atraviesan</li>
                <li>Qué reglas querés que respete siempre</li>
              </ul>
              <div className="writer-init-note">
                No hace falta decidir todo ahora. La idea es salir con un artista usable y después seguir ajustándolo en el Artist Profile.
              </div>
            </aside>
          </div>
        ) : (
          <div className="writer-init-preview">
            <section className="writer-init-card writer-init-card--hero">
              <div className="writer-init-eyebrow">Identity Preview</div>
              <h3 className="writer-init-preview-name">{preview.name}</h3>
              <p className="writer-init-preview-summary">{preview.summary}</p>

              <div className="writer-init-block">
                <h4>Purpose</h4>
                <p>{preview.purpose}</p>
              </div>
            </section>

            <div className="writer-init-preview-grid">
              <section className="writer-init-card">
                <div className="writer-init-section-head">
                  <h4>Core Identity</h4>
                  <span className="writer-init-badge">Más activa hoy</span>
                </div>

                <div className="writer-init-block">
                  <h5>Personality</h5>
                  <div className="config-tags">
                    {Object.entries(preview.personality).map(([key, value]) => (
                      <TraitBadge key={key} name={key} value={value} />
                    ))}
                  </div>
                </div>

                <div className="writer-init-block">
                  <h5>Emotions</h5>
                  <div className="config-emotion-bars">
                    {sortedEmotions.map(([key, value]) => (
                      <EmotionBar key={key} name={key} value={value} />
                    ))}
                  </div>
                </div>

                <div className="writer-init-block">
                  <h5>Constraints</h5>
                  <div className="config-constraints">
                    {Object.entries(preview.constraints).length > 0 ? (
                      Object.entries(preview.constraints).map(([key, value]) => (
                        <ConstraintCard key={key} name={key} value={value} />
                      ))
                    ) : (
                      <span className="config-empty-text">No constraints set</span>
                    )}
                  </div>
                </div>
              </section>

              <section className="writer-init-card">
                <div className="writer-init-section-head">
                  <h4>Secondary Seeds</h4>
                  <span className="writer-init-badge writer-init-badge--soft">Hoy influyen menos</span>
                </div>

                <details className="writer-init-details">
                  <summary>Ver topics y objetivos iniciales</summary>

                  <div className="writer-init-block">
                    <h5>Topics</h5>
                    <div className="config-tags">
                      {preview.topics.length > 0 ? (
                        preview.topics.map((topic) => (
                          <span key={topic} className="config-tag config-tag--topic">
                            {topic}
                          </span>
                        ))
                      ) : (
                        <span className="config-empty-text">No topics defined</span>
                      )}
                    </div>
                  </div>

                  <div className="writer-init-block">
                    <h5>Lifelong Objectives</h5>
                    <ul className="config-objectives">
                      {preview.lifelong_objectives.length > 0 ? (
                        preview.lifelong_objectives.map((objective) => (
                          <li key={objective}>{objective}</li>
                        ))
                      ) : (
                        <li className="config-empty-text">No objectives defined</li>
                      )}
                    </ul>
                  </div>
                </details>

                <div className="writer-init-note writer-init-note--memory">
                  Las memorias arrancan vacías. Aparecen después, con experiencia real.
                </div>
              </section>
            </div>

            <div className="writer-init-actions writer-init-actions--footer">
              <div className="writer-init-hint">
                Si no te convence, podés volver a editar la descripción o pedir otra síntesis.
              </div>
              <div className="writer-init-footer-buttons">
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => setPreview(null)}
                  disabled={creating}
                >
                  Editar descripción
                </button>
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={handleGenerate}
                  disabled={!hasDescription || generating || creating}
                >
                  {generating ? 'Regenerando...' : 'Regenerar'}
                </button>
                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={handleCreate}
                  disabled={creating}
                >
                  {creating ? 'Creando...' : 'Crear writer'}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
