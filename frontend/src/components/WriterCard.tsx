import { useNavigate } from 'react-router-dom';
import type { Writer } from '../types';
import { useWriterStore } from '../stores/writerStore';

interface WriterCardProps {
  writer: Writer;
}

export default function WriterCard({ writer }: WriterCardProps) {
  const navigate = useNavigate();
  const { deleteWriter } = useWriterStore();

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString();
  };

  const handleDelete = async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (window.confirm(`Delete writer "${writer.name}"?`)) {
      try {
        await deleteWriter(writer.id);
      } catch (err) {
        alert(err instanceof Error ? err.message : 'Failed to delete writer');
      }
    }
  };

  return (
    <div
      className="writer-card"
      onClick={() => navigate(`/writer/${writer.id}`)}
    >
      <div className="writer-card-header">
        <h3 className="writer-card-name">{writer.name}</h3>
        <button
          className="writer-card-delete"
          onClick={handleDelete}
          title="Delete writer"
        >
          x
        </button>
      </div>
      <p className="writer-card-purpose">{writer.purpose}</p>
      <div className="writer-card-footer">
        <span className="writer-card-date">
          Created {formatDate(writer.created_at)}
        </span>
      </div>
    </div>
  );
}
