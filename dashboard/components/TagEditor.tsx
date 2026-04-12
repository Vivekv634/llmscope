"use client";

import { useState } from "react";

interface TagEditorProps {
  runId: string;
  initialTags: string[];
}

export function TagEditor({ runId, initialTags }: TagEditorProps) {
  const [tags, setTags] = useState<string[]>(initialTags);
  const [input, setInput] = useState<string>("");
  const [saving, setSaving] = useState<boolean>(false);

  async function persist(next: string[]): Promise<void> {
    setSaving(true);
    try {
      await fetch(`http://localhost:8080/api/runs/${runId}/tags`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tags: next }),
      });
    } finally {
      setSaving(false);
    }
  }

  function addTag(): void {
    const trimmed = input.trim();
    if (!trimmed || tags.includes(trimmed)) {
      setInput("");
      return;
    }
    const next = [...tags, trimmed];
    setTags(next);
    setInput("");
    void persist(next);
  }

  function removeTag(tag: string): void {
    const next = tags.filter((t) => t !== tag);
    setTags(next);
    void persist(next);
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>): void {
    if (e.key === "Enter") {
      e.preventDefault();
      addTag();
    }
  }

  return (
    <div className="flex flex-wrap items-center gap-2">
      {tags.map((tag) => (
        <span
          key={tag}
          className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-indigo-100 text-indigo-700"
        >
          {tag}
          <button
            type="button"
            onClick={() => removeTag(tag)}
            className="hover:text-indigo-900 leading-none"
            aria-label={`Remove tag ${tag}`}
          >
            ×
          </button>
        </span>
      ))}
      <div className="flex items-center gap-1">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="add tag…"
          className="text-xs border border-gray-300 rounded px-2 py-1 w-24 focus:outline-none focus:ring-1 focus:ring-indigo-400"
        />
        <button
          type="button"
          onClick={addTag}
          disabled={saving}
          className="text-xs px-2 py-1 bg-indigo-600 text-white rounded hover:bg-indigo-700 disabled:opacity-40"
        >
          +
        </button>
      </div>
    </div>
  );
}
