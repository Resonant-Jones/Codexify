type TruthMatrixRow = {
  control: string;
  uiPresent: boolean;
  localDraftState: boolean;
  savedLocally: boolean;
  backendPersisted: boolean;
  appliedToRuntime: boolean;
};

const TRUTH_MATRIX_BASE_TRUTH = {
  uiPresent: true,
  localDraftState: true,
  savedLocally: true,
  backendPersisted: false,
  appliedToRuntime: false,
} as const;

const TRUTH_MATRIX_CONTROLS = [
  "Persona Name",
  "Description",
  "Model Provider",
  "Model ID",
  "Temperature",
  "Generation Top K",
  "Top P",
  "Max Tokens",
  "Voice Enabled",
  "Voice Provider",
  "Voice Preset",
  "Wake Word",
  "Interruptible Voice",
  "System Prompt",
  "Style Notes",
  "Directives",
  "Pinned Tools",
  "Allowed Tools",
  "Skills",
  "Web Permission",
  "Email Permission",
  "Calendar Permission",
  "CLI Permission",
  "Filesystem Permission",
  "Retrieval Enabled",
  "Retrieval Mode",
  "Retrieval Top K",
  "Retrieval Rerank",
] as const;

const TRUTH_MATRIX_ROWS: TruthMatrixRow[] = TRUTH_MATRIX_CONTROLS.map((control) => ({
  control,
  ...TRUTH_MATRIX_BASE_TRUTH,
}));

function TruthValuePill({ value }: { value: boolean }) {
  return (
    <span
      className={`inline-flex min-w-[3rem] justify-center rounded-full border px-2 py-0.5 text-[10px] font-medium ${
        value
          ? "border-[rgba(34,197,94,0.35)] bg-[rgba(34,197,94,0.12)] text-[rgb(74,222,128)]"
          : "border-[var(--panel-border)] bg-transparent text-[var(--muted)]"
      }`}
    >
      {value ? "Yes" : "No"}
    </span>
  );
}

export default function TruthMatrix() {
  return (
    <div className="space-y-2">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h4 className="text-xs font-semibold text-[var(--muted)]">Truth Matrix</h4>
          <p className="text-[11px] leading-tight text-[var(--muted)]">
            Field-by-field implementation truth
          </p>
          <p className="text-[11px] leading-tight text-[var(--muted)]">
            Backend Persisted and Applied to Runtime remain No.
          </p>
        </div>
      </div>

      <div className="max-h-[280px] overflow-auto rounded-lg border border-[var(--panel-border)] bg-[rgba(0,0,0,0.12)]">
        <table
          aria-label="Persona Studio truth matrix"
          className="w-full table-fixed text-[11px]"
        >
          <colgroup>
            <col className="w-[30%]" />
            <col className="w-[14%]" />
            <col className="w-[14%]" />
            <col className="w-[14%]" />
            <col className="w-[14%]" />
            <col className="w-[14%]" />
          </colgroup>
          <thead className="sticky top-0 z-10 bg-[rgba(0,0,0,0.18)]">
            <tr>
              <th
                scope="col"
                className="px-2 py-2 text-left font-medium leading-tight text-[var(--muted)]"
              >
                Control
              </th>
              <th
                scope="col"
                className="px-2 py-2 text-left font-medium leading-tight text-[var(--muted)]"
              >
                UI Present
              </th>
              <th
                scope="col"
                className="px-2 py-2 text-left font-medium leading-tight text-[var(--muted)]"
              >
                Local Draft State
              </th>
              <th
                scope="col"
                className="px-2 py-2 text-left font-medium leading-tight text-[var(--muted)]"
              >
                Saved Locally
              </th>
              <th
                scope="col"
                className="px-2 py-2 text-left font-medium leading-tight text-[var(--muted)]"
              >
                Backend Persisted
              </th>
              <th
                scope="col"
                className="px-2 py-2 text-left font-medium leading-tight text-[var(--muted)]"
              >
                Applied to Runtime
              </th>
            </tr>
          </thead>
          <tbody>
            {TRUTH_MATRIX_ROWS.map((row, index) => (
              <tr
                key={row.control}
                className={`border-t border-[var(--panel-border)] ${
                  index % 2 === 0 ? "bg-transparent" : "bg-[rgba(255,255,255,0.02)]"
                }`}
              >
                <th
                  scope="row"
                  className="px-2 py-2 text-left font-medium leading-tight text-[var(--text)]"
                >
                  {row.control}
                </th>
                <td className="px-2 py-2">
                  <TruthValuePill value={row.uiPresent} />
                </td>
                <td className="px-2 py-2">
                  <TruthValuePill value={row.localDraftState} />
                </td>
                <td className="px-2 py-2">
                  <TruthValuePill value={row.savedLocally} />
                </td>
                <td className="px-2 py-2">
                  <TruthValuePill value={row.backendPersisted} />
                </td>
                <td className="px-2 py-2">
                  <TruthValuePill value={row.appliedToRuntime} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
