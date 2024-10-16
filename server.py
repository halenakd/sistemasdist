# https://pymotw.com/2/socket/multicast.html

import socket
import struct
from threading import Event
import os
import json
import uuid

class Server:
    def __init__(self, addr_group, port, server_dir):
        self.multicast_group = addr_group
        self.server_address = ('', port)
        self.server_dir = server_dir
        self.hash_table = {}  # Hash table para armazenar os GUIDs -> mapear os dados
        self.load_hash_table_from_file() 

    def put(self, file_name, data, sock, address):
        """Armazena dados usando um GUID e atualiza a tabela hash."""
        guid = str(uuid.uuid4())

        file_path = os.path.join(self.server_dir, guid)
        with open(file_path, 'w') as file:
            file.write(data)
        print(f"Dados armazenados em: {guid}")

        # Atualiza a tabela hash
        self.hash_table[file_name] = guid
        print(f"Arquivo {file_name} e GUID {guid} adicionados à tabela hash.")

        # Transmite a tabela hash atualizada para todos os peers
        self.broadcast_hash_table(sock)

    def get(self, file_name):
        """Recupera dados usando o GUID da tabela hash e arquivos do sistema."""
        if file_name in self.hash_table:
            guid = self.hash_table.get(file_name)
            file_path = os.path.join(self.server_dir, guid)
            if os.path.exists(file_path):
                with open(file_path, 'r') as file:
                    data = file.read()
                print(f"Dados recuperados para o arquivo {file_name}")
                return data
            else:
                print(f"Arquivo não encontrado.")
                return None
        else:
            print(f"GUID {file_name} não encontrado na tabela hash.")
            return None

    def load_hash_table_from_file(self):
        """Carrega a tabela hash de um arquivo JSON, se existir."""
        hash_table_file_path = 'hash_table.json'
        if os.path.exists(hash_table_file_path):
            with open(hash_table_file_path, 'r') as json_file:
                self.hash_table = json.load(json_file)
            print("Tabela hash carregada a partir do arquivo.")
        else:
            print("Arquivo de tabela hash não encontrado. Usando tabela vazia.")

    def synchronize_hash_table(self):
        """Sincroniza a tabela hash com os arquivos existentes no diretório do servidor."""
        if not os.path.exists(self.server_dir):
            os.mkdir(self.server_dir)

        # Loop pelos arquivos existentes no diretório
        for file_name in os.listdir(self.server_dir):
            guid = self.hash_table.get(file_name)
            self.hash_table[file_name] = guid  # Mapeia GUID para nome do arquivo (ambos iguais aqui)
        print("Tabela hash sincronizada com arquivos existentes.")

    def save_hash_table_to_file(self):
        """Salva a tabela hash em um arquivo JSON."""
        hash_table_file_path = os.path.join(self.server_dir, 'hash_table.json')
        with open(hash_table_file_path, 'w') as json_file:
            json.dump(self.hash_table, json_file)
        print(f"Tabela hash salva em {hash_table_file_path}.")

    def broadcast_hash_table(self, sock):
        """Transmite a tabela hash atualizada para peers."""
        self.save_hash_table_to_file()  # Salva a tabela hash em um arquivo JSON
        hash_table_message = json.dumps({
            'action': 'sync_ht',
            'hash_table': self.hash_table
        })
        # Envia para o grupo multicast
        sock.sendto(hash_table_message.encode(), (self.multicast_group, 10000))
        print("Tabela hash transmitida para peers.")

    def run(self) -> None:
        "Loop principal de Server"

        if not os.path.exists(self.server_dir):
            os.mkdir(self.server_dir)

        # Create the socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # Bind to the server address
        sock.bind(self.server_address)

        # Tell the operating system to add the socket to the multicast group
        # on all interfaces.
        group = socket.inet_aton(self.multicast_group)
        mreq = struct.pack('4sL', group, socket.INADDR_ANY)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

        # Receive/respond loop
        while True:
            # print(sys.stderr, '\nwaiting to receive message')
            print('\n<<< waiting to receive message\n')
            data, address = sock.recvfrom(1024)
            
            #print(sys.stderr, 'received %s bytes from %s' % (len(data), address))
            print('<<< received %s bytes from %s: %s' % (len(data), address, data.decode('utf-8')))

            message = json.loads(data.decode())

            # Manipula solicitações para armazenar ou recuperar dados
            if message['action'] == 'put':
                self.put(message['file_name'], message['data'], sock, address)
            elif message['action'] == 'get':
                response_data = self.get(message['file_name'])
                if response_data:
                    sock.sendto(response_data.encode(), address)
                else:
                    sock.sendto(json.dumps({'error': 'Arquivo não encontrado'}).encode(), address)
            
            #print(sys.stderr, 'sending acknowledgement to', address)
            #print('sending acknowledgement to', address)
            #sock.sendto('ack'.encode(), address)