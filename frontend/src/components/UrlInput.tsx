import { useRef, useState } from "react";

const ACCEPTED_FORMATS = ".mp3,.wav,.m4a,.ogg,.mp4,.webm,.mkv";

interface UrlInputProps {
  onSubmit: (url: string, language: string, file?: File) => void;
  disabled: boolean;
}

export function UrlInput({ onSubmit, disabled }: UrlInputProps) {
  const [url, setUrl] = useState("");
  const [language, setLanguage] = useState("ru");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (selectedFile) {
      onSubmit("", language, selectedFile);
    } else if (url.trim()) {
      onSubmit(url.trim(), language);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setSelectedFile(file);
      setUrl("");
    }
  };

  const clearFile = () => {
    setSelectedFile(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const canSubmit = selectedFile || url.trim();

  return (
    <form onSubmit={handleSubmit} className="url-input">
      <div className="input-group">
        {selectedFile ? (
          <div className="file-selected">
            <span className="file-name">{selectedFile.name}</span>
            <button
              type="button"
              className="file-clear"
              onClick={clearFile}
              disabled={disabled}
            >
              x
            </button>
          </div>
        ) : (
          <input
            type="url"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="YouTube video URL..."
            disabled={disabled}
          />
        )}
        <select
          value={language}
          onChange={(e) => setLanguage(e.target.value)}
          disabled={disabled}
        >
          <option value="ru">Russian</option>
          <option value="en">English</option>
          <option value="uk">Ukrainian</option>
        </select>
        <button type="submit" disabled={disabled || !canSubmit}>
          Analyze
        </button>
      </div>
      {!selectedFile && (
        <div className="file-upload-row">
          <button
            type="button"
            className="file-upload-btn"
            onClick={() => fileInputRef.current?.click()}
            disabled={disabled}
          >
            or upload a file
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept={ACCEPTED_FORMATS}
            onChange={handleFileChange}
            hidden
          />
        </div>
      )}
    </form>
  );
}
