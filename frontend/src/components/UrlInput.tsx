import { useRef, useState } from "react";

const ACCEPTED_FORMATS = ".mp3,.wav,.m4a,.ogg,.mp4,.webm,.mkv";

interface UrlInputProps {
  onSubmit: (file: File, language: string, gameContext: string) => void;
  disabled: boolean;
}

export function UrlInput({ onSubmit, disabled }: UrlInputProps) {
  const [language, setLanguage] = useState("ru");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [gameContext, setGameContext] = useState("");
  const [contextOpen, setContextOpen] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (selectedFile) {
      onSubmit(selectedFile, language, gameContext);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setSelectedFile(file);
    }
  };

  const clearFile = () => {
    setSelectedFile(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

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
          <button
            type="button"
            className="file-upload-btn"
            onClick={() => fileInputRef.current?.click()}
            disabled={disabled}
          >
            Choose audio file
          </button>
        )}
        <input
          ref={fileInputRef}
          type="file"
          accept={ACCEPTED_FORMATS}
          onChange={handleFileChange}
          hidden
        />
        <select
          value={language}
          onChange={(e) => setLanguage(e.target.value)}
          disabled={disabled}
        >
          <option value="ru">Russian</option>
          <option value="en">English</option>
          <option value="uk">Ukrainian</option>
        </select>
        <button type="submit" disabled={disabled || !selectedFile}>
          Analyze
        </button>
      </div>
      <div className="context-section">
        <button
          type="button"
          className="context-toggle"
          onClick={() => setContextOpen(!contextOpen)}
          disabled={disabled}
        >
          {contextOpen ? "Hide" : "Add"} game context (optional)
        </button>
        {contextOpen && (
          <textarea
            className="context-textarea"
            placeholder="Paste game moves, kills, voting results, role reveals, or any other context to improve the analysis..."
            value={gameContext}
            onChange={(e) => setGameContext(e.target.value)}
            disabled={disabled}
            rows={4}
          />
        )}
      </div>
    </form>
  );
}
