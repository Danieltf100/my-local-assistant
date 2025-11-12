// DOM Elements
const messagesContainer = document.getElementById('messages-container');
const userInput = document.getElementById('user-input');
const chatForm = document.getElementById('chat-form');
const sendBtn = document.getElementById('send-btn');
const newChatBtn = document.getElementById('new-chat-btn');
const historyList = document.getElementById('history-list');
const settingsBtn = document.getElementById('settings-btn');
const settingsModal = document.getElementById('settings-modal');
const closeSettings = document.getElementById('close-settings');
const saveSettings = document.getElementById('save-settings');
const resetSettings = document.getElementById('reset-settings');
const themeToggle = document.getElementById('theme-toggle');
const currentChatTitle = document.getElementById('current-chat-title');

// File upload elements
const fileDropOverlay = document.getElementById('file-drop-overlay');
const fileDropZone = document.getElementById('file-drop-zone');
const fileInput = document.getElementById('file-input');
const filePreviewList = document.getElementById('file-preview-list');
const fileItems = document.getElementById('file-items');
const clearFilesBtn = document.getElementById('clear-files-btn');
const attachBtn = document.getElementById('attach-btn');
const fileCount = document.getElementById('file-count');
const fileCountText = document.getElementById('file-count-text');

// Settings elements
const temperatureSlider = document.getElementById('temperature');
const temperatureValue = document.getElementById('temperature-value');
const maxTokensSlider = document.getElementById('max-tokens');
const maxTokensValue = document.getElementById('max-tokens-value');
const topPSlider = document.getElementById('top-p');
const topPValue = document.getElementById('top-p-value');
const topKSlider = document.getElementById('top-k');
const topKValue = document.getElementById('top-k-value');
const streamingCheckbox = document.getElementById('streaming');
const saveHistoryCheckbox = document.getElementById('save-history');
const systemPromptTextarea = document.getElementById('system-prompt');
const resetSystemPromptBtn = document.getElementById('reset-system-prompt');

// State
let currentChatId = generateId();
let conversations = {};
let isGenerating = false;
let currentController = null;
let attachedFiles = [];

// Default settings
const defaultSettings = {
    temperature: 0.7,
    maxTokens: 100,
    topP: 0.9,
    topK: 50,
    streaming: true,
    saveHistory: true,
    systemPrompt: '' // Empty means use default with function calling
};

// Current settings
let settings = { ...defaultSettings };

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadSettings();
    loadConversations();
    setupEventListeners();
    adjustTextareaHeight();
});

// Setup event listeners
function setupEventListeners() {
    // Chat form submission
    chatForm.addEventListener('submit', handleSubmit);
    
    // Auto-resize textarea
    userInput.addEventListener('input', adjustTextareaHeight);
    
    // Enter key handling
    userInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            if (userInput.value.trim()) {
                chatForm.dispatchEvent(new Event('submit'));
            }
        }
    });
    
    // New chat button
    newChatBtn.addEventListener('click', startNewChat);
    
    // Settings modal
    settingsBtn.addEventListener('click', () => settingsModal.classList.add('active'));
    closeSettings.addEventListener('click', () => settingsModal.classList.remove('active'));
    
    // Save settings
    saveSettings.addEventListener('click', () => {
        saveCurrentSettings();
        settingsModal.classList.remove('active');
    });
    
    // Reset settings
    resetSettings.addEventListener('click', resetToDefaultSettings);
    
    // Reset system prompt
    resetSystemPromptBtn.addEventListener('click', () => {
        systemPromptTextarea.value = '';
        settings.systemPrompt = '';
    });
    
    // Theme toggle
    themeToggle.addEventListener('click', toggleTheme);
    
    // Settings sliders
    setupSliders();
    
    // File upload event listeners
    setupFileUploadListeners();
}

// Handle form submission
async function handleSubmit(e) {
    e.preventDefault();
    
    const message = userInput.value.trim();
    if (!message || isGenerating) return;
    
    // Clear input and adjust height
    userInput.value = '';
    adjustTextareaHeight();
    
    // Add user message to UI
    addMessageToUI('user', message);
    
    // Save to conversation
    if (!conversations[currentChatId]) {
        conversations[currentChatId] = {
            id: currentChatId,
            title: 'New Conversation', // Temporary title
            messages: []
        };
        
        // Generate title asynchronously
        generateTitle(message).then(title => {
            conversations[currentChatId].title = title;
            updateChatHistory();
        });
    }
    
    conversations[currentChatId].messages.push({
        role: 'user',
        content: message,
        timestamp: new Date().toISOString()
    });
    
    // Update chat history if this is the first message
    if (conversations[currentChatId].messages.length === 1) {
        updateChatHistory();
    }
    
    // Save conversations if enabled
    if (settings.saveHistory) {
        saveConversations();
    }
    
    // Check if files are attached
    if (attachedFiles.length > 0) {
        // Update file statuses to processing
        attachedFiles.forEach(file => {
            updateFileStatus(file.name, 'processing');
        });
        
        // Generate response with files
        await generateResponseWithFiles(message);
        
        // Clear attached files after successful submission
        clearAllFiles();
    } else {
        // Generate response without files
        await generateResponse();
    }
}

// Custom error classes for better error handling
class APIError extends Error {
    constructor(message, status) {
        super(message);
        this.name = 'APIError';
        this.status = status;
    }
}

class StreamError extends Error {
    constructor(message, originalError) {
        super(message);
        this.name = 'StreamError';
        this.originalError = originalError;
    }
}

// Prepare request data for API call
function prepareRequestData() {
    const messages = conversations[currentChatId].messages.map(msg => ({
        role: msg.role,
        content: msg.content,
        ...(msg.name && { name: msg.name }) // Include name for function messages
    }));
    
    const requestData = {
        messages,
        max_tokens: settings.maxTokens,
        temperature: settings.temperature,
        top_p: settings.topP,
        top_k: settings.topK
    };
    
    // Add custom system prompt if set
    if (settings.systemPrompt && settings.systemPrompt.trim()) {
        requestData.system_prompt = settings.systemPrompt.trim();
    }
    
    return requestData;
}

// Update message UI with markdown rendering and syntax highlighting
function updateMessageUI(messageTextElement, responseText) {
    messageTextElement.innerHTML = marked.parse(responseText);
    highlightCode(messageTextElement);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

// Parse stream buffer and extract tokens from JSON chunks
function parseStreamBuffer(buffer, isFirstChunk) {
    const tokens = [];
    let updatedBuffer = buffer;
    let stillFirstChunk = isFirstChunk;
    
    try {
        // Handle first chunk - remove JSON opening and find the choices array
        if (stillFirstChunk && updatedBuffer.includes('{"id":') && updatedBuffer.includes('"choices": [')) {
            stillFirstChunk = false;
            const choicesStart = updatedBuffer.indexOf('"choices": [') + '"choices": ['.length;
            updatedBuffer = updatedBuffer.substring(choicesStart);
        }
        
        // Process complete JSON objects in the buffer
        // We need to find complete JSON objects by counting braces
        while (updatedBuffer.length > 0) {
            // Skip leading whitespace and commas
            updatedBuffer = updatedBuffer.trimStart();
            if (updatedBuffer.startsWith(',')) {
                updatedBuffer = updatedBuffer.substring(1).trimStart();
            }
            
            // Check if we're at the end of the choices array
            if (updatedBuffer.startsWith(']')) {
                // Stream is complete
                break;
            }
            
            // Find the start of a JSON object
            if (!updatedBuffer.startsWith('{')) {
                // No JSON object starts here, wait for more data
                break;
            }
            
            // Find the matching closing brace
            let braceCount = 0;
            let endPos = -1;
            let inString = false;
            let escapeNext = false;
            
            for (let i = 0; i < updatedBuffer.length; i++) {
                const char = updatedBuffer[i];
                
                if (escapeNext) {
                    escapeNext = false;
                    continue;
                }
                
                if (char === '\\') {
                    escapeNext = true;
                    continue;
                }
                
                if (char === '"') {
                    inString = !inString;
                    continue;
                }
                
                if (!inString) {
                    if (char === '{') {
                        braceCount++;
                    } else if (char === '}') {
                        braceCount--;
                        if (braceCount === 0) {
                            endPos = i + 1;
                            break;
                        }
                    }
                }
            }
            
            // If we didn't find a complete JSON object, wait for more data
            if (endPos === -1) {
                break;
            }
            
            // Extract and parse the JSON object
            const jsonStr = updatedBuffer.substring(0, endPos);
            
            try {
                const data = JSON.parse(jsonStr);
                if (data.delta?.content) {
                    tokens.push(data.delta.content);
                }
            } catch (e) {
                console.log('Error parsing JSON:', e.message, 'JSON:', jsonStr.substring(0, 100));
            }
            
            // Remove processed part from buffer
            updatedBuffer = updatedBuffer.substring(endPos);
        }
    } catch (e) {
        console.log('Error in parseStreamBuffer:', e);
    }
    
    return { updatedBuffer, tokens, isFirstChunk: stillFirstChunk };
}

// Helper function to detect function calls in text
function detectFunctionCall(text) {
    const functionCallRegex = /<function_call>([\s\S]*?)<\/function_call>/;
    const match = text.match(functionCallRegex);
    
    if (match) {
        const beforeCall = text.substring(0, match.index);
        const functionCallJson = match[1].trim();
        const afterCall = text.substring(match.index + match[0].length);
        
        try {
            const functionCall = JSON.parse(functionCallJson);
            return {
                found: true,
                beforeCall: beforeCall.trim(),
                functionCall: functionCall,
                afterCall: afterCall.trim(),
                fullMatch: match[0]
            };
        } catch (e) {
            console.error('Error parsing function call JSON:', e);
            return { found: false };
        }
    }
    
    return { found: false };
}

// Execute a function call
async function executeFunction(functionName, functionArgs) {
    try {
        const response = await fetch('/api/execute_function', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                function_name: functionName,
                arguments: functionArgs
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const result = await response.json();
        return result;
    } catch (error) {
        console.error('Error executing function:', error);
        return {
            success: false,
            error: error.message
        };
    }
}

// Helper function to animate text character by character
async function animateText(text, messageTextElement, currentText, delay = 20) {
    let displayText = currentText;
    
    for (let i = 0; i < text.length; i++) {
        displayText += text[i];
        updateMessageUI(messageTextElement, displayText);
        
        // Add a small delay between characters for smooth animation
        if (delay > 0) {
            await new Promise(resolve => setTimeout(resolve, delay));
        }
    }
    
    return displayText;
}

// Process stream chunks and update UI in real-time with typewriter effect and function calling
async function processStreamChunks(readableStream, messageTextElement) {
    const reader = readableStream.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let responseText = '';
    let isFirstChunk = true;
    let pendingTokens = [];
    let isAnimating = false;
    let reasoningIndicator = null;
    
    // Function to process pending tokens with animation
    async function processPendingTokens() {
        if (isAnimating || pendingTokens.length === 0) return;
        
        isAnimating = true;
        while (pendingTokens.length > 0) {
            const token = pendingTokens.shift();
            responseText = await animateText(token, messageTextElement, responseText, 20);
            
            // Check for function calls in the accumulated response
            const functionCallDetection = detectFunctionCall(responseText);
            if (functionCallDetection.found) {
                // Stop animation and handle function call
                pendingTokens = []; // Clear remaining tokens
                break;
            }
        }
        isAnimating = false;
    }
    
    try {
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            
            // Decode chunk and add to buffer
            buffer += decoder.decode(value);
            
            // Parse buffer and extract tokens
            const result = parseStreamBuffer(buffer, isFirstChunk);
            buffer = result.updatedBuffer;
            isFirstChunk = result.isFirstChunk;
            
            // Add tokens to pending queue
            if (result.tokens.length > 0) {
                pendingTokens.push(...result.tokens);
                // Start processing if not already animating
                if (!isAnimating) {
                    await processPendingTokens();
                }
            }
            
            // Check if we detected a function call
            const functionCallDetection = detectFunctionCall(responseText);
            if (functionCallDetection.found) {
                // Show reasoning text if any
                if (functionCallDetection.beforeCall) {
                    updateMessageUI(messageTextElement, functionCallDetection.beforeCall);
                }
                
                // Show reasoning indicator
                reasoningIndicator = addReasoningIndicator();
                
                // Execute the function
                const functionCallUI = addFunctionCallUI(
                    functionCallDetection.functionCall.name,
                    functionCallDetection.functionCall.arguments
                );
                
                const functionResult = await executeFunction(
                    functionCallDetection.functionCall.name,
                    functionCallDetection.functionCall.arguments
                );
                
                // Update function call UI with result
                updateFunctionCallResult(functionCallUI, functionResult);
                
                // Remove reasoning indicator
                if (reasoningIndicator) {
                    removeReasoningIndicator();
                }
                
                // Don't save "Calling function..." message - it's just UI feedback
                // Add function result as a function message to conversation
                const functionResultText = JSON.stringify(functionResult, null, 2);
                conversations[currentChatId].messages.push({
                    role: 'function',
                    name: functionCallDetection.functionCall.name,
                    content: functionResultText,
                    timestamp: new Date().toISOString()
                });
                
                // Save conversations
                if (settings.saveHistory) {
                    saveConversations();
                }
                
                // Now make another API call to get the model's response based on the function result
                // Show typing indicator for the follow-up response
                showTypingIndicator();
                
                // Prepare request with updated conversation including function result
                const followUpRequestData = prepareRequestData();
                
                // Create new message element for the follow-up response
                removeTypingIndicator();
                const followUpMessageElement = addMessageToUI('assistant', '');
                const followUpMessageText = followUpMessageElement.querySelector('.message-text');
                
                // Make streaming request for follow-up response
                const followUpResponse = await fetch('/v1/stream', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(followUpRequestData)
                });
                
                if (!followUpResponse.ok) {
                    throw new APIError(`HTTP error! status: ${followUpResponse.status}`, followUpResponse.status);
                }
                
                // Process the follow-up stream recursively
                const followUpText = await processStreamChunks(followUpResponse.body, followUpMessageText);
                
                // Add glow effect when streaming completes
                followUpMessageElement.classList.add('stream-complete');
                setTimeout(() => {
                    followUpMessageElement.classList.remove('stream-complete');
                }, 1500);
                
                // Return the follow-up text (will be saved by caller)
                return followUpText;
            }
        }
        
        // Wait for any remaining animations to complete
        while (isAnimating || pendingTokens.length > 0) {
            await new Promise(resolve => setTimeout(resolve, 50));
            if (!isAnimating && pendingTokens.length > 0) {
                await processPendingTokens();
            }
        }
        
        // Clean up reasoning indicator if still present
        if (reasoningIndicator) {
            removeReasoningIndicator();
        }
        
    } catch (error) {
        if (reasoningIndicator) {
            removeReasoningIndicator();
        }
        throw new StreamError('Error processing stream chunks', error);
    }
    
    return responseText;
}

// Handle streaming response from API
async function handleStreamingResponse(requestData, signal) {
    const response = await fetch('/v1/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestData),
        signal
    });
    
    if (!response.ok) {
        throw new APIError(`HTTP error! status: ${response.status}`, response.status);
    }
    
    // Remove typing indicator and create message container
    removeTypingIndicator();
    const messageElement = addMessageToUI('assistant', '');
    const messageText = messageElement.querySelector('.message-text');
    
    // Process stream and return complete response
    const responseText = await processStreamChunks(response.body, messageText);
    
    // Add glow effect when streaming completes
    messageElement.classList.add('stream-complete');
    
    // Remove the class after animation completes to allow it to be triggered again
    setTimeout(() => {
        messageElement.classList.remove('stream-complete');
    }, 1500);
    
    return responseText;
}

// Handle non-streaming response from API
async function handleNonStreamingResponse(requestData, signal) {
    const response = await fetch('/v1/chat/completions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestData),
        signal
    });
    
    if (!response.ok) {
        throw new APIError(`HTTP error! status: ${response.status}`, response.status);
    }
    
    const data = await response.json();
    const responseText = data.choices[0].message.content;
    
    // Remove typing indicator and add complete message
    removeTypingIndicator();
    addMessageToUI('assistant', responseText);
    
    return responseText;
}

// Generate and update conversation title
function generateAndUpdateTitle() {
    console.log('Generating title for first exchange...');
    const firstMessage = conversations[currentChatId].messages[0].content;
    
    generateTitle(firstMessage).then(title => {
        console.log('Generated title:', title);
        conversations[currentChatId].title = title;
        currentChatTitle.textContent = title;
        updateChatHistory();
        
        if (settings.saveHistory) {
            saveConversations();
        }
    });
}

// Save assistant response to conversation history
function saveResponseToConversation(responseText) {
    console.log('Saving response to chat history:', responseText.substring(0, 100) + '...');
    
    conversations[currentChatId].messages.push({
        role: 'assistant',
        content: responseText,
        timestamp: new Date().toISOString()
    });
    
    if (settings.saveHistory) {
        saveConversations();
        console.log('Chat history saved to localStorage');
    }
    
    // Generate title after first user message gets a response
    // Count only user and assistant messages (not function messages)
    const userAssistantMessages = conversations[currentChatId].messages.filter(
        msg => msg.role === 'user' || msg.role === 'assistant'
    );
    
    // Generate title after first complete exchange (1 user + 1 assistant)
    if (userAssistantMessages.length === 2 && conversations[currentChatId].title === 'New Conversation') {
        generateAndUpdateTitle();
    }
}

// Handle errors during response generation
function handleGenerationError(error) {
    console.log('---------------------');
    console.log(error);
    console.log('---------------------');
    
    // Don't show error message for user-initiated cancellations
    if (error.name === 'AbortError') {
        console.log('Request aborted by user');
        return;
    }
    
    console.error('Error generating response:', error);
    removeTypingIndicator();
    
    // Provide specific error messages based on error type
    let errorMessage = 'An error occurred while generating a response. Please try again.';
    
    if (error instanceof APIError) {
        errorMessage = `Server error (${error.status}): Unable to generate response. Please try again.`;
    } else if (error instanceof StreamError) {
        errorMessage = 'Error processing response stream. Please try again.';
    }
    
    addErrorMessage(errorMessage);
}

// Generate AI response
async function generateResponse() {
    try {
        isGenerating = true;
        showTypingIndicator();
        
        const requestData = prepareRequestData();
        currentController = new AbortController();
        
        // Handle streaming or non-streaming based on settings
        const responseText = settings.streaming
            ? await handleStreamingResponse(requestData, currentController.signal)
            : await handleNonStreamingResponse(requestData, currentController.signal);
        
        saveResponseToConversation(responseText);
        
    } catch (error) {
        handleGenerationError(error);
    } finally {
        isGenerating = false;
        currentController = null;
    }
}

// Generate AI response with file uploads
async function generateResponseWithFiles(prompt) {
    try {
        isGenerating = true;
        showTypingIndicator();
        
        // Create FormData for file upload
        const formData = new FormData();
        formData.append('prompt', prompt);
        formData.append('max_tokens', settings.maxTokens);
        formData.append('temperature', settings.temperature);
        formData.append('top_p', settings.topP);
        formData.append('top_k', settings.topK);
        
        // Add system prompt if set
        if (settings.systemPrompt && settings.systemPrompt.trim()) {
            formData.append('system_prompt', settings.systemPrompt.trim());
        }
        
        // Add all attached files
        attachedFiles.forEach(file => {
            formData.append('files', file);
        });
        
        currentController = new AbortController();
        
        // Send request to file upload endpoint
        const response = await fetch('/v1/chat/upload', {
            method: 'POST',
            body: formData,
            signal: currentController.signal
        });
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new APIError(
                errorData.detail || `HTTP error! status: ${response.status}`,
                response.status
            );
        }
        
        const data = await response.json();
        
        console.log('File upload response:', data);
        
        // Update file statuses to success
        attachedFiles.forEach(file => {
            updateFileStatus(file.name, 'success');
        });
        
        // Extract response text - handle different response structures
        let responseText;
        if (data.choices && data.choices[0] && data.choices[0].message) {
            responseText = data.choices[0].message.content;
        } else if (data.response) {
            responseText = data.response;
        } else if (data.content) {
            responseText = data.content;
        } else if (typeof data === 'string') {
            responseText = data;
        } else {
            throw new Error('Unexpected response format from server');
        }
        
        // Remove typing indicator and add complete message
        removeTypingIndicator();
        addMessageToUI('assistant', responseText);
        
        // Save response to conversation
        saveResponseToConversation(responseText);
        
        // Log file processing info if available
        if (data.file_processing_info) {
            console.log('File processing info:', data.file_processing_info);
        }
        
    } catch (error) {
        // Update file statuses to error
        attachedFiles.forEach(file => {
            updateFileStatus(file.name, 'error');
        });
        
        handleGenerationError(error);
    } finally {
        isGenerating = false;
        currentController = null;
    }
}

// Add reasoning indicator
function addReasoningIndicator() {
    const reasoning = document.createElement('div');
    reasoning.className = 'message assistant-message reasoning-message';
    reasoning.id = 'reasoning-indicator';
    reasoning.innerHTML = `
        <div class="message-avatar assistant-avatar">A</div>
        <div class="message-content">
            <div class="message-header">
                <span class="message-sender">Assistant</span>
                <span class="message-time">${formatTime(new Date())}</span>
            </div>
            <div class="message-text reasoning-text">
                <span class="reasoning-icon">🤔</span> Thinking...
            </div>
        </div>
    `;
    
    messagesContainer.appendChild(reasoning);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
    
    return reasoning;
}

// Remove reasoning indicator
function removeReasoningIndicator() {
    const reasoning = document.getElementById('reasoning-indicator');
    if (reasoning) {
        reasoning.remove();
    }
}

// Add function call UI
function addFunctionCallUI(functionName, functionArgs) {
    const functionCall = document.createElement('div');
    functionCall.className = 'message function-call-message';
    
    const argsDisplay = Object.entries(functionArgs)
        .map(([key, value]) => `<div class="function-arg"><span class="arg-name">${key}:</span> <span class="arg-value">${escapeHTML(JSON.stringify(value))}</span></div>`)
        .join('');
    
    functionCall.innerHTML = `
        <div class="message-avatar function-avatar">🔧</div>
        <div class="message-content">
            <div class="message-header">
                <span class="message-sender">Function Call</span>
                <span class="message-time">${formatTime(new Date())}</span>
            </div>
            <div class="function-call-content">
                <div class="function-name">${escapeHTML(functionName)}</div>
                <div class="function-args">${argsDisplay}</div>
                <div class="function-status">Executing...</div>
            </div>
        </div>
    `;
    
    messagesContainer.appendChild(functionCall);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
    
    return functionCall;
}

// Update function call with result
function updateFunctionCallResult(functionCallElement, result) {
    const statusElement = functionCallElement.querySelector('.function-status');
    const contentElement = functionCallElement.querySelector('.function-call-content');
    
    if (result.success) {
        statusElement.textContent = '✓ Completed';
        statusElement.className = 'function-status success';
        
        // Add result display
        const resultDisplay = document.createElement('div');
        resultDisplay.className = 'function-result';
        resultDisplay.innerHTML = `<pre>${escapeHTML(JSON.stringify(result.result, null, 2))}</pre>`;
        contentElement.appendChild(resultDisplay);
    } else {
        statusElement.textContent = '✗ Failed: ' + result.error;
        statusElement.className = 'function-status error';
    }
    
    // Add glow effect
    functionCallElement.classList.add('function-complete');
    setTimeout(() => {
        functionCallElement.classList.remove('function-complete');
    }, 1500);
}

// Add message to UI
function addMessageToUI(role, content) {
    const message = document.createElement('div');
    message.className = `message ${role}-message`;
    message.innerHTML = `
        <div class="message-avatar ${role}-avatar">${role === 'user' ? 'U' : 'A'}</div>
        <div class="message-content">
            <div class="message-header">
                <span class="message-sender">${role === 'user' ? 'You' : 'Assistant'}</span>
                <span class="message-time">${formatTime(new Date())}</span>
            </div>
            <div class="message-text">${role === 'user' ? escapeHTML(content) : marked.parse(content)}</div>
        </div>
    `;
    
    messagesContainer.appendChild(message);
    
    // Apply syntax highlighting to code blocks
    if (role === 'assistant') {
        highlightCode(message.querySelector('.message-text'));
    }
    
    // Scroll to bottom
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
    
    // Add animation class
    setTimeout(() => {
        message.classList.add('animated');
    }, 10);
    
    return message;
}

// Show typing indicator
function showTypingIndicator() {
    const typingIndicator = document.createElement('div');
    typingIndicator.className = 'typing-indicator';
    typingIndicator.innerHTML = `
        <div class="message-avatar assistant-avatar">A</div>
        <div class="message-content">
            <div class="message-header">
                <span class="message-sender">Assistant</span>
                <span class="message-time">${formatTime(new Date())}</span>
            </div>
            <div class="typing-dots">
                <span></span>
                <span></span>
                <span></span>
            </div>
        </div>
    `;
    
    messagesContainer.appendChild(typingIndicator);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

// Remove typing indicator
function removeTypingIndicator() {
    const typingIndicator = document.querySelector('.typing-indicator');
    if (typingIndicator) {
        typingIndicator.remove();
    }
}

// Add error message
function addErrorMessage(message) {
    const errorMessage = document.createElement('div');
    errorMessage.className = 'message error-message';
    errorMessage.innerHTML = `
        <div class="message-avatar assistant-avatar">!</div>
        <div class="message-content">
            <div class="message-header">
                <span class="message-sender">System</span>
                <span class="message-time">${formatTime(new Date())}</span>
            </div>
            <div class="message-text error-text">${message}</div>
        </div>
    `;
    
    messagesContainer.appendChild(errorMessage);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

// Start new chat
function startNewChat() {
    // Save current chat if needed
    if (settings.saveHistory && conversations[currentChatId]?.messages?.length > 0) {
        saveConversations();
    }
    
    // Create new chat
    currentChatId = generateId();
    conversations[currentChatId] = {
        id: currentChatId,
        title: 'New Conversation',
        messages: []
    };
    
    // Update UI
    currentChatTitle.textContent = 'New Conversation';
    messagesContainer.innerHTML = `
        <div class="welcome-message">
            <h2>Welcome to Granite Chat</h2>
            <p>This is a chat interface for the IBM Granite 4.0 1B model.</p>
            <p>Ask me anything to get started!</p>
        </div>
    `;
    
    // Update chat history
    updateChatHistory();
}

// Update chat history sidebar
function updateChatHistory() {
    historyList.innerHTML = '';
    
    // Sort conversations by most recent message
    const sortedConversations = Object.values(conversations)
        .filter(conv => conv.messages && conv.messages.length > 0)
        .sort((a, b) => {
            const aTime = a.messages[a.messages.length - 1].timestamp;
            const bTime = b.messages[b.messages.length - 1].timestamp;
            return new Date(bTime) - new Date(aTime);
        });
    
    sortedConversations.forEach(conv => {
        const item = document.createElement('li');
        item.className = `history-item ${conv.id === currentChatId ? 'active' : ''}`;
        item.dataset.id = conv.id;
        item.innerHTML = `
            <i class="fas fa-comment"></i>
            <span class="history-title">${escapeHTML(conv.title)}</span>
            <button class="delete-chat-btn" title="Delete conversation">
                <i class="fas fa-trash"></i>
            </button>
        `;
        
        // Click on title to load conversation
        const titleSpan = item.querySelector('.history-title');
        titleSpan.addEventListener('click', () => loadConversation(conv.id));
        
        // Click on delete button to delete conversation
        const deleteBtn = item.querySelector('.delete-chat-btn');
        deleteBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            deleteConversation(conv.id);
        });
        
        historyList.appendChild(item);
    });
}

// Delete conversation
function deleteConversation(chatId) {
    // Confirm deletion
    if (!confirm('Are you sure you want to delete this conversation?')) {
        return;
    }
    
    // Delete from conversations object
    delete conversations[chatId];
    
    // Save to localStorage
    if (settings.saveHistory) {
        saveConversations();
    }
    
    // If deleting current conversation, start a new one
    if (chatId === currentChatId) {
        startNewChat();
    } else {
        // Just update the history list
        updateChatHistory();
    }
}

// Load conversation
function loadConversation(chatId) {
    if (!conversations[chatId]) return;
    
    currentChatId = chatId;
    currentChatTitle.textContent = conversations[chatId].title;
    
    // Update active state in history
    document.querySelectorAll('.history-item').forEach(item => {
        item.classList.toggle('active', item.dataset.id === chatId);
    });
    
    // Clear messages container
    messagesContainer.innerHTML = '';
    
    // Add messages - only display user and assistant messages, not function messages
    conversations[chatId].messages.forEach((msg, index) => {
        // Skip function role messages - they're for API context only
        if (msg.role === 'function') {
            return;
        }
        
        const messageElement = addMessageToUI(msg.role, msg.content);
        
        // Add regenerate button to user messages (except the last one if it's still generating)
        if (msg.role === 'user' && index < conversations[chatId].messages.length - 1) {
            addRegenerateButton(messageElement, index);
        }
    });
}

// Add regenerate button to a message
function addRegenerateButton(messageElement, messageIndex) {
    const messageContent = messageElement.querySelector('.message-content');
    const regenerateBtn = document.createElement('button');
    regenerateBtn.className = 'regenerate-btn';
    regenerateBtn.title = 'Regenerate response';
    regenerateBtn.innerHTML = '<i class="fas fa-redo"></i> Regenerate';
    
    regenerateBtn.addEventListener('click', () => {
        regenerateResponse(messageIndex);
    });
    
    messageContent.appendChild(regenerateBtn);
}

// Regenerate response from a specific message
async function regenerateResponse(messageIndex) {
    if (isGenerating) {
        alert('Please wait for the current generation to complete.');
        return;
    }
    
    // Remove all messages after the selected one
    const messagesToKeep = conversations[currentChatId].messages.slice(0, messageIndex + 1);
    conversations[currentChatId].messages = messagesToKeep;
    
    // Save conversations
    if (settings.saveHistory) {
        saveConversations();
    }
    
    // Reload the conversation to update UI
    loadConversation(currentChatId);
    
    // Generate new response
    await generateResponse();
}

// Save conversations to localStorage
function saveConversations() {
    if (settings.saveHistory) {
        localStorage.setItem('conversations', JSON.stringify(conversations));
    }
}

// Load conversations from localStorage
function loadConversations() {
    const saved = localStorage.getItem('conversations');
    if (saved) {
        conversations = JSON.parse(saved);
        updateChatHistory();
        
        // Load most recent conversation
        const mostRecent = Object.values(conversations)
            .filter(conv => conv.messages && conv.messages.length > 0)
            .sort((a, b) => {
                const aTime = a.messages[a.messages.length - 1].timestamp;
                const bTime = b.messages[b.messages.length - 1].timestamp;
                return new Date(bTime) - new Date(aTime);
            })[0];
        
        if (mostRecent) {
            loadConversation(mostRecent.id);
        }
    }
}

// Save current settings
function saveCurrentSettings() {
    settings = {
        temperature: parseFloat(temperatureSlider.value),
        maxTokens: parseInt(maxTokensSlider.value),
        topP: parseFloat(topPSlider.value),
        topK: parseInt(topKSlider.value),
        streaming: streamingCheckbox.checked,
        saveHistory: saveHistoryCheckbox.checked,
        systemPrompt: systemPromptTextarea.value.trim()
    };
    
    localStorage.setItem('settings', JSON.stringify(settings));
}

// Load settings from localStorage
function loadSettings() {
    const saved = localStorage.getItem('settings');
    if (saved) {
        settings = { ...defaultSettings, ...JSON.parse(saved) };
    }
    
    // Update UI
    temperatureSlider.value = settings.temperature;
    temperatureValue.textContent = settings.temperature;
    
    maxTokensSlider.value = settings.maxTokens;
    maxTokensValue.textContent = settings.maxTokens;
    
    topPSlider.value = settings.topP;
    topPValue.textContent = settings.topP;
    
    topKSlider.value = settings.topK;
    topKValue.textContent = settings.topK;
    
    streamingCheckbox.checked = settings.streaming;
    saveHistoryCheckbox.checked = settings.saveHistory;
    systemPromptTextarea.value = settings.systemPrompt || '';
    
    // Set theme
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme === 'dark') {
        document.body.classList.add('dark-mode');
        themeToggle.innerHTML = '<i class="fas fa-sun"></i>';
    }
}

// Reset to default settings
function resetToDefaultSettings() {
    settings = { ...defaultSettings };
    
    // Update UI
    temperatureSlider.value = settings.temperature;
    temperatureValue.textContent = settings.temperature;
    
    maxTokensSlider.value = settings.maxTokens;
    maxTokensValue.textContent = settings.maxTokens;
    
    topPSlider.value = settings.topP;
    topPValue.textContent = settings.topP;
    
    topKSlider.value = settings.topK;
    topKValue.textContent = settings.topK;
    
    streamingCheckbox.checked = settings.streaming;
    saveHistoryCheckbox.checked = settings.saveHistory;
    systemPromptTextarea.value = settings.systemPrompt || '';
}

// Setup sliders
function setupSliders() {
    // Temperature slider
    temperatureSlider.addEventListener('input', () => {
        temperatureValue.textContent = temperatureSlider.value;
    });
    
    // Max tokens slider
    maxTokensSlider.addEventListener('input', () => {
        maxTokensValue.textContent = maxTokensSlider.value;
    });
    
    // Top P slider
    topPSlider.addEventListener('input', () => {
        topPValue.textContent = topPSlider.value;
    });
    
    // Top K slider
    topKSlider.addEventListener('input', () => {
        topKValue.textContent = topKSlider.value;
    });
}

// Toggle theme
function toggleTheme() {
    const isDark = document.body.classList.toggle('dark-mode');
    themeToggle.innerHTML = isDark ? '<i class="fas fa-sun"></i>' : '<i class="fas fa-moon"></i>';
    localStorage.setItem('theme', isDark ? 'dark' : 'light');
}

// Adjust textarea height
function adjustTextareaHeight() {
    userInput.style.height = 'auto';
    userInput.style.height = (userInput.scrollHeight) + 'px';
}

// Generate a simple ID
function generateId() {
    return Date.now().toString(36) + Math.random().toString(36).substr(2);
}

// Generate a title from the first message using the API
async function generateTitle(message) {
    try {
        // Default title in case API call fails
        let defaultTitle = message.split(/[.!?]/)[0].trim();
        defaultTitle = defaultTitle.length > 50 ? defaultTitle.substring(0, 47) + '...' : defaultTitle;
        
        // For simple messages, just use the first sentence
        if (message.length < 100) {
            return defaultTitle;
        }
        
        // Create a simple prompt for title generation
        const titlePrompt = `Create a short title (3-8 words) for this message: ${message.substring(0, 200)}`;
        
        // Call the API to generate a title
        const response = await fetch('/generate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                prompt: titlePrompt,
                max_tokens: 20,
                temperature: 0.5,
                top_p: 0.9,
                do_sample: true
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        let generatedTitle = data.generated_text.trim();
        
        // The response includes the prompt, so we need to extract only the new text
        // Remove the prompt from the beginning
        if (generatedTitle.startsWith(titlePrompt)) {
            generatedTitle = generatedTitle.substring(titlePrompt.length).trim();
        }
        
        // Try to extract just the title part
        // Remove common prefixes
        generatedTitle = generatedTitle.replace(/^(title|Title):\s*/i, '').trim();
        generatedTitle = generatedTitle.replace(/^["']|["']$/g, '').trim();
        
        // Take only the first line
        const firstLine = generatedTitle.split('\n')[0].trim();
        if (firstLine.length > 0 && firstLine.length < 100) {
            generatedTitle = firstLine;
        }
        
        // Remove any remaining quotes or special characters at the start/end
        generatedTitle = generatedTitle.replace(/^[:\-\s"']+|[:\-\s"']+$/g, '').trim();
        
        // Ensure the title is not too long
        if (generatedTitle.length > 50) {
            generatedTitle = generatedTitle.substring(0, 47) + '...';
        }
        
        // Validate the title - it should be reasonable
        if (generatedTitle.length < 3 || generatedTitle.length > 100 ||
            generatedTitle.toLowerCase().includes('generate') ||
            generatedTitle.toLowerCase().includes('create a') ||
            generatedTitle.toLowerCase().includes('message:')) {
            return defaultTitle;
        }
        
        // Return the generated title or fall back to default
        return generatedTitle || defaultTitle;
    } catch (error) {
        console.error('Error generating title:', error);
        
        // Fall back to simple title extraction
        const title = message.split(/[.!?]/)[0].trim();
        return title.length > 50 ? title.substring(0, 47) + '...' : title;
    }
}

// Format time
function formatTime(date) {
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

// Escape HTML
function escapeHTML(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Apply syntax highlighting to code blocks
function highlightCode(element) {
    element.querySelectorAll('pre code').forEach((block) => {
        hljs.highlightElement(block);
    });
}

// File Upload Functions
function setupFileUploadListeners() {
    let dragCounter = 0;
    
    // Attach button click
    attachBtn.addEventListener('click', () => {
        fileInput.click();
    });
    
    // File input change
    fileInput.addEventListener('change', handleFileSelect);
    
    // Window-level drag events to show/hide overlay
    window.addEventListener('dragenter', (e) => {
        e.preventDefault();
        dragCounter++;
        if (dragCounter === 1) {
            fileDropOverlay.style.display = 'flex';
            fileDropOverlay.classList.add('active');
        }
    });
    
    window.addEventListener('dragleave', (e) => {
        e.preventDefault();
        dragCounter--;
        if (dragCounter === 0) {
            fileDropOverlay.style.display = 'none';
            fileDropOverlay.classList.remove('active');
            fileDropZone.classList.remove('drag-over');
        }
    });
    
    window.addEventListener('dragover', (e) => {
        e.preventDefault();
    });
    
    window.addEventListener('drop', (e) => {
        e.preventDefault();
        dragCounter = 0;
        fileDropOverlay.style.display = 'none';
        fileDropOverlay.classList.remove('active');
        fileDropZone.classList.remove('drag-over');
        
        // If dropped outside the drop zone, still process files
        if (e.dataTransfer && e.dataTransfer.files.length > 0) {
            const files = Array.from(e.dataTransfer.files);
            addFiles(files);
        }
    });
    
    // Drop zone specific events
    fileDropZone.addEventListener('dragover', handleDragOver);
    fileDropZone.addEventListener('dragleave', handleDragLeave);
    fileDropZone.addEventListener('drop', handleDrop);
    
    // Clear files button
    clearFilesBtn.addEventListener('click', clearAllFiles);
}

function handleFileSelect(e) {
    const files = Array.from(e.target.files);
    addFiles(files);
    fileInput.value = ''; // Reset input
}

function handleDragOver(e) {
    e.preventDefault();
    e.stopPropagation();
    // Only add drag-over class if we're over the drop zone itself
    if (e.target === fileDropZone || fileDropZone.contains(e.target)) {
        fileDropZone.classList.add('drag-over');
    }
}

function handleDragLeave(e) {
    e.preventDefault();
    e.stopPropagation();
    // Only remove drag-over class if we're leaving the drop zone
    if (e.target === fileDropZone || !fileDropZone.contains(e.relatedTarget)) {
        fileDropZone.classList.remove('drag-over');
    }
}

function handleDrop(e) {
    e.preventDefault();
    e.stopPropagation();
    
    // Reset drag counter and hide overlay
    fileDropZone.classList.remove('drag-over');
    fileDropOverlay.style.display = 'none';
    fileDropOverlay.classList.remove('active');
    
    const files = Array.from(e.dataTransfer.files);
    addFiles(files);
}

function addFiles(files) {
    const maxSize = 50 * 1024 * 1024; // 50MB
    const allowedExtensions = ['.pdf', '.docx', '.pptx', '.xlsx', '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff'];
    
    files.forEach(file => {
        // Validate file size
        if (file.size > maxSize) {
            addErrorMessage(`File "${file.name}" is too large. Maximum size is 50MB.`);
            return;
        }
        
        // Validate file extension
        const extension = '.' + file.name.split('.').pop().toLowerCase();
        if (!allowedExtensions.includes(extension)) {
            addErrorMessage(`File "${file.name}" has an unsupported format. Supported formats: PDF, DOCX, PPTX, XLSX, Images.`);
            return;
        }
        
        // Check if file already attached
        if (attachedFiles.some(f => f.name === file.name && f.size === file.size)) {
            addErrorMessage(`File "${file.name}" is already attached.`);
            return;
        }
        
        // Add file to attached files
        attachedFiles.push(file);
        addFilePreview(file);
    });
    
    updateFileUI();
}

function addFilePreview(file) {
    const fileItem = document.createElement('div');
    fileItem.className = 'file-item';
    fileItem.dataset.fileName = file.name;
    
    const extension = file.name.split('.').pop().toLowerCase();
    const iconClass = getFileIconClass(extension);
    const fileSize = formatFileSize(file.size);
    
    fileItem.innerHTML = `
        <div class="file-icon ${iconClass}">
            <i class="${getFileIcon(extension)}"></i>
        </div>
        <div class="file-info-container">
            <div class="file-name">${escapeHTML(file.name)}</div>
            <div class="file-size">${fileSize}</div>
        </div>
        <span class="file-status pending">Pending</span>
        <button type="button" class="remove-file-btn" title="Remove file">
            <i class="fas fa-times"></i>
        </button>
    `;
    
    // Add remove button event listener
    const removeBtn = fileItem.querySelector('.remove-file-btn');
    removeBtn.addEventListener('click', () => removeFile(file.name));
    
    fileItems.appendChild(fileItem);
}

function removeFile(fileName) {
    attachedFiles = attachedFiles.filter(f => f.name !== fileName);
    
    const fileItem = fileItems.querySelector(`[data-file-name="${fileName}"]`);
    if (fileItem) {
        fileItem.remove();
    }
    
    updateFileUI();
}

function clearAllFiles() {
    attachedFiles = [];
    fileItems.innerHTML = '';
    updateFileUI();
}

function updateFileUI() {
    if (attachedFiles.length > 0) {
        filePreviewList.style.display = 'block';
        fileCount.style.display = 'flex';
        fileCountText.textContent = `${attachedFiles.length} file${attachedFiles.length > 1 ? 's' : ''}`;
        attachBtn.classList.add('active');
    } else {
        filePreviewList.style.display = 'none';
        fileCount.style.display = 'none';
        attachBtn.classList.remove('active');
    }
}

function getFileIconClass(extension) {
    const iconMap = {
        'pdf': 'pdf',
        'docx': 'docx',
        'doc': 'docx',
        'pptx': 'pptx',
        'ppt': 'pptx',
        'xlsx': 'xlsx',
        'xls': 'xlsx',
        'jpg': 'image',
        'jpeg': 'image',
        'png': 'image',
        'gif': 'image',
        'bmp': 'image',
        'tiff': 'image'
    };
    
    return iconMap[extension] || 'default';
}

function getFileIcon(extension) {
    const iconMap = {
        'pdf': 'fas fa-file-pdf',
        'docx': 'fas fa-file-word',
        'doc': 'fas fa-file-word',
        'pptx': 'fas fa-file-powerpoint',
        'ppt': 'fas fa-file-powerpoint',
        'xlsx': 'fas fa-file-excel',
        'xls': 'fas fa-file-excel',
        'jpg': 'fas fa-file-image',
        'jpeg': 'fas fa-file-image',
        'png': 'fas fa-file-image',
        'gif': 'fas fa-file-image',
        'bmp': 'fas fa-file-image',
        'tiff': 'fas fa-file-image'
    };
    
    return iconMap[extension] || 'fas fa-file';
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
}

function updateFileStatus(fileName, status) {
    const fileItem = fileItems.querySelector(`[data-file-name="${fileName}"]`);
    if (fileItem) {
        const statusElement = fileItem.querySelector('.file-status');
        statusElement.className = `file-status ${status}`;
        statusElement.textContent = status.charAt(0).toUpperCase() + status.slice(1);
    }
}

// Handle mobile sidebar
if (window.innerWidth <= 768) {
    const sidebar = document.querySelector('.sidebar');
    const sidebarHeader = document.querySelector('.sidebar-header');
    
    sidebarHeader.addEventListener('click', () => {
        sidebar.classList.toggle('expanded');
    });
}

// Made with Bob
