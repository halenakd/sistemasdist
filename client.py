import socket
import struct
import json
import os
from threading import Event
import uuid

ADDR = '224.3.29.71'
PORT = 10000

def clear_buffer(sock):
    while True:
        try:
            data = sock.recv(1024)
            if not data:
                break
            else:
                print("liberando socket....")
        except:
            print("socket vazio!")
            break


class Client:

    def __init__(self, addr_group, port, client_dir):
        self.multicast_group = (addr_group, port)
        self.client_dir = client_dir
        self.hash_table = {}  # Tabela hash local do cliente

    def run(self) -> None:
        
        if not os.path.exists(self.client_dir):
            os.mkdir(self.client_dir)
        
        # Create the datagram socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # Set a timeout so the socket does not block indefinitely when trying
        # to receive data.
        sock.settimeout(0.5)

        # Set the time-to-live for messages to 1 so they do not go past the
        # local network segment.
        ttl = struct.pack('b', 1)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)

        # Join multicast group
        group = socket.inet_aton(self.multicast_group[0])
        mreq = struct.pack('4sL', group, socket.INADDR_ANY)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

        while True:
            print("\nEscolha uma ação:")
            print("1. Enviar arquivo (put)")
            print("2. Buscar arquivo (get)")
            action = input("--> Escolha uma ação (1 ou 2): ")

            if action == '1':
                file_name = input("Digite o nome do arquivo para criar: ")
                data = input("Digite os dados do arquivo: ")

                guid = str(uuid.uuid4())

                file_path = os.path.join(self.client_dir, guid)
                with open(file_path, 'w') as file:
                    file.write(data)
                print(f"Dados armazenados em: {guid}")
                
                put_data = json.dumps({'action': 'put', 'guid': guid, 'file_name': file_name, 'data': data})
                print(f"Enviando dados: {put_data}")  # Verificando os dados que serão enviados
                sock.sendto(put_data.encode(), self.multicast_group)

            elif action == '2':
                file_name = input("Digite o nome do arquivo para buscar: ")
                get_data = json.dumps({'action': 'get', 'file_name': file_name})
                sock.sendto(get_data.encode(), self.multicast_group)

                while True:
                    print ('waiting to receive')
                    try:
                        data, server = sock.recvfrom(1024)
                    
                    except socket.timeout:
                        print('--> Timeout esperando resposta :(')
                        break
                    
                    else:
                        decoded_data = json.loads(data.decode())  # Decodificar a resposta JSON do servidor
                        
                        # Verifica se houve um erro na resposta
                        if 'error' in decoded_data:
                            print(f"Erro: {decoded_data['error']}")
                        else:
                            # Caso os dados do arquivo sejam recebidos corretamente
                            guid = decoded_data['guid']  # O GUID será enviado de volta junto com os dados
                            file_data = decoded_data['data']
                            
                            # Salva o arquivo no diretório local do cliente
                            file_path = os.path.join(self.client_dir, guid)
                            with open(file_path, 'w') as file:
                                file.write(file_data)
                            print(f"Arquivo {file_name} baixado e salvo como {file_path}")

                        break

            else:
                print("Opção inválida. Tente novamente.")
