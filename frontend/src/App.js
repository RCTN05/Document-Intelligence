import { useState } from "react";
import axios from "axios";

export default function App() {
  const [files, setFiles] = useState([]);
  const [uploadedFiles, setUploadedFiles] = useState([]);
  const [query, setQuery] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleFileChange = (e) => {
    setFiles(Array.from(e.target.files));
  };

  const handleUpload = async () => {
    if (files.length === 0) return alert("Select files first");

    const formData = new FormData();
    files.forEach((f) => formData.append("files", f));

    const res = await axios.post("https://document-intelligence-11.onrender.com/upload", formData);
    setUploadedFiles(res.data.files);
  };

  const handleProcess = async () => {
    if (!query.trim()) return alert("Enter query");

    setLoading(true);

    const res = await axios.post("https://document-intelligence-11.onrender.com/process", {
      files: uploadedFiles,
      query,
      persona: "Analyst",
    });

    setResult(res.data);
    setLoading(false);
  };

  return (
    <div className="flex h-screen bg-gray-100">

      {/* Sidebar */}
      <div className="w-1/4 bg-white border-r p-5 flex flex-col">
        <h2 className="text-2xl font-bold mb-4 text-blue-600">
          📄 Docs
        </h2>

        <input
          type="file"
          multiple
          onChange={handleFileChange}
          className="text-sm"
        />

        <button
          onClick={handleUpload}
          className="bg-blue-600 hover:bg-blue-700 transition text-white py-2 mt-3 rounded-lg shadow"
        >
          Upload Files
        </button>

        <div className="mt-6 flex-1 overflow-auto">
          <h3 className="text-sm font-semibold mb-2 text-gray-500">
            Uploaded
          </h3>

          {uploadedFiles.length === 0 && (
            <p className="text-gray-400 text-sm">No files yet</p>
          )}

          <ul className="space-y-2">
            {uploadedFiles.map((f, i) => (
              <li
                key={i}
                className="bg-gray-100 px-3 py-2 rounded-lg text-xs truncate"
              >
                📄 {f}
              </li>
            ))}
          </ul>
        </div>
      </div>

      {/* Main */}
      <div className="flex-1 p-6 overflow-auto">

        {/* Header */}
        <h1 className="text-3xl font-bold mb-6 text-gray-800">
          Document Intelligence
        </h1>

        {/* Query Box */}
        <div className="bg-white p-5 rounded-xl shadow mb-6">
          <h2 className="text-lg font-semibold mb-3">
            🔍 Ask your documents
          </h2>

          <div className="flex gap-3">
            <input
              className="border p-2 flex-1 rounded-lg"
              placeholder="e.g. tips for travel"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />

            <button
              onClick={handleProcess}
              className="bg-green-600 hover:bg-green-700 transition text-white px-5 rounded-lg"
            >
              Generate
            </button>
          </div>
        </div>

        {/* Loading */}
        {loading && (
          <p className="text-center text-gray-500">
            ⏳ Analyzing documents...
          </p>
        )}

        {/* Results */}
        {result && (
          <div>
            <h2 className="text-2xl font-bold mb-4">
              📊 Insights
            </h2>

            <div className="grid md:grid-cols-2 gap-4">
              {result.subsection_analysis.map((item, i) => {
                const sec = result.extracted_sections[i];

                return (
                  <div
                    key={i}
                    className="bg-white p-4 rounded-xl shadow hover:shadow-lg transition"
                  >
                    {/* Title */}
                    <h3 className="text-lg font-semibold text-blue-600">
                      {sec.section_title}
                    </h3>

                    {/* Meta */}
                    <div className="text-xs text-gray-500 mt-1">
                      📄 {item.document.split("_").slice(1).join("_")}  
                      | Page {item.page_number}
                    </div>

                    {/* Summary */}
                    <p className="mt-3 text-gray-700 text-sm leading-relaxed">
                      {item.refined_text}
                    </p>

                    {/* Score Bar */}
                    <div className="mt-4">
                      <div className="h-2 bg-gray-200 rounded">
                        <div className="h-2 bg-green-500 rounded w-4/5"></div>
                      </div>
                      <p className="text-xs text-gray-400 mt-1">
                        Relevance Score
                      </p>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
