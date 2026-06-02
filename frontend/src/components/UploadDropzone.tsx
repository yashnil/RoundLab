"use client";

import { useRef } from "react";
import { Upload, FileAudio, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const ALLOWED_EXT = ["mp3", "wav", "m4a", "webm", "ogg", "mp4"];
const MAX_MB = 50;

interface UploadDropzoneProps {
  selectedFile: File | null;
  fileError: string;
  uploadError: string;
  uploading: boolean;
  onFileChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  onUpload: () => void;
  onClearFile: () => void;
}

export default function UploadDropzone({
  selectedFile, fileError, uploadError, uploading,
  onFileChange, onUpload, onClearFile,
}: UploadDropzoneProps) {
  const inputRef = useRef<HTMLInputElement>(null);

  return (
    <div className="flex flex-col gap-3">
      <label
        className={cn(
          "group flex cursor-pointer flex-col items-center gap-4 rounded-xl border-2 border-dashed p-10 text-center transition-all",
          selectedFile
            ? "border-lav/40 bg-lav/5"
            : "border-hairline-strong hover:border-lav/40 hover:bg-lav/[0.03]",
          uploading && "pointer-events-none opacity-50",
        )}
      >
        {selectedFile ? (
          <>
            <FileAudio size={24} className="text-lav" />
            <div className="flex flex-col gap-1">
              <span className="text-sm font-medium text-ink">{selectedFile.name}</span>
              <span className="text-xs text-ink-subtle">
                {(selectedFile.size / 1024 / 1024).toFixed(1)} MB
              </span>
            </div>
          </>
        ) : (
          <>
            <div className="flex h-10 w-10 items-center justify-center rounded-lg border border-hairline bg-surface-2 transition-colors group-hover:border-lav/30 group-hover:bg-lav/5">
              <Upload size={16} className="text-ink-subtle transition-colors group-hover:text-lav" />
            </div>
            <div className="flex flex-col gap-1">
              <span className="text-sm font-medium text-ink">Click to select an audio file</span>
              <span className="text-xs text-ink-subtle">
                {ALLOWED_EXT.join(", ")} · max {MAX_MB} MB
              </span>
            </div>
          </>
        )}
        <input
          ref={inputRef}
          type="file"
          accept={ALLOWED_EXT.map((e) => `.${e}`).join(",")}
          onChange={onFileChange}
          disabled={uploading}
          className="sr-only"
        />
      </label>

      {fileError   && <p className="text-xs text-danger">{fileError}</p>}
      {uploadError && <p className="text-xs text-danger">{uploadError}</p>}

      {selectedFile && (
        <div className="flex gap-2">
          <Button disabled={uploading} onClick={onUpload} size="sm" className="flex-1">
            {uploading ? "Uploading…" : "Upload Audio"}
          </Button>
          <Button variant="secondary" size="sm" disabled={uploading} onClick={onClearFile} className="gap-1.5">
            <X size={12} />
            Clear
          </Button>
        </div>
      )}
    </div>
  );
}
