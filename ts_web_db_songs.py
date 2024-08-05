import pyodbc
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from datetime import datetime, timedelta
import time
import re

# Caminho para o ChromeDriver
chromedriver_path = "C:/WebDrivers/chromedriver.exe"

# Configuração da string de conexão com o banco de dados SQL Server
conn_str = (
    r'DRIVER={SQL Server};'
    r'SERVER=Claudio;'
    r'DATABASE=taylor_swift;'
    r'Trusted_Connection=yes;'
)

# Dicionário para substituir nomes de músicas baseados na URL
url_nome_musica = {
    "https://open.spotify.com/track/6xsEAm6w9oMQYYg3jkEkMT": "Bad Blood (feat. Kendrick Lamar) - Single",
    "https://open.spotify.com/track/7vBlnGdfOLzVEqiOQQxeU8": "The Story Of Us (US Version)",
}

# Função para escrever log
def write_log(message):
    log_file_path = '(Seu diretório)'
    with open(log_file_path, 'a', encoding='utf-8') as log_file:
        log_file.write(message.strip() + '\n')
    print(message.strip())  # Imprime a mensagem no console

# Função para extrair a data de ontem
def extract_date():
    return (datetime.now() - timedelta(days=1)).strftime('%d/%m/%Y').strip()

# Função para substituir "Taylor's" por "Taylor’s" e remover aspas
def replace_taylors(text):
    text = text.replace("'", "’")
    text = text.replace('"', '')
    text = text.replace('*', '')
    return text.strip()

# Função para obter os dados da página web
def get_music_data(driver):
    driver.get('https://kworb.net/spotify/artist/06HL4z0CvFAxyc27GXpf02_songs.html')
    time.sleep(5)
    
    tabela = driver.find_element("xpath", '/html/body/div[1]/div[5]/table[2]/tbody')
    dados = []

    linhas = tabela.find_elements("xpath", './/tr')
    for linha in linhas:
        elemento_clicavel = linha.find_element("xpath", './/td[1]')
        div = elemento_clicavel.find_element("xpath", './/div')
        a = div.find_element("xpath", './/a')
        link = a.get_attribute('href').strip()

        colunas = linha.find_elements("xpath", './/td')
        nome_atual = colunas[0].text.strip()
        if nome_atual.startswith('^'):
            nome_atual = nome_atual[1:].strip()
        nome_atual = replace_taylors(nome_atual)
        total_atual = colunas[1].text.strip().replace(',', '').strip()
        diario_atual = colunas[2].text.strip().replace(',', '').strip()

        # Validar e substituir nome da música baseado na URL
        if link in url_nome_musica:
            nome_atual = url_nome_musica[link].strip()

        dados.append([nome_atual.strip(), total_atual.strip(), diario_atual.strip(), link.strip()])

    return dados

# Função para verificar se a data de atualização já existe no banco de dados
def check_data_existence(cursor, data_atualizacao):
    check_query = "SELECT COUNT(*) FROM songs WHERE atualizado_em = ?"
    cursor.execute(check_query.strip(), (data_atualizacao.strip(),))
    result = cursor.fetchone()
    return result[0] > 0

# Função para buscar dados da música no banco de dados
def get_song_data(cursor, nome_musicas):
    select_query = """
    SELECT nome_musicas, versao, era, album
    FROM songs 
    WHERE nome_musicas = ?
    """
    cursor.execute(select_query.strip(), (nome_musicas.strip(),))
    return cursor.fetchone()

# Passo 1: Configurar o ChromeDriver
service = Service(chromedriver_path.strip())
options = webdriver.ChromeOptions()
options.add_argument("--start-maximized")
options.add_argument('--ignore-certificate-errors')
driver = webdriver.Chrome(service=service, options=options)

# Passo 2: Obter os dados da página web e a data de atualização
dados = get_music_data(driver)

# Fechar o navegador
driver.quit()

# Passo 3: Conectar ao banco de dados
try:
    conn = pyodbc.connect(conn_str.strip())
    cursor = conn.cursor()
    write_log('Conexão ao banco de dados estabelecida com sucesso!')
except pyodbc.Error as e:
    error_message = f'Erro ao tentar conectar ao banco de dados: {e}'
    write_log(error_message)
    raise SystemExit(error_message.strip())

# Passo 4: Verificar se a data de atualização já existe no banco de dados
data_atualizacao = extract_date().strip()
if check_data_existence(cursor, data_atualizacao):
    write_log(f'Data de atualização {data_atualizacao} já existe no banco de dados. Encerrando a execução.')
    cursor.close()
    conn.close()
    raise SystemExit(f'Data de atualização {data_atualizacao} já existe no banco de dados.'.strip())

# Passo 5: Inserir dados no banco de dados
for nome_atual, total_atual, diario_atual, link in dados:
    album_data = get_song_data(cursor, nome_atual.strip())
    if album_data:
        nome_musicas, versao, era, album = album_data
        insert_query = """
        INSERT INTO songs (nome_musicas, album, versao, total_streams, streams_diarios, atualizado_em, era)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        cursor.execute(insert_query.strip(), (nome_musicas.strip(), album.strip(), versao.strip(), total_atual.strip(), diario_atual.strip(), data_atualizacao.strip(), era.strip()))
        conn.commit()
        write_log(f'Registro de {nome_musicas} para a data {data_atualizacao} inserido no banco de dados com sucesso')
    else:
        write_log(f'Nenhum dado encontrado para a música: {nome_atual}')

# Passo 6: Fechar a conexão
cursor.close()
conn.close()

# Escrever "Fim" no final do log com espaçamento
write_log('Fim\n\n----------------------------------------\n\n')
