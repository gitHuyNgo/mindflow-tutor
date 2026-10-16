import React, { useRef } from "react";
import { Upload, FileText, Loader2, X, AlertCircle, CheckCircle2 } from "lucide-react";
import type { DocFile, FileStatus } from "@/features/chat/types";

interface DocumentListPanelProps {
  files: DocFile[];
  onUpload: (e: React.ChangeEvent<HTMLInputElement>) => void;
  onRemove: (id: string) => void;
  className?: string;
}

const STATUS_ICONS: Record<FileStatus, { label: string; className: string }> = {
  uploading: { label: "Uploading...", className: "text-blue-400 bg-blue-500/10 border-blue-500/20" },
  processing: { label: "Indexing...", className: "text-amber-400 bg-amber-500/10 border-amber-500/20" },
  ready: { label: "Indexed", className: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20" },
  error: { label: "Failed", className: "text-rose-400 bg-rose-500/10 border-rose-500/20" },
};

export const DocumentListPanel: React.FC<DocumentListPanelProps> = ({
  files,
  onUpload,
  onRemove,
  className = "",
}) => {
  const inputRef = useRef<HTMLInputElement>(null);

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className={`flex flex-col h-full bg-card/40 backdrop-blur-md border-r border-border/60 ${className}`}>
      <div className="p-4 border-b border-border/50 flex items-center justify-between">
        <div>
          <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">Study Materials</h4>
          <p className="text-[11px] text-muted-foreground mt-0.5">PDF documents indexed for RAG</p>
        </div>
        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          className="px-3 py-1.5 rounded-lg bg-primary text-primary-foreground text-xs font-semibold hover:bg-primary/90 transition-colors flex items-center gap-1.5 shadow-xs"
        >
          <Upload className="w-3.5 h-3.5" />
          <span>Upload</span>
        </button>
        <input
          ref={inputRef}
          type="file"
          accept=".pdf"
          onChange={onUpload}
          className="hidden"
        />
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {files.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-48 text-center px-4 border border-dashed border-border/60 rounded-xl">
            <FileText className="w-8 h-8 text-muted-foreground/50 mb-2" />
            <p className="text-xs font-medium text-muted-foreground">No documents added yet</p>
            <p className="text-[11px] text-muted-foreground/70 mt-0.5">Upload textbook chapters or lecture slides</p>
          </div>
        ) : (
          files.map((file) => {
            const statusInfo = STATUS_ICONS[file.status];
            return (
              <div
                key={file.id}
                className="group p-2.5 rounded-xl bg-card/80 hover:bg-card border border-border/50 transition-all flex items-center justify-between gap-2 shadow-xs"
              >
                <div className="flex items-center gap-2.5 min-w-0">
                  <div className="p-1.5 rounded-lg bg-muted text-muted-foreground shrink-0">
                    <FileText className="w-4 h-4 text-primary" />
                  </div>
                  <div className="min-w-0">
                    <p className="text-xs font-medium truncate text-foreground">{file.name}</p>
                    <div className="flex items-center gap-2 mt-0.5">
                      <span className="text-[10px] text-muted-foreground">{formatSize(file.size)}</span>
                      <span
                        className={`text-[9px] px-1.5 py-0.5 rounded font-semibold border ${statusInfo.className}`}
                      >
                        {statusInfo.label}
                      </span>
                    </div>
                  </div>
                </div>

                <button
                  type="button"
                  onClick={() => onRemove(file.id)}
                  title="Remove document"
                  className="p-1 rounded-lg text-muted-foreground hover:text-rose-400 hover:bg-rose-500/10 transition-colors opacity-0 group-hover:opacity-100"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};

export default DocumentListPanel;
