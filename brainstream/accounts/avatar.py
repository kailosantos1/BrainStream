"""Processamento das fotos de perfil (upload no perfil ou foto da conta Google)."""
import uuid
from io import BytesIO

from django.core.files.base import ContentFile
from PIL import Image, ImageOps, UnidentifiedImageError

AVATAR_TAMANHO = 256
AVATAR_LIMITE_BYTES = 2 * 1024 * 1024
AVATAR_LIMITE_PIXELS = 6000
AVATAR_FORMATOS = {'JPEG', 'PNG', 'WEBP'}


class ImagemInvalida(ValueError):
    pass


def processar_avatar(origem):
    """
    Lê a imagem (arquivo ou bytes), confere formato e tamanho, aplica a rotação do EXIF, corta ao
    centro em 256 px e regrava como WebP — o que descarta todos os metadados (inclusive GPS).
    """
    if isinstance(origem, (bytes, bytearray)):
        origem = BytesIO(origem)
    origem.seek(0)
    try:
        with Image.open(origem) as imagem:
            if imagem.format not in AVATAR_FORMATOS:
                raise ImagemInvalida('formato')
            if max(imagem.size) > AVATAR_LIMITE_PIXELS:
                raise ImagemInvalida('dimensões')
            imagem = ImageOps.exif_transpose(imagem).convert('RGB')
            quadrada = ImageOps.fit(imagem, (AVATAR_TAMANHO, AVATAR_TAMANHO), Image.Resampling.LANCZOS)
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as erro:
        raise ImagemInvalida('imagem ilegível') from erro
    saida = BytesIO()
    quadrada.save(saida, format='WEBP', quality=85)
    return ContentFile(saida.getvalue())


def salvar_avatar(estudante, conteudo):
    """Troca a foto do estudante (apaga a anterior) por ``conteudo`` já processado. Não salva o model."""
    if estudante.avatar:
        estudante.avatar.delete(save=False)
    estudante.avatar.save(f'{uuid.uuid4().hex}.webp', conteudo, save=False)
