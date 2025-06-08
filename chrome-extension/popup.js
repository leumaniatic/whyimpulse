/* global chrome */

// Configuration
const API_BASE_URL = 'https://e581c80c-36c8-433f-9fe0-c7f8897a053a.preview.emergentagent.com/api';
const WEB_APP_URL = 'https://e581c80c-36c8-433f-9fe0-c7f8897a053a.preview.emergentagent.com';

// DOM Elements
const pageStatus = document.getElementById('pageStatus');
const statusText = document.getElementById('statusText');
const analyzeCurrentBtn = document.getElementById('analyzeCurrentBtn');
const urlInput = document.getElementById('urlInput');
const analyzeManualBtn = document.getElementById('analyzeManualBtn');
const loadingSection = document.getElementById('loadingSection');
const resultsSection = document.getElementById('resultsSection');
const errorSection = document.getElementById('errorSection');

// State
let currentTabUrl = '';
let isAmazonPage = false;

// Initialize popup
document.addEventListener('DOMContentLoaded', async () => {
    await checkCurrentPage();
    setupEventListeners();
});

// Check if current page is Amazon
async function checkCurrentPage() {
    try {
        const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
        currentTabUrl = tab.url;
        
        if (isAmazonURL(currentTabUrl)) {
            isAmazonPage = true;
            pageStatus.classList.add('amazon');
            statusText.innerHTML = '<span class="amazon-detected">✅ Amazon Product Page Detected</span>';
            statusText.innerHTML += '<br><small>Click below to analyze this product</small>';
            analyzeCurrentBtn.disabled = false;
            analyzeCurrentBtn.textContent = '🛒 Analyze This Product';
        } else {
            isAmazonPage = false;
            statusText.innerHTML = '<span class="not-amazon">📄 Not on Amazon</span>';
            statusText.innerHTML += '<br><small>Navigate to Amazon or paste a URL below</small>';
            analyzeCurrentBtn.disabled = true;
            analyzeCurrentBtn.textContent = 'Visit Amazon First';
        }
    } catch (error) {
        console.error('Error checking current page:', error);
        statusText.innerHTML = '<span class="not-amazon">❌ Unable to check page</span>';
    }
}

// Setup event listeners
function setupEventListeners() {
    analyzeCurrentBtn.addEventListener('click', () => {
        if (isAmazonPage && currentTabUrl) {
            analyzeProduct(currentTabUrl);
        }
    });
    
    analyzeManualBtn.addEventListener('click', () => {
        const url = urlInput.value.trim();
        if (url) {
            analyzeProduct(url);
        } else {
            showError('Please enter an Amazon URL');
        }
    });
    
    urlInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            analyzeManualBtn.click();
        }
    });
}

// Check if URL is Amazon
function isAmazonURL(url) {
    const amazonDomains = [
        'amazon.com', 'amazon.co.uk', 'amazon.ca', 'amazon.de',
        'amazon.fr', 'amazon.it', 'amazon.es', 'a.co', 'amzn.to'
    ];
    return amazonDomains.some(domain => url.includes(domain));
}

// Analyze product
async function analyzeProduct(url) {
    if (!isAmazonURL(url)) {
        showError('Please provide a valid Amazon URL');
        return;
    }
    
    showLoading();
    hideError();
    hideResults();
    
    try {
        const response = await fetch(`${API_BASE_URL}/analyze`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ amazon_url: url })
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Analysis failed');
        }
        
        const data = await response.json();
        showResults(data);
    } catch (error) {
        console.error('Analysis error:', error);
        showError(`Analysis failed: ${error.message}`);
    } finally {
        hideLoading();
    }
}

// Show loading state
function showLoading() {
    loadingSection.style.display = 'block';
    resultsSection.style.display = 'none';
    errorSection.style.display = 'none';
}

// Hide loading state
function hideLoading() {
    loadingSection.style.display = 'none';
}

// Show results
function showResults(data) {
    hideLoading();
    hideError();
    
    const verdictClass = data.verdict.toLowerCase().includes('buy') ? 'buy' :
                        data.verdict.toLowerCase().includes('wait') ? 'wait' : 'skip';
    
    resultsSection.innerHTML = `
        <div class="result-card">
            <div class="product-title">${data.product_data.title}</div>
            
            <div class="verdict ${verdictClass}">
                ${data.verdict}
            </div>
            
            <div class="impulse-score">
                <div style="font-size: 12px; margin-bottom: 5px;">
                    <strong>Impulse Score: ${data.impulse_score}/100</strong>
                    <span style="color: ${getScoreColor(data.impulse_score)}">
                        ${getScoreText(data.impulse_score)}
                    </span>
                </div>
                <div class="score-bar">
                    <div class="score-fill" style="width: ${data.impulse_score}%"></div>
                </div>
            </div>
            
            ${data.deal_analysis ? `
                <div style="font-size: 12px; margin-bottom: 10px;">
                    <strong>Deal Quality:</strong> ${data.deal_analysis.quality.toUpperCase()} 
                    (${data.deal_analysis.score}/100)
                </div>
            ` : ''}
            
            ${data.alternatives && data.alternatives.length > 0 ? `
                <div style="font-size: 12px; margin-bottom: 10px;">
                    <strong>💡 ${data.alternatives.length} better alternatives found!</strong>
                </div>
            ` : ''}
            
            <div class="action-buttons">
                <a href="${data.affiliate_link}" target="_blank" class="btn btn-buy">
                    🛒 Buy Now
                </a>
                <a href="${WEB_APP_URL}?url=${encodeURIComponent(data.url)}" target="_blank" class="btn btn-full">
                    📊 Full Analysis
                </a>
            </div>
        </div>
    `;
    
    resultsSection.style.display = 'block';
}

// Show error
function showError(message) {
    errorSection.textContent = message;
    errorSection.style.display = 'block';
    hideLoading();
    hideResults();
}

// Hide error
function hideError() {
    errorSection.style.display = 'none';
}

// Hide results
function hideResults() {
    resultsSection.style.display = 'none';
}

// Get score color
function getScoreColor(score) {
    if (score >= 80) return '#f44336';
    if (score >= 60) return '#ff9800';
    if (score >= 40) return '#ffc107';
    return '#4caf50';
}

// Get score text
function getScoreText(score) {
    if (score >= 80) return '🚨 High Risk';
    if (score >= 60) return '⚠️ Medium Risk';
    if (score >= 40) return '🟡 Low Risk';
    return '✅ Safe Purchase';
}