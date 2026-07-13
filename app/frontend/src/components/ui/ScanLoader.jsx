export const ScanLoader = ({
  label = "PROCESSING",
  testId,
}) => {
  return (
    <div data-testid={testId} className="border border-gray-200 bg-white">
      <div className="px-4 py-3 border-b border-gray-200 flex items-center justify-between">
        <span className="text-xs font-mono uppercase tracking-overline text-gray-500">
          {label}
        </span>

        <span className="text-xs font-mono text-klein">
          ▮ ACTIVE
        </span>
      </div>

      <div className="scan-line h-1 bg-gray-100" />

      <div className="p-6 font-mono text-xs text-gray-500 space-y-2">
        <div>&gt; Parsing input stream...</div>
        <div>&gt; Invoking AI inference...</div>
        <div>&gt; Composing structured output...</div>
      </div>
    </div>
  );
};