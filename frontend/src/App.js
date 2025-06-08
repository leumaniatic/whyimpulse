import React, { useState } from "react";
import "./App.css";
import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const ImpulseSaver = () => {
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [analysis, setAnalysis] = useState(null);
  const [error, setError] = useState("");

  const analyzeProduct = async () => {
    if (!url.trim()) {
      setError("Please enter an Amazon URL");
      return;
    }

    if (!url.includes('amazon.')) {
      setError("Please enter a valid Amazon URL");
      return;
    }

    setLoading(true);
    setError("");
    setAnalysis(null);

    try {
      const response = await axios.post(`${API}/analyze`, {
        amazon_url: url
      });
      setAnalysis(response.data);
    } catch (error) {
      console.error('Analysis error:', error);
      setError(error.response?.data?.detail || "Failed to analyze product. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const getScoreColor = (score) => {
    if (score >= 80) return "text-red-600 bg-red-100";
    if (score >= 60) return "text-orange-600 bg-orange-100";
    if (score >= 40) return "text-yellow-600 bg-yellow-100";
    return "text-green-600 bg-green-100";
  };

  const getVerdictStyle = (verdict) => {
    const lower = verdict.toLowerCase();
    if (lower.includes('buy')) return "bg-green-500 text-white";
    if (lower.includes('wait')) return "bg-yellow-500 text-white";
    if (lower.includes('skip')) return "bg-red-500 text-white";
    return "bg-gray-500 text-white";
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-50 to-blue-50">
      {/* Header */}
      <div className="bg-white shadow-sm border-b">
        <div className="max-w-6xl mx-auto px-4 py-6">
          <div className="text-center">
            <h1 className="text-4xl font-bold text-gray-900 mb-2">
              💡 Impulse Saver
            </h1>
            <p className="text-lg text-gray-600">
              Smart Amazon purchase decisions powered by AI
            </p>
          </div>
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-4 py-8">
        {/* URL Input Section */}
        <div className="bg-white rounded-xl shadow-lg p-8 mb-8">
          <div className="text-center mb-6">
            <h2 className="text-2xl font-semibold text-gray-800 mb-2">
              Paste Amazon Product URL
            </h2>
            <p className="text-gray-600">
              Get instant AI-powered buying recommendations
            </p>
          </div>

          <div className="flex gap-4 max-w-2xl mx-auto">
            <input
              type="url"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://amazon.com/product-link..."
              className="flex-1 px-4 py-3 border-2 border-gray-200 rounded-lg focus:border-purple-500 focus:outline-none text-lg"
              onKeyPress={(e) => e.key === 'Enter' && analyzeProduct()}
            />
            <button
              onClick={analyzeProduct}
              disabled={loading}
              className="px-8 py-3 bg-purple-600 hover:bg-purple-700 disabled:bg-purple-400 text-white font-semibold rounded-lg transition-colors text-lg"
            >
              {loading ? "Analyzing..." : "Analyze"}
            </button>
          </div>

          {error && (
            <div className="mt-4 p-4 bg-red-100 border border-red-300 rounded-lg text-red-700 text-center">
              {error}
            </div>
          )}
        </div>

        {/* Loading State */}
        {loading && (
          <div className="bg-white rounded-xl shadow-lg p-8 text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600 mx-auto mb-4"></div>
            <p className="text-lg text-gray-600">Analyzing product with AI...</p>
            <p className="text-sm text-gray-500 mt-2">This may take a few seconds</p>
          </div>
        )}

        {/* Analysis Results */}
        {analysis && (
          <div className="space-y-6">
            {/* Product Overview */}
            <div className="bg-white rounded-xl shadow-lg p-6">
              <div className="flex flex-col md:flex-row gap-6">
                {analysis.product_data.image_url && (
                  <div className="md:w-48 flex-shrink-0">
                    <img
                      src={analysis.product_data.image_url}
                      alt="Product"
                      className="w-full h-48 object-contain rounded-lg bg-gray-50"
                    />
                  </div>
                )}
                <div className="flex-1">
                  <h3 className="text-xl font-semibold text-gray-900 mb-3">
                    {analysis.product_data.title}
                  </h3>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                    {analysis.product_data.price && (
                      <div>
                        <span className="text-gray-500">Price:</span>
                        <p className="font-semibold text-lg text-green-600">
                          {analysis.product_data.price}
                        </p>
                      </div>
                    )}
                    {analysis.product_data.rating && (
                      <div>
                        <span className="text-gray-500">Rating:</span>
                        <p className="font-semibold">
                          ⭐ {analysis.product_data.rating}
                        </p>
                      </div>
                    )}
                    {analysis.product_data.review_count && (
                      <div>
                        <span className="text-gray-500">Reviews:</span>
                        <p className="font-semibold">
                          {analysis.product_data.review_count}
                        </p>
                      </div>
                    )}
                    {analysis.product_data.availability && (
                      <div>
                        <span className="text-gray-500">Status:</span>
                        <p className="font-semibold text-green-600">
                          {analysis.product_data.availability}
                        </p>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>

            {/* Verdict & Impulse Score */}
            <div className="grid md:grid-cols-2 gap-6">
              <div className="bg-white rounded-xl shadow-lg p-6">
                <h4 className="text-lg font-semibold text-gray-800 mb-4">AI Verdict</h4>
                <div className={`inline-block px-4 py-2 rounded-full font-semibold text-lg ${getVerdictStyle(analysis.verdict)}`}>
                  {analysis.verdict}
                </div>
              </div>

              <div className="bg-white rounded-xl shadow-lg p-6">
                <h4 className="text-lg font-semibold text-gray-800 mb-4">Impulse Score</h4>
                <div className="flex items-center gap-4">
                  <div className={`text-3xl font-bold px-4 py-2 rounded-full ${getScoreColor(analysis.impulse_score)}`}>
                    {analysis.impulse_score}
                  </div>
                  <div className="flex-1">
                    <div className="w-full bg-gray-200 rounded-full h-3">
                      <div 
                        className="bg-gradient-to-r from-green-500 via-yellow-500 to-red-500 h-3 rounded-full transition-all duration-500"
                        style={{ width: `${analysis.impulse_score}%` }}
                      ></div>
                    </div>
                    <p className="text-sm text-gray-600 mt-1">
                      {analysis.impulse_score >= 80 ? "High impulse risk!" :
                       analysis.impulse_score >= 60 ? "Medium impulse" :
                       analysis.impulse_score >= 40 ? "Low impulse" : "Smart purchase"}
                    </p>
                  </div>
                </div>
              </div>
            </div>

            {/* Pros & Cons */}
            <div className="grid md:grid-cols-2 gap-6">
              <div className="bg-white rounded-xl shadow-lg p-6">
                <h4 className="text-lg font-semibold text-gray-800 mb-4 flex items-center">
                  <span className="text-green-500 mr-2">✅</span>
                  Pros
                </h4>
                <ul className="space-y-2">
                  {analysis.pros.map((pro, index) => (
                    <li key={index} className="flex items-start">
                      <span className="text-green-500 mr-2 mt-1">•</span>
                      <span className="text-gray-700">{pro}</span>
                    </li>
                  ))}
                </ul>
              </div>

              <div className="bg-white rounded-xl shadow-lg p-6">
                <h4 className="text-lg font-semibold text-gray-800 mb-4 flex items-center">
                  <span className="text-red-500 mr-2">❌</span>
                  Cons
                </h4>
                <ul className="space-y-2">
                  {analysis.cons.map((con, index) => (
                    <li key={index} className="flex items-start">
                      <span className="text-red-500 mr-2 mt-1">•</span>
                      <span className="text-gray-700">{con}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>

            {/* Recommendation */}
            <div className="bg-white rounded-xl shadow-lg p-6">
              <h4 className="text-lg font-semibold text-gray-800 mb-4">
                💡 AI Recommendation
              </h4>
              <p className="text-gray-700 leading-relaxed">
                {analysis.recommendation}
              </p>
            </div>

            {/* Action Button */}
            <div className="text-center">
              <button
                onClick={() => {
                  setUrl("");
                  setAnalysis(null);
                  setError("");
                }}
                className="px-8 py-3 bg-purple-600 hover:bg-purple-700 text-white font-semibold rounded-lg transition-colors"
              >
                Analyze Another Product
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Footer */}
      <footer className="bg-white border-t mt-16">
        <div className="max-w-6xl mx-auto px-4 py-8 text-center">
          <p className="text-gray-600">
            <span className="font-semibold">Impulse Saver</span> - Making smarter purchase decisions with AI
          </p>
          <p className="text-sm text-gray-500 mt-2">
            Analyze any Amazon product to get instant buying recommendations
          </p>
        </div>
      </footer>
    </div>
  );
};

function App() {
  return <ImpulseSaver />;
}

export default App;
