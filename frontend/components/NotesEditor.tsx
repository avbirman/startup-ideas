'use client';

import { useState } from 'react';
import { api } from '@/lib/api';

interface NotesEditorProps {
  problemId: number;
  notes: string | null;
  onUpdate?: (notes: string) => void;
}

export function NotesEditor({ problemId, notes: initialNotes, onUpdate }: NotesEditorProps) {
  const [notes, setNotes] = useState(initialNotes || '');
  const [savedNotes, setSavedNotes] = useState(initialNotes || '');
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  const hasChanges = notes !== savedNotes;

  const handleSave = async () => {
    if (!hasChanges) return;
    setSaving(true);
    setSaved(false);
    try {
      await api.updateNotes(problemId, notes);
      setSavedNotes(notes);
      setSaved(true);
      onUpdate?.(notes);
      setTimeout(() => setSaved(false), 2000);
    } catch (err) {
      console.error('Failed to save notes:', err);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div>
      <textarea
        value={notes}
        onChange={(e) => setNotes(e.target.value)}
        placeholder="Добавьте заметки..."
        rows={4}
        className="input-ui w-full resize-y text-sm"
      />
      <div className="flex items-center justify-between mt-2">
        <div className="text-xs text-[var(--muted)]">
          {saved && <span className="text-emerald-600 dark:text-emerald-300">Сохранено</span>}
        </div>
        <button
          onClick={handleSave}
          disabled={!hasChanges || saving}
          className="btn-primary rounded-md px-4 py-1.5 text-sm font-semibold transition-colors disabled:opacity-50"
        >
          {saving ? 'Сохранение...' : 'Сохранить'}
        </button>
      </div>
    </div>
  );
}
