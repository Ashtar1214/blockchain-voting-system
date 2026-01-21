from flask import Flask, render_template_string, request, jsonify
import hashlib
import time
import threading
import json
from datetime import datetime

app = Flask(__name__)

# ========== BLOCKCHAIN CLASSES ==========
class Block:
    def __init__(self, index, transactions, timestamp, previous_hash):
        self.index = index
        self.transactions = transactions
        self.timestamp = timestamp
        self.previous_hash = previous_hash
        self.nonce = 0
        self.hash = self.calculate_hash()
    
    def calculate_hash(self):
        block_string = json.dumps({
            "index": self.index,
            "transactions": self.transactions,
            "timestamp": self.timestamp,
            "previous_hash": self.previous_hash,
            "nonce": self.nonce
        }, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()
    
    def mine_block(self, difficulty):
        """Simple Proof of Work"""
        print(f"⛏️  Mining block {self.index}...")
        while self.hash[:difficulty] != "0" * difficulty:
            self.nonce += 1
            self.hash = self.calculate_hash()
        print(f"✅ Block {self.index} mined! Hash: {self.hash[:16]}...")
    
    def to_dict(self):
        return {
            "index": self.index,
            "transactions": self.transactions,
            "timestamp": datetime.fromtimestamp(self.timestamp).strftime('%H:%M:%S'),
            "previous_hash": self.previous_hash[:16] + "...",
            "hash": self.hash[:16] + "...",
            "nonce": self.nonce
        }

class Blockchain:
    def __init__(self):
        self.chain = []
        self.difficulty = 2  # Lower difficulty for faster mining
        self.pending_transactions = []  # Votes waiting to be mined
        self.voted_voters = set()  # Track who has voted (including pending)
        self.create_genesis_block()
    
    def create_genesis_block(self):
        """Create the first block in the chain"""
        genesis = Block(0, [{"message": "Genesis Block"}], time.time(), "0")
        genesis.mine_block(self.difficulty)
        self.chain.append(genesis)
        print("✅ Genesis block created")
    
    def get_latest_block(self):
        return self.chain[-1]
    
    def add_vote(self, voter_id, candidate):
        """Add a vote to pending transactions"""
        if voter_id in self.voted_voters:
            return False, "This voter has already voted"
        
        transaction = {
            "type": "vote",
            "voter_id": voter_id,
            "candidate": candidate,
            "timestamp": time.time()
        }
        
        self.pending_transactions.append(transaction)
        self.voted_voters.add(voter_id)  # Mark as voted
        print(f"✅ Vote added: {voter_id} -> {candidate}")
        return True, "Vote added successfully"
    
    def mine_pending_transactions(self):
        """Mine all pending votes into a new block"""
        if not self.pending_transactions:
            print("ℹ️  No votes to mine")
            return False, "No votes to mine"
        
        print(f"⛏️  Mining {len(self.pending_transactions)} votes...")
        
        # Create new block
        new_block = Block(
            len(self.chain),
            self.pending_transactions.copy(),  # Copy to avoid reference issues
            time.time(),
            self.get_latest_block().hash
        )
        
        new_block.mine_block(self.difficulty)
        self.chain.append(new_block)
        
        # Clear pending transactions (they're now in the blockchain)
        mined_count = len(self.pending_transactions)
        self.pending_transactions = []
        
        print(f"✅ Successfully mined {mined_count} votes into block #{new_block.index}")
        return True, f"Mined {mined_count} votes into block #{new_block.index}"
    
    def get_results(self):
        """Get current vote counts from blockchain"""
        results = {}
        
        # Count votes from mined blocks
        for block in self.chain[1:]:  # Skip genesis block
            for transaction in block.transactions:
                if isinstance(transaction, dict) and 'candidate' in transaction:
                    candidate = transaction['candidate']
                    results[candidate] = results.get(candidate, 0) + 1
        
        # Also count pending votes
        for transaction in self.pending_transactions:
            if isinstance(transaction, dict) and 'candidate' in transaction:
                candidate = transaction['candidate']
                results[candidate] = results.get(candidate, 0) + 1
        
        return results
    
    def get_chain_data(self):
        """Get blockchain data for display"""
        return {
            "blocks": [block.to_dict() for block in self.chain],
            "pending_count": len(self.pending_transactions),
            "total_votes": sum(len(block.transactions) for block in self.chain[1:]) + len(self.pending_transactions)
        }
    
    def validate_voter(self, voter_id):
        """Check if voter can vote"""
        return voter_id not in self.voted_voters
    
    def is_chain_valid(self):
        """Validate blockchain integrity"""
        for i in range(1, len(self.chain)):
            current = self.chain[i]
            previous = self.chain[i-1]
            
            if current.hash != current.calculate_hash():
                return False
            if current.previous_hash != previous.hash:
                return False
        
        return True

# ========== VOTING SYSTEM ==========
class VotingSystem:
    def __init__(self):
        self.blockchain = Blockchain()
        self.registered_voters = {}  # voter_id: token
        self.candidates = ["Alice", "Bob", "Charlie", "Diana", "Edward"]
    
    def register_voter(self, voter_id):
        """Register a new voter"""
        if voter_id in self.registered_voters:
            return False, "Voter already registered", None
        
        # Generate secure token
        token = hashlib.sha256(f"{voter_id}{time.time()}".encode()).hexdigest()[:12]
        self.registered_voters[voter_id] = token
        
        print(f"✅ Registered voter: {voter_id} (token: {token})")
        return True, "Registration successful", token
    
    def verify_voter(self, voter_id, token):
        """Verify voter credentials"""
        if voter_id not in self.registered_voters:
            return False, "Voter not registered"
        
        if self.registered_voters.get(voter_id) != token:
            return False, "Invalid token"
        
        return True, "Verification successful"
    
    def cast_vote(self, voter_id, token, candidate):
        """Process a vote"""
        # Verify voter
        is_valid, message = self.verify_voter(voter_id, token)
        if not is_valid:
            return False, message
        
        # Check candidate
        if candidate not in self.candidates:
            return False, f"Invalid candidate. Choose from: {', '.join(self.candidates)}"
        
        # Add vote to blockchain
        success, message = self.blockchain.add_vote(voter_id, candidate)
        return success, message
    
    def get_results(self):
        """Get voting results"""
        return self.blockchain.get_results()
    
    def get_voter_status(self):
        """Get status of all voters"""
        status = {}
        for voter_id, token in self.registered_voters.items():
            has_voted = not self.blockchain.validate_voter(voter_id)
            status[voter_id] = {
                "registered": True,
                "has_voted": has_voted,
                "token_preview": token[:4] + "****",
                "voted_at": "Pending" if has_voted and voter_id in [t.get('voter_id') for t in self.blockchain.pending_transactions] else "Mined" if has_voted else "Not voted"
            }
        return status
    
    def mine_votes(self):
        """Mine pending votes"""
        return self.blockchain.mine_pending_transactions()

# ========== INITIALIZE SYSTEM ==========
voting_system = VotingSystem()

# Auto-mining thread (mines every 20 seconds)
def auto_mining_thread():
    while True:
        time.sleep(20)
        if voting_system.blockchain.pending_transactions:
            success, message = voting_system.mine_votes()
            if success:
                print(f"🤖 Auto-mined: {message}")

threading.Thread(target=auto_mining_thread, daemon=True).start()

# ========== HTML TEMPLATE ==========
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Blockchain Voting System</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
            color: #333;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        
        .header {
            text-align: center;
            color: white;
            margin-bottom: 30px;
            padding: 20px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 15px;
            backdrop-filter: blur(10px);
        }
        
        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        
        .header p {
            font-size: 1.1em;
            opacity: 0.9;
        }
        
        .nav-buttons {
            display: flex;
            justify-content: center;
            gap: 10px;
            margin-bottom: 30px;
            flex-wrap: wrap;
        }
        
        .nav-btn {
            background: rgba(255, 255, 255, 0.2);
            color: white;
            border: 2px solid white;
            padding: 12px 24px;
            border-radius: 30px;
            cursor: pointer;
            font-weight: bold;
            transition: all 0.3s ease;
            font-size: 14px;
        }
        
        .nav-btn:hover {
            background: white;
            color: #667eea;
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(0,0,0,0.2);
        }
        
        .nav-btn.active {
            background: white;
            color: #667eea;
        }
        
        .content-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 25px;
        }
        
        .card {
            background: white;
            border-radius: 15px;
            padding: 30px;
            box-shadow: 0 15px 35px rgba(0,0,0,0.1);
            transition: transform 0.3s ease;
        }
        
        .card:hover {
            transform: translateY(-5px);
        }
        
        .card h2 {
            color: #444;
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 3px solid #667eea;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .card h2::before {
            font-size: 1.2em;
        }
        
        .form-group {
            margin-bottom: 20px;
        }
        
        .form-group label {
            display: block;
            margin-bottom: 8px;
            color: #555;
            font-weight: 600;
            font-size: 14px;
        }
        
        .form-control {
            width: 100%;
            padding: 14px;
            border: 2px solid #e1e5e9;
            border-radius: 8px;
            font-size: 16px;
            transition: all 0.3s;
            background: #f8f9fa;
        }
        
        .form-control:focus {
            border-color: #667eea;
            background: white;
            outline: none;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }
        
        select.form-control {
            appearance: none;
            background-image: url("data:image/svg+xml;charset=UTF-8,%3csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3e%3cpolyline points='6 9 12 15 18 9'%3e%3c/polyline%3e%3c/svg%3e");
            background-repeat: no-repeat;
            background-position: right 15px center;
            background-size: 16px;
            padding-right: 40px;
        }
        
        .btn {
            display: inline-block;
            width: 100%;
            padding: 15px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            font-weight: bold;
            cursor: pointer;
            transition: all 0.3s;
            text-align: center;
            margin-top: 10px;
        }
        
        .btn:hover {
            opacity: 0.9;
            transform: translateY(-2px);
            box-shadow: 0 7px 14px rgba(102, 126, 234, 0.3);
        }
        
        .btn-secondary {
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        }
        
        .result-box {
            margin-top: 20px;
            padding: 20px;
            border-radius: 8px;
            background: #f8f9fa;
            border-left: 4px solid #667eea;
            font-size: 14px;
        }
        
        .success {
            color: #28a745;
            background-color: #d4edda;
            border-color: #c3e6cb;
        }
        
        .error {
            color: #dc3545;
            background-color: #f8d7da;
            border-color: #f5c6cb;
        }
        
        .info {
            color: #17a2b8;
            background-color: #d1ecf1;
            border-color: #bee5eb;
        }
        
        .results-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin-top: 20px;
        }
        
        .result-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            transition: transform 0.3s;
        }
        
        .result-card:hover {
            transform: scale(1.05);
        }
        
        .result-card h3 {
            font-size: 18px;
            margin-bottom: 10px;
            opacity: 0.9;
        }
        
        .result-card .votes {
            font-size: 32px;
            font-weight: bold;
            margin: 10px 0;
        }
        
        .blockchain-display {
            max-height: 400px;
            overflow-y: auto;
            margin-top: 20px;
            padding-right: 10px;
        }
        
        .block-item {
            background: #f8f9fa;
            border: 1px solid #e1e5e9;
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 15px;
            font-family: 'Courier New', monospace;
            font-size: 13px;
        }
        
        .block-header {
            display: flex;
            justify-content: space-between;
            margin-bottom: 10px;
            padding-bottom: 10px;
            border-bottom: 1px solid #dee2e6;
        }
        
        .block-index {
            font-weight: bold;
            color: #667eea;
        }
        
        .block-hash {
            color: #666;
            font-size: 12px;
        }
        
        .status-badge {
            display: inline-block;
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: bold;
            margin: 2px;
        }
        
        .badge-success {
            background: #d4edda;
            color: #155724;
        }
        
        .badge-warning {
            background: #fff3cd;
            color: #856404;
        }
        
        .badge-danger {
            background: #f8d7da;
            color: #721c24;
        }
        
        @media (max-width: 768px) {
            .content-grid {
                grid-template-columns: 1fr;
            }
            
            .header h1 {
                font-size: 2em;
            }
            
            .nav-buttons {
                flex-direction: column;
            }
            
            .nav-btn {
                width: 100%;
                text-align: center;
            }
        }
        
        .candidate-option {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 10px;
            border: 1px solid #e1e5e9;
            border-radius: 8px;
            margin-bottom: 10px;
            cursor: pointer;
            transition: all 0.3s;
        }
        
        .candidate-option:hover {
            background: #f8f9fa;
            border-color: #667eea;
        }
        
        .candidate-option input[type="radio"] {
            margin: 0;
        }
        
        .loader {
            display: inline-block;
            width: 20px;
            height: 20px;
            border: 3px solid #f3f3f3;
            border-top: 3px solid #667eea;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin-right: 10px;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🗳️ Blockchain Voting System</h1>
            <p>Secure • Transparent • Tamper-proof Voting using Blockchain Technology</p>
            <div style="margin-top: 15px; font-size: 14px; opacity: 0.8;">
                <span id="statusInfo">🟢 System Online | Auto-mining enabled</span>
            </div>
        </div>
        
        <div class="nav-buttons">
            <button class="nav-btn active" onclick="showSection('register')">📝 Register</button>
            <button class="nav-btn" onclick="showSection('vote')">✓ Vote</button>
            <button class="nav-btn" onclick="showSection('results')">📊 Results</button>
            <button class="nav-btn" onclick="showSection('blockchain')">⛓️ Blockchain</button>
            <button class="nav-btn" onclick="showSection('status')">👥 Voter Status</button>
            <button class="nav-btn btn-secondary" onclick="mineNow()">⛏️ Mine Now</button>
        </div>
        
        <div class="content-grid">
            <!-- Register Card -->
            <div class="card" id="registerCard">
                <h2>📝 Register Voter</h2>
                <div class="form-group">
                    <label for="voterId">Voter ID</label>
                    <input type="text" id="voterId" class="form-control" placeholder="Enter your unique ID (e.g., V001)">
                    <small style="color: #666; display: block; margin-top: 5px;">This will be your voting identity</small>
                </div>
                <button class="btn" onclick="registerVoter()">Generate Registration Token</button>
                <div id="registerResult" class="result-box" style="display: none;"></div>
            </div>
            
            <!-- Vote Card -->
            <div class="card" id="voteCard" style="display: none;">
                <h2>✓ Cast Your Vote</h2>
                <div class="form-group">
                    <label for="voteVoterId">Voter ID</label>
                    <input type="text" id="voteVoterId" class="form-control" placeholder="Enter your registered ID">
                </div>
                <div class="form-group">
                    <label for="voteToken">Registration Token</label>
                    <input type="text" id="voteToken" class="form-control" placeholder="Enter your token">
                    <small style="color: #666; display: block; margin-top: 5px;">Check registration section for your token</small>
                </div>
                <div class="form-group">
                    <label>Select Candidate</label>
                    <div id="candidatesList">
                        <!-- Candidates will be loaded here -->
                    </div>
                </div>
                <button class="btn" onclick="castVote()">Submit Vote</button>
                <div id="voteResult" class="result-box" style="display: none;"></div>
            </div>
            
            <!-- Results Card -->
            <div class="card" id="resultsCard" style="display: none;">
                <h2>📊 Live Results</h2>
                <div id="resultsDisplay">
                    <p class="info">Click "Refresh Results" to see current vote counts</p>
                </div>
                <button class="btn" onclick="getResults()">🔄 Refresh Results</button>
                <div style="margin-top: 20px; padding: 15px; background: #f8f9fa; border-radius: 8px;">
                    <h4>📈 Statistics</h4>
                    <p>Total Votes: <span id="totalVotes">0</span></p>
                    <p>Blocks Mined: <span id="blocksMined">0</span></p>
                    <p>Pending Votes: <span id="pendingVotes">0</span></p>
                </div>
            </div>
            
            <!-- Blockchain Card -->
            <div class="card" id="blockchainCard" style="display: none;">
                <h2>⛓️ Blockchain Explorer</h2>
                <div style="display: flex; justify-content: space-between; margin-bottom: 15px;">
                    <span>Total Blocks: <strong id="blockCount">1</strong></span>
                    <span>Chain Valid: <strong id="chainValid">✅ Yes</strong></span>
                </div>
                <div class="blockchain-display" id="chainDisplay">
                    <!-- Blocks will be displayed here -->
                </div>
                <button class="btn" onclick="getChain()">🔄 Refresh Blockchain</button>
            </div>
            
            <!-- Status Card -->
            <div class="card" id="statusCard" style="display: none;">
                <h2>👥 Voter Status</h2>
                <div id="statusDisplay">
                    <p class="info">Loading voter information...</p>
                </div>
                <button class="btn" onclick="getStatus()">🔄 Refresh Status</button>
            </div>
        </div>
    </div>

    <script>
        let currentSection = 'register';
        
        // Initialize candidates
        function loadCandidates() {
            const candidates = ["Alice", "Bob", "Charlie", "Diana", "Edward"];
            const container = document.getElementById('candidatesList');
            container.innerHTML = '';
            
            candidates.forEach(candidate => {
                const div = document.createElement('div');
                div.className = 'candidate-option';
                div.innerHTML = `
                    <input type="radio" id="candidate_${candidate}" name="candidate" value="${candidate}">
                    <label for="candidate_${candidate}" style="cursor: pointer; flex: 1;">
                        <strong>${candidate}</strong>
                    </label>
                `;
                container.appendChild(div);
                
                // Add click handler to select radio
                div.addEventListener('click', () => {
                    document.getElementById(`candidate_${candidate}`).checked = true;
                });
            });
        }
        
        // Navigation
        function showSection(sectionId) {
            // Hide all cards
            document.querySelectorAll('.card').forEach(card => {
                card.style.display = 'none';
            });
            
            // Remove active class from all buttons
            document.querySelectorAll('.nav-btn').forEach(btn => {
                btn.classList.remove('active');
            });
            
            // Show selected card and activate button
            document.getElementById(`${sectionId}Card`).style.display = 'block';
            document.querySelector(`.nav-btn[onclick="showSection('${sectionId}')"]`).classList.add('active');
            
            currentSection = sectionId;
            
            // Load data if needed
            if(sectionId === 'results') getResults();
            if(sectionId === 'blockchain') getChain();
            if(sectionId === 'status') getStatus();
            if(sectionId === 'vote') loadCandidates();
        }
        
        // Register voter
        async function registerVoter() {
            const voterId = document.getElementById('voterId').value.trim();
            if(!voterId) {
                alert('Please enter a voter ID');
                return;
            }
            
            const resultDiv = document.getElementById('registerResult');
            resultDiv.style.display = 'block';
            resultDiv.innerHTML = '<div class="info"><span class="loader"></span> Registering voter...</div>';
            
            try {
                const response = await fetch('/register', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({voter_id: voterId})
                });
                
                const data = await response.json();
                
                if(data.success) {
                    resultDiv.innerHTML = `
                        <div class="success">
                            <h4>✅ Registration Successful!</h4>
                            <p><strong>Voter ID:</strong> ${voterId}</p>
                            <p><strong>Your Token:</strong> <code style="background: #333; color: #fff; padding: 5px 10px; border-radius: 4px; font-size: 16px;">${data.token}</code></p>
                            <p><em>⚠️ Save this token securely! You will need it to vote.</em></p>
                            <p><small>Token preview: ${data.token.substring(0, 4)}****</small></p>
                        </div>
                    `;
                    document.getElementById('voterId').value = '';
                } else {
                    resultDiv.innerHTML = `<div class="error">❌ ${data.message}</div>`;
                }
            } catch(error) {
                resultDiv.innerHTML = `<div class="error">❌ Network error: ${error.message}</div>`;
            }
        }
        
        // Cast vote
        async function castVote() {
            const voterId = document.getElementById('voteVoterId').value.trim();
            const token = document.getElementById('voteToken').value.trim();
            const candidate = document.querySelector('input[name="candidate"]:checked');
            
            if(!voterId || !token) {
                alert('Please enter both Voter ID and Token');
                return;
            }
            
            if(!candidate) {
                alert('Please select a candidate');
                return;
            }
            
            const resultDiv = document.getElementById('voteResult');
            resultDiv.style.display = 'block';
            resultDiv.innerHTML = '<div class="info"><span class="loader"></span> Processing your vote...</div>';
            
            try {
                const response = await fetch('/vote', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        voter_id: voterId,
                        token: token,
                        candidate: candidate.value
                    })
                });
                
                const data = await response.json();
                
                if(data.success) {
                    resultDiv.innerHTML = `
                        <div class="success">
                            <h4>✅ Vote Submitted!</h4>
                            <p>You voted for: <strong>${candidate.value}</strong></p>
                            <p>${data.message}</p>
                            <p><small>Your vote will be added to the blockchain during the next mining cycle.</small></p>
                            <button class="btn" style="margin-top: 10px; padding: 10px;" onclick="mineNow()">
                                ⛏️ Mine Votes Now
                            </button>
                        </div>
                    `;
                    
                    // Clear form
                    document.getElementById('voteVoterId').value = '';
                    document.getElementById('voteToken').value = '';
                    document.querySelectorAll('input[name="candidate"]').forEach(radio => {
                        radio.checked = false;
                    });
                } else {
                    resultDiv.innerHTML = `<div class="error">❌ ${data.message}</div>`;
                }
            } catch(error) {
                resultDiv.innerHTML = `<div class="error">❌ Error: ${error.message}</div>`;
            }
        }
        
        // Get results
        async function getResults() {
            const resultsDiv = document.getElementById('resultsDisplay');
            resultsDiv.innerHTML = '<div class="info"><span class="loader"></span> Loading results...</div>';
            
            try {
                const response = await fetch('/results');
                const results = await response.json();
                
                const chainResponse = await fetch('/chain');
                const chainData = await chainResponse.json();
                
                let totalVotes = 0;
                let html = '<div class="results-grid">';
                
                // Sort results by vote count (descending)
                const sortedResults = Object.entries(results).sort((a, b) => b[1] - a[1]);
                
                sortedResults.forEach(([candidate, votes]) => {
                    totalVotes += votes;
                    const percentage = totalVotes > 0 ? ((votes / totalVotes) * 100).toFixed(1) : 0;
                    
                    html += `
                        <div class="result-card">
                            <h3>${candidate}</h3>
                            <div class="votes">${votes}</div>
                            <div>votes</div>
                            <div style="margin-top: 10px; font-size: 12px; opacity: 0.8;">
                                ${percentage}%
                            </div>
                        </div>
                    `;
                });
                
                html += '</div>';
                
                // Update statistics
                document.getElementById('totalVotes').textContent = totalVotes;
                document.getElementById('blocksMined').textContent = chainData.blocks ? chainData.blocks.length - 1 : 0;
                document.getElementById('pendingVotes').textContent = chainData.pending_count || 0;
                
                if(totalVotes === 0) {
                    html = '<div class="info">No votes have been cast yet. Be the first to vote!</div>';
                }
                
                resultsDiv.innerHTML = html;
            } catch(error) {
                resultsDiv.innerHTML = `<div class="error">❌ Error loading results: ${error.message}</div>`;
            }
        }
        
        // Get blockchain
        async function getChain() {
            const chainDiv = document.getElementById('chainDisplay');
            chainDiv.innerHTML = '<div class="info"><span class="loader"></span> Loading blockchain...</div>';
            
            try {
                const response = await fetch('/chain');
                const data = await response.json();
                
                document.getElementById('blockCount').textContent = data.blocks ? data.blocks.length : 0;
                
                const validResponse = await fetch('/validate');
                const validData = await validResponse.json();
                document.getElementById('chainValid').innerHTML = validData.valid ? '✅ Yes' : '❌ No';
                
                if(!data.blocks || data.blocks.length === 0) {
                    chainDiv.innerHTML = '<div class="info">No blocks in the chain yet.</div>';
                    return;
                }
                
                let html = '';
                
                // Display blocks in reverse order (newest first)
                data.blocks.slice().reverse().forEach(block => {
                    html += `
                        <div class="block-item">
                            <div class="block-header">
                                <span class="block-index">Block #${block.index}</span>
                                <span class="status-badge ${block.index === 0 ? 'badge-warning' : 'badge-success'}">
                                    ${block.index === 0 ? 'Genesis' : 'Vote Block'}
                                </span>
                            </div>
                            <p><strong>Hash:</strong> ${block.hash}</p>
                            <p><strong>Previous Hash:</strong> ${block.previous_hash}</p>
                            <p><strong>Time:</strong> ${block.timestamp}</p>
                            <p><strong>Transactions:</strong> ${block.transactions.length}</p>
                            <p><strong>Nonce:</strong> ${block.nonce}</p>
                        </div>
                    `;
                });
                
                chainDiv.innerHTML = html;
            } catch(error) {
                chainDiv.innerHTML = `<div class="error">❌ Error loading blockchain: ${error.message}</div>`;
            }
        }
        
        // Get voter status
        async function getStatus() {
            const statusDiv = document.getElementById('statusDisplay');
            statusDiv.innerHTML = '<div class="info"><span class="loader"></span> Loading voter status...</div>';
            
            try {
                const response = await fetch('/status');
                const status = await response.json();
                
                if(Object.keys(status).length === 0) {
                    statusDiv.innerHTML = '<div class="info">No voters registered yet.</div>';
                    return;
                }
                
                let html = '<div style="overflow-x: auto;">';
                html += `
                    <table style="width: 100%; border-collapse: collapse;">
                        <thead>
                            <tr style="background: #f8f9fa;">
                                <th style="padding: 12px; text-align: left; border-bottom: 2px solid #dee2e6;">Voter ID</th>
                                <th style="padding: 12px; text-align: left; border-bottom: 2px solid #dee2e6;">Status</th>
                                <th style="padding: 12px; text-align: left; border-bottom: 2px solid #dee2e6;">Token Preview</th>
                                <th style="padding: 12px; text-align: left; border-bottom: 2px solid #dee2e6;">Vote Status</th>
                            </tr>
                        </thead>
                        <tbody>
                `;
                
                for(const [voterId, data] of Object.entries(status)) {
                    html += `
                        <tr style="border-bottom: 1px solid #dee2e6;">
                            <td style="padding: 12px;"><strong>${voterId}</strong></td>
                            <td style="padding: 12px;">
                                <span class="status-badge badge-success">Registered</span>
                            </td>
                            <td style="padding: 12px;"><code>${data.token_preview}</code></td>
                            <td style="padding: 12px;">
                                ${data.has_voted ? 
                                    `<span class="status-badge badge-success">✅ Voted (${data.voted_at})</span>` : 
                                    `<span class="status-badge badge-warning">❌ Not Voted</span>`
                                }
                            </td>
                        </tr>
                    `;
                }
                
                html += '</tbody></table></div>';
                statusDiv.innerHTML = html;
            } catch(error) {
                statusDiv.innerHTML = `<div class="error">❌ Error loading status: ${error.message}</div>`;
            }
        }
        
        // Mine votes
        async function mineNow() {
            try {
                const response = await fetch('/mine', {method: 'POST'});
                const data = await response.json();
                
                alert(data.message);
                
                // Refresh current view
                if(currentSection === 'results') getResults();
                if(currentSection === 'blockchain') getChain();
                if(currentSection === 'status') getStatus();
            } catch(error) {
                alert(`Error: ${error.message}`);
            }
        }
        
        // Auto-refresh
        setInterval(() => {
            if(currentSection === 'results') getResults();
            if(currentSection === 'blockchain') getChain();
        }, 10000); // Refresh every 10 seconds
        
        // Initialize
        loadCandidates();
        showSection('register');
        
        // Load initial blockchain data
        getChain();
    </script>
</body>
</html>
'''

# ========== FLASK ROUTES ==========
@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        voter_id = data.get('voter_id', '').strip()
        
        if not voter_id:
            return jsonify({"success": False, "message": "Voter ID is required"})
        
        success, message, token = voting_system.register_voter(voter_id)
        
        return jsonify({
            "success": success,
            "message": message,
            "token": token
        })
    except Exception as e:
        return jsonify({"success": False, "message": f"Error: {str(e)}"})

@app.route('/vote', methods=['POST'])
def vote():
    try:
        data = request.get_json()
        voter_id = data.get('voter_id', '').strip()
        token = data.get('token', '').strip()
        candidate = data.get('candidate', '').strip()
        
        if not all([voter_id, token, candidate]):
            return jsonify({"success": False, "message": "All fields are required"})
        
        success, message = voting_system.cast_vote(voter_id, token, candidate)
        
        return jsonify({
            "success": success,
            "message": message
        })
    except Exception as e:
        return jsonify({"success": False, "message": f"Error: {str(e)}"})

@app.route('/results')
def results():
    try:
        results = voting_system.get_results()
        return jsonify(results)
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/chain')
def chain():
    try:
        chain_data = voting_system.blockchain.get_chain_data()
        return jsonify(chain_data)
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/status')
def status():
    try:
        status_data = voting_system.get_voter_status()
        return jsonify(status_data)
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/mine', methods=['POST'])
def mine():
    try:
        success, message = voting_system.mine_votes()
        return jsonify({
            "success": success,
            "message": message
        })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

@app.route('/validate')
def validate():
    try:
        is_valid = voting_system.blockchain.is_chain_valid()
        return jsonify({"valid": is_valid})
    except Exception as e:
        return jsonify({"valid": False, "error": str(e)})

@app.route('/test')
def test():
    """Test endpoint to check if system is working"""
    return jsonify({
        "status": "online",
        "blocks": len(voting_system.blockchain.chain),
        "pending_votes": len(voting_system.blockchain.pending_transactions),
        "registered_voters": len(voting_system.registered_voters)
    })

# ========== RUN APPLICATION ==========
if __name__ == '__main__':
    print("\n" + "="*60)
    print("🚀 BLOCKCHAIN VOTING SYSTEM")
    print("="*60)
    print("\n✅ System initialized successfully!")
    print(f"✅ Candidates: {', '.join(voting_system.candidates)}")
    print("✅ Auto-mining enabled (every 20 seconds)")
    print("\n🌐 Open your browser and navigate to:")
    print("   http://localhost:5000")
    print("\n📋 Quick Start:")
    print("   1. Register a voter to get a token")
    print("   2. Use the token to cast a vote")
    print("   3. View real-time results")
    print("   4. Watch votes being added to the blockchain")
    print("="*60 + "\n")
    
    app.run(debug=True, host='0.0.0.0', port=5000)