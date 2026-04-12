"use client";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="text-center py-16">
      <p className="text-red-600 font-medium mb-2">Something went wrong</p>
      <p className="text-sm text-gray-500 mb-4">{error.message}</p>
      <button
        onClick={reset}
        className="px-4 py-2 text-sm bg-gray-900 text-white rounded hover:bg-gray-700"
      >
        Retry
      </button>
    </div>
  );
}
