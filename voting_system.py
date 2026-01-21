import hashlib
import time
from blockchain import Blockchain

class VotingSystem:
    def __init__(self):
        self.blockchain = Blockchain()
        self.voters = {}  # voter_id: {'token': token, 'voted': False}
        self.candidates = ["Alice", "Bob", "Charlie", "Diana"]
        self.pending_votes = {}  # Track votes that are pending (not yet mined)
    
    def register_voter(self, voter_id: str) -> str:
        """Register a new voter and return their token"""
        if voter_id in self.voters:
            raise Exception("Voter already registered")
        
        # Create unique token
        token = hashlib.sha256(f"{voter_id}{time.time()}".encode()).hexdigest()[:12]
        self.voters[voter_id] = {'token': token, 'voted': False}
        
        print(f"Voter {voter_id} registered with token: {token}")
        return token
    
    def verify_token(self, voter_id: str, token: str) -> bool:
        """Verify if token is valid for voter"""
        return voter_id in self.voters and self.voters[voter_id]['token'] == token
    
    def cast_vote(self, voter_id: str, token: str, candidate: str) -> str:
        """Cast a vote if valid"""
        # Check if voter is registered
        if voter_id not in self.voters:
            return "Voter not registered"
        
        # Validate token
        if not self.verify_token(voter_id, token):
            return "Invalid token"
        
        # Check if candidate is valid
        if candidate not in self.candidates:
            return "Invalid candidate"
        
        # Check if voter has already voted (in blockchain OR pending)
        has_voted_in_blockchain = self.blockchain.has_voter_voted(voter_id)
        has_voted_pending = voter_id in self.pending_votes
        
        if self.voters[voter_id]['voted'] or has_voted_in_blockchain or has_voted_pending:
            return "Voter has already cast a vote"
        
        # Create vote transaction
        vote_transaction = {
            "type": "vote",
            "voter_id": voter_id,
            "candidate": candidate,
            "timestamp": time.time()
        }
        
        # Add to pending votes
        self.pending_votes[voter_id] = vote_transaction
        
        # Add to blockchain pending transactions
        self.blockchain.add_transaction(vote_transaction)
        
        # Mark voter as voted
        self.voters[voter_id]['voted'] = True
        
        return "Vote cast successfully! It will be added to blockchain when mined."
    
    def mine_votes(self):
        """Mine pending votes into blockchain"""
        success = self.blockchain.mine_pending_transactions()
        if success:
            # Clear pending votes after mining
            self.pending_votes = {}
            return "Votes mined successfully!"
        return "No votes to mine"
    
    def get_results(self) -> dict:
        """Get current voting results from blockchain"""
        return self.blockchain.get_vote_counts()
    
    def get_voter_status(self) -> dict:
        """Get voter registration and voting status"""
        status = {}
        votes = self.blockchain.get_voter_votes()
        
        for voter_id, data in self.voters.items():
            status[voter_id] = {
                "registered": True,
                "has_voted": data['voted'] or voter_id in votes or voter_id in self.pending_votes,
                "voted_for": votes.get(voter_id, "Not voted yet"),
                "token": data['token'][:4] + "..."  # Show partial token for security
            }
        
        return status
    
    def get_pending_votes_count(self) -> int:
        """Get number of votes waiting to be mined"""
        return len(self.pending_votes)