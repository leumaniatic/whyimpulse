/* global chrome */

// Content script for Amazon pages
(function() {
    'use strict';
    
    // Configuration
    const API_BASE_URL = 'https://e581c80c-36c8-433f-9fe0-c7f8897a053a.preview.emergentagent.com/api';
    
    // Check if this is a product page
    function isProductPage() {
        return window.location.pathname.includes('/dp/') || 
               window.location.pathname.includes('/gp/product/') ||
               document.querySelector('#productTitle') !== null;
    }
    
    // Extract current product URL
    function getCurrentProductURL() {
        return window.location.href;
    }
    
    // Create floating analyze button
    function createAnalyzeButton() {
        const button = document.createElement('div');
        button.id = 'whyimpulse-analyze-btn';
        button.innerHTML = `
            <div class="whyimpulse-btn-content">
                <span class="whyimpulse-icon">🧠</span>
                <span class="whyimpulse-text">Analyze with WHY IMPULSE?</span>
            </div>
        `;
        
        button.addEventListener('click', () => {
            analyzeCurrentProduct();
        });
        
        return button;
    }
    
    // Create results panel
    function createResultsPanel() {
        const panel = document.createElement('div');
        panel.id = 'whyimpulse-results-panel';
        panel.style.display = 'none';
        return panel;
    }
    
    // Show analyze button if on product page
    function showAnalyzeButton() {
        if (!isProductPage()) return;
        
        // Remove existing button if present
        const existingButton = document.getElementById('whyimpulse-analyze-btn');
        if (existingButton) {
            existingButton.remove();
        }
        
        // Add new button
        const button = createAnalyzeButton();
        document.body.appendChild(button);
        
        // Add results panel
        const existingPanel = document.getElementById('whyimpulse-results-panel');
        if (!existingPanel) {
            const panel = createResultsPanel();
            document.body.appendChild(panel);
        }
    }
    
    // Analyze current product
    async function analyzeCurrentProduct() {
        const button = document.getElementById('whyimpulse-analyze-btn');
        const panel = document.getElementById('whyimpulse-results-panel');
        
        if (!button || !panel) return;
        
        // Show loading state
        button.innerHTML = `
            <div class="whyimpulse-btn-content loading">
                <span class="whyimpulse-spinner"></span>
                <span class="whyimpulse-text">Analyzing...</span>
            </div>
        `;
        button.style.pointerEvents = 'none';
        
        try {
            const response = await fetch(`${API_BASE_URL}/analyze`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ amazon_url: getCurrentProductURL() })
            });
            
            if (!response.ok) {
                throw new Error('Analysis failed');
            }
            
            const data = await response.json();
            showResults(data);
            
        } catch (error) {
            console.error('Analysis error:', error);
            showError('Analysis failed. Please try again.');
        } finally {
            // Reset button
            button.innerHTML = `
                <div class="whyimpulse-btn-content">
                    <span class="whyimpulse-icon">🧠</span>
                    <span class="whyimpulse-text">Analyze with WHY IMPULSE?</span>
                </div>
            `;
            button.style.pointerEvents = 'auto';
        }
    }
    
    // Show analysis results
    function showResults(data) {
        const panel = document.getElementById('whyimpulse-results-panel');
        if (!panel) return;
        
        const verdictClass = data.verdict.toLowerCase().includes('buy') ? 'buy' :
                            data.verdict.toLowerCase().includes('wait') ? 'wait' : 'skip';
        
        const scoreColor = data.impulse_score >= 80 ? '#f44336' :
                          data.impulse_score >= 60 ? '#ff9800' :
                          data.impulse_score >= 40 ? '#ffc107' : '#4caf50';
        
        panel.innerHTML = `
            <div class="whyimpulse-panel-header">
                <h3>🧠 WHY IMPULSE? Analysis</h3>
                <button class="whyimpulse-close-btn" onclick="this.parentElement.parentElement.style.display='none'">×</button>
            </div>
            <div class="whyimpulse-panel-content">
                <div class="whyimpulse-verdict ${verdictClass}">
                    ${data.verdict}
                </div>
                
                <div class="whyimpulse-score">
                    <div class="whyimpulse-score-label">
                        Impulse Score: <strong>${data.impulse_score}/100</strong>
                    </div>
                    <div class="whyimpulse-score-bar">
                        <div class="whyimpulse-score-fill" style="width: ${data.impulse_score}%; background: ${scoreColor}"></div>
                    </div>
                </div>
                
                ${data.deal_analysis ? `
                    <div class="whyimpulse-deal">
                        <strong>Deal Quality:</strong> ${data.deal_analysis.quality.toUpperCase()} (${data.deal_analysis.score}/100)
                    </div>
                ` : ''}
                
                <div class="whyimpulse-actions">
                    <a href="${data.affiliate_link}" target="_blank" class="whyimpulse-btn-buy">
                        🛒 Buy Now
                    </a>
                    <a href="https://e581c80c-36c8-433f-9fe0-c7f8897a053a.preview.emergentagent.com/?url=${encodeURIComponent(data.url)}" target="_blank" class="whyimpulse-btn-full">
                        📊 Full Analysis
                    </a>
                </div>
                
                ${data.alternatives && data.alternatives.length > 0 ? `
                    <div class="whyimpulse-alternatives">
                        <strong>💡 ${data.alternatives.length} better alternatives found!</strong>
                        <a href="https://e581c80c-36c8-433f-9fe0-c7f8897a053a.preview.emergentagent.com/?url=${encodeURIComponent(data.url)}" target="_blank">View All</a>
                    </div>
                ` : ''}
            </div>
        `;
        
        panel.style.display = 'block';
    }
    
    // Show error message
    function showError(message) {
        const panel = document.getElementById('whyimpulse-results-panel');
        if (!panel) return;
        
        panel.innerHTML = `
            <div class="whyimpulse-panel-header">
                <h3>🧠 WHY IMPULSE?</h3>
                <button class="whyimpulse-close-btn" onclick="this.parentElement.parentElement.style.display='none'">×</button>
            </div>
            <div class="whyimpulse-panel-content">
                <div class="whyimpulse-error">
                    ❌ ${message}
                </div>
            </div>
        `;
        
        panel.style.display = 'block';
    }
    
    // Initialize
    function init() {
        // Show button on page load
        showAnalyzeButton();
        
        // Re-show button when navigating (for SPA behavior)
        let lastUrl = location.href;
        new MutationObserver(() => {
            const url = location.href;
            if (url !== lastUrl) {
                lastUrl = url;
                setTimeout(showAnalyzeButton, 1000); // Delay to ensure page is loaded
            }
        }).observe(document, { subtree: true, childList: true });
    }
    
    // Start when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();