/* global chrome */

// Background script for WHY IMPULSE? Chrome Extension

// Handle extension installation
chrome.runtime.onInstalled.addListener((details) => {
    if (details.reason === 'install') {
        // Open welcome page on first install
        chrome.tabs.create({
            url: 'https://e581c80c-36c8-433f-9fe0-c7f8897a053a.preview.emergentagent.com/?welcome=extension'
        });
    }
});

// Handle extension icon click
chrome.action.onClicked.addListener((tab) => {
    // This will open the popup, but we can add additional logic here if needed
    console.log('WHY IMPULSE? extension clicked on tab:', tab.url);
});

// Listen for messages from content script
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === 'analyzeProduct') {
        // Forward to API or handle analysis request
        handleProductAnalysis(request.url, sendResponse);
        return true; // Keep message channel open for async response
    }
});

// Handle product analysis
async function handleProductAnalysis(url, sendResponse) {
    try {
        const response = await fetch('https://e581c80c-36c8-433f-9fe0-c7f8897a053a.preview.emergentagent.com/api/analyze', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ amazon_url: url })
        });
        
        if (!response.ok) {
            throw new Error('Analysis failed');
        }
        
        const data = await response.json();
        sendResponse({ success: true, data });
    } catch (error) {
        sendResponse({ success: false, error: error.message });
    }
}

// Update badge based on page
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
    if (changeInfo.status === 'complete' && tab.url) {
        const isAmazonPage = isAmazonURL(tab.url);
        
        if (isAmazonPage) {
            // Set badge to indicate Amazon page
            chrome.action.setBadgeText({
                text: '!',
                tabId: tabId
            });
            chrome.action.setBadgeBackgroundColor({
                color: '#ff9800',
                tabId: tabId
            });
            chrome.action.setTitle({
                title: 'WHY IMPULSE? - Analyze this Amazon product',
                tabId: tabId
            });
        } else {
            // Clear badge for non-Amazon pages
            chrome.action.setBadgeText({
                text: '',
                tabId: tabId
            });
            chrome.action.setTitle({
                title: 'WHY IMPULSE? - Smart Amazon Shopping',
                tabId: tabId
            });
        }
    }
});

// Helper function to check if URL is Amazon
function isAmazonURL(url) {
    const amazonDomains = [
        'amazon.com', 'amazon.co.uk', 'amazon.ca', 'amazon.de',
        'amazon.fr', 'amazon.it', 'amazon.es', 'a.co', 'amzn.to'
    ];
    return amazonDomains.some(domain => url.includes(domain));
}