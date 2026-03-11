import { useState } from "react";

interface UrlInputProps {
  onSubmit: (url: string, language: string) => void;
  disabled: boolean;
}

export function UrlInput({ onSubmit, disabled }: UrlInputProps) {
  const [url, setUrl] = useState("");
  const [language, setLanguage] = useState("ru");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (url.trim()) {
      onSubmit(url.trim(), language);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="url-input">
      <div className="input-group">
        <input
          type="url"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="YouTube video URL..."
          disabled={disabled}
          required
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
        <button type="submit" disabled={disabled || !url.trim()}>
          Analyze
        </button>
      </div>
    </form>
  );
}
