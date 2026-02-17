'use client';

import { useState } from 'react';
import { api } from '@/lib/api';

interface TagInputProps {
  problemId: number;
  tags: string[];
  onUpdate?: (tags: string[]) => void;
}

export function TagInput({ problemId, tags: initialTags, onUpdate }: TagInputProps) {
  const [tags, setTags] = useState<string[]>(initialTags);
  const [input, setInput] = useState('');
  const [saving, setSaving] = useState(false);

  const saveTags = async (newTags: string[]) => {
    setSaving(true);
    try {
      await api.updateTags(problemId, newTags);
      setTags(newTags);
      onUpdate?.(newTags);
    } catch (err) {
      console.error('Failed to update tags:', err);
    } finally {
      setSaving(false);
    }
  };

  const addTag = () => {
    const tag = input.trim().toLowerCase();
    if (!tag || tags.includes(tag)) {
      setInput('');
      return;
    }
    saveTags([...tags, tag]);
    setInput('');
  };

  const removeTag = (tagToRemove: string) => {
    saveTags(tags.filter((t) => t !== tagToRemove));
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      addTag();
    }
  };

  const TAG_COLORS = [
    'bg-cyan-500/20 text-cyan-700 dark:text-cyan-300',
    'bg-emerald-500/20 text-emerald-700 dark:text-emerald-300',
    'bg-indigo-500/20 text-indigo-700 dark:text-indigo-300',
    'bg-amber-500/20 text-amber-700 dark:text-amber-300',
    'bg-rose-500/20 text-rose-700 dark:text-rose-300',
    'bg-teal-500/20 text-teal-700 dark:text-teal-300',
  ];

  return (
    <div>
      <div className="flex flex-wrap gap-2 mb-2">
        {tags.map((tag, i) => (
          <span
            key={tag}
            className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium ${TAG_COLORS[i % TAG_COLORS.length]}`}
          >
            {tag}
            <button
              onClick={() => removeTag(tag)}
              className="ml-0.5 hover:opacity-70"
              title="Удалить тег"
            >
              x
            </button>
          </span>
        ))}
      </div>
      <div className="flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Добавить тег..."
          className="input-ui flex-1 text-sm"
          disabled={saving}
        />
        <button
          onClick={addTag}
          disabled={!input.trim() || saving}
          className="btn-secondary rounded-md px-3 py-1.5 text-sm font-semibold transition-colors disabled:opacity-50"
        >
          +
        </button>
      </div>
    </div>
  );
}
