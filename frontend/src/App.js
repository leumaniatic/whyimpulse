import React, { useState } from "react";
import "./App.css";
import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const EnhancedImpulseSaver = () => {
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

  const getDealQualityColor = (quality) => {
    const colors = {
      'excellent': 'bg-green-500 text-white',
      'very good': 'bg-green-400 text-white',
      'good': 'bg-blue-500 text-white',
      'fair': 'bg-yellow-500 text-white',
      'poor': 'bg-red-500 text-white'
    };
    return colors[quality] || 'bg-gray-500 text-white';
  };

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD'
    }).format(amount);
  };

  const PriceHistoryChart = ({ priceHistory }) => {
    if (!priceHistory || priceHistory.length === 0) return null;

    const maxPrice = Math.max(...priceHistory.map(p => p.price));
    const minPrice = Math.min(...priceHistory.map(p => p.price));
    const priceRange = maxPrice - minPrice;

    return (
      <div className="bg-white rounded-xl shadow-lg p-6">
        <h4 className="text-lg font-semibold text-gray-800 mb-4">
          📈 Price History (Last 30 Data Points)
        </h4>
        <div className="h-32 relative border-2 border-gray-200 rounded-lg p-2">
          <svg className="w-full h-full">
            <polyline
              fill="none"
              stroke="#3b82f6"
              strokeWidth="2"
              points={priceHistory.map((point, index) => {
                const x = (index / (priceHistory.length - 1)) * 100;
                const y = 100 - ((point.price - minPrice) / priceRange) * 100;
                return `${x},${y}`;
              }).join(' ')}
            />
          </svg>
          <div className="absolute top-0 left-0 text-xs text-gray-600">
            {formatCurrency(maxPrice)}
          </div>
          <div className="absolute bottom-0 left-0 text-xs text-gray-600">
            {formatCurrency(minPrice)}
          </div>
        </div>
        <div className="flex justify-between mt-2 text-xs text-gray-500">
          <span>{priceHistory[0]?.date}</span>
          <span>{priceHistory[priceHistory.length - 1]?.date}</span>
        </div>
      </div>
    );
  };

  const ImpulseFactors = ({ impulseScore, impulseFactors }) => {
    const factors = [
      { key: 'price_manipulation', label: 'Price Manipulation', icon: '⚠️' },
      { key: 'scarcity_tactics', label: 'Scarcity Tactics', icon: '⏰' },
      { key: 'emotional_triggers', label: 'Emotional Language', icon: '💭' },
      { key: 'urgency_language', label: 'Urgency Words', icon: '🚨' },
      { key: 'deal_authenticity', label: 'Deal Authenticity', icon: '🔍' },
      { key: 'volatility_factor', label: 'Price Volatility', icon: '📊' }
    ];

    return (
      <div className="bg-white rounded-xl shadow-lg p-6">
        <h4 className="text-lg font-semibold text-gray-800 mb-4">
          🧠 Impulse Factor Breakdown
        </h4>
        <div className="space-y-3">
          {factors.map(factor => {
            const factorValue = impulseFactors[factor.key] || 0;
            const maxValue = 30; // Maximum value for any factor
            const percentage = (factorValue / maxValue) * 100;
            
            return (
              <div key={factor.key} className="flex items-center justify-between">
                <div className="flex items-center">
                  <span className="mr-2">{factor.icon}</span>
                  <span className="text-sm text-gray-700">{factor.label}</span>
                </div>
                <div className="flex items-center">
                  <div className="w-24 bg-gray-200 rounded-full h-2 mr-2">
                    <div 
                      className="bg-red-500 h-2 rounded-full transition-all duration-500"
                      style={{ width: `${Math.max(5, percentage)}%` }}
                    ></div>
                  </div>
                  <span className="text-sm font-semibold text-gray-600">
                    {factorValue}/{maxValue}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
        <div className="mt-4 p-3 bg-gray-50 rounded-lg">
          <div className="text-sm text-gray-600">
            <strong>Total Impulse Score: {impulseScore}/100</strong>
          </div>
          <div className="text-xs text-gray-500 mt-1">
            {impulseScore >= 80 ? "🚨 High manipulation risk - be very careful!" :
             impulseScore >= 60 ? "⚠️ Moderate manipulation detected" :
             impulseScore >= 40 ? "🟡 Some impulse triggers present" :
             "✅ Low manipulation risk"}
          </div>
        </div>
      </div>
    );
  };

  const AlternativesSection = ({ alternatives }) => {
    if (!alternatives || alternatives.length === 0) return null;

    return (
      <div className="bg-white rounded-xl shadow-lg p-6">
        <h4 className="text-lg font-semibold text-gray-800 mb-4">
          💡 Better Alternatives Found
        </h4>
        <div className="space-y-4">
          {alternatives.map((alt, index) => (
            <div key={index} className="border border-gray-200 rounded-lg p-4 hover:bg-gray-50 transition-colors">
              <div className="flex gap-4">
                {/* Product Image */}
                {alt.image_url && (
                  <div className="w-24 h-24 flex-shrink-0">
                    <img
                      src={alt.image_url}
                      alt={alt.title}
                      className="w-full h-full object-contain rounded-lg bg-gray-50"
                      onError={(e) => {
                        e.target.style.display = 'none';
                      }}
                    />
                  </div>
                )}
                
                <div className="flex justify-between items-start flex-1">
                  <div className="flex-1">
                    <h5 className="font-semibold text-gray-800 text-sm mb-2">
                      {alt.title.length > 80 ? alt.title.substring(0, 80) + '...' : alt.title}
                    </h5>
                    
                    {/* Price and Rating Row */}
                    <div className="flex items-center gap-4 text-sm text-gray-600 mb-2">
                      <span className="font-bold text-green-600 text-lg">
                        {formatCurrency(alt.price)}
                      </span>
                      {alt.rating && (
                        <span className="flex items-center">
                          <span className="text-yellow-500 mr-1">⭐</span>
                          <span className="font-medium">{alt.rating.toFixed(1)}/5</span>
                        </span>
                      )}
                      {alt.review_count && (
                        <span className="text-gray-500">
                          ({alt.review_count.toLocaleString()} reviews)
                        </span>
                      )}
                    </div>
                    
                    {/* Savings Information */}
                    <div className="mb-3">
                      <div className="bg-green-100 text-green-800 px-2 py-1 rounded-md text-sm font-semibold inline-block">
                        Save {formatCurrency(alt.savings)} ({alt.savings_percent}% off)
                      </div>
                    </div>
                    
                    {/* Why Better */}
                    <div className="text-xs text-gray-600 mb-3">
                      <span className="font-medium text-blue-600">Why this is better:</span> {alt.why_better}
                    </div>
                    
                    {/* Product ASIN */}
                    <div className="text-xs text-gray-400">
                      ASIN: {alt.asin}
                    </div>
                  </div>
                  
                  {/* Action Buttons */}
                  <div className="ml-4 flex flex-col gap-2">
                    <a 
                      href={alt.amazon_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-block bg-orange-500 hover:bg-orange-600 text-white px-4 py-2 rounded text-sm font-medium transition-colors text-center"
                    >
                      View on Amazon
                    </a>
                    <a 
                      href={alt.affiliate_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-block bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded text-sm font-medium transition-colors text-center"
                    >
                      Buy with Support
                    </a>
                  </div>
                </div>
              </div>
              
              {/* Comparison Highlight */}
              <div className="mt-3 pt-3 border-t border-gray-100">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-gray-500">Compared to original:</span>
                  <div className="flex items-center gap-4">
                    <span className="text-green-600 font-medium">
                      {alt.savings > 0 ? `${alt.savings_percent}% cheaper` : 'Similar price'}
                    </span>
                    {alt.rating && (
                      <span className="text-blue-600 font-medium">
                        {alt.rating >= 4.5 ? 'Excellent rating' : 
                         alt.rating >= 4.0 ? 'Very good rating' : 
                         alt.rating >= 3.5 ? 'Good rating' : 'Fair rating'}
                      </span>
                    )}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
        
        {/* Alternative Search Info */}
        <div className="mt-4 p-3 bg-blue-50 rounded-lg">
          <div className="text-sm text-blue-800">
            <span className="font-medium">💡 Smart Tip:</span> These alternatives are found based on similar features, 
            better ratings, or lower prices. "View on Amazon" shows the direct product page, while "Buy with Support" 
            includes our affiliate link to support the service.
          </div>
        </div>
      </div>
    );
  };

  const DealAnalysisCard = ({ dealAnalysis, inflationAnalysis }) => {
    return (
      <div className="bg-white rounded-xl shadow-lg p-6">
        <h4 className="text-lg font-semibold text-gray-800 mb-4">
          🏷️ Deal Intelligence
        </h4>
        
        {/* Deal Quality */}
        <div className="mb-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-gray-600">Deal Quality</span>
            <span className={`px-3 py-1 rounded-full text-sm font-semibold ${getDealQualityColor(dealAnalysis.quality)}`}>
              {dealAnalysis.quality.toUpperCase()}
            </span>
          </div>
          <div className="text-xs text-gray-500 mb-2">
            Score: {dealAnalysis.score}/100 • {dealAnalysis.analysis}
          </div>
        </div>

        {/* Price Statistics */}
        <div className="grid grid-cols-2 gap-4 mb-4">
          <div className="text-center p-3 bg-gray-50 rounded-lg">
            <div className="text-lg font-bold text-green-600">
              {formatCurrency(dealAnalysis.current_price)}
            </div>
            <div className="text-xs text-gray-500">Current Price</div>
          </div>
          <div className="text-center p-3 bg-gray-50 rounded-lg">
            <div className="text-lg font-bold text-gray-600">
              {formatCurrency(dealAnalysis.average_price)}
            </div>
            <div className="text-xs text-gray-500">Average Price</div>
          </div>
        </div>

        {/* Savings Indicator */}
        <div className="mb-4">
          <div className="flex justify-between text-sm mb-1">
            <span>Savings vs Average</span>
            <span className={`font-semibold ${dealAnalysis.savings_percent > 0 ? 'text-green-600' : 'text-red-600'}`}>
              {dealAnalysis.savings_percent > 0 ? '+' : ''}{dealAnalysis.savings_percent.toFixed(1)}%
            </span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div 
              className={`h-2 rounded-full transition-all duration-500 ${dealAnalysis.savings_percent > 0 ? 'bg-green-500' : 'bg-red-500'}`}
              style={{ width: `${Math.min(Math.abs(dealAnalysis.savings_percent), 50)}%` }}
            ></div>
          </div>
        </div>

        {/* Price Range */}
        <div className="text-xs text-gray-500 mb-4">
          <div className="flex justify-between">
            <span>Lowest: {formatCurrency(dealAnalysis.min_price)}</span>
            <span>Highest: {formatCurrency(dealAnalysis.max_price)}</span>
          </div>
          <div className="mt-1">
            Better than {(100 - dealAnalysis.percentile).toFixed(1)}% of historical prices
          </div>
        </div>

        {/* Inflation Warning */}
        {inflationAnalysis.inflation_detected && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-3">
            <div className="flex items-center mb-1">
              <span className="text-red-500 mr-2">⚠️</span>
              <span className="text-sm font-semibold text-red-800">Price Manipulation Detected</span>
            </div>
            <div className="text-xs text-red-700">
              {inflationAnalysis.analysis}
            </div>
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-50 to-blue-50">
      {/* Header */}
      <div className="bg-white shadow-sm border-b">
        <div className="max-w-6xl mx-auto px-4 py-6">
          <div className="text-center">
            <h1 className="text-4xl font-bold text-gray-900 mb-2">
              🧠 WHY IMPULSE?
            </h1>
            <p className="text-lg text-gray-600">
              AI-powered Amazon analysis with historical pricing & market intelligence
            </p>
          </div>
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-4 py-8">
        {/* URL Input Section */}
        <div className="bg-white rounded-xl shadow-lg p-8 mb-8">
          <div className="text-center mb-6">
            <h2 className="text-2xl font-semibold text-gray-800 mb-2">
              Analyze Amazon Product URL
            </h2>
            <p className="text-gray-600">
              Get comprehensive analysis with historical pricing, alternatives, and manipulation detection
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
            <p className="text-lg text-gray-600">Running comprehensive analysis...</p>
            <p className="text-sm text-gray-500 mt-2">
              Analyzing historical prices, detecting manipulation, finding alternatives...
            </p>
          </div>
        )}

        {/* Enhanced Analysis Results */}
        {analysis && (
          <div className="space-y-6">
            {/* Affiliate Disclosure */}
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 text-center">
              <p className="text-sm text-blue-800">
                <span className="font-medium">💡 Affiliate Disclosure:</span> WHY IMPULSE? may earn a commission from purchases made through our links. 
                This helps keep our service free while providing you with honest, data-driven recommendations.
              </p>
            </div>
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
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm mb-4">
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
                    <div>
                      <span className="text-gray-500">ASIN:</span>
                      <p className="font-semibold font-mono text-sm">
                        {analysis.asin}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-4">
                    <div className={`inline-block px-4 py-2 rounded-full font-semibold text-lg ${getVerdictStyle(analysis.verdict)}`}>
                      {analysis.verdict}
                    </div>
                    <div className="text-sm text-gray-600">
                      Confidence: {analysis.confidence_score}%
                    </div>
                  </div>
                  
                  {/* Affiliate Call-to-Action */}
                  <div className="mt-4 flex gap-3">
                    <a 
                      href={analysis.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-block bg-orange-500 hover:bg-orange-600 text-white px-6 py-2 rounded-lg font-medium transition-colors"
                    >
                      View on Amazon
                    </a>
                    <a 
                      href={analysis.affiliate_link}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-block bg-green-600 hover:bg-green-700 text-white px-6 py-2 rounded-lg font-medium transition-colors"
                    >
                      Buy Now (Support Us)
                    </a>
                  </div>
                </div>
              </div>
            </div>

            {/* Enhanced Analysis Grid */}
            <div className="grid lg:grid-cols-2 gap-6">
              {/* Deal Analysis */}
              <DealAnalysisCard 
                dealAnalysis={analysis.deal_analysis} 
                inflationAnalysis={analysis.inflation_analysis}
              />

              {/* Impulse Score */}
              <div className="bg-white rounded-xl shadow-lg p-6">
                <h4 className="text-lg font-semibold text-gray-800 mb-4">Impulse Risk Score</h4>
                <div className="flex items-center gap-4 mb-4">
                  <div className={`text-4xl font-bold px-6 py-4 rounded-full ${getScoreColor(analysis.impulse_score)}`}>
                    {analysis.impulse_score}
                  </div>
                  <div className="flex-1">
                    <div className="w-full bg-gray-200 rounded-full h-4">
                      <div 
                        className="bg-gradient-to-r from-green-500 via-yellow-500 to-red-500 h-4 rounded-full transition-all duration-500"
                        style={{ width: `${analysis.impulse_score}%` }}
                      ></div>
                    </div>
                    <p className="text-sm text-gray-600 mt-2">
                      {analysis.impulse_score >= 80 ? "🚨 High manipulation risk!" :
                       analysis.impulse_score >= 60 ? "⚠️ Moderate manipulation" :
                       analysis.impulse_score >= 40 ? "🟡 Some manipulation" : "✅ Low manipulation risk"}
                    </p>
                  </div>
                </div>
              </div>
            </div>

            {/* Price History Chart */}
            {analysis.price_history && analysis.price_history.length > 0 && (
              <PriceHistoryChart priceHistory={analysis.price_history} />
            )}

            {/* Impulse Factors Breakdown */}
            <ImpulseFactors 
              impulseScore={analysis.impulse_score} 
              impulseFactors={analysis.impulse_factors}
            />

            {/* Alternatives */}
            <AlternativesSection alternatives={analysis.alternatives} />

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

            {/* AI Recommendation */}
            <div className="bg-white rounded-xl shadow-lg p-6">
              <h4 className="text-lg font-semibold text-gray-800 mb-4">
                🤖 Expert AI Recommendation
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
            <span className="font-semibold">WHY IMPULSE?</span> - Advanced Amazon analysis with AI
          </p>
          <p className="text-sm text-gray-500 mt-2">
            Historical pricing • Manipulation detection • Smart alternatives • AI recommendations
          </p>
        </div>
      </footer>
    </div>
  );
};

function App() {
  return <EnhancedImpulseSaver />;
}

export default App;
