import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api.js";
import "./Upload_page.css";

export default function UploadPage() {
  const [file, setFile] = useState(null);
  const [url, setUrl] = useState("");
  const [language, setLanguage] = useState("auto");
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!file && !url.trim()) {
      setError("Provide either a file or a URL.");
      return;
    }
    setError(null);
    setIsUploading(true);
    try {
      const formData = new FormData();
      if (file) formData.append("file", file);
      if (url.trim()) formData.append("url", url.trim());
      formData.append("language", language);

      const meeting = await api.uploadMeeting(formData);
      navigate(`/meetings/${meeting.id}`);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="upload-page">
      <h1>Upload a meeting</h1>
      <p className="upload-subtitle">
        Upload a video/audio file or paste a URL to transcribe and chat with it later.
      </p>

      <form className="upload-form" onSubmit={handleSubmit}>
        <label className="upload-dropzone">
          <input
            type="file"
            accept="audio/*,video/*"
            onChange={(e) => setFile(e.target.files?.[0] || null)}
          />
          <span>{file ? file.name : "Click to select a file"}</span>
        </label>

        <div className="upload-divider">or</div>

        <input
          type="text"
          placeholder="Paste a video/audio URL"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          className="upload-input"
        />

        <div className="upload-field">
          <label htmlFor="language">Language</label>
          <select
            id="language"
            value={language}
            onChange={(e) => setLanguage(e.target.value)}
          >
            <option value="auto">Auto-detect</option>
            <option value="en">English</option>
            <option value="ur">Urdu</option>
            <option value="hi">Hindi</option>
          </select>
        </div>

        {error && <div className="upload-error">{error}</div>}

        <button type="submit" disabled={isUploading} className="upload-button">
          {isUploading ? "Uploading..." : "Upload & Process"}
        </button>
      </form>
    </div>
  );
}