import { useCallback, useState } from "react";

interface FileUploadProps {
  onFile: (file: File) => void;
  file: File | null;
}

export default function FileUpload({ onFile, file }: FileUploadProps) {
  const [dragging, setDragging] = useState(false);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragging(false);
      const f = e.dataTransfer.files[0];
      if (f && f.name.endsWith(".zip")) onFile(f);
    },
    [onFile]
  );

  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const f = e.target.files?.[0];
      if (f) onFile(f);
    },
    [onFile]
  );

  return (
    <label
      onDragOver={(e) => {
        e.preventDefault();
        setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={handleDrop}
      className={`
        block w-full border-2 border-dashed rounded-xl p-10 text-center cursor-pointer transition-all
        ${
          dragging
            ? "border-primary-500 bg-primary-500/10"
            : file
              ? "border-green-500/40 bg-green-500/5"
              : "border-gray-700 hover:border-gray-600 bg-gray-900/50"
        }
      `}
    >
      <input
        type="file"
        accept=".zip"
        onChange={handleChange}
        className="hidden"
      />
      {file ? (
        <div>
          <div className="text-3xl mb-2">📦</div>
          <p className="text-white font-medium">{file.name}</p>
          <p className="text-gray-400 text-sm mt-1">
            {(file.size / 1024 / 1024).toFixed(2)} MB — Click or drag to replace
          </p>
        </div>
      ) : (
        <div>
          <div className="text-3xl mb-2">☁️</div>
          <p className="text-gray-300 font-medium">
            Drag & drop your .zip file here
          </p>
          <p className="text-gray-500 text-sm mt-1">or click to browse</p>
        </div>
      )}
    </label>
  );
}
