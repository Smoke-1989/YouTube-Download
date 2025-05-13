# Downloader de Vídeos Universal (Python Script)

Este é um script Python interativo para baixar vídeos de diversas plataformas da internet utilizando a poderosa biblioteca `yt-dlp`. Ele permite ao usuário fornecer a URL do vídeo, escolher a pasta de destino e selecionar a qualidade ou formato desejado para o download.

## Funcionalidades

* Download de vídeos de centenas de sites suportados pelo `yt-dlp`.
* Interface de linha de comando interativa:
    * Solicita a URL do vídeo.
    * Solicita a pasta de destino para salvar o arquivo (cria a pasta se não existir).
    * Oferece um menu para escolha de formatos e qualidades, incluindo:
        * Melhor qualidade geral (vídeo+áudio).
        * Melhor qualidade em formato MP4.
        * Melhor qualidade apenas de áudio.
        * Converter áudio para MP3 (requer FFmpeg).
        * Listar todos os formatos disponíveis para escolha manual avançada.
* Exibição do progresso do download.
* Possibilidade de baixar múltiplos vídeos em sequência.

## Pré-requisitos

* **Python 3.6+**: Se você não tem o Python instalado, baixe-o em [python.org](https://www.python.org/).
* **pip**: O gerenciador de pacotes do Python (geralmente vem instalado com o Python).

## Dependências

* **`yt-dlp`**: A biblioteca principal usada para interagir com os sites de vídeo e realizar os downloads.

## Instalação

1.  **Baixe o script:**
    Salve o código do programa como `meu_downloader.py` em uma pasta no seu computador.

2.  **Instale a dependência `yt-dlp`:**
    Abra seu terminal ou prompt de comando e execute:
    ```bash
    pip install yt-dlp
    ```
    É altamente recomendável manter o `yt-dlp` atualizado para garantir compatibilidade com o maior número de sites possível:
    ```bash
    pip install --upgrade yt-dlp
    ```

3.  **Instale o FFmpeg (Altamente Recomendado):**
    Para funcionalidades avançadas como baixar vídeos em alta qualidade (que muitas vezes são servidos como faixas de áudio e vídeo separadas) ou converter áudio para o formato MP3, o **FFmpeg** é necessário.
    * Baixe o FFmpeg em [ffmpeg.org](https://ffmpeg.org/download.html).
    * Instale-o e adicione o diretório `bin` do FFmpeg ao PATH do seu sistema.
    * Alternativamente, você pode editar o script `meu_downloader.py` e definir o caminho para o executável do FFmpeg na variável `FFMPEG_PATH` no início do arquivo, caso não queira adicioná-lo ao PATH.

## Como Usar

1.  Abra seu terminal ou prompt de comando.
2.  Navegue até a pasta onde você salvou o script `meu_downloader.py`.
3.  Execute o script com o Python:
    ```bash
    python meu_downloader.py
    ```
4.  O programa iniciará e solicitará as seguintes informações:
    * **URL do vídeo**: Cole a URL completa do vídeo que deseja baixar.
    * **Pasta de destino**: Especifique onde o vídeo deve ser salvo. Se deixado em branco, uma pasta chamada `downloads_videos` será criada (ou usada) no mesmo diretório do script.
    * **Opção de formato/qualidade**: Um menu será apresentado com diferentes opções. Digite o número da opção desejada.
        * **Opção 1 (Melhor qualidade geral):** Tenta baixar a melhor qualidade de vídeo e áudio combinados. Pode resultar em formatos como WebM ou MKV e pode requerer FFmpeg para mesclagem.
        * **Opção 2 (Melhor qualidade MP4):** Tenta baixar a melhor qualidade de vídeo e áudio combinados no formato MP4. Frequentemente requer FFmpeg para mesclagem.
        * **Opção 3 (Melhor áudio - original):** Baixa a melhor faixa de áudio no formato original fornecido pela plataforma.
        * **Opção 4 (Melhor áudio - MP3):** Baixa a melhor faixa de áudio e a converte para MP3 usando FFmpeg.
        * **Opção 5 (Listar e escolher):** Exibe uma lista detalhada de todos os formatos (vídeo, áudio, combinados) disponíveis para aquela URL específica, permitindo que você digite o ID do formato desejado. Útil para usuários avançados.
        * **Opção 0 (Padrão):** Similar à opção 1.

5.  O download será iniciado e o progresso será exibido no terminal.
6.  Após a conclusão (ou falha) do download, o programa perguntará se você deseja baixar outro vídeo.

## Observações Importantes

* **Legalidade e Termos de Serviço:**
    Lembre-se de que baixar conteúdo protegido por direitos autorais sem a permissão explícita do detentor dos direitos é ilegal em muitos países e pode violar os termos de serviço das plataformas de vídeo. Utilize este programa de forma responsável e ética, respeitando os direitos autorais e os termos de uso das plataformas.

* **Manter `yt-dlp` Atualizado:**
    Os sites de vídeo frequentemente alteram suas estruturas, o que pode quebrar a funcionalidade de download. Mantenha a biblioteca `yt-dlp` atualizada executando `pip install --upgrade yt-dlp` regularmente.

* **Importância do FFmpeg:**
    Conforme mencionado, o FFmpeg é crucial para mesclar faixas de áudio e vídeo separadas (comum para qualidades HD no YouTube e outras plataformas) e para conversões de formato (como para MP3). Se downloads de alta qualidade falharem ou resultarem em arquivos sem som (ou sem vídeo), a ausência ou má configuração do FFmpeg é uma causa provável.

* **Resolução de Problemas:**
    * Verifique se a URL está correta e acessível no navegador.
    * Certifique-se de que sua conexão com a internet está estável.
    * Se um site específico não funcionar, tente atualizar o `yt-dlp`.
    * Para erros de mesclagem ou conversão, verifique sua instalação do FFmpeg.
    * O script tenta capturar erros comuns, mas mensagens do `yt-dlp` podem aparecer diretamente no console, oferecendo mais detalhes sobre o problema.

---

Este script é fornecido como uma ferramenta educacional e de conveniência. O uso responsável é de inteira responsabilidade do usuário.