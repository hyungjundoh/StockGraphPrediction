type Tone = 'normal' | 'amber' | 'red';

const toneClass: Record<Tone, string> = {
  normal: 'border-slate-200 bg-white',
  amber: 'border-amber-300 bg-amber-50',
  red: 'border-red-300 bg-red-50',
};

interface Props {
  label: string;
  value: string;
  tone?: Tone;
  hint?: string;
}

export default function MetricCard({ label, value, tone = 'normal', hint }: Props) {
  return (
    <div className={`border rounded-md p-3 ${toneClass[tone]}`}>
      <div className="text-[10px] uppercase tracking-wide text-slate-500">{label}</div>
      <div className="text-2xl font-semibold mt-1">{value}</div>
      {hint && <div className="text-xs text-slate-500 mt-1">{hint}</div>}
    </div>
  );
}
