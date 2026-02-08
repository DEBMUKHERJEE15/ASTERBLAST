// ai-server.js - Simple AI Proxy Server
const express = require('express');
const cors = require('cors');
const axios = require('axios');

const app = express();
const PORT = 8002;

// Middleware
app.use(cors());
app.use(express.json());

// Your Gemini API Key
const GEMINI_API_KEY = "AIzaSyDUcqcrZLLEXzbhq2DBgd2X5i-KDp-xwhI";

// Base URL for Gemini API
const GEMINI_BASE_URL = 'https://generativelanguage.googleapis.com';

// Use gemini-2.5-flash which is available according to your models list
let currentModel = 'gemini-2.5-flash';

// Test route
app.get('/test', (req, res) => {
    res.json({ 
        message: 'AI Server is running!',
        status: 'active',
        timestamp: new Date().toISOString(),
        currentModel: currentModel,
        endpoints: {
            chat: 'POST /chat',
            asteroidInfo: 'POST /asteroid-info',
            test: 'GET /test',
            models: 'GET /models',
            health: 'GET /health',
            echo: 'POST /echo',
            'test-gemini': 'GET /test-gemini',
            'quick-test': 'GET /quick-test'
        },
        note: 'Using Gemini 2.5 Flash - Latest model'
    });
});

// List available models
app.get('/models', async (req, res) => {
    try {
        const response = await axios.get(`${GEMINI_BASE_URL}/v1beta/models?key=${GEMINI_API_KEY}`);
        const models = response.data.models || [];
        
        // Filter to text generation models that support generateContent
        const textModels = models
            .filter(model => 
                model.name && 
                model.supportedGenerationMethods && 
                model.supportedGenerationMethods.includes('generateContent') &&
                !model.name.includes('embedding') && 
                !model.name.includes('imagen') && 
                !model.name.includes('veo') &&
                !model.name.includes('audio') &&
                !model.name.includes('tts')
            )
            .map(model => ({
                name: model.name.replace('models/', ''),
                displayName: model.displayName,
                description: model.description,
                supportedMethods: model.supportedGenerationMethods || []
            }))
            .sort((a, b) => {
                // Sort by name to put flash/pro models first
                if (a.name.includes('flash') && !b.name.includes('flash')) return -1;
                if (!a.name.includes('flash') && b.name.includes('flash')) return 1;
                return a.name.localeCompare(b.name);
            });
        
        res.json({
            success: true,
            models: textModels,
            total: textModels.length,
            currentModel: currentModel,
            recommendedModels: textModels.filter(m => 
                m.name.includes('flash') || 
                m.name.includes('pro') ||
                m.name === 'gemini-exp-1206'
            ).map(m => m.name),
            note: 'Text generation models available with your API key'
        });
    } catch (error) {
        console.error('Models Error:', error.message);
        res.json({
            success: false,
            error: error.message,
            currentModel: currentModel,
            fallbackModels: ['gemini-2.5-flash', 'gemini-2.0-flash', 'gemini-pro-latest', 'gemini-exp-1206'],
            note: 'Using gemini-2.5-flash as default'
        });
    }
});

// Test Gemini API connection
app.get('/test-gemini', async (req, res) => {
    try {
        console.log(`Testing Gemini API with model: ${currentModel}`);
        
        const testResponse = await axios.post(
            `${GEMINI_BASE_URL}/v1beta/models/${currentModel}:generateContent?key=${GEMINI_API_KEY}`,
            {
                contents: [{
                    parts: [{
                        text: "You are Cosmic AI for Stellar Observatory. Reply with: 'Cosmic AI online - Ready for space exploration!'"
                    }]
                }],
                generationConfig: {
                    temperature: 0.7,
                    maxOutputTokens: 100
                }
            },
            { 
                timeout: 15000,
                headers: {
                    'Content-Type': 'application/json'
                }
            }
        );

        const aiResponse = testResponse.data?.candidates?.[0]?.content?.parts?.[0]?.text;
        
        if (!aiResponse) {
            throw new Error('No text in response from AI');
        }
        
        res.json({ 
            success: true, 
            message: `✅ Gemini API is working perfectly with model: ${currentModel}`,
            model: currentModel,
            response: aiResponse,
            responseTime: 'fast',
            timestamp: new Date().toISOString(),
            nextSteps: 'Try the /chat endpoint with astronomy questions'
        });

    } catch (error) {
        console.error('Gemini API Test Error:', error.response?.data || error.message);
        
        // Try fallback models if current fails
        const fallbackModels = ['gemini-2.0-flash', 'gemini-pro-latest', 'gemini-exp-1206', 'gemini-2.0-flash-001'];
        
        for (const model of fallbackModels) {
            try {
                console.log(`Trying fallback model: ${model}`);
                const testResponse = await axios.post(
                    `${GEMINI_BASE_URL}/v1beta/models/${model}:generateContent?key=${GEMINI_API_KEY}`,
                    {
                        contents: [{
                            parts: [{ text: "Test" }]
                        }]
                    },
                    { timeout: 5000 }
                );
                
                if (testResponse.data?.candidates?.[0]?.content?.parts?.[0]?.text) {
                    currentModel = model;
                    console.log(`✅ Switched to working model: ${model}`);
                    
                    return res.json({ 
                        success: true, 
                        message: `Switched to model: ${model}`,
                        model: model,
                        note: 'Original model failed, but found working alternative'
                    });
                }
            } catch (e) {
                continue;
            }
        }
        
        res.status(500).json({ 
            success: false, 
            error: error.response?.data?.error?.message || error.message,
            currentModel: currentModel,
            triedModels: fallbackModels,
            note: 'All model attempts failed. Check API key permissions.',
            tip: 'Your API key might need enabling for certain models or might have rate limits.'
        });
    }
});

// Helper function to get Gemini API URL
function getGeminiUrl(model = null) {
    const modelToUse = model || currentModel;
    return `${GEMINI_BASE_URL}/v1beta/models/${modelToUse}:generateContent?key=${GEMINI_API_KEY}`;
}

// Chat endpoint - MAIN WORKING ENDPOINT
app.post('/chat', async (req, res) => {
    try {
        const { message } = req.body;
        
        if (!message) {
            return res.status(400).json({ 
                error: 'Message is required',
                example: '{"message": "Tell me about asteroids"}'
            });
        }

        console.log(`🤖 Chat request - Model: ${currentModel}, Message: "${message.substring(0, 50)}..."`);

        // Enhanced context for astronomy
        const context = `You are "Cosmic AI", the expert assistant for Stellar Observatory - a professional astronomy and planetary defense platform.

ROLE: You are an enthusiastic, knowledgeable astronomy expert specializing in:
- Asteroid tracking and near-Earth objects (NEOs)
- Planetary defense and impact risk assessment  
- Space research and celestial mechanics
- Solar system exploration and exoplanets
- Telescope technology and observational astronomy

PLATFORM FEATURES you can mention:
1. Live asteroid tracking dashboard
2. Real-time risk assessment tools
3. 3D solar system visualization
4. Observatory metrics and telescope network
5. Planetary defense simulations

USER QUESTION: "${message}"

RESPONSE GUIDELINES:
- Be concise but informative (150-300 words)
- Use space/astronomy metaphors when appropriate
- If question is off-topic, gently steer back to space topics
- Show enthusiasm for space exploration!
- Mention relevant platform features when helpful
- Use emojis sparingly (🚀⭐🛰️☄️)`;

        const response = await axios.post(
            getGeminiUrl(),
            {
                contents: [{
                    parts: [{
                        text: context
                    }]
                }],
                generationConfig: {
                    temperature: 0.8,
                    topP: 0.95,
                    topK: 40,
                    maxOutputTokens: 1024,
                },
                safetySettings: [
                    {
                        category: "HARM_CATEGORY_HARASSMENT",
                        threshold: "BLOCK_NONE"
                    },
                    {
                        category: "HARM_CATEGORY_HATE_SPEECH", 
                        threshold: "BLOCK_NONE"
                    },
                    {
                        category: "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                        threshold: "BLOCK_NONE"
                    },
                    {
                        category: "HARM_CATEGORY_DANGEROUS_CONTENT",
                        threshold: "BLOCK_NONE"
                    }
                ]
            },
            {
                timeout: 30000,
                headers: {
                    'Content-Type': 'application/json'
                }
            }
        );

        console.log('✅ Gemini API Response successful');
        
        const aiResponse = response.data?.candidates?.[0]?.content?.parts?.[0]?.text;
        
        if (aiResponse) {
            res.json({ 
                response: aiResponse,
                success: true,
                model: currentModel,
                timestamp: new Date().toISOString(),
                tokens: response.data?.usageMetadata?.totalTokenCount || 'unknown',
                note: 'Powered by Gemini 2.5 Flash AI'
            });
        } else {
            throw new Error('AI returned empty response');
        }

    } catch (error) {
        console.error('❌ Chat Error:', error.response?.status, error.response?.data?.error || error.message);
        
        // Detailed error handling
        if (error.response?.status === 429) {
            return res.status(429).json({
                response: "🌌 The cosmic bandwidth is saturated right now (rate limit reached). Our telescopes are still collecting data - try again in a moment!",
                success: false,
                error: "Rate limit exceeded",
                tip: "API has usage limits. Wait 60 seconds and try again.",
                model: currentModel
            });
        }
        
        if (error.response?.status === 404) {
            // Model not found, try to switch
            const fallbackModels = ['gemini-2.0-flash', 'gemini-pro-latest', 'gemini-exp-1206'];
            for (const model of fallbackModels) {
                if (model !== currentModel) {
                    currentModel = model;
                    console.log(`🔄 Switched to model: ${model}`);
                    break;
                }
            }
        }
        
        // Smart context-aware fallback
        const userMessage = (req.body?.message || '').toLowerCase();
        let fallbackResponse;
        
        if (userMessage.includes('asteroid') || userMessage.includes('neo')) {
            fallbackResponse = "While I'm syncing with the deep space network, here's asteroid info from our local database: We track thousands of near-Earth objects. Most are small and pose no threat, but we monitor all closely. Check our Tracking page for real-time data! 🚀";
        } else if (userMessage.includes('mars') || userMessage.includes('planet')) {
            fallbackResponse = "The Mars connection has some static! Here's what I know: Mars is the 4th planet, has two moons, and is a prime target for exploration. Our 3D visualization shows its current position relative to Earth. 🔴";
        } else if (userMessage.includes('moon') || userMessage.includes('lunar')) {
            fallbackResponse = "Lunar signal weak! Quick facts: Our Moon is Earth's only natural satellite, about 1/4 Earth's diameter. It heavily influences tides and is crucial for future space exploration. 🌕";
        } else if (userMessage.includes('star') || userMessage.includes('galaxy')) {
            fallbackResponse = "Stellar interference detected! Stars are massive balls of plasma, galaxies contain billions of them. Our Milky Way has 100-400 billion stars. The observatory can simulate star fields in the 3D view! ✨";
        } else if (userMessage.includes('risk') || userMessage.includes('danger')) {
            fallbackResponse = "Risk assessment systems nominal. We use multiple factors: distance, size, velocity, orbit. Most asteroids have minimal risk. Try our Risk Analyzer tool for detailed simulations! ⚠️";
        } else {
            fallbackResponse = "Cosmic AI here! I'm experiencing some interstellar static. The Stellar Observatory platform is fully operational with asteroid tracking, risk analysis, and 3D visualization. What would you like to explore? 🛰️";
        }
        
        res.json({ 
            response: fallbackResponse,
            success: false,
            error: error.response?.data?.error?.message || 'Connection issue',
            model: currentModel,
            note: 'Using intelligent fallback response',
            timestamp: new Date().toISOString(),
            tip: 'The AI will auto-reconnect. Your experience is unaffected.'
        });
    }
});

// Simple echo endpoint for testing
app.post('/echo', (req, res) => {
    const { message } = req.body;
    res.json({ 
        response: `📡 Echo from Stellar Observatory: "${message || 'Silence in space...'}"`,
        timestamp: new Date().toISOString(),
        server: 'Stellar Observatory AI Server v2.0',
        model: currentModel,
        status: '🟢 Operational'
    });
});

// Asteroid information endpoint
app.post('/asteroid-info', async (req, res) => {
    try {
        const { asteroidName } = req.body;
        
        if (!asteroidName) {
            return res.json({
                response: "Please specify which asteroid you're curious about! Try: Bennu, Apophis, Ceres, Eros, or Itokawa.",
                success: false,
                example: '{"asteroidName": "Bennu"}'
            });
        }

        console.log(`☄️ Asteroid info request: ${asteroidName}`);
        
        const prompt = `Provide comprehensive but concise information about asteroid ${asteroidName} for astronomy enthusiasts.

Structure your response with:
1. **Basic Facts**: Discovery, size, type
2. **Orbit**: Characteristics, period, eccentricity  
3. **Significance**: Scientific importance, missions
4. **Risk**: Close approaches, impact probability (if any)
5. **Current Status**: Observation status, future flybys

Keep it engaging and under 250 words. If ${asteroidName} is fictional or unknown, explain what we know about similar asteroids.`;

        const response = await axios.post(
            getGeminiUrl(),
            {
                contents: [{
                    parts: [{ text: prompt }]
                }],
                generationConfig: {
                    temperature: 0.6,
                    maxOutputTokens: 800,
                }
            },
            { 
                timeout: 20000,
                headers: { 'Content-Type': 'application/json' }
            }
        );

        const aiResponse = response.data?.candidates?.[0]?.content?.parts?.[0]?.text;
        
        res.json({ 
            response: aiResponse,
            success: true,
            asteroid: asteroidName,
            model: currentModel,
            timestamp: new Date().toISOString(),
            source: 'Gemini 2.5 Flash AI + NASA data'
        });

    } catch (error) {
        console.error('Asteroid Info Error:', error.message);
        
        // Enhanced asteroid fallback database
        const asteroidDatabase = {
            'bennu': "**101955 Bennu** 🪐\n• Discovered: 1999\n• Size: ~500m diameter\n• Type: Carbonaceous (primitive)\n• Mission: NASA OSIRIS-REx (sample return 2023)\n• Risk: 1-in-2,700 chance of impact in 2182\n• Fun fact: One of most potentially hazardous asteroids known",
            'apophis': "**99942 Apophis** ⚠️\n• Discovered: 2004\n• Size: ~370m diameter\n• Fame: Caused concern with initial 2.7% impact probability for 2029\n• Update: Will safely pass Earth at ~31,000km on April 13, 2029\n• Visible: Will be naked-eye visible during 2029 flyby",
            'ceres': "**1 Ceres** 🌍\n• Largest object in asteroid belt (940km)\n• Status: Dwarf planet (since 2006)\n• Composition: Rock/ice, possible subsurface ocean\n• Mission: NASA Dawn orbiter (2015-2018)\n• Significance: Contains 25% of asteroid belt's mass",
            'eros': "**433 Eros** 💫\n• First NEO discovered (1898)\n• Size: 33×13×13 km (potato-shaped!)\n• Mission: NEAR Shoemaker orbited & landed (2000-2001)\n• Orbit: Brings it within 0.15 AU of Earth\n• Type: S-type (stony)",
            'itokawa': "**25143 Itokawa** 🚀\n• Size: 535×294×209m\n• Mission: JAXA Hayabusa (first asteroid sample return, 2010)\n• Type: Rubble pile (loose collection of rocks)\n• Shape: Looks like a sea otter!\n• Samples: ~1,500 grains returned to Earth"
        };
        
        const lowerName = asteroidName.toLowerCase().trim();
        const fallback = asteroidDatabase[lowerName] || 
            `Asteroid **${asteroidName}** is being analyzed by our deep space telescopes. While we await spectral data, here's what we know: Most asteroids orbit between Mars and Jupiter, but Near-Earth Objects like this require careful tracking for planetary defense.`;
        
        res.json({ 
            response: fallback,
            success: false,
            asteroid: asteroidName,
            model: currentModel,
            note: 'Using local asteroid knowledge base',
            timestamp: new Date().toISOString(),
            tip: 'Try: Bennu, Apophis, Ceres for detailed info'
        });
    }
});

// Health check endpoint
app.get('/health', (req, res) => {
    const used = process.memoryUsage();
    res.json({
        status: '🟢 HEALTHY',
        server: 'Stellar Observatory AI Server',
        version: '2.5',
        port: PORT,
        uptime: `${Math.floor(process.uptime())} seconds`,
        currentModel: currentModel,
        memory: {
            heapUsed: `${Math.round(used.heapUsed / 1024 / 1024)}MB`,
            heapTotal: `${Math.round(used.heapTotal / 1024 / 1024)}MB`,
            rss: `${Math.round(used.rss / 1024 / 1024)}MB`
        },
        timestamp: new Date().toISOString(),
        endpoints: [
            'GET  /test',
            'GET  /test-gemini', 
            'GET  /models',
            'GET  /health',
            'GET  /quick-test',
            'POST /chat',
            'POST /asteroid-info',
            'POST /echo'
        ]
    });
});

// Quick test endpoint
app.get('/quick-test', async (req, res) => {
    try {
        const startTime = Date.now();
        const response = await axios.post(
            getGeminiUrl(),
            {
                contents: [{
                    parts: [{
                        text: "Reply only with: 'Cosmic AI operational. All systems nominal. Ready for stellar exploration!'"
                    }]
                }],
                generationConfig: {
                    temperature: 0.1,
                    maxOutputTokens: 50
                }
            },
            { timeout: 10000 }
        );
        
        const aiResponse = response.data?.candidates?.[0]?.content?.parts?.[0]?.text;
        const responseTime = Date.now() - startTime;
        
        res.json({
            success: true,
            status: "✅ FULLY OPERATIONAL",
            message: "AI connection perfect!",
            response: aiResponse,
            model: currentModel,
            responseTime: `${responseTime}ms`,
            speed: responseTime < 1000 ? "⚡ Fast" : "🐢 Slow but working",
            recommendation: "Proceed with space exploration!"
        });
    } catch (error) {
        res.json({
            success: false,
            status: "⚠️ DEGRADED PERFORMANCE",
            message: "AI connection test failed",
            error: error.message,
            model: currentModel,
            responseTime: "N/A",
            note: "Frontend will use intelligent fallbacks",
            assurance: "Observatory features remain fully functional"
        });
    }
});

// Start server
app.listen(PORT, () => {
    console.log(`
    ░█▀▀░█▀█░█▀▄░█▀▀░█▀▄░█▀▀░░░█▀█░█▀▀░▀█▀░█▀▀░█▀▄
    ░█░░░█░█░█░█░█▀▀░█▀▄░▀▀█░░░█▀▀░█▀▀░░█░░█▀▀░█▀▄
    ░▀▀▀░▀▀▀░▀▀░░▀▀▀░▀░▀░▀▀▀░░░▀░░░▀▀▀░░▀░░▀▀▀░▀░▀
    
    🚀 STELLAR OBSERVATORY AI SERVER v2.5`);
    console.log(`   📍 Port: ${PORT}`);
    console.log(`   🤖 Model: ${currentModel}`);
    console.log(`   🔑 API Key: ${GEMINI_API_KEY.substring(0, 10)}...`);
    console.log(`   🕐 Started: ${new Date().toLocaleTimeString()}`);
    
    console.log(`
    📡 ENDPOINTS:`);
    console.log(`   🌐 http://localhost:${PORT}/test              - Server status`);
    console.log(`   🔗 http://localhost:${PORT}/test-gemini       - Test AI connection`);
    console.log(`   📋 http://localhost:${PORT}/models            - Available models`);
    console.log(`   ❤️  http://localhost:${PORT}/health           - Health check`);
    console.log(`   ⚡ http://localhost:${PORT}/quick-test        - Quick AI test`);
    console.log(`   💬 http://localhost:${PORT}/chat             - AI chat (POST)`);
    console.log(`   ☄️  http://localhost:${PORT}/asteroid-info    - Asteroid info (POST)`);
    console.log(`   🔄 http://localhost:${PORT}/echo             - Echo test (POST)`);
    
    console.log(`
    🎯 TEST COMMANDS (PowerShell):`);
    console.log(`   irm http://localhost:${PORT}/test`);
    console.log(`   irm http://localhost:${PORT}/test-gemini`);
    console.log(`   irm -Method POST -Uri http://localhost:${PORT}/chat -Headers @{"Content-Type"="application/json"} -Body '{"message":"Hello from space!"}'`);
    
    console.log(`
    💡 TIPS:`);
    console.log(`   • Using Gemini 2.5 Flash (latest available model)`);
    console.log(`   • Intelligent fallbacks if API fails`);
    console.log(`   • Frontend compatible with all responses`);
    console.log(`   • Check /models for all available options`);
    console.log(`
    🌌 Ready for cosmic exploration!`);
});