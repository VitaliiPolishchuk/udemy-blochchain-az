#create cryptocurrency

import datetime
import hashlib
import json
from flask import Flask, jsonify, request
import requests
from uuid import uuid4
from urllib.parse import urlparse


#-----------------
#DATA STRUCTURE BLOCKCHAIN
#-----------------
class Blockchain:
    
    def __init__(self):
        self.chain = []
        self.transactions = []
        self.create_block(proof = 1, previous_hash = '0')
        self.nodes = set()
        
    def create_block(self, proof, previous_hash):
        '''
        create a block and append to chain
        '''
        block = {
                  'index': len(self.chain) + 1,
                  'timestamp': str(datetime.datetime.now()),
                  'proof': proof,
                  'previous_hash': previous_hash,
                  'transactions': self.transactions
                }
        self.transactions = []
        self.chain.append(block)
        return block
    
    def get_previous_block(self):
        '''
        return previous block from chain
        '''
        return self.chain[-1]
    
    def proof_of_work(self, previous_proof):
        '''
        return proof of work
        '''
        
        #initialization
        new_proof = 1
        check_proof = False
        
        #create new proof
        while check_proof is False:
            hash_operation = hashlib.sha256(str(new_proof**2 - previous_proof**2).encode()).hexdigest()
            if hash_operation[:4] == '0000':
                check_proof = True
            else:
                new_proof += 1
        return new_proof
    
    def hash(self, block):
        '''
        return hash for block
        '''
        encoded_block = json.dumps(block, sort_keys = True).encode()
        return hashlib.sha256(encoded_block).hexdigest()
    
    def is_chain_valid(self, chain):
        '''
        check for validation all blocks in chain
        '''
        #initialization
        previous_block = chain[0]
        block_index = 1
        
        #check each block
        while block_index < len(chain):
            
            #check index
            block = chain[block_index]
            if block['previous_hash'] != self.hash(previous_block):
                return False
            
            #check first four 0
            previous_proof = previous_block['proof']
            proof = block['proof']
            hash_operation = hashlib.sha256(str(proof**2 - previous_proof**2).encode()).hexdigest()
            if hash_operation[:4] != '0000':
                return False 
            
            #update parametries
            previous_block = block
            block_index += 1

        return True
    
    def add_transaction(self, sender, receiver, amount):
        '''
        add transaction and return index of current block
        '''
        self.transactions.append({
                    'sender': sender,
                    'receiver': receiver,
                    'amount': amount
                })
        
        previous_block = self.get_previous_block()
        return previous_block['index'] + 1
    
    def add_node(self, address):
        '''
        add node to nodes
        '''
        parsed_url = urlparse(address)
        self.nodes.add(parsed_url.netloc)
        
    def replace_chain(self):
        '''
        replace chain if exist longest chain
        '''
        #initialization
        network = self.nodes
        longest_chain = None
        max_length = len(self.chain)
        
        #search for longest chain
        for node in network:
            response = requests.get(f'http://{node}/get_chain')
            if response.status_code == 200:
                length = response.json()['length']
                chain = response.json()['chain']
                if length > max_length and self.is_chain_valid(chain):
                    max_length = length
                    longest_chain = chain
        
        #replace chain
        if longest_chain:
            self.chain = longest_chain
            return True
        
        return False
    
#-----------------
#CREATE FLASK APP
#-----------------
app = Flask(__name__)
 

#-----------------
#CREATE WITH BLOCKCHAIN
#-----------------
blockchain = Blockchain()

#CREATING AN ADDRESS FOR NODE ON PORT 5000
node_address = str(uuid4()).replace('-', '')

#-----------------
#MINING A NEW BLOCK
#-----------------
@app.route('/mine_block', methods=['GET'])
def mine_block():
    #initialization
    previous_block = blockchain.get_previous_block()
    previous_proof = previous_block['proof']
    
    #create new block and append it to chain
    proof = blockchain.proof_of_work(previous_proof)
    previous_hash = blockchain.hash(previous_block)
    block = blockchain.create_block(proof, previous_hash)
    
    #create first transaction 
    blockchain.add_transaction(sender = node_address, receiver = 'Kirill', amount = 1)
    
    #return message of success
    response = {'message': 'Congradulations, you just mined a block!',
                'index': block['index'],
                'timestamp': block['timestamp'],
                'proof': block['proof'],
                'previous_hash': block['previous_hash'],
                'transactions': block['transactions']}
    return jsonify(response), 200

#-----------------
#GETTING THE FULL BLOCKCHAIN
#-----------------
@app.route('/get_chain', methods=['GET'])
def get_chain():
    response = {'chain': blockchain.chain,
                'length': len(blockchain.chain)}
    return jsonify(response), 200

#-----------------
#GETTING THE FULL BLOCKCHAIN
#-----------------
@app.route('/is_valid', methods=['GET'])
def is_valid():
    is_valid = blockchain.is_chain_valid(blockchain.chain)
    if is_valid:
        response = {'message': "All good. The Blockchain is valid"}
    else:
        response = {'message': "Houston, we have a problems. The block chain is not valid"}
    return jsonify(response), 200


#ADD TRANSACTION
@app.route('/add_transaction', methods=['POST'])
def add_transaction():
    #get information
    json = request.get_json()
    
    #check validation of information
    transaction_keys = ['sender', 'receiver', 'amount']
    if not all (key in json for key in transaction_keys):
        return 'Some elements of thansaction are missing', 400
    
    #get index current block and add transaction
    index_current_block = blockchain.add_transaction(json['sender'], json['receiver'], json['amount'])
    
    #return response
    response = {'message': f'This transaction will be added to Block {index_current_block}'}
    return jsonify(response), 201


#-----------------
#DECENTRALIZING THE BLOCKCHAIN
#-----------------
@app.route('/connect_node', methods=['POST'])
def connect_node():
    json = request.get_json()
    nodes = json.get('nodes')
    
    if nodes is None:
        return "No node", 400
    
    for node in nodes:
        blockchain.add_node(node)
        
    response = {'message': 'All the nodes are now connected',
                'total_nodes': list(blockchain.nodes)}
    return jsonify(response), 201

#REPLACING THE CHAIN BY THE LONGEST CHAIN IF NEEDED
@app.route('/replace_chain', methods=['GET'])
def replace_chain():
    is_chain_replaced = blockchain.replace_chain()
    if is_chain_replaced:
        response = {'message': "The nodes had different chains so the chain was replaced be the longest",
                    'new_chain': blockchain.chain}
    else:
        response = {'message': "All good. The chain is the longest one.",
                    'actual_chain': blockchain.chain}
    return jsonify(response), 200
#-----------------
#RUNNING THE APP
#-----------------
app.run(host = '0.0.0.0', port = 5002)