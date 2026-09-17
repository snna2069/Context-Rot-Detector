/** A small tag reinforcing that no classification produced by this system
 * is an independently verified fact. Used everywhere a hallucination
 * classification is shown, per the "never present probabilistic detector
 * output as absolute truth" requirement. */
export function NotVerifiedTag() {
  return (
    <span
      className="inline-flex items-center rounded-full border border-slate-300 bg-white px-2 py-0.5 text-[11px] font-medium text-slate-500"
      title="This classification is produced by automated evidence comparison. No independent fact-checking has occurred."
    >
      Not independently verified
    </span>
  );
}
