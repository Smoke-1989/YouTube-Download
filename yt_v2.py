"""
Atualização do seu downloader (yt.py) — versão mais robusta.
Recursos adicionados:
 - Suporte a playlists (YouTube e outros provedores suportados pelo yt-dlp)
 - Filtros aplicáveis a playlists: duração mínima/máxima, intervalo de data, título contém (substring/regex)
 - Evitar duplicatas: checagem por ID e por arquivo existente + banco local (JSON)
 - Modo interativo e modo comando (CLI) com argparse
 - Opção para preservar o nome (sem adicionar [id]) ou incluir id para garantir unicidade
 - Suporte a conversão MP3, mesclagem com ffmpeg, resume automático
 - Registro (logging) e arquivo de histórico (downloaded_ids.json)
 - Paralelismo configurável (ThreadPoolExecutor) - cuidado com limites do provedor
 - Retry simples para downloads com backoff
 - Hooks de progresso com logs limpos

OBSERVAÇÕES:
 - Não é possível garantir "nome de arquivo original no servidor" — o que existe é o título/metadata que o yt-dlp fornece. Há uma opção `--preserve-filename` que tenta reduzir alterações no título, mas downloads idênticos podem causar sobrescrita se não usar o id.
 - Vídeos privados/restritos não podem ser baixados sem credenciais/contas/autenticação apropriada.
 - Use com responsabilidade e respeite direitos autorais e termos de serviço.

"""

import argparse
import json
import logging
import os
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

import yt_dlp

# Configuração padrão
FFMPEG_PATH = "C:/ffmpeg/bin/ffmpeg.exe"  # Ajuste ou deixe como None
DB_FILENAME = "downloaded_ids.json"
LOG_FILENAME = "yt_downloader.log"
DEFAULT_DEST = os.path.join(os.getcwd(), "downloads_videos")

# Logger
logger = logging.getLogger("yt_downloader")
logger.setLevel(logging.DEBUG)
fh = logging.FileHandler(LOG_FILENAME, encoding="utf-8")
fh.setLevel(logging.DEBUG)
ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", "%Y-%m-%d %H:%M:%S")
fh.setFormatter(formatter)
ch.setFormatter(formatter)
logger.addHandler(fh)
logger.addHandler(ch)

# Lock para acesso ao DB compartilhado
db_lock = threading.Lock()


# ----------------- Utilitários -----------------

def ensure_folder(folder_path: str):
    os.makedirs(folder_path, exist_ok=True)


def load_db(db_path: str):
    if os.path.exists(db_path):
        try:
            with open(db_path, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except Exception as e:
            logger.warning(f"Falha ao ler DB '{db_path}': {e}. Recriando DB vazio.")
            return set()
    return set()


def save_db(db_path: str, id_set: set):
    tmp = db_path + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(list(id_set), f, ensure_ascii=False, indent=2)
        os.replace(tmp, db_path)
    except Exception as e:
        logger.error(f"Erro salvando DB: {e}")


def parse_date_YYYYMMDD(s: str):
    # aceita formatos 'YYYY-MM-DD', 'YYYYMMDD', 'DD/MM/YYYY'
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%Y%m%d", "%d/%m/%Y"):
        try:
            d = datetime.strptime(s, fmt)
            return d.strftime("%Y%m%d")
        except Exception:
            continue
    raise argparse.ArgumentTypeError(f"Formato de data inválido: {s}")


def parse_duration_to_seconds(s: str):
    # Aceita segundos ou mm:ss ou hh:mm:ss
    if not s:
        return None
    if s.isdigit():
        return int(s)
    parts = s.split(":")
    try:
        parts = [int(p) for p in parts]
    except Exception:
        raise argparse.ArgumentTypeError(f"Formato de duração inválido: {s}")
    if len(parts) == 2:
        return parts[0] * 60 + parts[1]
    if len(parts) == 3:
        return parts[0] * 3600 + parts[1] * 60 + parts[2]
    raise argparse.ArgumentTypeError(f"Formato de duração inválido: {s}")


# --------------- Downloader core ----------------

def build_ydl_opts(outtmpl, format_id, ffmpeg_path=None, convert_mp3=False, quiet=False, continuedl=True):
    opts = {
        "format": format_id or "best",
        "outtmpl": outtmpl,
        "noplaylist": True,
        "nocheckcertificate": True,
        "continuedl": continuedl,
        "progress_hooks": [progress_hook],
        "quiet": quiet,
    }
    if ffmpeg_path:
        opts["ffmpeg_location"] = ffmpeg_path
    if convert_mp3:
        opts["postprocessors"] = [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }]
        opts["format"] = "bestaudio/best"
    return opts


def progress_hook(d):
    status = d.get("status")
    if status == "downloading":
        p = d.get("_percent_str", "0.0%")
        speed = d.get("speed_str", "N/A")
        eta = d.get("eta", "N/A")
        filename = os.path.basename(d.get("filename") or d.get("info_dict", {}).get("_filename", ""))
        print(f"\rBaixando {filename}: {p} @ {speed} (ETA: {eta})", end="")
    elif status == "finished":
        filename = d.get("filename") or d.get("info_dict", {}).get("_filename")
        logger.info(f"Download concluído: {filename}")
    elif status == "error":
        logger.error("Erro no hook de progresso: %s", d)


def should_skip_entry(entry, filters, downloaded_ids, dest, preserve_filename):
    # entry é um dict do yt-dlp com keys como 'id', 'duration', 'upload_date', 'title'
    vid = entry.get("id")
    if not vid:
        return False, "sem-id"
    if filters.get("skip_downloaded") and vid in downloaded_ids:
        return True, "id no DB"

    # Checa arquivo existente
    if not preserve_filename:
        # buscamos por [id] no diretório
        pattern = f"*[{vid}]*"
        matches = list(Path(dest).glob(f"*{vid}*"))
        if matches:
            return True, "arquivo existente com id"
    else:
        # se preserva nome, checar por title.ext (pode colidir)
        title = entry.get("title", "")
        # simplificação: checar algum arquivo que contenha o título (não 100% confiável)
        for p in Path(dest).iterdir():
            if p.is_file() and title and title in p.name:
                return True, "arquivo existente por título"

    dur = entry.get("duration")
    if filters.get("min_duration") and dur is not None and dur < filters["min_duration"]:
        return True, "duração menor"
    if filters.get("max_duration") and dur is not None and dur > filters["max_duration"]:
        return True, "duração maior"

    upload_date = entry.get("upload_date")  # formato YYYYMMDD
    if filters.get("date_from") and upload_date and upload_date < filters["date_from"]:
        return True, "upload_date antes do limite"
    if filters.get("date_to") and upload_date and upload_date > filters["date_to"]:
        return True, "upload_date depois do limite"

    title = entry.get("title", "")
    match_title = filters.get("match_title")
    if match_title:
        if filters.get("match_regex"):
            try:
                if not re.search(match_title, title, re.IGNORECASE):
                    return True, "título não bate regex"
            except re.error:
                logger.warning("Regex inválido fornecido para --match-title; ignorando regex e usando substring.")
                if match_title.lower() not in title.lower():
                    return True, "título não contém substring"
        else:
            if match_title.lower() not in title.lower():
                return True, "título não contém substring"

    return False, "ok"


def download_with_retries(url, ydl_opts, retries=3, backoff=3):
    attempt = 0
    last_exc = None
    while attempt < retries:
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            return True
        except Exception as e:
            last_exc = e
            attempt += 1
            wait = backoff * attempt
            logger.warning(f"Falha no download (tentativa {attempt}/{retries}) para {url}: {e}. Retry em {wait}s")
            time.sleep(wait)
    logger.error(f"Todas as tentativas falharam para {url}. Último erro: {last_exc}")
    return False


# ---------------- Playlist / flow ----------------

def process_playlist(url, dest, args):
    # Extrai info da playlist
    ydl_info = yt_dlp.YoutubeDL({'quiet': True, 'nocheckcertificate': True, 'ffmpeg_location': FFMPEG_PATH if FFMPEG_PATH else None})
    try:
        info = ydl_info.extract_info(url, download=False)
    except Exception as e:
        logger.error(f"Erro ao extrair informações da URL: {e}")
        return

    entries = []
    if info.get('entries'):
        # playlist
        entries = [e for e in info['entries'] if e]
    else:
        # single vídeo
        entries = [info]

    logger.info(f"Encontrados {len(entries)} entradas na lista.")

    # Carrega DB
    db_path = os.path.join(dest, DB_FILENAME)
    downloaded_ids = load_db(db_path)

    filters = {
        'min_duration': args.min_duration,
        'max_duration': args.max_duration,
        'date_from': args.date_from,
        'date_to': args.date_to,
        'match_title': args.match_title,
        'match_regex': args.match_regex,
        'skip_downloaded': args.skip_downloaded,
    }

    tasks = []
    with ThreadPoolExecutor(max_workers=args.parallel) as exe:
        futures = {}
        for entry in entries:
            # Some playlist entries might be None or missing id
            if not entry:
                continue
            # Each entry may not have complete metadata until ydl.extract_info(entry_url) is called.
            # However many fields are present in playlist entries already.
            skip, reason = should_skip_entry(entry, filters, downloaded_ids, dest, args.preserve_filename)
            if skip:
                logger.info(f"Pulando {entry.get('title') or entry.get('id')} — {reason}")
                continue

            # Determine URL for the entry
            entry_url = entry.get('webpage_url') or entry.get('url') or f"https://www.youtube.com/watch?v={entry.get('id')}"

            # Prepare outtmpl
            if args.preserve_filename:
                outtmpl = os.path.join(dest, '%(title)s.%(ext)s')
            else:
                outtmpl = os.path.join(dest, '%(title)s [%(id)s].%(ext)s')

            ydl_opts = build_ydl_opts(outtmpl, args.format, FFMPEG_PATH, convert_mp3=args.convert_mp3, quiet=False, continuedl=True)

            # Submit task
            futures[exe.submit(worker_download_entry, entry_url, entry.get('id'), ydl_opts, db_path, args)] = entry

        # Wait for completion and report
        for fut in as_completed(futures):
            entry = futures[fut]
            try:
                success = fut.result()
                if success:
                    logger.info(f"Processado: {entry.get('title') or entry.get('id')}")
                else:
                    logger.warning(f"Falha ao processar: {entry.get('title') or entry.get('id')}")
            except Exception as e:
                logger.exception(f"Erro inesperado processando {entry.get('title') or entry.get('id')}: {e}")


def worker_download_entry(entry_url, entry_id, ydl_opts, db_path, args):
    # efetua download com retries e atualiza DB
    success = download_with_retries(entry_url, ydl_opts, retries=args.retries, backoff=args.backoff)
    if success and entry_id:
        with db_lock:
            ids = load_db(db_path)
            ids.add(entry_id)
            save_db(db_path, ids)
    return success


# ----------------- CLI / interface -----------------

def interactive_flow():
    print("Modo interativo ativado.")
    url = input("Cole a URL do vídeo/playlist: ").strip()
    if not url:
        print("URL vazia. Saindo.")
        return
    dest = input(f"Pasta destino (enter para usar '{DEFAULT_DEST}'): ").strip() or DEFAULT_DEST
    ensure_folder(dest)

    print("Escolha formato/qualidade:")
    print("  0 - padrão (melhor)")
    print("  1 - melhor MP4")
    print("  2 - apenas áudio (bestaudio)")
    fmt_choice = input("Opção (0/1/2): ").strip()
    fmt = None
    convert_mp3 = False
    if fmt_choice == '1':
        fmt = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
    elif fmt_choice == '2':
        fmt = 'bestaudio/best'
        if input("Converter para MP3? (s/N): ").strip().lower() == 's':
            convert_mp3 = True
    else:
        fmt = 'bestvideo+bestaudio/best'

    # Filtros básicos
    min_d = input("Duração mínima (segundos ou mm:ss) [vazio para ignorar]: ").strip()
    max_d = input("Duração máxima (segundos ou mm:ss) [vazio para ignorar]: ").strip()
    date_from = input("Data mínima upload (YYYY-MM-DD) [vazio]: ").strip()
    date_to = input("Data máxima upload (YYYY-MM-DD) [vazio]: ").strip()

    parser_args = argparse.Namespace(
        url=url,
        dest=dest,
        format=fmt,
        convert_mp3=convert_mp3,
        preserve_filename=False,
        min_duration=parse_duration_to_seconds(min_d) if min_d else None,
        max_duration=parse_duration_to_seconds(max_d) if max_d else None,
        date_from=parse_date_YYYYMMDD(date_from) if date_from else None,
        date_to=parse_date_YYYYMMDD(date_to) if date_to else None,
        match_title=None,
        match_regex=False,
        skip_downloaded=True,
        parallel=1,
        retries=3,
        backoff=3,
    )

    process_playlist(parser_args.url, parser_args.dest, parser_args)


def build_arg_parser():
    p = argparse.ArgumentParser(description="Downloader robusto com suporte a playlists e filtros (yt-dlp)")
    p.add_argument("url", nargs='?', help="URL do vídeo ou playlist")
    p.add_argument("--dest", "-d", default=DEFAULT_DEST, help="Pasta destino")
    p.add_argument("--format", "-f", default=None, help="Formato yt-dlp (ex: 'best', 'bestaudio/best', '137+140')")
    p.add_argument("--convert-mp3", action='store_true', help="Extrair áudio e converter para mp3")
    p.add_argument("--preserve-filename", action='store_true', help="Não adicionar [id] ao nome do arquivo (pode causar duplicatas)")
    p.add_argument("--min-duration", type=parse_duration_to_seconds, default=None, help="Duração mínima (segundos ou mm:ss)")
    p.add_argument("--max-duration", type=parse_duration_to_seconds, default=None, help="Duração máxima (segundos ou mm:ss)")
    p.add_argument("--date-from", type=parse_date_YYYYMMDD, default=None, help="Data mínima de upload (YYYY-MM-DD or DD/MM/YYYY)")
    p.add_argument("--date-to", type=parse_date_YYYYMMDD, default=None, help="Data máxima de upload")
    p.add_argument("--match-title", default=None, help="Baixar apenas vídeos cujo título contenha essa substring ou regex")
    p.add_argument("--match-regex", action='store_true', help="Interpreta --match-title como regex")
    p.add_argument("--skip-downloaded", action='store_true', default=True, help="Pular vídeos já registrados no DB")
    p.add_argument("--parallel", type=int, default=1, help="Número de downloads simultâneos (cuidado com limites)")
    p.add_argument("--retries", type=int, default=3, help="Tentativas de retry por vídeo")
    p.add_argument("--backoff", type=int, default=3, help="Backoff base (segundos) entre retries)")
    p.add_argument("--quiet", action='store_true', help="Modo silencioso")
    p.add_argument("--interactive", action='store_true', help="Modo interativo")
    return p


def main():
    parser = build_arg_parser()
    args = parser.parse_args()

    if args.interactive:
        return interactive_flow()

    if not args.url:
        parser.print_help()
        return

    dest = args.dest
    ensure_folder(dest)

    # Sanitize some defaults
    if not args.format:
        args.format = 'bestvideo+bestaudio/best' if not args.convert_mp3 else 'bestaudio/best'

    process_playlist(args.url, dest, args)


if __name__ == '__main__':
    try:
        # se houver argumentos de linha de comando, use CLI; senão, interativo
        if len(sys.argv) > 1:
            main()
        else:
            # se estiver no Termux (variável TERMUX_VERSION presente), forçar interativo
            if 'TERMUX_VERSION' in os.environ or len(sys.argv) == 1:
                interactive_flow()
            else:
                main()
    except KeyboardInterrupt:
        logger.info("Interrompido pelo usuário.")
    except Exception as e:
        logger.exception(f"Erro crítico: {e}")
