"use client";

interface ModelToggleProps {
  models: string[];
  selected: string[];
  onChange: (selected: string[]) => void;
}

export function ModelToggle({ models, selected, onChange }: ModelToggleProps) {
  function toggle(model: string) {
    if (selected.includes(model)) {
      onChange(selected.filter((m) => m !== model));
    } else {
      onChange([...selected, model]);
    }
  }

  if (models.length === 0) {
    return (
      <p className="text-sm text-gray-400 italic">
        No models found — is the backend running?
      </p>
    );
  }

  return (
    <div className="flex flex-wrap gap-2">
      {models.map((model) => {
        const active = selected.includes(model);
        return (
          <button
            key={model}
            type="button"
            onClick={() => toggle(model)}
            className={[
              "px-3 py-1.5 rounded-full text-sm font-medium border transition-colors",
              active
                ? "bg-indigo-600 border-indigo-600 text-white"
                : "bg-white border-gray-300 text-gray-700 hover:border-indigo-400 hover:text-indigo-600",
            ].join(" ")}
          >
            {model}
          </button>
        );
      })}
    </div>
  );
}
