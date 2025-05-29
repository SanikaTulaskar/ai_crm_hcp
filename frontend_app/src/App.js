// frontend_app/src/App.js
import React, { useState, useEffect, useRef } from 'react';
import { Provider, useSelector, useDispatch } from 'react-redux';
import { configureStore, createSlice } from '@reduxjs/toolkit';
import axios from 'axios';

// --- Configuration ---
const API_BASE_URL = 'http://localhost:8000/api'; // Backend API URL

// --- Redux Slice for Interactions ---
const initialState = {
  interactions: [],
  loading: false,
  error: null,
  chatHistory: [],
  currentChatAIMessage: '',
  isChatComplete: false,
  currentExtractedData: {}, // Store data extracted by AI during chat
};

const interactionSlice = createSlice({
  name: 'interactions',
  initialState,
  reducers: {
    logRequest: (state) => {
      state.loading = true;
      state.error = null;
    },
    logFormSuccess: (state, action) => {
      state.loading = false;
      state.interactions.push(action.payload);
      // Optionally clear chat if form submission is related
    },
    logChatChunk: (state, action) => {
        state.loading = false;
        const { ai_message, is_complete, extracted_data, interaction_id } = action.payload;
        
        // Add AI message to chat history
        if (ai_message) {
            state.chatHistory.push({ role: 'assistant', content: ai_message });
        }
        state.currentChatAIMessage = ai_message; // For immediate display or further use
        state.isChatComplete = is_complete;
        
        if (extracted_data) {
            state.currentExtractedData = extracted_data;
        }
        if (is_complete && interaction_id) {
            // If chat interaction was logged, potentially add to a list of logged interactions
            // For now, we just mark as complete and reset extracted data for next chat.
            console.log(`Chat interaction logged with ID: ${interaction_id}`);
            state.currentExtractedData = {}; // Reset for next interaction
            // You might want to add a system message like "Interaction Logged" to chatHistory
        }
    },
    addUserMessageToChat: (state, action) => {
        state.chatHistory.push({ role: 'user', content: action.payload });
    },
    logFailure: (state, action) => {
      state.loading = false;
      state.error = action.payload;
    },
    clearChat: (state) => {
        state.chatHistory = [];
        state.currentChatAIMessage = '';
        state.isChatComplete = false;
        state.currentExtractedData = {};
    },
    resetError: (state) => {
        state.error = null;
    }
  },
});

export const {
  logRequest,
  logFormSuccess,
  logChatChunk,
  addUserMessageToChat,
  logFailure,
  clearChat,
  resetError
} = interactionSlice.actions;

// --- Redux Store Configuration ---
const store = configureStore({
  reducer: {
    interactions: interactionSlice.reducer,
  },
});

// --- API Thunks (Async Actions) ---
export const submitInteractionForm = (formData) => async (dispatch) => {
  dispatch(logRequest());
  try {
    const response = await axios.post(`${API_BASE_URL}/log_interaction_form`, formData);
    dispatch(logFormSuccess(response.data));
    return response.data; // Return data for potential further use in component
  } catch (error) {
    const errorMessage = error.response?.data?.detail || error.message || "An unknown error occurred";
    dispatch(logFailure(errorMessage));
    throw error; // Re-throw for component to handle
  }
};

export const sendChatMessage = (message, history, currentExtractedData) => async (dispatch) => {
  dispatch(logRequest());
  dispatch(addUserMessageToChat(message)); // Add user message to history immediately
  try {
    const payload = { 
        message, 
        history: history, // Send previous history for context
        current_extraction_data: currentExtractedData
    };
    const response = await axios.post(`${API_BASE_URL}/log_interaction_chat`, payload);
    dispatch(logChatChunk(response.data)); // AI response, completion status, extracted data
    return response.data;
  } catch (error) {
    const errorMessage = error.response?.data?.detail || error.message || "Failed to send chat message";
    dispatch(logFailure(errorMessage));
    dispatch(logChatChunk({ ai_message: `Error: ${errorMessage}`, is_complete: false, extracted_data: currentExtractedData })); // Show error in chat
    throw error;
  }
};


// --- React Components ---

// Notification Component
const Notification = ({ message, type, onClose }) => {
  if (!message) return null;
  const bgColor = type === 'success' ? 'bg-green-500' : 'bg-red-500';
  return (
    <div className={`fixed top-5 right-5 p-4 rounded-md text-white ${bgColor} shadow-lg z-50`}>
      <span>{message}</span>
      <button onClick={onClose} className="ml-4 font-bold">X</button>
    </div>
  );
};

// InteractionForm Component
const InteractionForm = () => {
  const dispatch = useDispatch();
  const [formData, setFormData] = useState({
    hcp_name: '',
    interaction_date: new Date().toISOString().split('T')[0], // Default to today
    products_discussed: '',
    key_discussion_points: '',
    sentiment: '', // 'Positive', 'Neutral', 'Negative'
    follow_up_actions: '',
  });
  const [formError, setFormError] = useState('');
  const [formSuccess, setFormSuccess] = useState('');

  const { loading, error: reduxError } = useSelector((state) => state.interactions);
   useEffect(() => {
    if (reduxError) {
      setFormError(reduxError);
      const timer = setTimeout(() => {
        setFormError('');
        dispatch(resetError());
      }, 5000);
      return () => clearTimeout(timer);
    }
  }, [reduxError, dispatch]);


  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setFormError('');
    setFormSuccess('');
    if (!formData.hcp_name || !formData.interaction_date) {
      setFormError('HCP Name and Interaction Date are required.');
      return;
    }
    try {
      await dispatch(submitInteractionForm(formData));
      setFormSuccess('Interaction logged successfully!');
      setFormData({ // Reset form
        hcp_name: '',
        interaction_date: new Date().toISOString().split('T')[0],
        products_discussed: '',
        key_discussion_points: '',
        sentiment: '',
        follow_up_actions: '',
      });
      setTimeout(() => setFormSuccess(''), 3000);
    } catch (err) {
      // Error is handled by reduxError effect, or setFormError can be used here too
      // setFormError(err.response?.data?.detail || err.message || 'Failed to log interaction.');
      // setTimeout(() => setFormError(''), 5000);
    }
  };

  const inputClass = "mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-dark focus:ring focus:ring-primary-light focus:ring-opacity-50 text-sm p-2";
  const labelClass = "block text-sm font-medium text-gray-700";

  return (
    <form onSubmit={handleSubmit} className="space-y-6 p-4 sm:p-6 bg-white shadow-md rounded-lg">
      {formError && <Notification message={formError} type="error" onClose={() => setFormError('')} />}
      {formSuccess && <Notification message={formSuccess} type="success" onClose={() => setFormSuccess('')} />}
      
      <div>
        <label htmlFor="hcp_name" className={labelClass}>HCP Name <span className="text-red-500">*</span></label>
        <input type="text" name="hcp_name" id="hcp_name" value={formData.hcp_name} onChange={handleChange} className={inputClass} required />
      </div>
      <div>
        <label htmlFor="interaction_date" className={labelClass}>Date of Interaction <span className="text-red-500">*</span></label>
        <input type="date" name="interaction_date" id="interaction_date" value={formData.interaction_date} onChange={handleChange} className={inputClass} required />
      </div>
      <div>
        <label htmlFor="products_discussed" className={labelClass}>Products Discussed</label>
        <input type="text" name="products_discussed" id="products_discussed" value={formData.products_discussed} onChange={handleChange} className={inputClass} placeholder="e.g., ProductA, ProductB"/>
      </div>
      <div>
        <label htmlFor="key_discussion_points" className={labelClass}>Key Discussion Points</label>
        <textarea name="key_discussion_points" id="key_discussion_points" value={formData.key_discussion_points} onChange={handleChange} rows="3" className={inputClass}></textarea>
      </div>
      <div>
        <label htmlFor="sentiment" className={labelClass}>Sentiment</label>
        <select name="sentiment" id="sentiment" value={formData.sentiment} onChange={handleChange} className={inputClass}>
          <option value="">Select Sentiment</option>
          <option value="Positive">Positive</option>
          <option value="Neutral">Neutral</option>
          <option value="Negative">Negative</option>
        </select>
      </div>
      <div>
        <label htmlFor="follow_up_actions" className={labelClass}>Follow-up Actions</label>
        <textarea name="follow_up_actions" id="follow_up_actions" value={formData.follow_up_actions} onChange={handleChange} rows="2" className={inputClass}></textarea>
      </div>
      <div>
        <button type="submit" disabled={loading} className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-primary hover:bg-primary-dark focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-dark disabled:opacity-50">
          {loading ? 'Submitting...' : 'Submit Interaction'}
        </button>
      </div>
    </form>
  );
};

// InteractionChat Component
const InteractionChat = () => {
  const dispatch = useDispatch();
  const [message, setMessage] = useState('');
  const { chatHistory, loading, currentExtractedData, error: reduxError } = useSelector((state) => state.interactions);
  const chatMessagesRef = useRef(null);
  const [chatError, setChatError] = useState('');

  useEffect(() => {
    if (chatMessagesRef.current) {
      chatMessagesRef.current.scrollTop = chatMessagesRef.current.scrollHeight;
    }
  }, [chatHistory]);

  useEffect(() => {
    if (reduxError) {
      setChatError(reduxError); // Display error from Redux state if it's chat related
      const timer = setTimeout(() => {
        setChatError('');
        dispatch(resetError());
      }, 5000);
      return () => clearTimeout(timer);
    }
  }, [reduxError, dispatch]);


  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!message.trim()) return;
    setChatError('');

    // Pass current chatHistory (before adding new user message) and currentExtractedData
    const historyForAPI = [...chatHistory]; 
    try {
      await dispatch(sendChatMessage(message, historyForAPI, currentExtractedData));
      setMessage(''); // Clear input after sending
    } catch (err) {
      // Error is handled by reduxError effect
      // setChatError(err.response?.data?.detail || err.message || 'Failed to send message.');
      // setTimeout(() => setChatError(''), 5000);
    }
  };
  
  const handleClearChat = () => {
    dispatch(clearChat());
  }

  return (
    <div className="flex flex-col h-[calc(100vh-200px)] max-h-[700px] bg-white shadow-md rounded-lg">
      {chatError && <Notification message={chatError} type="error" onClose={() => setChatError('')} />}
      <div className="p-4 border-b border-gray-200 flex justify-between items-center">
        <h3 className="text-lg font-semibold text-gray-800">Chat Interaction Log</h3>
        <button 
            onClick={handleClearChat}
            className="text-sm text-primary hover:text-primary-dark"
            title="Clear chat and start over"
        >
            Clear Chat
        </button>
      </div>
      <div ref={chatMessagesRef} className="flex-grow p-4 space-y-4 overflow-y-auto chat-messages">
        {chatHistory.map((chat, index) => (
          <div key={index} className={`flex ${chat.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-xs lg:max-w-md px-4 py-2 rounded-lg shadow ${chat.role === 'user' ? 'bg-primary text-white' : 'bg-gray-200 text-gray-800'}`}>
              <p className="text-sm">{chat.content}</p>
            </div>
          </div>
        ))}
        {loading && chatHistory.length > 0 && chatHistory[chatHistory.length-1].role === 'user' && (
            <div className="flex justify-start">
                <div className="max-w-xs lg:max-w-md px-4 py-2 rounded-lg shadow bg-gray-200 text-gray-800">
                    <p className="text-sm italic">AI is thinking...</p>
                </div>
            </div>
        )}
      </div>
      <form onSubmit={handleSendMessage} className="p-4 border-t border-gray-200">
        <div className="flex items-center space-x-2">
          <input
            type="text"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder="Describe the interaction... (e.g., 'Met Dr. Smith today...')"
            className="flex-grow block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-dark focus:ring focus:ring-primary-light focus:ring-opacity-50 text-sm p-2"
            disabled={loading}
          />
          <button type="submit" disabled={loading} className="px-4 py-2 bg-primary text-white rounded-md shadow-sm hover:bg-primary-dark focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-dark disabled:opacity-50 text-sm">
            Send
          </button>
        </div>
      </form>
       {Object.keys(currentExtractedData).length > 0 && (
        <div className="p-2 border-t border-gray-100 bg-gray-50 text-xs text-gray-600">
          <p className="font-semibold mb-1">AI has extracted so far:</p>
          <ul className="list-disc list-inside pl-2">
            {Object.entries(currentExtractedData).map(([key, value]) => 
              value ? <li key={key}><span className="font-medium">{key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}:</span> {String(value)}</li> : null
            )}
          </ul>
        </div>
      )}
    </div>
  );
};


// LogInteractionScreen Component (Main View)
const LogInteractionScreen = () => {
  const [activeTab, setActiveTab] = useState('form'); // 'form' or 'chat'

  const tabButtonClass = (tabName) => 
    `py-2 px-4 font-medium text-sm rounded-md focus:outline-none transition-colors duration-150 ease-in-out ` +
    (activeTab === tabName 
      ? 'bg-primary text-white shadow-md' 
      : 'text-gray-600 hover:bg-gray-200 hover:text-gray-800');

  return (
    <div className="min-h-screen bg-gray-100 py-8 px-4 sm:px-6 lg:px-8 font-sans">
      <div className="max-w-2xl mx-auto">
        <header className="mb-6 text-center">
          <h1 className="text-3xl font-bold text-gray-800">Log HCP Interaction</h1>
          <p className="text-sm text-gray-500 mt-1">Choose your preferred method to log interactions.</p>
        </header>
        
        <div className="mb-6 flex justify-center space-x-2 p-1 bg-gray-200 rounded-lg shadow-sm">
          <button onClick={() => setActiveTab('form')} className={tabButtonClass('form')}>
            Structured Form
          </button>
          <button onClick={() => setActiveTab('chat')} className={tabButtonClass('chat')}>
            Conversational Chat
          </button>
        </div>

        <div>
          {activeTab === 'form' ? <InteractionForm /> : <InteractionChat />}
        </div>
      </div>
    </div>
  );
};

// App Component (Root)
function App() {
  return (
    <Provider store={store}>
      <LogInteractionScreen />
    </Provider>
  );
}

export default App;
