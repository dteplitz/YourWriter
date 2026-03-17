import { useState } from 'react';

interface IterationInputProps {
  onIterate: (notes: string) => void;
  disabled?: boolean;
}

export default function IterationInput({ onIterate, disabled }: IterationInputProps) {
  const [notes, setNotes] = useState('');

  const handleSubmit = () => {
    if (disabled) return;
    onIterate(notes);
    setNotes('');
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="iteration-input">
      <div className="iteration-input-header">
        <span className="iteration-input-icon">✏</span>
        <span className="iteration-input-label">Producer notes</span>
      </div>
      <textarea
        className="iteration-input-textarea"
        value={notes}
        onChange={(e) => setNotes(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={'"más oscuro", "menos formal", "más corto"'}
        rows={2}
        disabled={disabled}
      />
      <div className="iteration-input-actions">
        <button
          className="btn btn-primary"
          onClick={handleSubmit}
          disabled={disabled}
        >
          Nuevo take
        </button>
      </div>
    </div>
  );
}
