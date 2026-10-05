"""Procesamiento de imágenes de documentos escaneados (OpenCV + Pillow).

Pipeline:
  1. Validación (extensión + contenido real JPEG/PNG + tamaño razonable).
  2. Auto-rotación según EXIF.
  3. Eliminación de sombras (opcional) por normalización de fondo.
  4. Corrección adaptativa de contraste/brillo (CLAHE sobre canal L de LAB).
  5. Guardado seguro (nombre UUID + timestamp) y miniatura de 300 px.

Las rutas devueltas son relativas a UPLOAD_FOLDER (p.ej. "images/2026/10/x.jpg")
para no exponer rutas absolutas del servidor.
"""
from __future__ import annotations

import io
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import BinaryIO

import cv2
import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError

logger = logging.getLogger(__name__)

# Protección contra "decompression bombs" (≈ 80 megapíxeles)
Image.MAX_IMAGE_PIXELS = 80_000_000
MAX_SIDE_PX = 4000  # Las imágenes mayores se reducen para limitar disco y memoria.
JPEG_QUALITY = 88


class ImageProcessingError(ValueError):
    """Error de validación o procesamiento de la imagen subida."""


@dataclass(frozen=True)
class ProcessedImage:
    image_path: str       # relativa a UPLOAD_FOLDER
    thumbnail_path: str   # relativa a UPLOAD_FOLDER
    width: int
    height: int


class ImageProcessor:
    def __init__(
        self,
        upload_root: str | Path,
        allowed_extensions: frozenset[str] = frozenset({"jpg", "jpeg", "png"}),
        allowed_formats: frozenset[str] = frozenset({"JPEG", "PNG"}),
        thumbnail_size: int = 300,
    ) -> None:
        self.upload_root = Path(upload_root).resolve()
        self.allowed_extensions = allowed_extensions
        self.allowed_formats = allowed_formats
        self.thumbnail_size = thumbnail_size

    # ------------------------------------------------------------------ #
    # API pública
    # ------------------------------------------------------------------ #
    def process_upload(
        self, stream: BinaryIO, original_filename: str, remove_shadows: bool = True
    ) -> ProcessedImage:
        """Valida, limpia y guarda la imagen. Devuelve rutas relativas."""
        self._validate_extension(original_filename)
        raw = stream.read()
        if not raw:
            raise ImageProcessingError("El archivo de imagen está vacío.")

        pil_image = self._open_and_verify(raw)
        pil_image = ImageOps.exif_transpose(pil_image)  # auto-rotación EXIF
        pil_image = self._to_rgb(pil_image)
        pil_image = self._limit_size(pil_image)

        bgr = cv2.cvtColor(np.asarray(pil_image), cv2.COLOR_RGB2BGR)
        if remove_shadows:
            bgr = self.remove_shadows(bgr)
        bgr = self.enhance_contrast(bgr)
        cleaned = Image.fromarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))

        relative_dir, base_name = self._build_target_name()
        image_rel = relative_dir / f"{base_name}.jpg"
        thumb_rel = relative_dir / "thumbnails" / f"{base_name}_thumb.jpg"

        image_abs = self._safe_abs(image_rel)
        thumb_abs = self._safe_abs(thumb_rel)
        image_abs.parent.mkdir(parents=True, exist_ok=True)
        thumb_abs.parent.mkdir(parents=True, exist_ok=True)

        try:
            # EXIF se descarta intencionadamente (privacidad: GPS, dispositivo...)
            cleaned.save(image_abs, format="JPEG", quality=JPEG_QUALITY, optimize=True)
            self._make_thumbnail(cleaned).save(thumb_abs, format="JPEG", quality=80, optimize=True)
        except OSError as exc:
            self.delete_files(str(image_rel), str(thumb_rel))
            logger.exception("No se pudo guardar la imagen procesada")
            raise ImageProcessingError("No se pudo guardar la imagen en el servidor.") from exc

        return ProcessedImage(
            image_path=image_rel.as_posix(),
            thumbnail_path=thumb_rel.as_posix(),
            width=cleaned.width,
            height=cleaned.height,
        )

    def absolute_path(self, relative_path: str) -> Path:
        """Resuelve una ruta relativa almacenada en BD impidiendo path traversal."""
        return self._safe_abs(Path(relative_path))

    def delete_files(self, *relative_paths: str | None) -> None:
        """Elimina ficheros (ignora inexistentes). Usado para rollback."""
        for rel in relative_paths:
            if not rel:
                continue
            try:
                self._safe_abs(Path(rel)).unlink(missing_ok=True)
            except (OSError, ImageProcessingError):
                logger.warning("No se pudo eliminar %s", rel)

    # ------------------------------------------------------------------ #
    # Filtros de imagen
    # ------------------------------------------------------------------ #
    @staticmethod
    def remove_shadows(bgr: np.ndarray) -> np.ndarray:
        """Normaliza la iluminación dividiendo cada canal por su fondo estimado.

        El fondo se estima con una dilatación (borra el texto) y un desenfoque
        de mediana grande; la división elimina gradientes y sombras suaves.
        """
        channels = []
        kernel = np.ones((7, 7), np.uint8)
        for channel in cv2.split(bgr):
            background = cv2.dilate(channel, kernel)
            background = cv2.medianBlur(background, 21)
            normalized = cv2.divide(channel, background, scale=255)
            channels.append(normalized)
        return cv2.merge(channels)

    @staticmethod
    def enhance_contrast(bgr: np.ndarray) -> np.ndarray:
        """Corrección adaptativa de contraste (CLAHE) y brillo según luminancia media."""
        lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB)
        l_channel, a_channel, b_channel = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        l_channel = clahe.apply(l_channel)

        # Ajuste de brillo suave hacia una luminancia objetivo (documentos claros).
        mean_luma = float(np.mean(l_channel))
        target = 170.0
        beta = float(np.clip(target - mean_luma, -40, 40)) * 0.5
        l_channel = cv2.convertScaleAbs(l_channel, alpha=1.0, beta=beta)

        return cv2.cvtColor(cv2.merge((l_channel, a_channel, b_channel)), cv2.COLOR_LAB2BGR)

    # ------------------------------------------------------------------ #
    # Utilidades internas
    # ------------------------------------------------------------------ #
    def _validate_extension(self, filename: str) -> None:
        ext = Path(filename or "").suffix.lower().lstrip(".")
        if ext not in self.allowed_extensions:
            allowed = ", ".join(sorted(self.allowed_extensions))
            raise ImageProcessingError(f"Extensión no permitida. Formatos aceptados: {allowed}.")

    def _open_and_verify(self, raw: bytes) -> Image.Image:
        try:
            with Image.open(io.BytesIO(raw)) as probe:
                if probe.format not in self.allowed_formats:
                    raise ImageProcessingError("El contenido del archivo no es JPEG ni PNG.")
                probe.verify()  # detecta ficheros truncados/corruptos
            image = Image.open(io.BytesIO(raw))  # verify() invalida la instancia
            image.load()
            return image
        except ImageProcessingError:
            raise
        except (UnidentifiedImageError, OSError, SyntaxError, Image.DecompressionBombError) as exc:
            raise ImageProcessingError("La imagen está dañada o no es válida.") from exc

    @staticmethod
    def _to_rgb(image: Image.Image) -> Image.Image:
        if image.mode in ("RGBA", "LA", "P"):
            image = image.convert("RGBA")
            background = Image.new("RGB", image.size, (255, 255, 255))
            background.paste(image, mask=image.split()[-1])
            return background
        return image.convert("RGB") if image.mode != "RGB" else image

    @staticmethod
    def _limit_size(image: Image.Image) -> Image.Image:
        if max(image.size) > MAX_SIDE_PX:
            image = image.copy()
            image.thumbnail((MAX_SIDE_PX, MAX_SIDE_PX), Image.Resampling.LANCZOS)
        return image

    def _make_thumbnail(self, image: Image.Image) -> Image.Image:
        thumb = image.copy()
        thumb.thumbnail((self.thumbnail_size, self.thumbnail_size), Image.Resampling.LANCZOS)
        return thumb

    @staticmethod
    def _build_target_name() -> tuple[Path, str]:
        now = datetime.now(timezone.utc)
        relative_dir = Path("images") / f"{now:%Y}" / f"{now:%m}"
        base_name = f"{now:%Y%m%dT%H%M%S}_{uuid.uuid4().hex}"
        return relative_dir, base_name

    def _safe_abs(self, relative: Path) -> Path:
        candidate = (self.upload_root / relative).resolve()
        if self.upload_root not in candidate.parents and candidate != self.upload_root:
            raise ImageProcessingError("Ruta de archivo no válida.")
        return candidate
