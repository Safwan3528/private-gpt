import requests
import json
from flask import Flask, render_template_string, request, jsonify, session, redirect, url_for
import webbrowser
from threading import Timer
import uuid
import os
import signal
from werkzeug.serving import WSGIRequestHandler
from datetime import datetime
from werkzeug.utils import secure_filename
import PyPDF2
import docx

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'doc', 'docx'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def get_available_models():
    url = "http://localhost:11434/api/tags"
    response = requests.get(url)
    if response.status_code == 200:
        models = json.loads(response.text)['models']
        return [model['name'] for model in models]
    else:
        return []

def generate_response(prompt, model):
    url = "http://localhost:11434/api/generate"
    data = {
        "model": model,
        "prompt": prompt,
        "stream": False
    }
    
    response = requests.post(url, json=data)
    if response.status_code == 200:
        return json.loads(response.text)['response']
    else:
        return f"Error: {response.status_code} - {response.text}"

@app.route('/')
def home():
    if 'user_id' not in session:
        session['user_id'] = str(uuid.uuid4())
    if 'current_model' not in session:
        session['current_model'] = 'phi'
    available_models = get_available_models()
    chat_history = get_chat_history()  # Ambil chat history
    return render_template_string('''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Private GPT</title>
        <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
        <style>
            html, body {
                height: 100%;
                margin: 0;
                padding: 0;
                overflow: hidden;
            }
            body {
                font-family: Arial, sans-serif;
                display: flex;
                transition: background-color 0.3s, color 0.3s;
            }
            body.dark-mode {
                background-color: #343541;
                color: #FFFFFF;
            }
            body.light-mode {
                background-color: #FFFFFF;
                color: #000000;
            }
            .sidebar {
                width: 250px;
                transition: width 0.3s;
                overflow-x: hidden;
                display: flex;
                flex-direction: column;
                height: 100vh;
            }
            .sidebar.collapsed {
                width: 60px;
            }
            .sidebar-toggle {
                cursor: pointer;
                font-size: 24px;
                margin-bottom: 20px;
            }
            .sidebar-content {
                width: 250px;
                transition: width 0.3s;
                flex-grow: 1;
                overflow-y: auto;
            }
            .sidebar.collapsed .sidebar-content {
                width: 60px;
            }
            .sidebar.collapsed .hide-on-collapse {
                display: none;
            }
            .sidebar.collapsed .settings-icon,
            .sidebar.collapsed .dark-mode-toggle {
                margin-right: 0;
                justify-content: center;
            }
            .logo {
                font-weight: bold;
                font-size: 24px;
                margin-bottom: 20px;
                text-align: center;
            }
            .sidebar.collapsed .logo {
                font-size: 18px;
            }
            .sidebar-footer {
                margin-top: auto;
                padding: 10px; /* Add some padding above the footer */
            }
            .delete-history, .end-session-btn {
                background-color: #FF4136;
                color: white;
                border: none;
                padding: 10px;
                cursor: pointer;
                margin-top: 10px;
                width: 100%;
                transition: background-color 0.3s;
            }
            .delete-history:hover, .end-session-btn:hover {
                background-color: #FF1A1A;
            }
            .sidebar-toggle {
                align-self: flex-end;
                background: none;
                border: none;
                font-size: 24px;
                cursor: pointer;
                margin-bottom: 20px;
            }
            .sidebar-content {
                display: flex;
                flex-direction: column;
                width: 100%;
            }
            .sidebar.collapsed .sidebar-content > *:not(.sidebar-toggle) {
                display: none;
            }
            .sidebar.collapsed .sidebar-toggle {
                align-self: center;
            }
            .dark-mode .sidebar {
                background-color: #202123;
            }
            .light-mode .sidebar {
                background-color: #F0F0F0;
            }
            .chat-container {
                flex-grow: 1;
                display: flex;
                flex-direction: column;
                height: 100vh;
            }
            .header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 10px 20px;
                transition: background-color 0.3s;
            }
            .dark-mode .header {
                background-color: #202123;
            }
            .light-mode .header {
                background-color: #F0F0F0;
            }
            .logo {
                font-weight: bold;
            }
            .main-content {
                display: flex;
                flex-direction: column;
                flex-grow: 1;
                padding: 20px;
                overflow: hidden;
            }
            .chat-area {
                flex-grow: 1;
                overflow-y: auto;
                margin-bottom: 20px;
                display: flex;
                flex-direction: column;
            }
            .message {
                max-width: 70%;
                padding: 10px;
                border-radius: 10px;
                margin-bottom: 10px;
                transition: background-color 0.3s;
            }
            .user-message {
                align-self: flex-end;
                background-color: #5C5D70;
            }
            .ai-message {
                align-self: flex-start;
                background-color: #3E3F4B;
            }
            .dark-mode .user-message {
                background-color: #5C5D70;
            }
            .dark-mode .ai-message {
                background-color: #3E3F4B;
            }
            .light-mode .user-message {
                background-color: #E1E1E1;
            }
            .light-mode .ai-message {
                background-color: #D1D1D1;
            }
            .chat-input {
                position: relative;
                display: flex;
                align-items: center;
            }
            #user-input {
                width: 100%;
                padding: 10px 70px 10px 10px; /* Reduced right padding */
                border-radius: 20px;
                border: 1px solid #5C5C5C;
                transition: background-color 0.3s, color 0.3s;
            }
            .attachment-icon, .send-icon {
                position: absolute;
                top: 50%;
                transform: translateY(-50%);
                cursor: pointer;
                font-size: 20px;
                background: none;
                border: none;
                padding: 0;
            }
            .attachment-icon {
                right: 35px; /* Moved closer to the send icon */
                color: #007BFF;
            }
            .send-icon {
                position: absolute;
                right: 15px; /* Ubah dari 10px ke 15px untuk menganjak ke dalam */
                top: 50%;
                transform: translateY(-50%);
                cursor: pointer;
                font-size: 20px;
                background: none;
                border: none;
                padding: 5px; /* Tambah sedikit padding */
                color: #007BFF;
            }
            .dark-mode #user-input {
                background-color: #40414F;
                color: #FFFFFF;
            }
            .light-mode #user-input {
                background-color: #FFFFFF;
                color: #000000;
            }
            .footer {
                text-align: center;
                padding: 10px;
                font-size: 0.8em;
            }
            .dark-mode .footer {
                color: #8E8EA0;
            }
            .light-mode .footer {
                color: #666666;
            }
            .new-chat, #dark-mode-toggle {
                color: white;
                border: none;
                padding: 10px;
                cursor: pointer;
                margin-bottom: 10px;
                width: 100%;
                transition: background-color 0.3s;
            }
            .dark-mode .new-chat, .dark-mode #dark-mode-toggle {
                background-color: #3E3F4B;
            }
            .light-mode .new-chat, .light-mode #dark-mode-toggle {
                background-color: #007BFF;
            }
            .switch {
                position: relative;
                display: inline-block;
                width: 60px;
                height: 34px;
            }
            .switch input {
                opacity: 0;
                width: 0;
                height: 0;
            }
            .slider {
                position: absolute;
                cursor: pointer;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background-color: #ccc;
                transition: .4s;
                border-radius: 34px;
            }
            .slider:before {
                position: absolute;
                content: "";
                height: 26px;
                width: 26px;
                left: 4px;
                bottom: 4px;
                background-color: white;
                transition: .4s;
                border-radius: 50%;
            }
            input:checked + .slider {
                background-color: #2196F3;
            }
            input:checked + .slider:before {
                transform: translateX(26px);
            }
            .dark-mode-label {
                margin-left: 10px;
                vertical-align: super;
            }
            .model-selector {
                margin-bottom: 10px;
            }
            #model-select {
                width: 100%;
                padding: 5px;
                border-radius: 5px;
                background-color: #3E3F4B;
                color: white;
                border: 1px solid #5C5C5C;
            }
            .settings-icon {
                font-size: 24px;
                cursor: pointer;
                margin-bottom: 10px;
                text-align: center;
            }
            .settings-panel {
                display: none;
                background-color: #3E3F4B;
                padding: 10px;
                border-radius: 5px;
                margin-bottom: 10px;
            }
            .modal {
                display: none;
                position: fixed;
                z-index: 1;
                left: 0;
                top: 0;
                width: 100%;
                height: 100%;
                overflow: auto;
                background-color: rgba(0,0,0,0.4);
            }
            .modal-content {
                background-color: #fefefe;
                margin: 15% auto;
                padding: 20px;
                border: 1px solid #888;
                width: 80%;
                max-width: 600px;
                border-radius: 5px;
            }
            .close {
                color: #aaa;
                float: right;
                font-size: 28px;
                font-weight: bold;
                cursor: pointer;
            }
            .close:hover,
            .close:focus {
                color: black;
                text-decoration: none;
                cursor: pointer;
            }
            .tab {
                overflow: hidden;
                border-bottom: 1px solid #ccc;
                background-color: #f1f1f1;
            }
            .tab button {
                background-color: inherit;
                float: left;
                border: none;
                outline: none;
                cursor: pointer;
                padding: 14px 16px;
                transition: 0.3s;
            }
            .tab button:hover {
                background-color: #ddd;
            }
            .tab button.active {
                background-color: #ccc;
            }
            .tabcontent {
                display: none;
                padding: 6px 12px;
                border-top: none;
            }
            .top-controls {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 10px;
            }
            .settings-and-mode {
                display: flex;
                align-items: center;
            }
            .settings-icon {
                margin-right: 10px;
            }
            .dark-mode-toggle {
                display: flex;
                align-items: center;
            }
            .chat-history-item {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 5px;
                cursor: pointer;
            }
            .chat-info {
                flex-grow: 1;
            }
            .chat-title {
                display: block;
            }
            .chat-date {
                font-size: 0.8em;
                color: #888;
            }
            .delete-chat-btn {
                background-color: transparent;
                border: none;
                color: #FF4136;
                cursor: pointer;
                font-size: 18px;
                padding: 0 5px;
            }
            .chat-input {
                display: flex;
                align-items: center;
            }
            #user-input {
                flex-grow: 1;
                padding: 10px;
                border-radius: 20px;
                border: 1px solid #5C5C5C;
                margin-right: 10px;
            }
            .send-icon, .attachment-icon {
                background: none;
                border: none;
                cursor: pointer;
                font-size: 20px;
                color: #007BFF;
            }
            .attachment-icon {
                margin-right: 10px;
            }
            .sidebar-footer {
                margin-top: auto;
                padding: 10px;
            }
            .sidebar-button {
                width: 100%;
                padding: 10px;
                margin-bottom: 10px;
                border: none;
                border-radius: 5px;
                cursor: pointer;
                transition: background-color 0.3s;
            }
            .new-chat {
                background-color: #4CAF50;
                color: white;
            }
            .new-chat:hover {
                background-color: #45a049;
            }
            .end-session-btn {
                background-color: #FF4136;
                color: white;
            }
            .end-session-btn:hover {
                background-color: #FF1A1A;
            }
            .delete-history {
                background-color: #FF4136;
                color: white;
            }
            .delete-history:hover {
                background-color: #FF1A1A;
            }
        </style>
    </head>
    <body class="dark-mode">
        <div class="sidebar" id="sidebar">
            <div class="sidebar-content">
                <button class="sidebar-toggle" onclick="toggleSidebar()">☰</button>
                <div class="top-controls">
                    <div class="settings-and-mode">
                        <div class="settings-icon" onclick="openSettingsModal()">
                            ⚙️
                        </div>
                        <div class="dark-mode-toggle">
                            <label class="switch">
                                <input type="checkbox" id="dark-mode-toggle" checked onchange="toggleDarkMode()">
                                <span class="slider"></span>
                            </label>
                            <span class="dark-mode-label hide-on-collapse">Dark</span>
                        </div>
                    </div>
                </div>
                <button class="sidebar-button new-chat" onclick="newChat()">New Chat</button>
                <div class="chat-history hide-on-collapse" id="chat-history">
                    {% for chat in chat_history %}
                    <div class="chat-history-item">
                        <div class="chat-info" onclick="loadChat('{{ chat.id }}')">
                            <span class="chat-title">{{ chat.title }}</span>
                            <span class="chat-date">{{ chat.date }}</span>
                        </div>
                        <button class="delete-chat-btn" onclick="deleteChat('{{ chat.id }}', event)">🗑️</button>
                    </div>
                    {% endfor %}
                </div>
            </div>
            <div class="sidebar-footer hide-on-collapse">
                <button class="sidebar-button delete-history" onclick="deleteAllHistory()">Delete All History</button>
                <button class="sidebar-button end-session-btn" onclick="endSession()">End Session & Exit</button>
            </div>
        </div>
        <div class="chat-container">
            <div class="header">
                <div class="logo">Private GPT</div>
            </div>
            <div class="main-content">
                <div class="chat-area" id="chat-area"></div>
                <div class="chat-input">
                    <input type="text" id="user-input" placeholder="Type your message here...">
                    <input type="file" id="file-upload" style="display: none;" onchange="handleFileUpload(this.files)">
                    <button class="attachment-icon" onclick="document.getElementById('file-upload').click()">📎</button>
                    <button class="send-icon" onclick="sendMessage()">➤</button>
                </div>
            </div>
            <div class="footer">
                All rights reserved Group 5 BTE1034
            </div>
        </div>

        <!-- Modal -->
        <div id="settingsModal" class="modal">
            <div class="modal-content">
                <span class="close" onclick="closeSettingsModal()">&times;</span>
                <div class="tab">
                    <button class="tablinks" onclick="openTab(event, 'ModelSelection')" id="defaultOpen">Model Selection</button>
                    <button class="tablinks" onclick="openTab(event, 'OpenAI')">OpenAI API</button>
                    <button class="tablinks" onclick="openTab(event, 'About')">About</button>
                </div>
                
                <div id="ModelSelection" class="tabcontent">
                    <h3>Model Selection</h3>
                    <div class="model-selector">
                        <label for="model-select">Select Model:</label>
                        <select id="model-select" onchange="changeModel()">
                            {% for model in available_models %}
                            <option value="{{ model }}" {% if model == session.current_model %}selected{% endif %}>{{ model }}</option>
                            {% endfor %}
                        </select>
                    </div>
                </div>
                
                <div id="OpenAI" class="tabcontent">
                    <h3>OpenAI API</h3>
                    <p>Enter your OpenAI API key:</p>
                    <input type="text" id="openai-api-key" placeholder="API Key">
                    <button onclick="saveOpenAIKey()">Save</button>
                </div>
                
                <div id="About" class="tabcontent">
                    <h3>About</h3>
                    <p>PrivateGPT is a locally hosted AI chat application.</p>
                    <p>Version: 1.0</p>
                    <p>Developed by: Group 5 BTE1034</p>
                </div>
            </div>
        </div>

        <script>
            let currentChatId = null;
            let isDarkMode = true;

            function toggleDarkMode() {
                isDarkMode = !isDarkMode;
                document.body.classList.toggle('dark-mode', isDarkMode);
                document.body.classList.toggle('light-mode', !isDarkMode);
                localStorage.setItem('darkMode', isDarkMode);
                document.querySelector('.dark-mode-label').textContent = isDarkMode ? 'Dark Mode' : 'Light Mode';
            }

            function loadDarkModePreference() {
                const savedMode = localStorage.getItem('darkMode');
                if (savedMode !== null) {
                    isDarkMode = savedMode === 'true';
                    document.getElementById('dark-mode-toggle').checked = isDarkMode;
                    toggleDarkMode();
                }
            }

            function toggleSidebar() {
                const sidebar = document.getElementById('sidebar');
                sidebar.classList.toggle('collapsed');
            }

            function newChat() {
                currentChatId = null;
                $('#chat-area').empty();
                $('#user-input').val('');
            }

            function changeModel() {
                var selectedModel = document.getElementById('model-select').value;
                fetch('/change_model', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/x-www-form-urlencoded',
                    },
                    body: 'model=' + encodeURIComponent(selectedModel)
                })
                .then(response => response.json())
                .then(data => {
                    console.log('Model changed to: ' + data.model);
                });
            }

            function sendMessage() {
                var userInput = $('#user-input').val();
                if (userInput.trim() === '') return;

                $('#chat-area').append('<div class="message user-message"><strong>You:</strong> ' + userInput + '</div>');
                $('#user-input').val('');
                $('#chat-area').scrollTop($('#chat-area')[0].scrollHeight);

                $.ajax({
                    url: '/get_response',
                    method: 'POST',
                    data: JSON.stringify({'prompt': userInput, 'chat_id': currentChatId}),
                    contentType: 'application/json',
                    success: function(response) {
                        currentChatId = response.chat_id;
                        $('#chat-area').append('<div class="message ai-message"><strong>AI:</strong> ' + response.response + '</div>');
                        $('#chat-area').scrollTop($('#chat-area')[0].scrollHeight);
                    }
                });
            }

            $('#user-input').keydown(function(e) {
                if (e.keyCode == 13) {
                    sendMessage();
                }
            });

            function openSettingsModal() {
                document.getElementById('settingsModal').style.display = 'block';
                document.getElementById("defaultOpen").click();
            }

            function closeSettingsModal() {
                document.getElementById('settingsModal').style.display = 'none';
            }

            function openTab(evt, tabName) {
                var i, tabcontent, tablinks;
                tabcontent = document.getElementsByClassName("tabcontent");
                for (i = 0; i < tabcontent.length; i++) {
                    tabcontent[i].style.display = "none";
                }
                tablinks = document.getElementsByClassName("tablinks");
                for (i = 0; i < tablinks.length; i++) {
                    tablinks[i].className = tablinks[i].className.replace(" active", "");
                }
                document.getElementById(tabName).style.display = "block";
                evt.currentTarget.className += " active";
            }

            function saveOpenAIKey() {
                var apiKey = document.getElementById("openai-api-key").value;
                // Implement the logic to save the API key
                console.log("Saving OpenAI API key:", apiKey);
                // You might want to send this to the server to save it securely
            }

            // When the user clicks anywhere outside of the modal, close it
            window.onclick = function(event) {
                var modal = document.getElementById('settingsModal');
                if (event.target == modal) {
                    modal.style.display = "none";
                }
            }

            function loadChat(chatId) {
                currentChatId = chatId;
                $.get(`/get_chat/${chatId}`, function(data) {
                    $('#chat-area').empty();
                    data.messages.forEach(function(message) {
                        const messageClass = message.sender === 'You' ? 'user-message' : 'ai-message';
                        $('#chat-area').append(`<div class="message ${messageClass}"><strong>${message.sender}:</strong> ${message.content}</div>`);
                    });
                    $('#chat-area').scrollTop($('#chat-area')[0].scrollHeight);
                });
            }

            function deleteAllHistory() {
                if (confirm("Are you sure you want to delete all chat history?")) {
                    $.post('/delete_history', function() {
                        $('#chat-history').empty();
                        newChat();
                    });
                }
            }

            function endSession() {
                if (confirm("Are you sure you want to end the session and exit?")) {
                    $.post('/end_session', function() {
                        window.location.href = '/session_ended';
                    });
                }
            }

            function deleteChat(chatId, event) {
                event.stopPropagation();  // Prevent loadChat from being called
                if (confirm("Are you sure you want to delete this chat?")) {
                    $.post('/delete_chat/' + chatId, function(response) {
                        if (response.success) {
                            $(event.target).closest('.chat-history-item').remove();
                            if (currentChatId === chatId) {
                                $('#chat-area').empty();
                                currentChatId = null;
                            }
                        } else {
                            alert("Failed to delete chat.");
                        }
                    });
                }
            }

            function handleFileUpload(files) {
                if (files.length > 0) {
                    const file = files[0];
                    const formData = new FormData();
                    formData.append('file', file);

                    $.ajax({
                        url: '/upload_document',
                        type: 'POST',
                        data: formData,
                        processData: false,
                        contentType: false,
                        success: function(response) {
                            if (response.success) {
                                $('#user-input').val(`I've uploaded a document named ${file.name}. `);
                                $('#user-input').focus();
                            } else {
                                alert('Error uploading file: ' + response.error);
                            }
                        },
                        error: function() {
                            alert('Error uploading file');
                        }
                    });
                }
            }

            function loadChatHistory() {
                $.get('/get_chat_history', function(data) {
                    $('#chat-history').empty();
                    data.forEach(function(chat) {
                        $('#chat-history').append(`
                            <div class="chat-history-item">
                                <div class="chat-info" onclick="loadChat('${chat.id}')">
                                    <span class="chat-title">${chat.title}</span>
                                    <span class="chat-date">${chat.date}</span>
                                </div>
                                <button class="delete-chat-btn" onclick="deleteChat('${chat.id}', event)">🗑️</button>
                            </div>
                        `);
                    });
                });
            }

            // Call this function when the page loads
            $(document).ready(function() {
                loadChatHistory();
            });

            loadDarkModePreference();
            document.getElementById("defaultOpen").click();
        </script>
    </body>
    </html>
    ''', available_models=available_models, chat_history=chat_history)

@app.route('/get_response', methods=['POST'])
def get_response():
    data = request.json
    prompt = data['prompt']
    chat_id = data['chat_id']
    
    if not chat_id:
        chat_id = datetime.now().strftime("%Y%m%d%H%M%S")
    
    current_model = session.get('current_model', 'phi')
    
    # If the prompt is asking to summarize the uploaded document
    if prompt.startswith("Summarize the uploaded document:"):
        # Retrieve the document content from the chat history
        chat = get_chat(chat_id)
        if chat:
            document_content = next((msg['content'] for msg in reversed(chat['messages']) if msg['sender'] == 'System' and msg['content'].startswith("Uploaded document:")), None)
            if document_content:
                prompt = f"Please summarize the following document:\n\n{document_content}"
    
    response = generate_response(prompt, current_model)
    
    save_chat_message(chat_id, 'You', prompt)
    save_chat_message(chat_id, 'AI', response)
    
    return jsonify({'response': response, 'chat_id': chat_id})

@app.route('/get_chat_history')
def get_chat_history_route():
    return jsonify(get_chat_history())

@app.route('/get_chat/<chat_id>')
def get_chat_route(chat_id):
    chat = get_chat(chat_id)
    if chat:
        return jsonify(chat)
    return jsonify({'error': 'Chat not found'}), 404

@app.route('/delete_chat/<chat_id>', methods=['POST'])
def delete_chat_route(chat_id):
    success = delete_chat(chat_id)
    return jsonify({'success': success})

@app.route('/delete_history', methods=['POST'])
def delete_history_route():
    success = delete_all_history()
    return jsonify({'success': success})

@app.route('/change_model', methods=['POST'])
def change_model():
    model = request.form['model']
    session['current_model'] = model
    return jsonify({'model': model})

@app.route('/end_session', methods=['POST'])
def end_session():
    return jsonify({'success': True})

@app.route('/session_ended')
def session_ended():
    return '''
    <html>
        <head>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    margin: 0;
                    background-color: #f0f0f0;
                }
                .message {
                    text-align: center;
                    padding: 20px;
                    background-color: white;
                    border-radius: 5px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }
            </style>
        </head>
        <body>
            <div class="message">
                <h1>Session Ended</h1>
                <p>You can now close this window.</p>
                <p>Thank you for using PrivateGPT!</p>
            </div>
            <script>
                fetch('/shutdown', { method: 'POST' });
            </script>
        </body>
    </html>
    '''

@app.route('/shutdown', methods=['POST'])
def shutdown():
    os.kill(os.getpid(), signal.SIGINT)
    return 'Server shutting down...'

def save_chat_message(chat_id, sender, content):
    chat_dir = os.path.join('chat_history', chat_id)
    os.makedirs(chat_dir, exist_ok=True)
    
    message = {
        'sender': sender,
        'content': content,
        'timestamp': datetime.now().isoformat()
    }
    
    messages_file = os.path.join(chat_dir, 'messages.json')
    if os.path.exists(messages_file):
        with open(messages_file, 'r') as f:
            messages = json.load(f)
    else:
        messages = []
    
    messages.append(message)
    
    with open(messages_file, 'w') as f:
        json.dump(messages, f, indent=2)

def get_chat_history():
    chat_history = []
    chat_dir = 'chat_history'
    if os.path.exists(chat_dir):
        for chat_id in os.listdir(chat_dir):
            messages_file = os.path.join(chat_dir, chat_id, 'messages.json')
            if os.path.exists(messages_file):
                with open(messages_file, 'r') as f:
                    messages = json.load(f)
                if messages:
                    first_message = messages[0]
                    chat_date = datetime.fromisoformat(first_message['timestamp']).strftime("%Y-%m-%d %H:%M")
                    chat_title = generate_chat_title(messages)
                    chat_history.append({
                        'id': chat_id,
                        'title': chat_title,
                        'date': chat_date
                    })
    return sorted(chat_history, key=lambda x: x['id'], reverse=True)

def get_chat(chat_id):
    messages_file = os.path.join('chat_history', chat_id, 'messages.json')
    if os.path.exists(messages_file):
        with open(messages_file, 'r') as f:
            messages = json.load(f)
        return {'id': chat_id, 'messages': messages}
    return None

def delete_chat(chat_id):
    chat_dir = os.path.join('chat_history', chat_id)
    if os.path.exists(chat_dir):
        for file in os.listdir(chat_dir):
            os.remove(os.path.join(chat_dir, file))
        os.rmdir(chat_dir)
        return True
    return False

def delete_all_history():
    chat_dir = 'chat_history'
    if os.path.exists(chat_dir):
        for chat_id in os.listdir(chat_dir):
            delete_chat(chat_id)
        return True
    return False

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def read_file_content(file_path):
    _, file_extension = os.path.splitext(file_path)
    content = ""

    if file_extension == '.txt':
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
    elif file_extension == '.pdf':
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                content += page.extract_text()
    elif file_extension in ['.doc', '.docx']:
        doc = docx.Document(file_path)
        for para in doc.paragraphs:
            content += para.text + "\n"

    return content

@app.route('/upload_document', methods=['POST'])
def upload_document():
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file part'})
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No selected file'})
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        # Read the content of the file
        content = read_file_content(file_path)
        
        # Save the content to the current chat
        chat_id = session.get('current_chat_id')
        if not chat_id:
            chat_id = datetime.now().strftime("%Y%m%d%H%M%S")
            session['current_chat_id'] = chat_id
        
        save_chat_message(chat_id, 'System', f"Uploaded document: {filename}")
        save_chat_message(chat_id, 'System', content[:1000] + "..." if len(content) > 1000 else content)
        
        return jsonify({'success': True})
    
    return jsonify({'success': False, 'error': 'File type not allowed'})

class CustomRequestHandler(WSGIRequestHandler):
    def log_message(self, format, *args):
        if "GET / HTTP/1.1" in args[0]:
            print("Welcome to PrivateGPT 1.0 - Developed by: Group 5 BTE1034")
        elif "POST" not in args[0]:  # Tidak mencetak log untuk permintaan POST
            super().log_message(format, *args)

def open_browser():
    webbrowser.open_new('http://127.0.0.1:5000/')

def generate_chat_title(messages):
    # Try to generate a title based on the first few messages
    user_messages = [msg['content'] for msg in messages if msg['sender'] == 'You']
    if user_messages:
        title = user_messages[0][:30]  # Use the first 30 characters of the first user message
        return title + "..." if len(title) == 30 else title
    return "Untitled Chat"

if __name__ == '__main__':
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    Timer(1, open_browser).start()
    app.run(debug=False, use_reloader=False, request_handler=CustomRequestHandler)