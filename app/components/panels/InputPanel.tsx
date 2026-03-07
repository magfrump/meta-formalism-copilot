import type { ArtifactType } from "@/app/lib/types/session";
import type { ArtifactLoadingState } from "@/app/hooks/useArtifactGeneration";
import FileUpload from "@/app/components/features/source-input/FileUpload";
import TextInput from "@/app/components/features/source-input/TextInput";
import FormalizationControls from "@/app/components/features/formalization-controls/FormalizationControls";

type InputPanelProps = {
  sourceText: string;
  onSourceTextChange: (value: string) => void;
  extractedFiles: { name: string; text: string }[];
  onFilesChanged: (files: { name: string; text: string }[]) => void;
  contextText: string;
  onContextTextChange: (value: string) => void;
  onFormalise: () => void;
  loading: boolean;
  /** Decompose source into proposition nodes */
  onDecompose?: () => void;
  decomposing?: boolean;
  /** Artifact type selection */
  selectedArtifactTypes: ArtifactType[];
  onArtifactTypesChange: (types: ArtifactType[]) => void;
  loadingState?: ArtifactLoadingState;
};

export default function InputPanel({
  sourceText,
  onSourceTextChange,
  extractedFiles,
  onFilesChanged,
  contextText,
  onContextTextChange,
  onFormalise,
  loading,
  onDecompose,
  decomposing = false,
  selectedArtifactTypes,
  onArtifactTypesChange,
  loadingState,
}: InputPanelProps) {
  return (
    <div className="relative flex h-full flex-col overflow-hidden bg-[var(--ivory-cream)]">
      {/* Top Section: Source Inputs */}
      <div className="flex min-h-0 flex-col overflow-hidden border-b border-[#DDD9D5]">
        <div className="border-b border-[#DDD9D5] bg-[#F5F1ED] px-4 py-2">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-[var(--ink-black)]">
            Source Inputs
          </h2>
        </div>
        <div className="flex min-h-0 flex-col gap-3 overflow-auto p-4">
          <TextInput value={sourceText} onChange={onSourceTextChange} />
          <FileUpload onFilesChanged={onFilesChanged} />

          {extractedFiles.length > 0 && (
            <section>
              <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-[#6B6560]">
                Uploaded Documents
              </h3>
              <ul className="space-y-1">
                {extractedFiles.map((f) => (
                  <li
                    key={f.name}
                    className="flex items-center gap-2 rounded-md border border-[#E8E4E0] bg-white px-3 py-2 text-sm text-[var(--ink-black)] shadow-sm"
                  >
                    <span className="text-green-600" aria-hidden>&#10003;</span>
                    <span className="truncate">{f.name}</span>
                    <span className="ml-auto shrink-0 text-[10px] text-[#9A9590]">
                      {f.text.length.toLocaleString()} chars
                    </span>
                  </li>
                ))}
              </ul>
            </section>
          )}

          {/* Decompose action */}
          {onDecompose && (
            <div className="pt-2">
              <button
                type="button"
                onClick={onDecompose}
                disabled={decomposing || loading}
                className="w-full rounded-full border border-[var(--ink-black)] bg-transparent px-6 py-2.5 text-sm font-medium text-[var(--ink-black)] shadow-sm transition-all duration-200 hover:bg-[var(--ink-black)] hover:text-white focus:outline-none focus:ring-2 focus:ring-[var(--ink-black)] focus:ring-offset-2 focus:ring-offset-[var(--ivory-cream)] disabled:opacity-50"
              >
                {decomposing ? "Decomposing..." : "Decompose into nodes"}
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Bottom Section: Context + Artifact Selection + Formalise */}
      <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
        <div className="border-b border-[#DDD9D5] bg-[#F5F1ED] px-4 py-2">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-[var(--ink-black)]">
            Direct Formalization
          </h2>
        </div>
        <FormalizationControls
          contextText={contextText}
          onContextChange={onContextTextChange}
          selectedArtifactTypes={selectedArtifactTypes}
          onArtifactTypesChange={onArtifactTypesChange}
          onGenerate={onFormalise}
          loading={loading}
          loadingState={loadingState}
        />
      </div>
    </div>
  );
}
