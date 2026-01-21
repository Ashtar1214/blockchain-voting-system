import hashlib
import json
import time
from datetime import datetime

class Block:
    def __init__(self, index: int, transactions: list, timestamp: float, previous_hash: str):
        self.index = index
        self.transactions = transactions
        self.timestamp = timestamp
        self.previous_hash = previous_hash
        self.nonce = 0
        self.hash = self.calculate_hash()
    
    def calculate_hash(self) -> str:
        block_string = json.dumps({
            "index": self.index,
            "transactions": self.transactions,
            "timestamp": self.timestamp,
            "previous_hash": self.previous_hash,
            "nonce": self.nonce
        }, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()
    
    def mine_block(self, difficulty: int):
        print(f"Mining block {self.index}...")
        while self.hash[:difficulty] != "0" * difficulty:
            self.nonce += 1
            self.hash = self.calculate_hash()
        print(f"Block {self.index} mined! Hash: {self.hash[:16]}...")
    
    def to_dict(self) -> dict:
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
        self.difficulty = 2  # Reduced for faster mining
        self.pending_transactions = []
        self.create_genesis_block()
    
    def create_genesis_block(self):
        genesis_block = Block(0, ["Genesis Block"], time.time(), "0")
        genesis_block.mine_block(self.difficulty)
        self.chain.append(genesis_block)
        print("Genesis block created")
    
    def get_latest_block(self):
        return self.chain[-1]
    
    def add_transaction(self, transaction: dict) -> bool:
        """Add a transaction to pending transactions"""
        self.pending_transactions.append(transaction)
        return True
    
    def mine_pending_transactions(self) -> bool:
        """Mine all pending transactions into a new block"""
        if not self.pending_transactions:
            print("No transactions to mine")
            return False
        
        print(f"Mining {len(self.pending_transactions)} votes...")
        
        block = Block(
            len(self.chain),
            self.pending_transactions[:],  # Copy the list
            time.time(),
            self.get_latest_block().hash
        )
        
        block.mine_block(self.difficulty)
        self.chain.append(block)
        
        # Clear pending transactions
        self.pending_transactions = []
        
        print(f"Successfully mined block #{block.index} with {len(block.transactions)} votes")
        return True
    
    def is_chain_valid(self) -> bool:
        """Validate the entire blockchain"""
        for i in range(1, len(self.chain)):
            current = self.chain[i]
            previous = self.chain[i-1]
            
            # Recalculate current block's hash
            if current.hash != current.calculate_hash():
                print(f"Block {i} hash is invalid!")
                return False
            
            # Check link to previous block
            if current.previous_hash != previous.hash:
                print(f"Block {i} previous hash doesn't match!")
                return False
        
        return True
    
    def get_voter_votes(self) -> dict:
        """Get all votes from blockchain with voter_id as key"""
        votes = {}
        for block in self.chain:
            for transaction in block.transactions:
                if isinstance(transaction, dict) and 'voter_id' in transaction:
                    votes[transaction['voter_id']] = transaction.get('candidate', 'Unknown')
        return votes
    
    def get_vote_counts(self) -> dict:
        """Count votes per candidate from mined blocks"""
        counts = {}
        for block in self.chain:
            if isinstance(block.transactions, list):
                for transaction in block.transactions:
                    if isinstance(transaction, dict) and 'candidate' in transaction:
                        candidate = transaction['candidate']
                        counts[candidate] = counts.get(candidate, 0) + 1
        return counts
    
    def has_voter_voted(self, voter_id: str) -> bool:
        """Check if voter has voted in mined blocks"""
        return voter_id in self.get_voter_votes()