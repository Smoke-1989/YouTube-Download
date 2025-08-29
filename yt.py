import yt_dlp
import os

# --- Configuração Opcional ---
# Se o FFmpeg não estiver no PATH do seu sistema, você pode especificar o caminho aqui.
# Exemplo no Windows: FFMPEG_PATH = "C:/ffmpeg/bin/ffmpeg.exe"
# Exemplo no Linux/macOS: FFMPEG_PATH = "/usr/local/bin/ffmpeg"
# Deixe como None para que o yt-dlp tente encontrar automaticamente.
FFMPEG_PATH = "C:/ffmpeg/bin/ffmpeg.exe"
# -----------------------------

def solicitar_url():
    """Solicita a URL do vídeo ao usuário."""
    while True:
        url = input("Digite a URL do vídeo que deseja baixar (ou deixe em branco para sair): ").strip()
        if not url:
            return None
        # Validação muito básica de URL
        if url.startswith("http://") or url.startswith("https://"):
            return url
        else:
            print("URL inválida. Por favor, insira uma URL completa (começando com http ou https).")

def solicitar_pasta_destino():
    """Solicita a pasta de destino para o download."""
    default_path = os.path.join(os.getcwd(), "downloads_videos") # Pasta padrão 'downloads_videos'
    print(f"A pasta padrão para downloads é: {default_path}")
    while True:
        pasta_input = input(f"Digite a pasta de destino (ou deixe em branco para usar '{default_path}'): ").strip()
        
        if not pasta_input:
            pasta_destino = default_path
        else:
            pasta_destino = pasta_input
        
        try:
            if not os.path.isdir(pasta_destino):
                os.makedirs(pasta_destino, exist_ok=True)
                print(f"Pasta '{pasta_destino}' criada.")
            return pasta_destino
        except OSError as e:
            print(f"Erro ao criar ou acessar a pasta '{pasta_destino}': {e}. Por favor, tente um caminho válido.")

def listar_e_escolher_formato(url):
    """
    Busca os formatos disponíveis para a URL, apresenta opções ao usuário
    e retorna o ID do formato escolhido e se é para converter para MP3.
    Retorna uma tupla (formato_string, converter_para_mp3_flag) ou None em caso de erro.
    """
    print("\nBuscando formatos disponíveis... Isso pode levar um momento.")
    ydl_opts_info = {'quiet': True, 'no_warnings': True}
    if FFMPEG_PATH:
        ydl_opts_info['ffmpeg_location'] = FFMPEG_PATH

    try:
        with yt_dlp.YoutubeDL(ydl_opts_info) as ydl:
            info_dict = ydl.extract_info(url, download=False) # Não baixa, apenas pega informações
            formats = info_dict.get('formats', [])
    except yt_dlp.utils.DownloadError as e:
        print(f"Erro ao buscar informações do vídeo: {e}")
        print("Verifique a URL ou sua conexão com a internet. A plataforma pode não ser suportada ou o vídeo pode ser privado/restrito.")
        return None, False
    except Exception as e:
        print(f"Erro inesperado ao buscar formatos: {e}")
        return None, False

    if not formats:
        print("Nenhum formato de vídeo/áudio encontrado para esta URL.")
        return None, False

    print("\n--- Opções de Qualidade/Formato ---")
    print("1. Melhor qualidade geral (vídeo+áudio, pode precisar de FFmpeg para mesclar)")
    print("2. Melhor qualidade em MP4 (vídeo+áudio, pode precisar de FFmpeg para mesclar)")
    print("3. Melhor qualidade apenas áudio (formato original da plataforma)")
    print("4. Melhor qualidade apenas áudio (converter para MP3, precisa de FFmpeg)")
    print("5. Listar todos os formatos disponíveis e escolher manualmente (avançado)")
    print("0. Padrão (melhor qualidade geral, como a opção 1)")

    while True:
        escolha_menu = input("Escolha uma opção (0-5): ").strip()
        if escolha_menu == '1':
            return 'bestvideo+bestaudio/best', False
        elif escolha_menu == '2':
            return 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best', False
        elif escolha_menu == '3':
            return 'bestaudio/best', False
        elif escolha_menu == '4':
            return 'bestaudio/best', True # Sinaliza para converter para MP3
        elif escolha_menu == '0':
            return 'bestvideo+bestaudio/best', False
        elif escolha_menu == '5':
            break # Prossegue para listagem detalhada
        else:
            print("Opção inválida. Tente novamente.")

    # Listagem detalhada para a opção '5'
    print("\n--- Formatos Disponíveis Detalhados ---")
    formatos_display = []
    for f in formats:
        # Ignora formatos que são apenas metadados ou thumbnails
        if not f.get('vcodec', 'none') == 'none' or not f.get('acodec', 'none') == 'none':
            formatos_display.append(f)
    
    if not formatos_display:
        print("Nenhum formato de vídeo/áudio detalhado encontrado.")
        return 'bestvideo+bestaudio/best', False # Fallback

    for i, f in enumerate(formatos_display):
        res = f.get('resolution', 'Áudio')
        ext = f.get('ext', 'N/A')
        vcodec = f.get('vcodec', 'none')
        acodec = f.get('acodec', 'none')
        format_note = f.get('format_note', '')
        filesize_approx = f.get('filesize') or f.get('filesize_approx') # 'filesize' é mais preciso se disponível
        filesize_str = f"{filesize_approx / (1024 * 1024):.2f} MB" if filesize_approx else "Desconhecido"
        
        tipo = ""
        if vcodec != 'none' and acodec != 'none':
            tipo = "Vídeo+Áudio"
        elif vcodec != 'none':
            tipo = "Vídeo Apenas"
        elif acodec != 'none':
            tipo = "Áudio Apenas"

        print(f"ID: {f['format_id']:<10} | Tipo: {tipo:<13} | Ext: {ext:<5} | Res: {res:<12} | Tamanho: {filesize_str:<15} | Nota: {format_note}")

    while True:
        id_escolhido = input("Digite o ID do formato desejado (ex: '137+140' para vídeo e áudio separados, ou '22' para um formato combinado) ou 'c' para cancelar e usar o padrão: ").strip()
        if id_escolhido.lower() == 'c':
            return 'bestvideo+bestaudio/best', False
        
        # Validação simples (yt-dlp lidará com IDs inválidos, mas podemos tentar uma verificação básica)
        # O usuário pode digitar combinações como "137+140", então a validação de ID único não é suficiente aqui.
        # Deixaremos o yt-dlp validar o formato_id complexo.
        if id_escolhido: # Se o usuário digitou algo
            return id_escolhido, False # Não há conversão para MP3 automática nesta opção
        else:
            print("ID inválido. Por favor, tente novamente.")


def baixar_video(url, formato_id, pasta_destino, converter_para_mp3=False):
    """Baixa o vídeo com as opções especificadas."""
    
    # Nome do arquivo de saída: Titulo [ID_Video].extensao
    # Adicionamos o ID do vídeo para evitar conflitos com títulos iguais.
    caminho_template = os.path.join(pasta_destino, '%(title)s [%(id)s].%(ext)s')

    ydl_opts = {
        'format': formato_id,
        'outtmpl': caminho_template,
        'noplaylist': True, # Baixa apenas o vídeo se a URL for de uma playlist
        'nocheckcertificate': True, # Pode ajudar em algumas redes com problemas de SSL
        'progress_hooks': [lambda d: print_progress(d, url)], # Hook para mostrar progresso
        # 'verbose': True, # Descomente para depuração
    }

    if FFMPEG_PATH:
        ydl_opts['ffmpeg_location'] = FFMPEG_PATH

    if converter_para_mp3:
        ydl_opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192', # Qualidade do MP3 em kbps
        }]
        # Se estamos extraindo áudio, não precisamos de merge_output_format para vídeo
        # E o formato deve ser apenas de áudio
        ydl_opts['format'] = 'bestaudio/best' if formato_id != 'bestaudio/best' and not 'audio' in formato_id.lower() else formato_id
        print("Configurado para baixar e converter para MP3.")
    elif formato_id and ('bestvideo' in formato_id or '+' in formato_id): # Formatos que podem precisar de mesclagem
        ydl_opts['merge_output_format'] = 'mp4' # Tenta mesclar em MP4 por padrão
        print(f"Formato selecionado ('{formato_id}') pode requerer mesclagem com FFmpeg.")


    print(f"\nIniciando download de: {url}")
    print(f"Formato: {formato_id}{' (convertendo para MP3)' if converter_para_mp3 else ''}")
    print(f"Salvando em: {pasta_destino}")
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        # O hook de progresso já informa a conclusão, mas podemos adicionar uma msg final.
        # print(f"Download de '{url}' concluído com sucesso!") # Removido pois o hook já faz algo similar
    except yt_dlp.utils.DownloadError as e:
        print(f"\nErro durante o download do yt-dlp: {e}")
        print("Verifique se o FFmpeg está instalado e no PATH se o formato escolhido requer mesclagem ou conversão.")
    except Exception as e:
        print(f"\nOcorreu um erro inesperado durante o download: {e}")

def print_progress(d, url_original="Vídeo"):
    """Função de hook para exibir o progresso do download."""
    if d['status'] == 'downloading':
        total_bytes_str = d.get('total_bytes_estimate_str') or d.get('total_bytes_str') or "N/A"
        downloaded_bytes_str = d.get('downloaded_bytes_str', "N/A")
        speed_str = d.get('speed_str', "N/A")
        eta_str = d.get('eta_str', "N/A")
        progress_percent_str = d.get('_percent_str', "0.0%")
        
        # Limpa a linha anterior para atualizar o progresso no mesmo lugar
        print(f"\rBaixando '{d.get('filename', url_original)}': {progress_percent_str} de {total_bytes_str} @ {speed_str} (ETA: {eta_str})", end="")
    
    elif d['status'] == 'finished':
        # Garante que a linha de progresso seja limpa e uma mensagem final seja impressa
        print(f"\rDownload de '{d.get('filename', url_original)}' concluído. Salvo como: {d.get('filename') or d.get('info_dict', {}).get('_filename')}")
        # print(f"Salvo como: {d.get('filename') or d.get('info_dict', {}).get('_filename')}")
    
    elif d['status'] == 'error':
        print(f"\rErro ao baixar '{d.get('filename', url_original)}'.")


def main():
    """Função principal do programa."""
    print("-----------------------------------------------------------")
    print("Bem-vindo ao Downloader de Vídeos Universal (usando yt-dlp)")
    print("-----------------------------------------------------------")
    print("Aviso: Baixar conteúdo protegido por direitos autorais sem")
    print("permissão pode ser ilegal. Use este programa de forma responsável.")
    print("\nLembre-se de manter o yt-dlp atualizado: pip install --upgrade yt-dlp")
    if not FFMPEG_PATH:
        print("Para melhor compatibilidade (mesclar formatos, converter para MP3),")
        print("certifique-se de que o FFmpeg está instalado e no PATH do sistema,")
        print("ou configure a variável FFMPEG_PATH no início deste script.")
    print("-----------------------------------------------------------\n")

    while True:
        url_video = solicitar_url()
        if not url_video:
            print("Saindo do programa.")
            break

        pasta_escolhida = solicitar_pasta_destino()
        
        retorno_formato = listar_e_escolher_formato(url_video)
        if retorno_formato is None or retorno_formato[0] is None:
            print("Não foi possível determinar o formato do vídeo. Tente outra URL ou verifique as mensagens de erro.")
            continue # Volta para solicitar nova URL
        
        formato_id, converter_para_mp3 = retorno_formato

        baixar_video(url_video, formato_id, pasta_escolhida, converter_para_mp3)

        print("-" * 50)
        continuar = input("Deseja baixar outro vídeo? (s/N): ").strip().lower()
        if continuar != 's':
            print("Obrigado por usar o programa! Saindo.")
            break
        print("\n")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nDownload interrompido pelo usuário. Saindo.")
    except Exception as e_global:
        print(f"\n--- ERRO CRÍTICO NO PROGRAMA ---")
        print(f"Ocorreu um erro inesperado: {e_global}")
        print("Por favor, reporte este erro se persistir.")