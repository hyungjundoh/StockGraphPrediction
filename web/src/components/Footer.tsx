interface Props {
  llmEnabled: boolean;
}

export default function Footer({ llmEnabled }: Props) {
  return (
    <footer className="border-t bg-white text-xs text-slate-500 px-6 py-3 text-center space-y-1">
      <div>Analytical tool only. Not investment advice. Risk models can fail in regime changes.</div>
      {!llmEnabled && (
        <div>
          LLM features disabled. Set <code>ENABLE_LLM=true</code> and{' '}
          <code>ANTHROPIC_API_KEY</code> to enable scenario generation and briefings.
        </div>
      )}
    </footer>
  );
}
